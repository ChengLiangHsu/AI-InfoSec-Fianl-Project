from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from pydantic_ai import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from typing_extensions import TypedDict

from src.agents import ChatDeps, agent
from src.controllers.dependencies import (
    get_odm_requester,
    get_task_repo,
    get_task_usecase,
)
from src.entities.task import Task
from src.usecases.ports.odm import OdmPort
from src.usecases.ports.task import TaskPort
from src.usecases.task import TaskUseCase
from src.utility.formulas import get_algorithm_list
from src.utility.imagery import extract_orthophoto_from_zip
from src.utility.spectral import generate_spectral_image

SRC_DIR = Path(__file__).resolve().parents[1]
ODM_DIR = SRC_DIR / "odm"
ODM_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(tags=["task"])


# ============================================================================
# 型別宣告 (Types & Schemas)
# ============================================================================

class Version(TypedDict):
    """前端畫布對話版本訊息規格。"""
    id: str
    content: str


class ModelMessageResponse(TypedDict):
    """前端串流渲染規範訊息物件。"""
    key: str
    role: Literal["user", "assistant"]
    versions: list[Version]


class MigrateChatRequest(BaseModel):
    from_project_id: str = "home"
    to_project_id: str


class PostChatRequest(BaseModel):
    prompt: str
    project_id: str = "home"


# ============================================================================
# 內部輔助與序列化子函式 (Helpers & Serializers)
# ============================================================================

def _task_to_dict(task: Task) -> dict[str, Any]:
    """將 Task 實體序列化為符合前端專案結構之字典。"""
    return {
        "id": task.id,
        "name": task.name,
        "images": task.images,
        "progress": task.progress,
        "plots": [asdict(p) for p in task.plots],
    }


