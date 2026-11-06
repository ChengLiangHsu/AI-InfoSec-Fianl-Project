from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from src.config import FRONTEND_DIR


def mount_frontend(app: FastAPI) -> None:
    """將建置成果掛在路由清單末端，API 仍保有自己的狀態碼。"""
    if (FRONTEND_DIR / "index.html").is_file():
        app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
