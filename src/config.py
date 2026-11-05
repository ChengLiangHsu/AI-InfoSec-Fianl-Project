from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(ROOT_DIR / "database.sqlite")))
ODM_DIR = Path(os.getenv("ODM_DIR", str(ROOT_DIR / "src" / "odm")))
FRONTEND_DIR = ROOT_DIR / "frontend" / "dist"
NODEODM_URL = os.getenv("NODEODM_URL", "http://localhost:3002")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_NAME = "__Host-visitor" if COOKIE_SECURE else "visitor"
VISITOR_MAX_AGE = 30 * 24 * 60 * 60
PUBLIC_ORIGIN = os.getenv("PUBLIC_ORIGIN", "").rstrip("/")
MAX_IMAGES = int(os.getenv("MAX_IMAGES", "100"))
MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", str(25 * 1024 * 1024)))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(1024 * 1024 * 1024)))
MAX_ACTIVE_TASKS = int(os.getenv("MAX_ACTIVE_TASKS", "3"))
MAX_CHAT_REQUESTS_PER_DAY = int(os.getenv("MAX_CHAT_REQUESTS_PER_DAY", "100"))


def prepare_storage() -> None:
    """建立可寫入的資料目錄。"""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ODM_DIR.mkdir(parents=True, exist_ok=True)
