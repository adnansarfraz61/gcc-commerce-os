from datetime import datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, Field


class AmazonLoginResponse(BaseModel):
    authorization_url: AnyHttpUrl
    state: str


class AmazonCallbackResponse(BaseModel):
    tenant_id: UUID
    seller_authorization_id: UUID
    marketplace: str = "amazon"
    external_seller_id: str
    status: str


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
