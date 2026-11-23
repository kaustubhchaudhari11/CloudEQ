"""Password gate for a public deployment; local development stays unchanged."""

import base64
import binascii
import secrets
from importlib import resources
from urllib.parse import parse_qs

from itsdangerous import BadSignature, URLSafeTimedSerializer
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse
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
        self.signer = URLSafeTimedSerializer(
            settings.cloudeq_web_password.get_secret_value(), salt="forge-web-session-v1"
        )
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
        if scope["method"] not in {"GET", "HEAD", "OPTIONS"}:
            origin = headers.get(b"origin")
            host = headers.get(b"host", b"")
            if origin and origin not in {b"https://" + host, b"http://" + host}:
                await JSONResponse({"detail": "Origin is not allowed."}, status_code=403)(
                    scope, receive, send
                )
                return
        if scope["path"] == "/login":
            await self._login(scope, receive, send)
            return
        if scope["path"] == "/logout" and scope["method"] == "POST":
            response = RedirectResponse("/login", status_code=303)
            response.delete_cookie("forge_session", secure=True, httponly=True, samesite="strict")
            await response(scope, receive, send)
            return
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
            cookie = Request(scope).cookies.get("forge_session", "")
            try:
                session = self.signer.loads(cookie, max_age=8 * 3600)
                valid = isinstance(session, dict) and session.get("user") == (
                    self.settings.cloudeq_web_username
                )
            except BadSignature:
                valid = False
        if not valid:
            if scope["method"] == "GET" and b"text/html" in headers.get(b"accept", b""):
                await RedirectResponse("/login", status_code=303)(scope, receive, send)
                return
            await JSONResponse(
                {"detail": "Sign in to FORGE SPAN."},
                status_code=401,
                headers={
                    "WWW-Authenticate": 'Basic realm="FORGE SPAN", charset="UTF-8"',
                    "Cache-Control": "no-store",
                },
            )(scope, receive, send)
            return
        await self.app(scope, receive, send)

    async def _login(self, scope: Scope, receive: Receive, send: Send) -> None:
        error = ""
        if scope["method"] == "POST":
            request = Request(scope, receive)
            body = b""
            async for chunk in request.stream():
                body += chunk
                if len(body) > 4096:
                    await JSONResponse({"detail": "Request too large."}, status_code=413)(
                        scope, receive, send
                    )
                    return
            try:
                fields = parse_qs(body.decode("utf-8"), max_num_fields=8)
                username = fields.get("username", [""])[0]
                password = fields.get("password", [""])[0]
            except (ValueError, UnicodeDecodeError):
                username = password = ""
            valid = secrets.compare_digest(
                username.encode(), self.settings.cloudeq_web_username.encode()
            )
            valid &= secrets.compare_digest(
                password.encode(), self.settings.cloudeq_web_password.get_secret_value().encode()
            )
            if valid:
                token = self.signer.dumps({"user": username, "nonce": secrets.token_hex(16)})
                response = RedirectResponse("/", status_code=303)
                response.set_cookie(
                    "forge_session",
                    token,
                    max_age=8 * 3600,
                    secure=True,
                    httponly=True,
                    samesite="strict",
                )
                response.headers["Cache-Control"] = "no-store"
                await response(scope, receive, send)
                return
            error = "Sign-in failed. Check your username and password."
        elif scope["method"] != "GET":
            await JSONResponse({"detail": "Method not allowed."}, status_code=405)(
                scope, receive, send
            )
            return
        page = resources.files("cloudeq.platform").joinpath("web/login.html").read_text("utf-8")
        await HTMLResponse(
            page.replace("<!--LOGIN_ERROR-->", error),
            status_code=401 if error else 200,
            headers={"Cache-Control": "no-store"},
        )(scope, receive, send)
