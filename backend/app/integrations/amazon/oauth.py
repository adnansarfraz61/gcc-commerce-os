from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status

from app.integrations.amazon.config import AmazonSPAPIConfig
from app.integrations.amazon.schemas import AmazonRefreshedToken, AmazonTokenResponse


class AmazonOAuthClient:
    def __init__(self, config: AmazonSPAPIConfig | None = None) -> None:
        self.config = config or AmazonSPAPIConfig.from_settings()

    def build_authorization_url(self, *, state: str) -> str:
        params = {
            "client_id": self.config.lwa_client_id,
            "scope": self.config.lwa_scopes,
            "response_type": "code",
            "redirect_uri": self.config.lwa_redirect_uri,
            "state": state,
        }
        return f"{self.config.lwa_auth_url}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, *, code: str) -> AmazonTokenResponse:
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.config.lwa_redirect_uri,
            "client_id": self.config.lwa_client_id,
            "client_secret": self.config.lwa_client_secret,
        }
        token_data = await self._post_token_request(payload)
        return AmazonTokenResponse.model_validate(token_data)

    async def refresh_access_token(self, *, refresh_token: str) -> AmazonRefreshedToken:
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.config.lwa_client_id,
            "client_secret": self.config.lwa_client_secret,
        }
        token_data = await self._post_token_request(payload)
        expires_in = int(token_data.get("expires_in", 3600))
        return AmazonRefreshedToken(
            access_token=token_data["access_token"],
            token_type=token_data.get("token_type", "bearer"),
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
            scope=token_data.get("scope"),
        )

    async def _post_token_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                self.config.lwa_token_url,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "message": "Amazon token exchange failed",
                    "status_code": response.status_code,
                    "response": response.text,
                },
            )
        return response.json()
