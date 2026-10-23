from __future__ import annotations as _annotations

import os
from zipfile import ZipFile
from io import BytesIO
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
import numpy as np
from PIL import Image
try:
    from formulas import lookup_formula, get_algorithm_list, algos, get_camera_filters_for
    from nodeodm_manager import ensure_nodeodm_running
except ImportError:
    from src.formulas import lookup_formula, get_algorithm_list, algos, get_camera_filters_for
    from src.nodeodm_manager import ensure_nodeodm_running
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


@agent.system_prompt
def system_prompt() -> str:
    return (
        "你是無人機田間試驗智慧評估代理人（Agricultural Drone Field Trial Agent）。\n"
        "你的核心專業是協助農業與植保試驗人員，針對高解析度無人機空拍正射影像進行分析、植生指標計算與藥效評估。\n"
        "當使用者詢問任何光譜或植生指標（例如 VARI, GLI, NDVI, EXG, SAVI 等）之公式、定義或適用情境時，"
        "請務必調用 `query_vegetation_index` 工具獲取精確公式與資訊，並結合無人機田間試驗實務進行專業解說。"
    )


@agent.tool_plain
def query_vegetation_index(name_or_keyword: str = "") -> dict:
    """查詢農業無人機植生指標（Vegetation Indices）的數學公式、說明、支援波段與適用情境。

    Args:
        name_or_keyword: 植生指標名稱代碼（如 VARI, GLI, NDVI, EXG, SAVI），或查詢關鍵字（如 'RGB', 'list'）。
    """
    query = (name_or_keyword or "").strip()

    # 1. 精確或大小寫比對
    for k, item in algos.items():
        if k.lower() == query.lower():
            filters = get_camera_filters_for(item["expr"], max_bands=4)
            is_rgb = "RGB" in filters
            return {
                "status": "success",
                "name": k,
                "formula_expr": item.get("expr"),
                "description": str(item.get("help", "無特別描述")),
                "range": item.get("range", [-1, 1]),
                "supported_bands": filters,
                "is_rgb_compatible": is_rgb,
                "note": "適用於一般無人機 RGB 空拍鏡頭" if is_rgb else "需要近紅外光 (NIR) 或多光譜鏡頭"
            }

    # 2. 關鍵字搜尋或清單查詢
    if query.lower() in ["rgb", "list", "all", ""]:
        rgb_list = [
            {"name": a["id"], "expr": a["expr"], "description": str(a.get("help", ""))}
            for a in get_algorithm_list(max_bands=3)
            if "RGB" in a.get("filters", [])
        ]
        return {
            "status": "list",
            "total_rgb_indices": len(rgb_list),
            "recommended_rgb_indices": rgb_list[:8],
            "message": "已列出無人機常見 RGB 植生指標。如需查詢特定指標細節，可指定指標名稱（例如 VARI、GLI）。"
        }

    # 3. 模糊搜尋
    matches = [
        {"name": k, "expr": v["expr"], "description": str(v.get("help", ""))}
        for k, v in algos.items()
        if query.lower() in k.lower() or query.lower() in str(v.get("help", "")).lower()
    ]
    if matches:
        return {
            "status": "matches",
            "matches": matches[:5]
        }

    return {
        "status": "not_found",
        "message": f"未找到名稱為「{query}」的植生指標。常見 RGB 指標包括：VARI, GLI, EXG, vNDVI, MPRI；NIR 多光譜指標包括：NDVI, GNDVI, SAVI, NDRE。"
    }


@asynccontextmanager
async def lifespan(_app: fastapi.FastAPI):
    if not ensure_nodeodm_running():
        raise RuntimeError("NodeODM 啟動失敗，中止後端服務。")
    async with Database.connect() as db:
        yield {"db": db}


app = fastapi.FastAPI(lifespan=lifespan)
logfire.instrument_fastapi(app)

async def get_db(request: Request) -> Database:
    return request.state.db