def _format_sse_data(payload: dict[str, Any]) -> bytes:
    """將字典資料包裝為標準 Server-Sent Events (SSE) 二進位資料。"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


def _is_task_finished(progress: int, status_code: int | None) -> bool:
    """判斷 NodeODM 任務是否已完成或終止（成功、失敗或取消）。"""
    if progress >= 100:
        return True
    return status_code in (30, 40, 50)


async def _extract_upload_payload(
    files: list[UploadFile],
) -> list[tuple[str, bytes, str]]:
    """自 FastAPI UploadFile 清單提煉純 Python 上傳位元組清單。"""
    payload = []
    for f in files:
        content = await f.read()
        payload.append((f.filename or "image.jpg", content, f.content_type or "image/jpeg"))
    return payload


async def _ensure_orthophoto_cached(
    task_id: str, odm_requester: OdmPort
) -> Path | None:
    """確保正射圖 PNG 檔案已於本機快取；若無則向 NodeODM 下載資產並轉換。"""
    file_path = ODM_DIR / f"{task_id}.png"
    if file_path.exists():
        return file_path
    try:
        zip_bytes = await odm_requester.download_task_assets(task_id, asset="all.zip")
        success = extract_orthophoto_from_zip(zip_bytes, file_path)
        if success and file_path.exists():
            return file_path
    except Exception:
        pass
    return None


async def _generate_spectral_cached(
    task_id: str, formula: str, odm_requester: OdmPort
) -> Path | None:
    """依據指定指標（如 VARI）產出光譜熱圖 PNG，必要時先載入原始正射圖。"""
    formula_upper = formula.strip().upper()
    spectral_file_path = ODM_DIR / f"{task_id}_{formula_upper}.png"
    if spectral_file_path.exists():
        return spectral_file_path

    ortho_path = await _ensure_orthophoto_cached(task_id, odm_requester)
    if not ortho_path or not ortho_path.exists():
        return None

    generate_spectral_image(ortho_path, spectral_file_path, formula_upper)
    return spectral_file_path if spectral_file_path.exists() else None


async def _cleanup_task_assets(
    task_id: str, usecase: TaskUseCase, odm_requester: OdmPort
) -> None:
    """調度 NodeODM 遠端任務移除、本機影像暫存清除與資料庫任務刪除。"""
    try:
        await odm_requester.remove_task(task_id)
    except Exception:
        pass

    for f in ODM_DIR.glob(f"{task_id}*.png"):
        try:
            f.unlink()
        except Exception:
            pass

    await usecase.delete_task(task_id)


def _to_model_message_response(m: ModelMessage) -> ModelMessageResponse | None:
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
    return json.dumps(payload, ensure_ascii=False).encode("utf-8") + b"\n"


async def _stream_agent_dialogue(
    prompt: str,
    project_id: str,
    usecase: TaskUseCase,
    task_port: TaskPort,
) -> AsyncGenerator[bytes, None]:
    """調度 Pydantic AI 串流對話，依據任務生命週期決定是否持久化歷史訊息。"""
    yield _format_initial_user_event(prompt)

    is_task_scoped = bool(project_id and project_id != "home")
    messages = await usecase.get_messages(project_id) if is_task_scoped else []
    deps = ChatDeps(project_id=project_id, task_port=task_port)

    async with agent.run_stream(prompt, message_history=messages, deps=deps) as result:
        async for text in result.stream_output(debounce_by=0.01):
            m = ModelResponse(parts=[TextPart(text)], timestamp=result.timestamp)
            converted = _to_model_message_response(m)
            if converted:
                yield json.dumps(converted, ensure_ascii=False).encode("utf-8") + b"\n"

    if is_task_scoped:
        await usecase.append_messages(project_id, result.new_messages_json())


async def _generate_task_progress_events(
    task_id: str,
    request: Request,
    usecase: TaskUseCase,
    odm_requester: OdmPort,
) -> AsyncGenerator[bytes, None]:
    """輪詢 NodeODM 並即時向客戶端推播 SSE 任務進度事件。"""
    try:
        task = await usecase.get_task(task_id)
    except KeyError:
        yield _format_sse_data({"error": f"Task not found: {task_id}"})
        return

    # 連線首刻主動同步最新狀態並立即推播
    code = None
    try:
        info = await odm_requester.get_task_info(task_id)
        progress = int(info.get("progress", 0))
        code = info.get("status", {}).get("code")
        task = await usecase.update_task_progress(task_id, progress=progress)
    except Exception:
        pass

    last_emitted_progress = task.progress
    yield _format_sse_data(_task_to_dict(task))

    if _is_task_finished(last_emitted_progress, code):
        return

    while True:
        if await request.is_disconnected():
            break
        await asyncio.sleep(1.0)

        try:
            info = await odm_requester.get_task_info(task_id)
            progress = int(info.get("progress", 0))
            code = info.get("status", {}).get("code")
            task = await usecase.update_task_progress(task_id, progress=progress)
        except Exception:
            break

        if task.progress != last_emitted_progress or _is_task_finished(task.progress, code):
            last_emitted_progress = task.progress
            yield _format_sse_data(_task_to_dict(task))

        if _is_task_finished(task.progress, code):
            break


# ============================================================================
# 控制器主流程調度端點 (Task Router Orchestrator Endpoints)
# ============================================================================

@router.post("/odm-task")
async def create_odm_task(
    name: Annotated[str, Form()],
    files: list[UploadFile] = File(...),
    usecase: TaskUseCase = Depends(get_task_usecase),
    odm_requester: OdmPort = Depends(get_odm_requester),
) -> dict[str, Any]:
    """主流程：接收空拍相片、派送 NodeODM 拼圖並持久化建立任務。"""
    files_payload = await _extract_upload_payload(files)
    uuid_str = await odm_requester.create_task(files=files_payload, name=name)
    await usecase.create_task(id=uuid_str, name=name, images=len(files))
    return {"result": True, "data": {"id": uuid_str, "name": name}}


@router.get("/odm-task-info/{task_id}")
async def get_odm_task_info(
    task_id: str,
    usecase: TaskUseCase = Depends(get_task_usecase),
    odm_requester: OdmPort = Depends(get_odm_requester),
) -> dict[str, Any]:
    """主流程：查詢任務最新進度、同步持久化並回傳任務資訊。"""
    try:
        info = await odm_requester.get_task_info(task_id)
        progress = int(info.get("progress", 0))
        task = await usecase.update_task_progress(task_id, progress=progress)
    except Exception:
        task = await usecase.get_task(task_id)
    return {"result": True, "data": _task_to_dict(task)}


@router.get("/odm-task-stream/{task_id}")
async def stream_odm_task_progress(
    task_id: str,
    request: Request,
    usecase: TaskUseCase = Depends(get_task_usecase),
    odm_requester: OdmPort = Depends(get_odm_requester),
) -> StreamingResponse:
    """主流程：建立 Server-Sent Events (SSE) 串流推播任務進度。"""
    stream = _generate_task_progress_events(task_id, request, usecase, odm_requester)
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/odm-task-orthophoto/{task_id}")
async def get_odm_task_orthophoto(
    task_id: str,
    odm_requester: OdmPort = Depends(get_odm_requester),
) -> Response:
    """主流程：取得航拍正射圖成果（必要時自 NodeODM 下載轉換）。"""
    file_path = await _ensure_orthophoto_cached(task_id, odm_requester)
    if not file_path:
        return Response(content="Orthophoto not found", status_code=404)
    return FileResponse(file_path, media_type="image/png")


@router.get("/odm-task-formulas")
async def get_odm_task_formulas() -> dict[str, Any]:
    """主流程：查詢系統目前支援之 RGB 植生指標算式清單。"""
    all_algos = get_algorithm_list(max_bands=3)
    rgb_algos = [
        {
            "id": a["id"],
            "expr": a["expr"],
            "help": str(a.get("help", "")),
            "range": a.get("range", (-1, 1)),
        }
        for a in all_algos
        if "RGB" in a.get("filters", [])
    ]
    return {"result": True, "data": rgb_algos}


@router.get("/odm-task-spectral/{task_id}")
async def get_odm_task_spectral(
    task_id: str,
    formula: str = "VARI",
    odm_requester: OdmPort = Depends(get_odm_requester),
) -> Response:
    """主流程：取得或計算指定專案在特定植生指標（如 VARI）下之光譜熱圖。"""
    file_path = await _generate_spectral_cached(task_id, formula, odm_requester)
    if not file_path:
        return Response(content="Spectral image could not be generated", status_code=404)
    return FileResponse(file_path, media_type="image/png")


@router.get("/odm-task-list")
async def get_odm_task_list(
    usecase: TaskUseCase = Depends(get_task_usecase),
) -> dict[str, Any]:
    """主流程：查詢所有任務清單。"""
    tasks = await usecase.get_tasks()
    return {"result": True, "data": [_task_to_dict(t) for t in tasks]}


@router.delete("/odm-task/{task_id}")
async def delete_odm_task(
    task_id: str,
    usecase: TaskUseCase = Depends(get_task_usecase),
    odm_requester: OdmPort = Depends(get_odm_requester),
) -> dict[str, Any]:
    """主流程：刪除指定任務與關聯影像資產。"""
    await _cleanup_task_assets(task_id, usecase, odm_requester)
    return {"result": True}


@router.post("/chat")
async def post_chat(
    request: PostChatRequest,
    usecase: TaskUseCase = Depends(get_task_usecase),
    task_port: TaskPort = Depends(get_task_repo),
) -> StreamingResponse:
    """主流程：接收使用者提問並啟動 Pydantic AI Agent 串流回應。"""
    stream = _stream_agent_dialogue(
        request.prompt, request.project_id, usecase, task_port
    )
    return StreamingResponse(stream, media_type="text/plain")


@router.get("/chat")
@router.get("/chat/")
async def get_chat(
    project_id: str = "home",
    usecase: TaskUseCase = Depends(get_task_usecase),
) -> Response:
    """主流程：查詢指定專案之對話歷史列表。"""
    if not project_id or project_id == "home":
        return Response(b"", media_type="text/plain")
    try:
        msgs = await usecase.get_messages(project_id=project_id)
    except KeyError:
        return Response(b"", media_type="text/plain")

    serialized = []
    for m in msgs:
        converted = _to_model_message_response(m)
        if converted:
            serialized.append(json.dumps(converted, ensure_ascii=False).encode("utf-8"))
    return Response(b"\n".join(serialized), media_type="text/plain")


@router.delete("/chat")
@router.delete("/chat/")
async def delete_chat(
    project_id: str = "home",
    usecase: TaskUseCase = Depends(get_task_usecase),
) -> dict[str, Any]:
    """主流程：清空指定專案之對話歷史紀錄。"""
    if project_id and project_id != "home":
        try:
            await usecase.clear_messages(project_id)
        except KeyError:
            pass
    return {"result": True}


@router.post("/chat/migrate")
@router.post("/chat/migrate/")
async def migrate_chat(
    request: MigrateChatRequest,
) -> dict[str, Any]:
    """主流程：維持前端呼叫相容性（依據架構規範拒絕跨任務對話複製）。"""
    return {"result": True}

