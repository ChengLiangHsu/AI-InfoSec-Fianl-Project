from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class SuccessResponse(BaseModel):
    """統一成功回應模型。"""

    result: bool = True
    data: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """統一失敗回應模型。"""

    result: bool = False
    message: str


def success_response(
    data: dict[str, Any] | None = None, status_code: int = 200
) -> JSONResponse:

    """產出符合 {"result": true, "data": ...} 規範的 JSONResponse。"""
    content_data = jsonable_encoder(data) if data is not None else {}
    return JSONResponse(
        status_code=status_code,
        content={"result": True, "data": content_data},
    )


def error_response(message: str, status_code: int = 400) -> JSONResponse:
    """產出符合 {"result": false, "message": "..."} 規範的 JSONResponse。"""
    return JSONResponse(
        status_code=status_code,
        content={"result": False, "message": message},
    )
