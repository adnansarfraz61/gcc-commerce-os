from datetime import datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, Field


class AmazonLoginResponse(BaseModel):
    authorization_url: AnyHttpUrl
    state: str
    marketplace_id: str
    region: str | None = None


class AmazonTestLoginResponse(AmazonLoginResponse):
    seller_central_region: str


class AmazonCallbackResponse(BaseModel):
    tenant_id: UUID
    amazon_seller_authorization_id: UUID
    seller_id: str
    marketplace_id: str
    created_at: datetime


class AmazonAuthorizationStatusItem(BaseModel):
    id: UUID
    seller_id: str
    marketplace_id: str
    created_at: datetime
    updated_at: datetime


class AmazonAuthorizationStatusResponse(BaseModel):
    tenant_id: UUID
    connected: bool
    authorizations: list[AmazonAuthorizationStatusItem]


class AmazonTokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int = Field(default=3600, ge=0)
    scope: str | None = None


class AmazonRefreshedToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    scope: str | None = None
