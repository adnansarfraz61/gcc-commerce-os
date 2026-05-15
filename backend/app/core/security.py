from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import get_settings


def create_access_token(
    *,
    subject: str,
    tenant_id: UUID | None = None,
    scopes: list[str] | None = None,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    settings = get_settings()
    expires_at = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    claims: dict[str, Any] = {
        "sub": subject,
        "exp": expires_at,
        "iat": datetime.now(UTC),
        "scopes": scopes or [],
    }
    if tenant_id:
        claims["tenant_id"] = str(tenant_id)
    if extra_claims:
        claims.update(extra_claims)
    return jwt.encode(claims, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_oauth_state(
    *,
    tenant_id: UUID,
    provider: str,
    return_path: str | None = None,
    marketplace_id: str | None = None,
    region: str | None = None,
    flow: str | None = None,
) -> str:
    settings = get_settings()
    return create_access_token(
        subject="oauth-state",
        tenant_id=tenant_id,
        expires_delta=timedelta(minutes=settings.oauth_state_expire_minutes),
        extra_claims={
            "provider": provider,
            "return_path": return_path,
            "marketplace_id": marketplace_id,
            "region": region,
            "flow": flow,
        },
    )


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc
