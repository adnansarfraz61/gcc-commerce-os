from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.integrations.amazon.router import router as amazon_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(amazon_router, prefix="/auth/amazon", tags=["amazon-auth"])
