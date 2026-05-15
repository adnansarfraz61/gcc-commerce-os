from datetime import datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, Field


class AmazonLoginResponse(BaseModel):
    authorization_url: AnyHttpUrl
    state: str
    marketplace_id: str


class AmazonCallbackResponse(BaseModel):
    tenant_id: UUID
    amazon_seller_authorization_id: UUID
    seller_id: str
    marketplace_id: str
    created_at: datetime


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
