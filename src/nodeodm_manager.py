import logging
import subprocess
import time
import httpx

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


def ensure_nodeodm_running(max_retries: int = 30, delay: float = 1.0) -> bool:
    """
    確保 NodeODM 已啟動：
    1. 先以 API 檢查，若已在運作則不執行任何 CLI 指令。
    2. 若未啟動，以 subprocess 喚醒容器（優先 start，失敗則 run）。
    3. 啟動後透過 API 輪詢驗證狀態。
    """
    if check_nodeodm_alive():
        logger.info("NodeODM 已在運作中。")
        return True

    logger.info("NodeODM 尚未啟動，正在喚醒容器...")
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

    for _ in range(max_retries):
        time.sleep(delay)
        if check_nodeodm_alive():
            logger.info("NodeODM 啟動成功並通過 API 驗證。")
            return True

    logger.error("NodeODM 啟動驗證逾時。")
    return False
