from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.integrations.amazon.schemas import AmazonCallbackResponse, AmazonLoginResponse
from app.integrations.amazon.service import AmazonAuthorizationService

router = APIRouter()


@router.get("/login", response_model=AmazonLoginResponse)
async def login_with_amazon(
    tenant_id: UUID = Query(..., description="Tenant that owns the seller authorization"),
    return_path: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> AmazonLoginResponse:
    service = AmazonAuthorizationService(db)
    return await service.create_login_url(tenant_id=tenant_id, return_path=return_path)


@router.get("/callback", response_model=AmazonCallbackResponse)
async def amazon_oauth_callback(
    state: str = Query(...),
    code: str | None = Query(default=None),
    spapi_oauth_code: str | None = Query(default=None),
    selling_partner_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> AmazonCallbackResponse:
    authorization_code = spapi_oauth_code or code
    if not authorization_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Amazon authorization code",
        )

    service = AmazonAuthorizationService(db)
    return await service.complete_callback(
        state=state,
        code=authorization_code,
        selling_partner_id=selling_partner_id,
    )
