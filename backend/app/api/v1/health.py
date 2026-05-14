from fastapi import APIRouter, Depends, status
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import get_redis
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", status_code=status.HTTP_200_OK)
async def ready(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, str]:
    await db.execute(text("SELECT 1"))
    await redis.ping()
    return {"status": "ready"}