@app.get("/chat/")
async def get_chat(project_id: str = "home", database: Database = Depends(get_db)) -> Response:
    msgs = await database.get_messages(project_id=project_id)
    serialized = []
    for m in msgs:
        converted = to_model_message(m)
        if converted:
            serialized.append(json.dumps(converted).encode("utf-8"))
    return Response(
        b"\n".join(serialized),
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


def to_model_message(m: ModelMessage) -> ModelMessageResponse | None:
    if isinstance(m, ModelRequest):
        for part in m.parts:
            if isinstance(part, UserPromptPart) and isinstance(part.content, str):
                return {
                    "role": "user",
                    "key": part.timestamp.isoformat(),
                    "versions": [
                        {
                            "id": "1",
                            "content": part.content
                        }
                    ]
                }
        return None
    elif isinstance(m, ModelResponse):
        for part in m.parts:
            if isinstance(part, TextPart):
                return {
                    "role": "assistant",
                    "key": m.timestamp.isoformat(),
                    "versions": [
                        {
                            "id": "1",
                            "content": part.content
                        }
                    ],
                }
        return None
    return None


class PostChatRequest(BaseModel):
    prompt: str
    project_id: str = "home"


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
        # get the chat history for this specific project
        messages = await database.get_messages(project_id=request.project_id)
        # run the agent with the user prompt and the chat history
        async with agent.run_stream(request.prompt, message_history=messages) as result:
            async for text in result.stream_output(debounce_by=0.01):
                # text here is a `str` and the frontend wants
                # JSON encoded ModelResponse, so we create one
                m = ModelResponse(parts=[TextPart(text)], timestamp=result.timestamp)
                yield json.dumps(to_model_message(m)).encode("utf-8") + b"\n"

        # add new messages with project_id to the database
        await database.add_messages(result.new_messages_json(), project_id=request.project_id)

    return StreamingResponse(stream_messages(), media_type="text/plain")


P = ParamSpec("P")
R = TypeVar("R")
class Project(TypedDict):
    id: str
    name: str
    images: int
    status: int
    time_elapsed: int

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
        name=name,
        images=len(files),
        progress=0
    )
    await database.add_project(project)
    response = {"id": r.json()["uuid"], "name": name}
    return {"result": True, "data": response}

@app.get("/odm-task-info/{task_id}")
async def get_odm_task_info(task_id: str, database: Database = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"http://localhost:3000/task/{task_id}/info")
    print(r.json())
    await database.update_project(task_id, r.json())
    project = await database.get_project(task_id)
    response = {
        "result": True,
        "data": project
    }
    return response

@app.get("/odm-task-orthophoto/{task_id}")
async def get_odm_task_orthophoto(task_id: str):
    file_path = THIS_DIR / 'odm' / f"{task_id}.png"
    if file_path.exists():
        return FileResponse(file_path, media_type="image/png")

    async with httpx.AsyncClient() as client:
        r = await client.get(f"http://localhost:3000/task/{task_id}/download/all.zip", timeout=120.0)
    zip_file = r.content
    Image.MAX_IMAGE_PIXELS = None
    with ZipFile(BytesIO(zip_file)) as z:
        with z.open('odm_orthophoto/odm_orthophoto.tif') as target:
            with Image.open(target) as im:
                im.save(file_path, 'PNG')
    return FileResponse(file_path, media_type="image/png")

def generate_spectral_image(input_path: Path, output_path: Path, formula: str = "VARI") -> bool:
    expr, hrange = lookup_formula(formula, "RGB")
    Image.MAX_IMAGE_PIXELS = None
    with Image.open(input_path) as img:
        arr = np.asarray(img, dtype=np.float32) / 255.0

    has_alpha = arr.shape[2] == 4
    if has_alpha:
        alpha = (arr[:, :, 3] * 255).astype(np.uint8)

    b1, b2, b3 = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

    with np.errstate(divide="ignore", invalid="ignore"):
        val = eval(expr, {"sqrt": np.sqrt}, {"b1": b1, "b2": b2, "b3": b3})
        val = np.nan_to_num(val, nan=0.0, posinf=1.0, neginf=-1.0)

    if hrange:
        vmin, vmax = hrange
    else:
        vmin, vmax = -1.0, 1.0

    norm = np.clip((val - vmin) / (vmax - vmin) * 255.0, 0, 255).astype(np.uint8)

    # Red (low) -> Yellow (mid) -> Green (high)
    lut = np.zeros((256, 3), dtype=np.uint8)
    for i in range(256):
        if i < 128:
            lut[i] = [255, int(255 * (i / 128.0)), 0]
        else:
            lut[i] = [int(255 * (1.0 - (i - 128) / 128.0)), 255, 0]

    rgb_colored = lut[norm]

    if has_alpha:
        rgba = np.dstack([rgb_colored, alpha])
        out_img = Image.fromarray(rgba, mode="RGBA")
    else:
        out_img = Image.fromarray(rgb_colored, mode="RGB")

    out_img.save(output_path, "PNG")
    return True

