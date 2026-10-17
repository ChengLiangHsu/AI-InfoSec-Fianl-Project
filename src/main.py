from __future__ import annotations as _annotations

import os
from dotenv import load_dotenv

load_dotenv()
import asyncio
import json
import sqlite3
from collections.abc import AsyncGenerator, Callable
from concurrent.futures.thread import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Annotated, Any, Literal, TypeVar

import fastapi
import logfire
import httpx
from fastapi import Depends, Request, File, UploadFile, Form
from fastapi.responses import FileResponse, Response, StreamingResponse
from typing_extensions import LiteralString, ParamSpec, TypedDict
from pydantic import BaseModel
from pydantic_ai import (
    Agent,
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    TextPart,
    UnexpectedModelBehavior,
    UserPromptPart,
)

# 'if-token-present' means nothing will be sent (and the example will work) if you don't have logfire configured
logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_pydantic_ai()

model = os.getenv("PYDANTIC_AI_MODEL", "google:gemini-3.7-flash")
agent = Agent(model)
THIS_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(_app: fastapi.FastAPI):
    async with Database.connect() as db:
        yield {"db": db}


app = fastapi.FastAPI(lifespan=lifespan)
logfire.instrument_fastapi(app)

async def get_db(request: Request) -> Database:
    return request.state.db

@app.get("/chat/")
async def get_chat(database: Database = Depends(get_db)) -> Response:
    msgs = await database.get_messages()
    return Response(
        b"\n".join(json.dumps(to_model_message(m)).encode("utf-8") for m in msgs),
        media_type="text/plain",
    )


class ModelMessageResponse(TypedDict):
    """Format of messages sent to the browser."""

    key: str
    role: "assistant"
    versions: list[Version]


class Version(TypedDict):
    """Format of a message version."""
    id: str
    content: str


def to_model_message(m: ModelMessage) -> ModelMessageResponse:
    first_part = m.parts[0]
    if isinstance(m, ModelRequest):
        if isinstance(first_part, UserPromptPart):
            assert isinstance(first_part.content, str)
            return {
                "role": "user",
                "key": first_part.timestamp.isoformat(),
                "versions": [
                    {
                        "id": "1",
                        "content": first_part.content
                    }
                ]
            }
    elif isinstance(m, ModelResponse):
        if isinstance(first_part, TextPart):
            return {
                "role": "assistant",
                "key": m.timestamp.isoformat(),
                "versions": [
                    {
                        "id": "1",
                        "content": first_part.content
                    }
                ],
            }
    raise UnexpectedModelBehavior(f"Unexpected message type for chat app: {m}")


class PostChatRequest(BaseModel):
    prompt: str


@app.post("/chat")
async def post_chat(
    request: PostChatRequest, database: Database = Depends(get_db)
) -> StreamingResponse:
    async def stream_messages():
        """Streams new line delimited JSON `Message`s to the client."""
        # stream the user prompt so that can be displayed straight away
        yield (
            json.dumps(
                {
                    "role": "user",
                    "key": datetime.now(tz=timezone.utc).isoformat(),
                    "versions": [
                        {
                            "id": "1",
                            "content": request.prompt
                        }
                    ]
                }
            ).encode("utf-8")
            + b"\n"
        )
        # get the chat history so far to pass as context to the agent
        messages = await database.get_messages()
        # run the agent with the user prompt and the chat history
        async with agent.run_stream(request.prompt, message_history=messages) as result:
            async for text in result.stream_output(debounce_by=0.01):
                # text here is a `str` and the frontend wants
                # JSON encoded ModelResponse, so we create one
                m = ModelResponse(parts=[TextPart(text)], timestamp=result.timestamp)
                yield json.dumps(to_model_message(m)).encode("utf-8") + b"\n"

        # add new messages (e.g. the user prompt and the agent response in this case) to the database
        await database.add_messages(result.new_messages_json())

    return StreamingResponse(stream_messages(), media_type="text/plain")


P = ParamSpec("P")
R = TypeVar("R")
class Project(TypedDict):
    id: str
    name: str

@app.post("/odm-task")
async def create_odm_task(name: Annotated[str, Form()], files: list[UploadFile], database: Database = Depends(get_db)):
    odm_files = [
        ("images", (f.filename, await f.read(), f.content_type))
        for f in files
    ]
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post("http://localhost:3000/task/new", files=odm_files)
    project = Project(
        id=r.json()["uuid"],
        name=name
    )
    await database.add_project(project)
    response = {"id": r.json()["uuid"], "name": name}
    return {"result": True, "data": response}

@app.get("/odm-task-info/{task_id}")
async def get_odm_task_info(task_id: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"http://localhost:3000/task/{task_id}/info")
    response = {
        "result": True,
        "data": r.json()
    }
    return response

@app.get("/odm-task-list")
async def get_odm_task_list(database: Database = Depends(get_db)):
    projects = await database.get_projects()
    return {"result": True, "data": projects}


@dataclass
class Database:
    con: sqlite3.Connection
    _loop: asyncio.AbstractEventLoop
    _executor: ThreadPoolExecutor

    @classmethod
    @asynccontextmanager
    async def connect(
        cls, file: Path = THIS_DIR / ".chat_app_messages.sqlite"
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
                id INT PRIMARY KEY,
                message_list TEXT
            );
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT
            );
        """)
        con.commit()
        return con

    async def add_project(self, project: Project):
        await self._asyncify(
            self._execute,
            "INSERT INTO projects (id, name) VALUES (?, ?);",
            project["id"],
            project["name"],
            commit=True,
        )
        await self._asyncify(self.con.commit)

    async def add_messages(self, messages: bytes):
        await self._asyncify(
            self._execute,
            "INSERT INTO messages (message_list) VALUES (?);",
            messages,
            commit=True,
        )
        await self._asyncify(self.con.commit)

    async def get_projects(self) -> list[Project]:
        c = await self._asyncify(
            self._execute, "SELECT id, name FROM projects order by id"
        )
        rows = await self._asyncify(c.fetchall)
        projects: list[Project] = []
        for row in rows:
            projects.append(Project(id=row[0], name=row[1]))
        return projects

    async def get_messages(self) -> list[ModelMessage]:
        c = await self._asyncify(
            self._execute, "SELECT message_list FROM messages order by id"
        )
        rows = await self._asyncify(c.fetchall)
        messages: list[ModelMessage] = []
        for row in rows:
            messages.extend(ModelMessagesTypeAdapter.validate_json(row[0]))
        return messages

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
        return await self._loop.run_in_executor(  # pyright: ignore[reportUnknownVariableType]
            self._executor,
            partial(func, **kwargs),
            *args,  # pyright: ignore[reportCallIssue]
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", app_dir=str(THIS_DIR), reload=True)
