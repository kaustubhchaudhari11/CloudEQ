"""Password gate for a public deployment; local development stays unchanged."""

import base64
import binascii
import secrets

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class AccessSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")
    cloudeq_require_auth: bool = False
    cloudeq_web_username: str = "forge"
    cloudeq_web_password: SecretStr = SecretStr("")


class DeploymentAccess:
    def __init__(self, app: ASGIApp, settings: AccessSettings) -> None:
        self.app = app
        self.settings = settings
        if settings.cloudeq_require_auth and (
            len(settings.cloudeq_web_password.get_secret_value()) < 16
            or not settings.cloudeq_web_username
        ):
            raise ValueError("Public deployment requires a username and a 16-character password.")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.settings.cloudeq_require_auth:
            await self.app(scope, receive, send)
            return
        if scope["path"] == "/health":
            await JSONResponse({"status": "ok", "service": "FORGE SPAN"})(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        try:
            scheme, token = headers.get(b"authorization", b"").split(b" ", 1)
            if scheme.lower() != b"basic":
                raise ValueError
            username, password = base64.b64decode(token, validate=True).split(b":", 1)
            valid = secrets.compare_digest(username, self.settings.cloudeq_web_username.encode())
            valid &= secrets.compare_digest(
                password, self.settings.cloudeq_web_password.get_secret_value().encode()
            )
        except (ValueError, binascii.Error):
            valid = False
        if not valid:
            await JSONResponse(
                {"detail": "Sign in to FORGE SPAN."},
                status_code=401,
                headers={
                    "WWW-Authenticate": 'Basic realm="FORGE SPAN", charset="UTF-8"',
                    "Cache-Control": "no-store",
                },
            )(scope, receive, send)
            return
        if scope["method"] not in {"GET", "HEAD", "OPTIONS"}:
            origin = headers.get(b"origin")
            host = headers.get(b"host", b"")
            if origin and origin not in {b"https://" + host, b"http://" + host}:
                await JSONResponse({"detail": "Origin is not allowed."}, status_code=403)(
                    scope, receive, send
                )
                return
        await self.app(scope, receive, send)
