from __future__ import annotations

from urllib.parse import urlsplit

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from src.config import PUBLIC_ORIGIN


def _is_cross_origin_write(request: Request) -> bool:
    """檢查寫入請求是否來自非預期跨站來源。"""
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return False
    if request.headers.get("sec-fetch-site") == "cross-site":
        return True
    origin = request.headers.get("origin")
    if not origin:
        return False
    expected = PUBLIC_ORIGIN or f"{request.url.scheme}://{request.url.netloc}"
    return urlsplit(origin)[:2] != urlsplit(expected)[:2]


class SecurityMiddleware:
    """跨站偽造防護 (CSRF / Origin 檢驗) 中介層：無狀態、不簽發 Cookie。"""

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

        await self.app(scope, receive, send)
