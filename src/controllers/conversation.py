from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
import json
from typing import Literal

from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pydantic_ai import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from typing_extensions import TypedDict

from src.agents import ChatDeps, agent
from src.controllers.dependencies import get_db
from src.database import Database

router = APIRouter(tags=["conversation"])


class Version(TypedDict):
    """Format of a message version."""
    id: str
    content: str


class ModelMessageResponse(TypedDict):
    """Format of messages sent to the browser."""
    key: str
    role: Literal["user", "assistant"]
    versions: list[Version]


class MigrateChatRequest(BaseModel):
    from_project_id: str = "home"
    to_project_id: str


class PostChatRequest(BaseModel):
    prompt: str
    project_id: str = "home"


def to_model_message(m: ModelMessage) -> ModelMessageResponse | None:
    """將 Pydantic AI 的 ModelMessage 轉為前端畫布規範的訊息格式。"""
    if isinstance(m, ModelRequest):
        for part in m.parts:
            if isinstance(part, UserPromptPart) and isinstance(part.content, str):
                return {
                    "role": "user",
                    "key": part.timestamp.isoformat(),
                    "versions": [{"id": "1", "content": part.content}],
                }
        return None
    if isinstance(m, ModelResponse):
        for part in m.parts:
            if isinstance(part, TextPart):
                return {
                    "role": "assistant",
                    "key": m.timestamp.isoformat(),
                    "versions": [{"id": "1", "content": part.content}],
                }
        return None
    return None


def _format_initial_user_event(prompt: str) -> bytes:
    """包裝並回傳即時回顯給前端的使用者提問 JSON 事件。"""
    payload = {
        "role": "user",
        "key": datetime.now(tz=timezone.utc).isoformat(),
        "versions": [{"id": "1", "content": prompt}],
    }
    return json.dumps(payload).encode("utf-8") + b"\n"


async def stream_agent_dialogue(
    prompt: str, project_id: str, database: Database
) -> AsyncGenerator[bytes, None]:
    """調度 Agent 串流回應並即時寫入資料庫的非同步生成器。"""
    yield _format_initial_user_event(prompt)

    messages = await database.get_messages(project_id=project_id)
    deps = ChatDeps(project_id=project_id, database=database)

    async with agent.run_stream(prompt, message_history=messages, deps=deps) as result:
        async for text in result.stream_output(debounce_by=0.01):
            m = ModelResponse(parts=[TextPart(text)], timestamp=result.timestamp)
            converted = to_model_message(m)
            if converted:
                yield json.dumps(converted).encode("utf-8") + b"\n"

    await database.add_messages(result.new_messages_json(), project_id=project_id)


@router.get("/chat")
@router.get("/chat/")
async def get_chat(
    project_id: str = "home", database: Database = Depends(get_db)
) -> Response:
    """取得指定專案的歷史對話訊息。"""
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


@router.delete("/chat")
@router.delete("/chat/")
async def delete_chat(project_id: str = "home", database: Database = Depends(get_db)):
    """清除指定專案的對話歷史。"""
    await database.delete_messages_by_project(project_id)
    return {"result": True}


@router.post("/chat/migrate")
@router.post("/chat/migrate/")
async def migrate_chat(
    request: MigrateChatRequest, database: Database = Depends(get_db)
):
    """將臨時專案 (如 home) 的對話遷移至指定專案 ID。"""
    await database.migrate_messages(request.from_project_id, request.to_project_id)
    return {"result": True}


@router.post("/chat")
async def post_chat(
    request: PostChatRequest, database: Database = Depends(get_db)
) -> StreamingResponse:
    """接收使用者提問並啟動 Pydantic AI Agent 串流回應。"""
    stream = stream_agent_dialogue(request.prompt, request.project_id, database)
    return StreamingResponse(stream, media_type="text/plain")
