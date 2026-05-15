from enum import StrEnum
from urllib.parse import urlencode

from fastapi import HTTPException, status
from pydantic import BaseModel

from app.core.config import Settings, get_settings


class AmazonAuthorizationRegion(StrEnum):
    NORTH_AMERICA = "north_america"
    EUROPE = "europe"
    FAR_EAST = "far_east"


class AmazonRegionDescriptor(BaseModel):
    key: AmazonAuthorizationRegion
    seller_central_authorize_url: str
    sp_api_endpoint: str
    default_marketplace_id: str


AMAZON_AUTHORIZATION_REGIONS: dict[AmazonAuthorizationRegion, AmazonRegionDescriptor] = {
    AmazonAuthorizationRegion.NORTH_AMERICA: AmazonRegionDescriptor(
        key=AmazonAuthorizationRegion.NORTH_AMERICA,
        seller_central_authorize_url="https://sellercentral.amazon.com/apps/authorize/consent",
        sp_api_endpoint="https://sellingpartnerapi-na.amazon.com",
        default_marketplace_id="ATVPDKIKX0DER",
    ),
    AmazonAuthorizationRegion.EUROPE: AmazonRegionDescriptor(
        key=AmazonAuthorizationRegion.EUROPE,
        seller_central_authorize_url=(
            "https://sellercentral-europe.amazon.com/apps/authorize/consent"
        ),
        sp_api_endpoint="https://sellingpartnerapi-eu.amazon.com",
        default_marketplace_id="A1F83G8C2ARO7P",
    ),
    AmazonAuthorizationRegion.FAR_EAST: AmazonRegionDescriptor(
        key=AmazonAuthorizationRegion.FAR_EAST,
        seller_central_authorize_url=(
            "https://sellercentral-japan.amazon.com/apps/authorize/consent"
        ),
        sp_api_endpoint="https://sellingpartnerapi-fe.amazon.com",
        default_marketplace_id="A1VC38T7YXB528",
    ),
}

REGION_ALIASES = {
    "na": AmazonAuthorizationRegion.NORTH_AMERICA,
    "north-america": AmazonAuthorizationRegion.NORTH_AMERICA,
    "north_america": AmazonAuthorizationRegion.NORTH_AMERICA,
    "us": AmazonAuthorizationRegion.NORTH_AMERICA,
    "eu": AmazonAuthorizationRegion.EUROPE,
    "europe": AmazonAuthorizationRegion.EUROPE,
    "uk": AmazonAuthorizationRegion.EUROPE,
    "fe": AmazonAuthorizationRegion.FAR_EAST,
    "far-east": AmazonAuthorizationRegion.FAR_EAST,
    "far_east": AmazonAuthorizationRegion.FAR_EAST,
    "jp": AmazonAuthorizationRegion.FAR_EAST,
}


def normalize_region(region: str | None) -> AmazonAuthorizationRegion:
    if not region:
        return AmazonAuthorizationRegion.EUROPE
    normalized = region.strip().lower()
    try:
        return REGION_ALIASES[normalized]
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported Amazon authorization region",
        ) from exc


class AmazonSPAPIConfig(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: str
    lwa_auth_url: str
    lwa_token_url: str
    lwa_scopes: str
    default_marketplace_id: str
    oauth_state_ttl_seconds: int
    sp_api_region: str
    sp_api_endpoint: str
    sp_api_application_id: str
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_session_token: str | None = None
    aws_role_arn: str | None = None

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "AmazonSPAPIConfig":
        settings = settings or get_settings()
        return cls(
            client_id=settings.amazon_client_id,
            client_secret=settings.amazon_client_secret,
            redirect_uri=settings.amazon_redirect_uri,
            lwa_auth_url=settings.amazon_lwa_auth_url,
            lwa_token_url=settings.amazon_lwa_token_url,
            lwa_scopes=settings.amazon_lwa_scopes,
            default_marketplace_id=settings.amazon_default_marketplace_id,
            oauth_state_ttl_seconds=settings.oauth_state_expire_minutes * 60,
            sp_api_region=settings.amazon_sp_api_region,
            sp_api_endpoint=settings.amazon_sp_api_endpoint,
            sp_api_application_id=settings.amazon_sp_api_application_id,
            aws_access_key_id=settings.amazon_aws_access_key_id,
            aws_secret_access_key=settings.amazon_aws_secret_access_key,
            aws_session_token=settings.amazon_aws_session_token,
            aws_role_arn=settings.amazon_aws_role_arn,
        )

    def get_region_descriptor(self, region: str | None) -> AmazonRegionDescriptor:
        return AMAZON_AUTHORIZATION_REGIONS[normalize_region(region)]

    def build_seller_central_authorization_url(
        self,
        *,
        state: str,
        region: str | None,
        version: str | None = None,
    ) -> str:
        if not self.sp_api_application_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Amazon SP-API application ID is not configured",
            )

        descriptor = self.get_region_descriptor(region)
        params = {
            "application_id": self.sp_api_application_id,
            "state": state,
        }
        if version:
            params["version"] = version
        return f"{descriptor.seller_central_authorize_url}?{urlencode(params)}"
