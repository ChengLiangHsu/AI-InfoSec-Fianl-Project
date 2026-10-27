from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from fastapi.responses import FileResponse
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


@router.get("/odm-task-info/{task_id}")
async def get_odm_task_info(task_id: str, database: Database = Depends(get_db)):
    """向 NodeODM 查詢指定任務的運算進度並同步更新資料庫。"""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{NODEODM_URL}/task/{task_id}/info")
    info_json = r.json()
    await database.update_project(task_id, info_json)
    project = await database.get_project(task_id)
    return {"result": True, "data": project}


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
