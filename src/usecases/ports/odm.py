from typing import Any, Protocol


class OdmPort(Protocol):
    """NodeODM 外部服務通訊埠（介面契約）：宣告 UseCase 對 NodeODM API 發送請求並取得回應之全部契約。"""

    async def check_alive(self, timeout: float = 2.0) -> bool:
        """非同步檢查 NodeODM 節點是否存活且正常運作。"""
        ...

    async def get_node_info(self, timeout: float = 10.0) -> dict[str, Any]:
        """非同步向 NodeODM /info 查詢節點系統資訊與狀態。"""
        ...

    async def create_task(
        self,
        files: list[tuple[str, bytes, str]],
        name: str | None = None,
        options: list[dict[str, Any]] | None = None,
        timeout: float = 120.0,
    ) -> str:
        """非同步上傳航拍影像資料包至 NodeODM /task/new，派送拼圖任務並取得回傳之任務 UUID。"""
        ...

    async def get_task_info(
        self, task_id: str, timeout: float = 10.0
    ) -> dict[str, Any]:
        """非同步向 NodeODM /task/{uuid}/info 查詢指定任務之執行進度與狀態。"""
        ...

    async def download_task_assets(
        self, task_id: str, asset: str = "all.zip", timeout: float = 120.0
    ) -> bytes:
        """非同步自 NodeODM /task/{uuid}/download/{asset} 下載產出之壓縮包或成果資產位元組。"""
        ...

    async def remove_task(self, task_id: str, timeout: float = 10.0) -> bool:
        """非同步向 NodeODM /task/remove 發送請求移除指定任務與暫存。"""
        ...

