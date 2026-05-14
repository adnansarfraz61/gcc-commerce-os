from uuid import UUID

from pydantic import BaseModel


class TokenClaims(BaseModel):
    subject: str
    tenant_id: UUID | None = None
    scopes: list[str] = []
