from enum import StrEnum
from functools import lru_cache
from typing import Any

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Marketplace(StrEnum):
    AMAZON = "amazon"
    NOON = "noon"
    SHOPIFY = "shopify"
    TIKTOK_SHOP = "tiktok_shop"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "GCC Commerce OS"
    app_env: Environment = Environment.LOCAL
    debug: bool = False
    api_prefix: str = "/api"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://gcc:gcc@postgres:5432/gcc_commerce_os"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    redis_url: str = "redis://redis:6379/0"

    secret_key: str = Field(min_length=16, default="change-me-in-production")
    token_encryption_key: str | None = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    oauth_state_expire_minutes: int = 15

    backend_cors_origins: list[AnyHttpUrl | str] = Field(default_factory=list)

    amazon_client_id: str = ""
    amazon_client_secret: str = ""
    amazon_redirect_uri: str = "http://localhost:8000/api/auth/amazon/callback"
    amazon_lwa_auth_url: str = "https://www.amazon.com/ap/oa"
    amazon_lwa_token_url: str = "https://api.amazon.com/auth/o2/token"
    amazon_lwa_scopes: str = "profile"
    amazon_default_marketplace_id: str = "A2VIGQ35RCS4UG"
    amazon_sp_api_region: str = "eu-west-1"
    amazon_sp_api_endpoint: str = "https://sellingpartnerapi-eu.amazon.com"
    amazon_sp_api_application_id: str = ""
    amazon_aws_access_key_id: str = ""
    amazon_aws_secret_access_key: str = ""
    amazon_aws_session_token: str | None = None
    amazon_aws_role_arn: str | None = None

    noon_client_id: str = ""
    noon_client_secret: str = ""
    shopify_client_id: str = ""
    shopify_client_secret: str = ""
    tiktok_shop_client_id: str = ""
    tiktok_shop_client_secret: str = ""

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, value: Any) -> list[str] | Any:
        if isinstance(value, str) and value and not value.startswith("["):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env == Environment.PRODUCTION


@lru_cache
def get_settings() -> Settings:
    return Settings()
