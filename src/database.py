from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Callable
from concurrent.futures.thread import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from pathlib import Path
import sqlite3
from typing import Any, TypeVar
import uuid

import logfire
from pydantic import NaiveDatetime
from pydantic_ai import ModelMessage, ModelMessagesTypeAdapter
from sqlmodel import Column, Field, JSON, Session, SQLModel, create_engine, select
from typing_extensions import LiteralString, ParamSpec, TypedDict

THIS_DIR = Path(__file__).parent
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


class ConversationModel(SQLModel, table=True):
    __tablename__ = "conversation"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    messages: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: NaiveDatetime = Field(default_factory=datetime.now)
    updated_at: NaiveDatetime = Field(default_factory=datetime.now)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        statement = select(ConversationModel)
        if not session.exec(statement).first():
            conversation = ConversationModel(messages=[])
            session.add(conversation)
            session.commit()


def get_session():
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


P = ParamSpec("P")
R = TypeVar("R")


class Project(TypedDict, total=False):
    id: str
    name: str
    images: int
    progress: int
    status: int
    time_elapsed: int
    imagesCount: int


@dataclass
class Database:
    """非同步/執行緒安全 SQLite 資料庫存取層，管理專案與聊天歷史。"""
    con: sqlite3.Connection
    _loop: asyncio.AbstractEventLoop
    _executor: ThreadPoolExecutor

    @classmethod
    @asynccontextmanager
    async def connect(
        cls, file: Path = THIS_DIR / "database.sqlite"
    ) -> AsyncGenerator[Database]:
        with logfire.span("connect to DB"):
            loop = asyncio.get_running_loop()
            executor = ThreadPoolExecutor(max_workers=1)
            con = await loop.run_in_executor(executor, cls._connect, file)
            slf = cls(con, loop, executor)
        try:
            yield slf
        finally:
            await slf._asyncify(con.close)

    @staticmethod
    def _connect(file: Path) -> sqlite3.Connection:
        con = sqlite3.connect(str(file))
        con = logfire.instrument_sqlite3(con)
        cur = con.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT DEFAULT 'home',
                message_list TEXT
            );
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT,
                images INT,
                progress INT
            );
        """)
        # Migration: ensure project_id column exists
        cur.execute("PRAGMA table_info(messages);")
        columns = [row[1] for row in cur.fetchall()]
        if "project_id" not in columns:
            cur.execute("ALTER TABLE messages ADD COLUMN project_id TEXT DEFAULT 'home';")
        con.commit()
        return con

    async def add_project(self, project: Project) -> None:
        await self._asyncify(
            self._execute,
            "INSERT INTO projects (id, name, images, progress) VALUES (?, ?, ?, ?);",
            project["id"],
            project["name"],
            project["images"],
            project.get("progress", 0),
            commit=True,
        )
        await self._asyncify(self.con.commit)

    async def add_messages(self, messages: bytes, project_id: str = "home") -> None:
        await self._asyncify(
            self._execute,
            "INSERT INTO messages (project_id, message_list) VALUES (?, ?);",
            project_id,
            messages,
            commit=True,
        )
        await self._asyncify(self.con.commit)

    async def get_project(self, task_id: str) -> Project:
        c = await self._asyncify(
            self._execute, "SELECT * FROM projects WHERE id = ?", task_id
        )
        row = await self._asyncify(c.fetchone)
        if not row:
            raise KeyError(f"專案不存在: {task_id}")
        return Project(id=row[0], name=row[1], images=int(row[2]), progress=int(row[3]))

    async def get_projects(self) -> list[Project]:
        c = await self._asyncify(
            self._execute, "SELECT * FROM projects"
        )
        rows = await self._asyncify(c.fetchall)
        projects: list[Project] = []
        for row in rows:
            projects.append(Project(id=row[0], name=row[1], images=int(row[2]), progress=int(row[3])))
        return projects

    async def get_messages(self, project_id: str = "home") -> list[ModelMessage]:
        c = await self._asyncify(
            self._execute, "SELECT message_list FROM messages WHERE project_id = ? ORDER BY id", project_id
        )
        rows = await self._asyncify(c.fetchall)
        messages: list[ModelMessage] = []
        for row in rows:
            messages.extend(ModelMessagesTypeAdapter.validate_json(row[0]))
        return messages

    async def update_project(self, task_id: str, project: dict[str, Any]) -> None:
        images_count = project.get("imagesCount", 0)
        progress = project.get("progress", 0)
        await self._asyncify(
            self._execute,
            "UPDATE projects SET images = ? , progress = ? WHERE id = ?;",
            images_count,
            progress,
            task_id,
            commit=True,
        )
        await self._asyncify(self.con.commit)

    async def delete_project(self, task_id: str) -> None:
        await self._asyncify(
            self._execute,
            "DELETE FROM projects WHERE id = ?;",
            task_id,
            commit=True,
        )
        await self._asyncify(self.con.commit)

    async def delete_messages_by_project(self, project_id: str) -> None:
        await self._asyncify(
            self._execute,
            "DELETE FROM messages WHERE project_id = ?;",
            project_id,
            commit=True,
        )
        await self._asyncify(self.con.commit)

    async def migrate_messages(self, from_project_id: str, to_project_id: str) -> None:
        await self._asyncify(
            self._execute,
            "UPDATE messages SET project_id = ? WHERE project_id = ?;",
            to_project_id,
            from_project_id,
            commit=True,
        )
        await self._asyncify(self.con.commit)

    def _execute(
        self, sql: LiteralString, *args: Any, commit: bool = False
    ) -> sqlite3.Cursor:
        cur = self.con.cursor()
        cur.execute(sql, args)
        if commit:
            self.con.commit()
        return cur

    async def _asyncify(
        self, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs
    ) -> R:
        return await self._loop.run_in_executor(
            self._executor,
            partial(func, **kwargs),
            *args,
        )
