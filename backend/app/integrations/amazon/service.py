from datetime import UTC, datetime, timedelta
import hashlib
import json
import logging
from uuid import UUID

from fastapi import HTTPException, status
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_oauth_state, decode_token
from app.integrations.amazon.config import AmazonSPAPIConfig
from app.integrations.amazon.oauth import AmazonOAuthClient
from app.integrations.amazon.schemas import (
    AmazonAuthorizationStatusItem,
    AmazonAuthorizationStatusResponse,
    AmazonCallbackResponse,
    AmazonLoginResponse,
    AmazonTestLoginResponse,
)
from app.models.integration import (
    AmazonSellerAuthorization,
    AuthorizationStatus,
    Marketplace,
    SellerAuthorization,
)
from app.models.tenant import Tenant
from app.services.auth.crypto import TokenCipher

logger = logging.getLogger("app.integrations.amazon.service")


class AmazonAuthorizationService:
    def __init__(
        self,
        db: AsyncSession,
        redis: Redis | None = None,
        oauth_client: AmazonOAuthClient | None = None,
        token_cipher: TokenCipher | None = None,
    ) -> None:
        self.db = db
        self.redis = redis
        self.config = AmazonSPAPIConfig.from_settings()
        self.oauth_client = oauth_client or AmazonOAuthClient()
        self.token_cipher = token_cipher or TokenCipher()

    async def create_login_url(
        self,
        *,
        tenant_id: UUID,
        marketplace_id: str | None = None,
        return_path: str | None = None,
    ) -> AmazonLoginResponse:
        await self._get_active_tenant(tenant_id)
        resolved_marketplace_id = marketplace_id or self.config.default_marketplace_id
        state = create_oauth_state(
            tenant_id=tenant_id,
            provider=Marketplace.AMAZON.value,
            return_path=return_path,
            marketplace_id=resolved_marketplace_id,
            region=None,
            flow="login_with_amazon",
        )
        await self._store_oauth_state(
            state=state,
            tenant_id=tenant_id,
            marketplace_id=resolved_marketplace_id,
            region=None,
            flow="login_with_amazon",
        )
        logger.info(
            "Generated Amazon OAuth consent URL",
            extra={"tenant_id": str(tenant_id), "marketplace_id": resolved_marketplace_id},
        )
        return AmazonLoginResponse(
            authorization_url=self.oauth_client.build_authorization_url(state=state),
            state=state,
            marketplace_id=resolved_marketplace_id,
        )

    async def create_test_login_url(
        self,
        *,
        tenant_id: UUID,
        region: str | None = None,
        marketplace_id: str | None = None,
        return_path: str | None = None,
        version: str | None = None,
    ) -> AmazonTestLoginResponse:
        await self._get_active_tenant(tenant_id)
        descriptor = self.config.get_region_descriptor(region)
        resolved_marketplace_id = marketplace_id or descriptor.default_marketplace_id
        state = create_oauth_state(
            tenant_id=tenant_id,
            provider=Marketplace.AMAZON.value,
            return_path=return_path,
            marketplace_id=resolved_marketplace_id,
            region=descriptor.key.value,
            flow="seller_central_authorization",
        )
        await self._store_oauth_state(
            state=state,
            tenant_id=tenant_id,
            marketplace_id=resolved_marketplace_id,
            region=descriptor.key.value,
            flow="seller_central_authorization",
        )
        logger.info(
            "Generated Amazon Seller Central authorization URL",
            extra={
                "tenant_id": str(tenant_id),
                "marketplace_id": resolved_marketplace_id,
                "region": descriptor.key.value,
            },
        )
        return AmazonTestLoginResponse(
            authorization_url=self.config.build_seller_central_authorization_url(
                state=state,
                region=descriptor.key.value,
                version=version,
            ),
            state=state,
            marketplace_id=resolved_marketplace_id,
            region=descriptor.key.value,
            seller_central_region=descriptor.key.value,
        )

    async def complete_callback(
        self,
        *,
        state: str,
        code: str,
        seller_id: str | None,
        marketplace_id: str | None,
    ) -> AmazonCallbackResponse:
        claims = decode_token(state)
        if claims.get("provider") != Marketplace.AMAZON.value:
            logger.warning("Amazon OAuth state provider mismatch")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth state provider mismatch",
            )

        try:
            tenant_id = UUID(claims["tenant_id"])
        except (KeyError, ValueError) as exc:
            logger.warning("Amazon OAuth state missing valid tenant identifier")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth state is missing tenant context",
            ) from exc

        stored_state = await self._consume_oauth_state(state)
        self._validate_stored_state(
            stored_state=stored_state,
            claims=claims,
            tenant_id=tenant_id,
        )
        await self._get_active_tenant(tenant_id)
        resolved_marketplace_id = (
            marketplace_id
            or claims.get("marketplace_id")
            or self.config.default_marketplace_id
        )
        if marketplace_id and marketplace_id != stored_state.get("marketplace_id"):
            logger.warning("Amazon OAuth callback marketplace mismatch")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth callback marketplace mismatch",
            )

        if not seller_id:
            logger.warning(
                "Amazon OAuth callback missing seller identifier",
                extra={"tenant_id": str(tenant_id), "marketplace_id": resolved_marketplace_id},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Amazon seller identifier",
            )

        token_response = await self.oauth_client.exchange_code_for_tokens(code=code)
        if not token_response.refresh_token:
            logger.warning(
                "Amazon token response did not include refresh token",
                extra={"tenant_id": str(tenant_id), "seller_id": seller_id},
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Amazon did not return a refresh token",
            )

        expires_at = datetime.now(UTC) + timedelta(seconds=token_response.expires_in)
        scopes = token_response.scope.split(" ") if token_response.scope else []

        encrypted_refresh_token = self.token_cipher.encrypt(token_response.refresh_token)
        try:
            await self._upsert_generic_authorization(
                tenant_id=tenant_id,
                external_seller_id=seller_id,
                encrypted_refresh_token=encrypted_refresh_token,
                access_token_expires_at=expires_at,
                scopes=scopes,
                marketplace_id=resolved_marketplace_id,
            )
            amazon_authorization = await self._upsert_amazon_authorization(
                tenant_id=tenant_id,
                seller_id=seller_id,
                marketplace_id=resolved_marketplace_id,
                encrypted_refresh_token=encrypted_refresh_token,
            )
            await self.db.commit()
            await self.db.refresh(amazon_authorization)
        except SQLAlchemyError as exc:
            await self.db.rollback()
            logger.exception(
                "Failed to store Amazon seller authorization",
                extra={"tenant_id": str(tenant_id), "seller_id": seller_id},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store Amazon seller authorization",
            ) from exc

        logger.info(
            "Stored Amazon seller authorization",
            extra={
                "tenant_id": str(tenant_id),
                "seller_id": seller_id,
                "marketplace_id": resolved_marketplace_id,
            },
        )

        return AmazonCallbackResponse(
            tenant_id=tenant_id,
            amazon_seller_authorization_id=amazon_authorization.id,
            seller_id=amazon_authorization.seller_id,
            marketplace_id=amazon_authorization.marketplace_id,
            created_at=amazon_authorization.created_at,
        )

    async def get_status(self, *, tenant_id: UUID) -> AmazonAuthorizationStatusResponse:
        await self._get_active_tenant(tenant_id)
        statement = (
            select(AmazonSellerAuthorization)
            .where(AmazonSellerAuthorization.tenant_id == tenant_id)
            .order_by(AmazonSellerAuthorization.created_at.desc())
        )
        authorizations = (await self.db.scalars(statement)).all()
        return AmazonAuthorizationStatusResponse(
            tenant_id=tenant_id,
            connected=bool(authorizations),
            authorizations=[
                AmazonAuthorizationStatusItem(
                    id=authorization.id,
                    seller_id=authorization.seller_id,
                    marketplace_id=authorization.marketplace_id,
                    created_at=authorization.created_at,
                    updated_at=authorization.updated_at,
                )
                for authorization in authorizations
            ],
        )

    async def refresh_access_token(self, authorization: SellerAuthorization):
        refresh_token = self.token_cipher.decrypt(authorization.encrypted_refresh_token)
        refreshed = await self.oauth_client.refresh_access_token(refresh_token=refresh_token)
        authorization.access_token_expires_at = refreshed.expires_at
        authorization.status = AuthorizationStatus.ACTIVE.value
        await self.db.commit()
        return refreshed

    async def _upsert_generic_authorization(
        self,
        *,
        tenant_id: UUID,
        external_seller_id: str,
        encrypted_refresh_token: str,
        access_token_expires_at: datetime,
        scopes: list[str],
        marketplace_id: str,
    ) -> SellerAuthorization:
        statement = select(SellerAuthorization).where(
            SellerAuthorization.tenant_id == tenant_id,
            SellerAuthorization.marketplace == Marketplace.AMAZON.value,
            SellerAuthorization.external_seller_id == external_seller_id,
        )
        existing = await self.db.scalar(statement)
        metadata = {
            "authorization_source": "login_with_amazon",
            "marketplace_id": marketplace_id,
        }

        if existing:
            existing.encrypted_refresh_token = encrypted_refresh_token
            existing.access_token_expires_at = access_token_expires_at
            existing.scopes = scopes
            existing.marketplace_metadata = metadata
            existing.status = AuthorizationStatus.ACTIVE.value
            authorization = existing
        else:
            authorization = SellerAuthorization(
                tenant_id=tenant_id,
                marketplace=Marketplace.AMAZON.value,
                external_seller_id=external_seller_id,
                status=AuthorizationStatus.ACTIVE.value,
                encrypted_refresh_token=encrypted_refresh_token,
                access_token_expires_at=access_token_expires_at,
                scopes=scopes,
                marketplace_metadata=metadata,
            )
            self.db.add(authorization)

        await self.db.flush()
        return authorization

    async def _upsert_amazon_authorization(
        self,
        *,
        tenant_id: UUID,
        seller_id: str,
        marketplace_id: str,
        encrypted_refresh_token: str,
    ) -> AmazonSellerAuthorization:
        statement = select(AmazonSellerAuthorization).where(
            AmazonSellerAuthorization.tenant_id == tenant_id,
            AmazonSellerAuthorization.seller_id == seller_id,
            AmazonSellerAuthorization.marketplace_id == marketplace_id,
        )
        existing = await self.db.scalar(statement)

        if existing:
            existing.encrypted_refresh_token = encrypted_refresh_token
            authorization = existing
        else:
            authorization = AmazonSellerAuthorization(
                tenant_id=tenant_id,
                seller_id=seller_id,
                marketplace_id=marketplace_id,
                encrypted_refresh_token=encrypted_refresh_token,
            )
            self.db.add(authorization)

        await self.db.flush()
        return authorization

    async def _get_active_tenant(self, tenant_id: UUID) -> Tenant:
        tenant = await self.db.get(Tenant, tenant_id)
        if tenant is None or not tenant.is_active:
            logger.warning("Amazon OAuth requested for unknown or inactive tenant")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found",
            )
        return tenant

    async def _store_oauth_state(
        self,
        *,
        state: str,
        tenant_id: UUID,
        marketplace_id: str,
        region: str | None,
        flow: str,
    ) -> None:
        if self.redis is None:
            logger.error("Amazon OAuth state store is not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Amazon OAuth state store is not configured",
            )

        payload = {
            "tenant_id": str(tenant_id),
            "marketplace_id": marketplace_id,
            "region": region,
            "flow": flow,
            "created_at": datetime.now(UTC).isoformat(),
        }
        try:
            await self.redis.set(
                self._state_key(state),
                json.dumps(payload),
                ex=self.config.oauth_state_ttl_seconds,
            )
        except RedisError as exc:
            logger.exception("Failed to store Amazon OAuth state")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Amazon OAuth state store is unavailable",
            ) from exc

    async def _consume_oauth_state(self, state: str) -> dict:
        if self.redis is None:
            logger.error("Amazon OAuth state store is not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Amazon OAuth state store is not configured",
            )

        key = self._state_key(state)
        try:
            payload = await self.redis.get(key)
            if payload:
                await self.redis.delete(key)
        except RedisError as exc:
            logger.exception("Failed to consume Amazon OAuth state")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Amazon OAuth state store is unavailable",
            ) from exc

        if not payload:
            logger.warning("Amazon OAuth callback state is missing or expired")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OAuth state",
            )

        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            logger.warning("Amazon OAuth state payload is invalid")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OAuth state",
            ) from exc

    def _validate_stored_state(
        self,
        *,
        stored_state: dict,
        claims: dict,
        tenant_id: UUID,
    ) -> None:
        expected_tenant_id = stored_state.get("tenant_id")
        expected_marketplace_id = stored_state.get("marketplace_id")
        if expected_tenant_id != str(tenant_id):
            logger.warning("Amazon OAuth state tenant mismatch")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth state tenant mismatch",
            )
        if expected_marketplace_id != claims.get("marketplace_id"):
            logger.warning("Amazon OAuth state marketplace mismatch")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth state marketplace mismatch",
            )
        if stored_state.get("flow") != claims.get("flow"):
            logger.warning("Amazon OAuth state flow mismatch")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth state flow mismatch",
            )

    def _state_key(self, state: str) -> str:
        state_hash = hashlib.sha256(state.encode("utf-8")).hexdigest()
        return f"amazon:oauth_state:{state_hash}"
