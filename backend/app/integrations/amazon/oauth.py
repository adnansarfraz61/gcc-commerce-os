from datetime import UTC, datetime, timedelta
import logging
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status

from app.integrations.amazon.config import AmazonSPAPIConfig
from app.integrations.amazon.schemas import AmazonRefreshedToken, AmazonTokenResponse

logger = logging.getLogger("app.integrations.amazon.oauth")


class AmazonOAuthClient:
    def __init__(self, config: AmazonSPAPIConfig | None = None) -> None:
        self.config = config or AmazonSPAPIConfig.from_settings()

    def build_authorization_url(self, *, state: str) -> str:
        if not self.config.client_id or not self.config.redirect_uri:
            logger.error("Amazon OAuth login requested with missing client configuration")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Amazon OAuth is not configured",
            )

        params = {
            "client_id": self.config.client_id,
            "scope": self.config.lwa_scopes,
            "response_type": "code",
            "redirect_uri": self.config.redirect_uri,
            "state": state,
        }
        return f"{self.config.lwa_auth_url}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, *, code: str) -> AmazonTokenResponse:
        if not self.config.client_id or not self.config.client_secret:
            logger.error("Amazon token exchange requested with missing client credentials")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Amazon OAuth is not configured",
            )

        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.config.redirect_uri,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }
        token_data = await self._post_token_request(payload)
        return AmazonTokenResponse.model_validate(token_data)

    async def refresh_access_token(self, *, refresh_token: str) -> AmazonRefreshedToken:
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
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
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    self.config.lwa_token_url,
                    data=payload,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
        except httpx.HTTPError as exc:
            logger.exception("Amazon token endpoint request failed")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Amazon token endpoint request failed",
            ) from exc

        try:
            response_payload = response.json()
        except ValueError as exc:
            logger.warning(
                "Amazon token endpoint returned non-JSON response",
                extra={"status_code": response.status_code},
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Amazon token endpoint returned an invalid response",
            ) from exc

        if response.status_code >= 400:
            logger.warning(
                "Amazon token endpoint rejected request",
                extra={
                    "status_code": response.status_code,
                    "amazon_error": response_payload.get("error"),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Amazon token exchange failed",
            )
        return response_payload
