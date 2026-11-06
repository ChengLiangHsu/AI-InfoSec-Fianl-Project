from fastapi import APIRouter, Request

from src.config import MAX_ACTIVE_TASKS, MAX_IMAGE_BYTES, MAX_IMAGES, MAX_UPLOAD_BYTES, VISITOR_MAX_AGE
from src.presenter.response_wrapper import success_response

router = APIRouter(tags=["system"])


@router.get("/healthz")
def health():
    """回報應用程式存活狀態，不呼叫外部服務。"""
    return {"status": "ok"}


@router.get("/api/session")
def visitor_session(request: Request):
    """前端啟動時先建立身分，再開始並行讀取任務。"""
    return success_response({
        "visitor_id": request.state.owner_id,
        "session_days": VISITOR_MAX_AGE // 86400,
        "limits": {
            "images": MAX_IMAGES, "image_bytes": MAX_IMAGE_BYTES,
            "upload_bytes": MAX_UPLOAD_BYTES, "active_tasks": MAX_ACTIVE_TASKS,
        },
    })
