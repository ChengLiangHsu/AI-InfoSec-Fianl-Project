from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

# 統一使用根目錄下的 database.sqlite
ROOT_DIR = Path(__file__).resolve().parent.parent
SQLITE_FILE = ROOT_DIR / "database.sqlite"
SQLITE_URL = f"sqlite:///{SQLITE_FILE}"

connect_args = {"check_same_thread": False}
engine = create_engine(SQLITE_URL, connect_args=connect_args)


def init_db() -> None:
    """初始化 SQLite 資料表結構。"""
    import src.repositories  # noqa: F401
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """提供 Session 依賴注入生成器。"""
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
