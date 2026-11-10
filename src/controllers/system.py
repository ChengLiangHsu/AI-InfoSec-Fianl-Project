from fastapi import APIRouter

from src.config import MAX_ACTIVE_TASKS, MAX_IMAGE_BYTES, MAX_IMAGES, MAX_UPLOAD_BYTES
from src.presenter.response_wrapper import success_response

router = APIRouter(tags=["system"])


@router.get("/healthz")
def health():
    """回報應用程式存活狀態，不呼叫外部服務。"""
    return {"status": "ok"}


@router.get("/api/session")
def visitor_session():
    """前端啟動時取得上傳限制與系統配置。"""
    return success_response({
        "limits": {
            "images": MAX_IMAGES, "image_bytes": MAX_IMAGE_BYTES,
            "upload_bytes": MAX_UPLOAD_BYTES, "active_tasks": MAX_ACTIVE_TASKS,
        },
    })
