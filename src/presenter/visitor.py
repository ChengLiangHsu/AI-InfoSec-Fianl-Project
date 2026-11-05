from __future__ import annotations

import asyncio
from urllib.parse import urlsplit

from sqlmodel import Session
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.config import COOKIE_NAME, COOKIE_SECURE, PUBLIC_ORIGIN, VISITOR_MAX_AGE
from src.database import engine
from src.repositories.visitor_repo import VisitorIdentity, resolve_visitor


def _resolve_identity(token: str) -> VisitorIdentity:
    with Session(engine) as session:
        return resolve_visitor(session, token)


def _is_cross_origin_write(request: Request) -> bool:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return False
    if request.headers.get("sec-fetch-site") == "cross-site":
        return True
    origin = request.headers.get("origin")
    if not origin:
        return False
    expected = PUBLIC_ORIGIN or f"{request.url.scheme}://{request.url.netloc}"
    return urlsplit(origin)[:2] != urlsplit(expected)[:2]


def _cookie_header(token: str) -> tuple[bytes, bytes]:
    response = Response()
    response.set_cookie(
        COOKIE_NAME, token, max_age=VISITOR_MAX_AGE, path="/",
        secure=COOKIE_SECURE, httponly=True, samesite="lax",
    )
    return next(header for header in response.raw_headers if header[0] == b"set-cookie")


class VisitorMiddleware:
    """為 API 注入匿名身分，並在串流回應開始前更新 Cookie。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith("/api/"):
            await self.app(scope, receive, send)
            return
        request = Request(scope)
        if _is_cross_origin_write(request):
            response = JSONResponse(
                {"result": False, "message": "不允許跨網站修改資料"}, status_code=403,
            )
            await response(scope, receive, send)
            return
        identity = await asyncio.to_thread(
            _resolve_identity, request.cookies.get(COOKIE_NAME, ""),
        )
        scope.setdefault("state", {})["owner_id"] = identity.owner_id

        async def send_with_identity(message: Message) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = [
                    (key, value) for key, value in message.get("headers", [])
                    if key.lower() != b"cache-control"
                ]
                message["headers"].extend([
                    _cookie_header(identity.token),
                    (b"cache-control", b"private, no-store"),
                ])
            await send(message)

        await self.app(scope, receive, send_with_identity)
