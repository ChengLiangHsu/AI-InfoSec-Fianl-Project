from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.config import MAX_UPLOAD_BYTES


class BodyLimitMiddleware:
    """在 multipart／JSON 解析前限制實際請求大小，涵蓋分塊傳輸。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        is_upload = scope["path"] == "/api/task/odm-task" and scope["method"] == "POST"
        limit = MAX_UPLOAD_BYTES + 1024 * 1024 if is_upload else 4 * 1024 * 1024
        headers = dict(scope.get("headers", []))
        length = headers.get(b"content-length", b"0")
        if length.isdigit() and int(length) > limit:
            response = JSONResponse({"result": False, "message": "上傳內容超過大小限制"}, status_code=413)
            await response(scope, receive, send)
            return
        total = 0

        async def limited_receive() -> Message:
            nonlocal total
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > limit:
                    raise HTTPException(413, "上傳內容超過大小限制")
            return message

        await self.app(scope, limited_receive, send)
