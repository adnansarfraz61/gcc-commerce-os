from pydantic import BaseModel

from app.core.config import Settings, get_settings


class AmazonSPAPIConfig(BaseModel):
    lwa_client_id: str
    lwa_client_secret: str
    lwa_redirect_uri: str
    lwa_auth_url: str
    lwa_token_url: str
    lwa_scopes: str
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
            lwa_client_id=settings.amazon_lwa_client_id,
            lwa_client_secret=settings.amazon_lwa_client_secret,
            lwa_redirect_uri=settings.amazon_lwa_redirect_uri,
            lwa_auth_url=settings.amazon_lwa_auth_url,
            lwa_token_url=settings.amazon_lwa_token_url,
            lwa_scopes=settings.amazon_lwa_scopes,
            sp_api_region=settings.amazon_sp_api_region,
            sp_api_endpoint=settings.amazon_sp_api_endpoint,
            sp_api_application_id=settings.amazon_sp_api_application_id,
            aws_access_key_id=settings.amazon_aws_access_key_id,
            aws_secret_access_key=settings.amazon_aws_secret_access_key,
            aws_session_token=settings.amazon_aws_session_token,
            aws_role_arn=settings.amazon_aws_role_arn,
        )
