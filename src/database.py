from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from src.config import DATABASE_PATH, prepare_storage

# 統一使用根目錄下的 database.sqlite
SQLITE_FILE = DATABASE_PATH
SQLITE_URL = f"sqlite:///{SQLITE_FILE}"

connect_args = {"check_same_thread": False, "timeout": 30}
engine = create_engine(SQLITE_URL, connect_args=connect_args)


def init_db() -> None:
    """初始化 SQLite 資料表結構。"""
    import src.repositories  # noqa: F401
    from src.repositories import quota_repo  # noqa: F401

    prepare_storage()
    _migrate_task_scenario()
    SQLModel.metadata.create_all(engine)


def _migrate_task_scenario() -> None:
    """為舊資料庫增量加上情境特徵欄位；無縫相容既有任務。"""
    with engine.begin() as connection:
        inspector = inspect(connection)
        if not inspector.has_table("tasks"):
            return
        names = {column["name"] for column in inspector.get_columns("tasks")}
        if "scenario" not in names:
            connection.execute(text("ALTER TABLE tasks ADD COLUMN scenario TEXT DEFAULT ''"))


def get_session() -> Generator[Session]:
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
