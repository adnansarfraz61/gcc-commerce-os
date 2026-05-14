from fastapi import Request
from redis.asyncio import Redis


def get_redis_client(redis_url: str) -> Redis:
    return Redis.from_url(redis_url, encoding="utf-8", decode_responses=True)


async def close_redis_client(redis: Redis | None) -> None:
    if redis is not None:
        await redis.aclose()


def get_redis(request: Request) -> Redis:
    return request.app.state.redis
