import io
import logging
from pathlib import Path
from zipfile import ZipFile

import httpx
from PIL import Image

logger = logging.getLogger("nodeodm")
NODEODM_URL = "http://localhost:3002"


def check_nodeodm_alive(timeout: float = 2.0) -> bool:
    """透過 HTTP API 檢查 NodeODM 是否正常運作。"""
    try:
        resp = httpx.get(f"{NODEODM_URL}/info", timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False


def ensure_nodeodm_running() -> bool:
    """
    驗證 NodeODM 是否已在運作中；若未啟動則回傳 False 阻止後端啟動。
    """
    if check_nodeodm_alive():
        logger.info("NodeODM 連線驗證成功，服務正常運作。")
        return True
    return False


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
