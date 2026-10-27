import io
import logging
from pathlib import Path
import subprocess
import time
from zipfile import ZipFile

import httpx
from PIL import Image

logger = logging.getLogger("nodeodm")
NODEODM_URL = "http://localhost:3000"
CONTAINER_NAME = "nodeodm"


def check_nodeodm_alive(timeout: float = 2.0) -> bool:
    """透過 HTTP API 檢查 NodeODM 是否正常運作。"""
    try:
        resp = httpx.get(f"{NODEODM_URL}/info", timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False


def start_nodeodm_container() -> None:
    """嘗試啟動既有容器，若不存在則新建立容器。"""
    res = subprocess.run(
        ["docker", "start", CONTAINER_NAME],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        subprocess.run(
            ["docker", "run", "-d", "-p", "3000:3000", "--name", CONTAINER_NAME, "opendronemap/nodeodm"],
            capture_output=True,
            text=True,
        )


def wait_for_nodeodm_ready(max_retries: int = 30, delay: float = 1.0) -> bool:
    """輪詢等待 NodeODM 容器就緒。"""
    for _ in range(max_retries):
        time.sleep(delay)
        if check_nodeodm_alive():
            logger.info("NodeODM 啟動成功並通過 API 驗證。")
            return True
    logger.error("NodeODM 啟動驗證逾時。")
    return False


def ensure_nodeodm_running(max_retries: int = 30, delay: float = 1.0) -> bool:
    """
    協調確保 NodeODM 已在背景正常運作（主流程調度模式）。
    """
    if check_nodeodm_alive():
        logger.info("NodeODM 已在運作中。")
        return True

    logger.info("NodeODM 尚未啟動，正在喚醒容器...")
    start_nodeodm_container()
    return wait_for_nodeodm_ready(max_retries=max_retries, delay=delay)


async def fetch_orthophoto_from_odm(task_id: str, output_path: Path) -> bool:
    """從 NodeODM 下載任務結果 zip 並提煉出正射圖 PNG。"""
    if output_path.exists():
        return True

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.get(f"{NODEODM_URL}/task/{task_id}/download/all.zip")
        if resp.status_code != 200:
            return False

        output_path.parent.mkdir(parents=True, exist_ok=True)
        Image.MAX_IMAGE_PIXELS = None
        with ZipFile(io.BytesIO(resp.content)) as z:
            with z.open("odm_orthophoto/odm_orthophoto.tif") as target:
                with Image.open(target) as im:
                    im.save(output_path, "PNG")
        return output_path.exists()
    except Exception as e:
        logger.error(f"下載正射圖失敗 ({task_id}): {e}")
        return False
