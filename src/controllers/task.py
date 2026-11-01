from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from dataclasses import asdict
from datetime import datetime, timezone
import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from pydantic_ai import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart

from src.agents import ChatDeps, agent
from src.controllers.dependencies import (
    get_task_repo,
    get_task_usecase,
)
from src.entities.task import ModelMessageResponse, Task, Version
from src.presenter.response_wrapper import success_response
from src.usecases.ports.task import TaskPort
from src.usecases.task import TaskUseCase
from src.utility.formulas import get_algorithm_list

router = APIRouter(tags=["task"])


# ============================================================================
# 請求模型宣告 (Request Schemas)
# ============================================================================

class PostChatRequest(BaseModel):
    prompt: str
    project_id: str = "home"


class PlotItemPayload(BaseModel):
    plot_number: int
    coords: str
    is_control: bool = False
    treatment: str = ""
    dose: str = ""
    metrics: dict[str, float] = Field(default_factory=dict)


class UpdatePlotsPayload(BaseModel):
    plots: list[PlotItemPayload]


class DetectMarkersPayload(BaseModel):
    roi: list[float] | None = None


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


def _to_model_message_response(m: ModelMessage) -> ModelMessageResponse | None:
    """將 Pydantic AI 的 ModelMessage 轉為前端畫布規範的訊息實體。"""
    if isinstance(m, ModelRequest):
        for part in m.parts:
            if isinstance(part, UserPromptPart) and isinstance(part.content, str):
                return ModelMessageResponse(
                    key=part.timestamp.isoformat(),
                    role="user",
                    versions=[Version(id="1", content=part.content)],
                )
        return None
    if isinstance(m, ModelResponse):
        for part in m.parts:
            if isinstance(part, TextPart):
                return ModelMessageResponse(
                    key=m.timestamp.isoformat(),
                    role="assistant",
                    versions=[Version(id="1", content=part.content)],
                )
        return None
    return None


def _format_initial_user_event(prompt: str) -> bytes:
    """包裝並回傳即時回顯給前端的使用者提問 JSON 事件。"""
    event = ModelMessageResponse(
        key=datetime.now(tz=timezone.utc).isoformat(),
        role="user",
        versions=[Version(id="1", content=prompt)],
    )
    return json.dumps(asdict(event), ensure_ascii=False).encode("utf-8") + b"\n"


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
                yield json.dumps(asdict(converted), ensure_ascii=False).encode("utf-8") + b"\n"

    if is_task_scoped:
        await usecase.append_messages(project_id, result.new_messages_json())


async def _generate_task_progress_events(
    task_id: str,
    request: Request,
    usecase: TaskUseCase,
) -> AsyncGenerator[bytes, None]:
    """輪詢 NodeODM 並即時向客戶端推播 SSE 任務進度事件。"""
    try:
        task = await usecase.get_task(task_id)
    except KeyError:
        yield _format_sse_data({"error": f"Task not found: {task_id}"})
        return

    # 連線首刻主動同步最新狀態並立即推播
    task, code = await usecase.sync_task_progress(task_id)
    last_emitted_progress = task.progress
    yield _format_sse_data(_task_to_dict(task))

    if _is_task_finished(last_emitted_progress, code):
        return

    while True:
        if await request.is_disconnected():
            break
        await asyncio.sleep(1.0)

        task, code = await usecase.sync_task_progress(task_id)
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
) -> JSONResponse:
    """主流程：接收空拍相片、派送 NodeODM 拼圖並持久化建立任務。"""
    files_payload = await _extract_upload_payload(files)
    task = await usecase.create_task(name=name, files=files_payload)
    return success_response(data={"id": task.id, "name": task.name})


@router.get("/odm-task-info/{task_id}")
async def get_odm_task_info(
    task_id: str,
    usecase: TaskUseCase = Depends(get_task_usecase),
) -> JSONResponse:
    """主流程：查詢任務最新進度、同步持久化並回傳任務資訊。"""
    task = await usecase.get_task_info(task_id)
    return success_response(data=_task_to_dict(task))


