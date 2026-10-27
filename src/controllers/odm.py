import asyncio
from collections.abc import AsyncGenerator
import json
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
import httpx

from src.controllers.dependencies import get_db
from src.database import Database, Project
from src.utility.formulas import get_algorithm_list
from src.utility.nodeodm import NODEODM_URL, fetch_orthophoto_from_odm
from src.utility.spectral import generate_spectral_image

SRC_DIR = Path(__file__).resolve().parents[1]
ODM_DIR = SRC_DIR / "odm"
ODM_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(tags=["odm"])


@router.post("/odm-task")
async def create_odm_task(
    name: Annotated[str, Form()],
    files: list[UploadFile] = File(...),
    database: Database = Depends(get_db),
):
    """上傳航拍照片並向 NodeODM 派送正射拼接任務。"""
    odm_files = [
        ("images", (f.filename, await f.read(), f.content_type))
        for f in files
    ]
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(f"{NODEODM_URL}/task/new", files=odm_files)
    uuid_str = r.json()["uuid"]
    project = Project(
        id=uuid_str,
        name=name,
        images=len(files),
        progress=0,
    )
    await database.add_project(project)
    return {"result": True, "data": {"id": uuid_str, "name": name}}


async def sync_odm_task_info(
    task_id: str, database: Database
) -> tuple[Project | None, dict[str, Any] | None]:
    """向 NodeODM 查詢指定任務進度並同步持久化至資料庫。"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{NODEODM_URL}/task/{task_id}/info")
        if resp.status_code != 200:
            return None, None
        info_json = resp.json()
        await database.update_project(task_id, info_json)
        project = await database.get_project(task_id)
        return project, info_json
    except Exception:
        try:
            cached_project = await database.get_project(task_id)
            return cached_project, None
        except KeyError:
            return None, None


def _format_sse_data(payload: dict[str, Any]) -> bytes:
    """將字典資料包裝為標準 Server-Sent Events (SSE) 資料格式。"""
    return f"data: {json.dumps(payload)}\n\n".encode("utf-8")


def _is_task_finished(progress: int, status_code: int | None) -> bool:
    """判斷 NodeODM 任務是否已完成或終止（成功、失敗或取消）。"""
    if progress >= 100:
        return True
    return status_code in (30, 40, 50)


async def generate_task_progress_events(
    task_id: str, request: Request, database: Database
) -> AsyncGenerator[bytes, None]:
    """定時輪詢 NodeODM 並產生 SSE 進度事件之非同步生成器。"""
    initial_project, initial_info = await sync_odm_task_info(task_id, database)
    if not initial_project:
        yield _format_sse_data({"error": f"Task not found: {task_id}"})
        return

    last_emitted_progress = initial_project.get("progress", 0)
    initial_code = initial_info.get("status", {}).get("code") if initial_info else None
    yield _format_sse_data(initial_project)

    if _is_task_finished(last_emitted_progress, initial_code):
        return

    while True:
        if await request.is_disconnected():
            break

        await asyncio.sleep(1.0)

        current_project, current_info = await sync_odm_task_info(task_id, database)
        if not current_project:
            break

        current_progress = current_project.get("progress", 0)
        current_code = current_info.get("status", {}).get("code") if current_info else None

        if current_progress != last_emitted_progress or _is_task_finished(current_progress, current_code):
            last_emitted_progress = current_progress
            yield _format_sse_data(current_project)

        if _is_task_finished(current_progress, current_code):
            break


@router.get("/odm-task-info/{task_id}")
async def get_odm_task_info(task_id: str, database: Database = Depends(get_db)):
    """向 NodeODM 查詢指定任務的運算進度並同步更新資料庫。"""
    project, _ = await sync_odm_task_info(task_id, database)
    if not project:
        return Response(content="Task not found", status_code=404)
    return {"result": True, "data": project}


@router.get("/odm-task-stream/{task_id}")
async def stream_odm_task_progress(
    task_id: str,
    request: Request,
    database: Database = Depends(get_db),
) -> StreamingResponse:
    """透過 SSE 串流即時推播 NodeODM 任務運算進度。"""
    stream = generate_task_progress_events(task_id, request, database)
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
async def get_odm_task_orthophoto(task_id: str):
    """取得航拍拼接完成的正射影像（若未快取則自 NodeODM 下載解壓）。"""
    file_path = ODM_DIR / f"{task_id}.png"
    if not file_path.exists():
        success = await fetch_orthophoto_from_odm(task_id, file_path)
        if not success or not file_path.exists():
            return Response(content="Orthophoto not found", status_code=404)
    return FileResponse(file_path, media_type="image/png")


@router.get("/odm-task-formulas")
async def get_odm_task_formulas():
    """查詢系統目前支援之 RGB 植生指標清單與數學算式。"""
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
async def get_odm_task_spectral(task_id: str, formula: str = "VARI"):
    """計算並取得指定專案在特定植生指標（如 VARI）下的光譜分析圖。"""
    formula_upper = formula.strip().upper()
    spectral_file_path = ODM_DIR / f"{task_id}_{formula_upper}.png"
    if spectral_file_path.exists():
        return FileResponse(spectral_file_path, media_type="image/png")

    ortho_file_path = ODM_DIR / f"{task_id}.png"
    if not ortho_file_path.exists():
        success = await fetch_orthophoto_from_odm(task_id, ortho_file_path)
        if not success or not ortho_file_path.exists():
            return Response(content="Orthophoto not found", status_code=404)

    try:
        generate_spectral_image(ortho_file_path, spectral_file_path, formula_upper)
    except Exception as e:
        return Response(content=f"Error generating spectral image: {e}", status_code=400)

    return FileResponse(spectral_file_path, media_type="image/png")


@router.get("/odm-task-list")
async def get_odm_task_list(database: Database = Depends(get_db)):
    """取得所有田間無人機拼接任務清單。"""
    projects = await database.get_projects()
    return {"result": True, "data": projects}


@router.delete("/odm-task/{task_id}")
async def delete_odm_task(task_id: str, database: Database = Depends(get_db)):
    """刪除指定 ODM 任務、本機快取影像檔與相關對話紀錄。"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(f"{NODEODM_URL}/task/remove", json={"uuid": task_id})
    except Exception:
        pass

    for f in ODM_DIR.glob(f"{task_id}*.png"):
        try:
            f.unlink()
        except Exception:
            pass

    await database.delete_project(task_id)
    await database.delete_messages_by_project(task_id)
    return {"result": True}
