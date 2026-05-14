from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_oauth_state, decode_token
from app.integrations.amazon.oauth import AmazonOAuthClient
from app.integrations.amazon.schemas import AmazonCallbackResponse, AmazonLoginResponse
from app.models.integration import AuthorizationStatus, Marketplace, SellerAuthorization
from app.models.tenant import Tenant
from app.services.auth.crypto import TokenCipher


class AmazonAuthorizationService:
    def __init__(
        self,
        db: AsyncSession,
        oauth_client: AmazonOAuthClient | None = None,
        token_cipher: TokenCipher | None = None,
    ) -> None:
        self.db = db
        self.oauth_client = oauth_client or AmazonOAuthClient()
        self.token_cipher = token_cipher or TokenCipher()

    async def create_login_url(
        self,
        *,
        tenant_id: UUID,
        return_path: str | None = None,
    ) -> AmazonLoginResponse:
        await self._get_active_tenant(tenant_id)
        state = create_oauth_state(
            tenant_id=tenant_id,
            provider=Marketplace.AMAZON.value,
            return_path=return_path,
        )
        return AmazonLoginResponse(
            authorization_url=self.oauth_client.build_authorization_url(state=state),
            state=state,
        )

    async def complete_callback(
        self,
        *,
        state: str,
        code: str,
        selling_partner_id: str | None,
    ) -> AmazonCallbackResponse:
        claims = decode_token(state)
        if claims.get("provider") != Marketplace.AMAZON.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth state provider mismatch",
            )

        tenant_id = UUID(claims["tenant_id"])
        await self._get_active_tenant(tenant_id)

        token_response = await self.oauth_client.exchange_code_for_tokens(code=code)
        if not token_response.refresh_token:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Amazon did not return a refresh token",
            )

        external_seller_id = selling_partner_id or f"amazon:{tenant_id}"
        expires_at = datetime.now(UTC) + timedelta(seconds=token_response.expires_in)
        scopes = token_response.scope.split(" ") if token_response.scope else []

        authorization = await self._upsert_authorization(
            tenant_id=tenant_id,
            external_seller_id=external_seller_id,
            encrypted_refresh_token=self.token_cipher.encrypt(token_response.refresh_token),
            access_token_expires_at=expires_at,
            scopes=scopes,
        )

        return AmazonCallbackResponse(
            tenant_id=tenant_id,
            seller_authorization_id=authorization.id,
            external_seller_id=authorization.external_seller_id,
            status=authorization.status,
        )

    async def refresh_access_token(self, authorization: SellerAuthorization):
        refresh_token = self.token_cipher.decrypt(authorization.encrypted_refresh_token)
        refreshed = await self.oauth_client.refresh_access_token(refresh_token=refresh_token)
        authorization.access_token_expires_at = refreshed.expires_at
        authorization.status = AuthorizationStatus.ACTIVE.value
        await self.db.commit()
        return refreshed

    async def _upsert_authorization(
        self,
        *,
        tenant_id: UUID,
        external_seller_id: str,
        encrypted_refresh_token: str,
        access_token_expires_at: datetime,
        scopes: list[str],
    ) -> SellerAuthorization:
        statement = select(SellerAuthorization).where(
            SellerAuthorization.tenant_id == tenant_id,
            SellerAuthorization.marketplace == Marketplace.AMAZON.value,
            SellerAuthorization.external_seller_id == external_seller_id,
        )
        existing = await self.db.scalar(statement)
        metadata = {"authorization_source": "login_with_amazon"}

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

        await self.db.commit()
        await self.db.refresh(authorization)
        return authorization

    async def _get_active_tenant(self, tenant_id: UUID) -> Tenant:
        tenant = await self.db.get(Tenant, tenant_id)
        if tenant is None or not tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found",
            )
        return tenant
