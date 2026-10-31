from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
import httpx
from starlette.exceptions import HTTPException as StarletteHTTPException

from .response_wrapper import error_response


def register_error_handlers(app: FastAPI) -> None:
    """向 FastAPI 應用註冊全域例外攔截器。

    將 Python 原生例外 (LookupError, ValueError, RuntimeError) 與外部服務例外 (httpx.HTTPError)
    轉譯為語意化 HTTP 狀態碼，並一律封裝成 {"result": false, "message": "..."} 格式。
    """

    @app.exception_handler(LookupError)
    @app.exception_handler(KeyError)
    async def handle_not_found(request: Request, exc: Exception) -> Any:
        msg = str(exc.args[0]) if getattr(exc, "args", None) else (str(exc) or "找不到請求的資源")
        return error_response(message=msg, status_code=404)

    @app.exception_handler(ValueError)
    async def handle_value_error(request: Request, exc: ValueError) -> Any:
        return error_response(message=str(exc), status_code=400)

    @app.exception_handler(RuntimeError)
    async def handle_runtime_error(request: Request, exc: RuntimeError) -> Any:
        return error_response(message=str(exc), status_code=409)

    @app.exception_handler(httpx.HTTPStatusError)
    async def handle_httpx_status_error(
        request: Request, exc: httpx.HTTPStatusError
    ) -> Any:
        status_code = exc.response.status_code
        http_code = 404 if status_code == 404 else (502 if status_code >= 500 else 400)
        detail = exc.response.text.strip() if exc.response.text else str(exc)
        return error_response(
            message=f"NodeODM 服務回應錯誤 [{status_code}]: {detail}",
            status_code=http_code,
        )

    @app.exception_handler(httpx.RequestError)
    async def handle_httpx_request_error(
        request: Request, exc: httpx.RequestError
    ) -> Any:
        return error_response(
            message=f"NodeODM 服務通訊失敗: {exc}",
            status_code=503,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> Any:
        errors = exc.errors()
        first_err = errors[0] if errors else {}
        loc = " -> ".join(str(l) for l in first_err.get("loc", []))
        msg = first_err.get("msg", "輸入資料驗證失敗")
        error_msg = f"欄位驗證錯誤 [{loc}]: {msg}"
        return error_response(message=error_msg, status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> Any:
        return error_response(message=str(exc.detail), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def handle_general_exception(request: Request, exc: Exception) -> Any:
        return error_response(message="伺服器內部發生非預期錯誤", status_code=500)
