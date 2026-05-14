from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from app.core.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


class Principal(BaseModel):
    subject: str
    tenant_id: UUID | None = None
    scopes: list[str] = []


async def get_current_principal(token: str = Depends(oauth2_scheme)) -> Principal:
    claims = decode_token(token)
    subject = claims.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject is missing",
        )

    tenant_id = claims.get("tenant_id")
    return Principal(
        subject=subject,
        tenant_id=UUID(tenant_id) if tenant_id else None,
        scopes=claims.get("scopes", []),
    )
