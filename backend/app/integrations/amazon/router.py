from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import get_redis
from app.db.session import get_db
from app.integrations.amazon.schemas import (
    AmazonAuthorizationStatusResponse,
    AmazonCallbackResponse,
    AmazonLoginResponse,
    AmazonTestLoginResponse,
)
from app.integrations.amazon.service import AmazonAuthorizationService

router = APIRouter()


@router.get("/login", response_model=AmazonLoginResponse)
async def login_with_amazon(
    tenant_id: UUID = Query(..., description="Tenant that owns the seller authorization"),
    marketplace_id: str | None = Query(default=None, description="Amazon marketplace ID"),
    return_path: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> AmazonLoginResponse:
    service = AmazonAuthorizationService(db, redis=redis)
    return await service.create_login_url(
        tenant_id=tenant_id,
        marketplace_id=marketplace_id,
        return_path=return_path,
    )


@router.get("/test-login", response_model=AmazonTestLoginResponse)
async def test_login_with_amazon(
    tenant_id: UUID = Query(..., description="Tenant that owns the seller authorization"),
    region: str = Query(default="europe", description="north_america, europe, or far_east"),
    marketplace_id: str | None = Query(default=None, description="Amazon marketplace ID"),
    return_path: str | None = Query(default=None),
    version: str | None = Query(default=None, description="Optional Seller Central app version"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> AmazonTestLoginResponse:
    service = AmazonAuthorizationService(db, redis=redis)
    return await service.create_test_login_url(
        tenant_id=tenant_id,
        region=region,
        marketplace_id=marketplace_id,
        return_path=return_path,
        version=version,
    )


@router.get("/callback", response_model=AmazonCallbackResponse)
async def amazon_oauth_callback(
    state: str = Query(...),
    code: str | None = Query(default=None),
    spapi_oauth_code: str | None = Query(default=None),
    seller_id: str | None = Query(default=None),
    selling_partner_id: str | None = Query(default=None),
    marketplace_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> AmazonCallbackResponse:
    authorization_code = spapi_oauth_code or code
    if not authorization_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Amazon authorization code",
        )

    service = AmazonAuthorizationService(db, redis=redis)
    return await service.complete_callback(
        state=state,
        code=authorization_code,
        seller_id=seller_id or selling_partner_id,
        marketplace_id=marketplace_id,
    )


@router.get("/status", response_model=AmazonAuthorizationStatusResponse)
async def amazon_authorization_status(
    tenant_id: UUID = Query(..., description="Tenant to inspect"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> AmazonAuthorizationStatusResponse:
    service = AmazonAuthorizationService(db, redis=redis)
    return await service.get_status(tenant_id=tenant_id)