@app.get("/odm-task-formulas")
async def get_odm_task_formulas():
    all_algos = get_algorithm_list(max_bands=3)
    rgb_algos = [
        {
            "id": a["id"],
            "expr": a["expr"],
            "help": str(a.get("help", "")),
            "range": a.get("range", (-1, 1))
        }
        for a in all_algos if "RGB" in a.get("filters", [])
    ]
    return {"result": True, "data": rgb_algos}

@app.get("/odm-task-spectral/{task_id}")
async def get_odm_task_spectral(task_id: str, formula: str = "VARI"):
    """
    取得生成的光譜圖
    """
    spectral_file_path = THIS_DIR / "odm" / f"{task_id}_{formula}.png"
    if spectral_file_path.exists():
        return FileResponse(spectral_file_path, media_type="image/png")

    ortho_file_path = THIS_DIR / "odm" / f"{task_id}.png"
    if not ortho_file_path.exists():
        await get_odm_task_orthophoto(task_id)
        if not ortho_file_path.exists():
            return Response(content="Orthophoto not found", status_code=404)

    try:
        generate_spectral_image(ortho_file_path, spectral_file_path, formula)
    except Exception as e:
        return Response(content=f"Error generating spectral image: {e}", status_code=400)

    return FileResponse(spectral_file_path, media_type="image/png")

@app.get("/odm-task-list")
async def get_odm_task_list(database: Database = Depends(get_db)):
    projects = await database.get_projects()
    return {"result": True, "data": projects}

@app.delete("/odm-task/{task_id}")
async def delete_odm_task(task_id: str, database: Database = Depends(get_db)):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post("http://localhost:3000/task/remove", json={"uuid": task_id})
    except Exception:
        pass
    for f in (THIS_DIR / "odm").glob(f"{task_id}*.png"):
        try:
            f.unlink()
        except Exception:
            pass
    await database.delete_project(task_id)
    await database.delete_messages_by_project(task_id)
    return {"result": True}


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

    async def add_project(self, project: Project):
        await self._asyncify(
            self._execute,
            "INSERT INTO projects (id, name, images, progress) VALUES (?, ?, ?, ?);",
            project["id"],
            project["name"],
            project["images"],
            project["progress"],
            commit=True,
        )
        await self._asyncify(self.con.commit)

    async def add_messages(self, messages: bytes, project_id: str = "home"):
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

    async def update_project(self, task_id: str, project: Project):
        await self._asyncify(
            self._execute,
            "UPDATE projects SET images = ? , progress = ? WHERE id = ?;",
            project["imagesCount"],
            project["progress"],
            task_id,
            commit=True,
        )
        await self._asyncify(self.con.commit)

    async def delete_project(self, task_id: str):
        await self._asyncify(
            self._execute,
            "DELETE FROM projects WHERE id = ?;",
            task_id,
            commit=True,
        )
        await self._asyncify(self.con.commit)

    async def delete_messages_by_project(self, project_id: str):
        await self._asyncify(
            self._execute,
            "DELETE FROM messages WHERE project_id = ?;",
            project_id,
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
        return await self._loop.run_in_executor(  # pyright: ignore[reportUnknownVariableType]
            self._executor,
            partial(func, **kwargs),
            *args,  # pyright: ignore[reportCallIssue]
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", app_dir=str(THIS_DIR), reload=True)