@router.get("/odm-task-stream/{task_id}")
async def stream_odm_task_progress(
    task_id: str,
    request: Request,
    usecase: TaskUseCase = Depends(get_task_usecase),
) -> StreamingResponse:
    """主流程：建立 Server-Sent Events (SSE) 串流推播任務進度。"""
    stream = _generate_task_progress_events(task_id, request, usecase)
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
    usecase: TaskUseCase = Depends(get_task_usecase),
) -> FileResponse:
    """主流程：取得航拍正射圖成果（必要時由 UseCase 自 NodeODM 下載轉換快取）。"""
    file_path = await usecase.get_orthophoto_path(task_id)
    return FileResponse(file_path, media_type="image/png")


@router.get("/odm-task-formulas")
async def get_odm_task_formulas() -> JSONResponse:
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
    return success_response(data=rgb_algos)


@router.get("/odm-task-spectral/{task_id}")
async def get_odm_task_spectral(
    task_id: str,
    formula: str = "VARI",
    usecase: TaskUseCase = Depends(get_task_usecase),
) -> FileResponse:
    """主流程：取得或計算指定專案在特定植生指標（如 VARI）下之光譜熱圖。"""
    file_path = await usecase.get_spectral_image_path(task_id, formula)
    return FileResponse(file_path, media_type="image/png")


@router.get("/odm-task-list")
async def get_odm_task_list(
    usecase: TaskUseCase = Depends(get_task_usecase),
) -> JSONResponse:
    """主流程：查詢所有任務清單。"""
    tasks = await usecase.get_tasks()
    return success_response(data=[_task_to_dict(t) for t in tasks])


@router.delete("/odm-task/{task_id}")
async def delete_odm_task(
    task_id: str,
    usecase: TaskUseCase = Depends(get_task_usecase),
) -> JSONResponse:
    """主流程：刪除指定任務與關聯影像資產。"""
    await usecase.delete_task(task_id)
    return success_response()


@router.get("/plots/{task_id}")
async def get_plots(
    task_id: str,
    usecase: TaskUseCase = Depends(get_task_usecase),
) -> JSONResponse:
    """主流程：查詢指定航拍任務之小區列表。"""
    plots = await usecase.get_plots(task_id)
    return success_response(data=[asdict(p) for p in plots])


@router.put("/plots/{task_id}")
async def update_plots(
    task_id: str,
    payload: UpdatePlotsPayload,
    usecase: TaskUseCase = Depends(get_task_usecase),
) -> JSONResponse:
    """主流程：整包批次更新指定航拍任務之小區幾何座標與處理設定。"""
    plots_data = [p.model_dump() for p in payload.plots]
    updated_plots = await usecase.update_plots(task_id, plots_data)
    return success_response(data=[asdict(p) for p in updated_plots])


@router.post("/detect-markers/{task_id}")
async def detect_markers(
    task_id: str,
    payload: DetectMarkersPayload | None = None,
    usecase: TaskUseCase = Depends(get_task_usecase),
) -> JSONResponse:
    """主流程：自動偵測空拍圖中田間 4 個白色定位標記牌座標。"""
    roi = payload.roi if payload else None
    corners = await usecase.detect_plot_markers(task_id, roi)
    return success_response(data={"corners": corners})


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
            serialized.append(json.dumps(asdict(converted), ensure_ascii=False).encode("utf-8"))
    return Response(b"\n".join(serialized), media_type="text/plain")


@router.delete("/chat")
@router.delete("/chat/")
async def delete_chat(
    project_id: str = "home",
    usecase: TaskUseCase = Depends(get_task_usecase),
) -> JSONResponse:
    """主流程：清空指定專案之對話歷史紀錄。"""
    if project_id and project_id != "home":
        try:
            await usecase.clear_messages(project_id)
        except KeyError:
            pass
    return success_response()
