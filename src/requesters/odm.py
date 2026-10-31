from __future__ import annotations

import json
from typing import Any

import httpx

from src.usecases.ports.odm import OdmPort


def _validate_task_id(task_id: str) -> None:
    """校驗任務 UUID 格式是否非空且合法。"""
    if not task_id or not isinstance(task_id, str) or not task_id.strip():
        raise ValueError("任務 ID 不得為空")


def _validate_files_payload(files: list[tuple[str, bytes, str]]) -> None:
    """校驗上傳相片資料包是否符合非空規範。"""
    if not files or not isinstance(files, list):
        raise ValueError("上傳相片檔案清單不得為空")
    for item in files:
        if not isinstance(item, tuple) or len(item) != 3:
            raise ValueError(f"無效的相片資料規格，預期為 (檔名, 內容, 類型): {item}")
        filename, content, _ = item
        if not filename or not filename.strip():
            raise ValueError("相片檔名不得為空")
        if not content:
            raise ValueError(f"相片檔案內容不得為空: {filename}")


def _build_multipart_payload(
    files: list[tuple[str, bytes, str]],
) -> list[tuple[str, tuple[str, bytes, str]]]:
    """將原始檔案 tuple 列表轉換為 httpx multipart 檔案上傳格式。"""
    return [
        ("images", (filename, content, content_type))
        for filename, content, content_type in files
    ]


def _build_data_payload(
    name: str | None,
    options: list[dict[str, Any]] | None,
) -> dict[str, str]:
    """建立建立任務時的額外表單設定參數。"""
    data: dict[str, str] = {}
    if name is not None and name.strip():
        data["name"] = name.strip()
    if options is not None:
        data["options"] = json.dumps(options, ensure_ascii=False)
    return data


def _parse_task_uuid(data: dict[str, Any]) -> str:
    """自 NodeODM 回應 JSON 中提煉任務 UUID 字串。"""
    uuid_val = data.get("uuid")
    if not uuid_val or not isinstance(uuid_val, str):
        raise RuntimeError(f"NodeODM 回應缺少有效之任務 UUID: {data}")
    return uuid_val


class OdmRequester(OdmPort):
    """NodeODM HTTP 請求適配器：實作 OdmPort 介面契約，負責與 NodeODM 進行非同步 HTTP 通訊。"""

    def __init__(self, base_url: str = "http://localhost:3002") -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url)

    async def check_alive(self, timeout: float = 2.0) -> bool:
        """非同步檢查 NodeODM 節點是否存活且正常運作。"""
        try:
            resp = await self._client.get(f"{self.base_url}/info", timeout=timeout)
            return resp.status_code == 200
        except Exception:
            return False

    async def get_node_info(self, timeout: float = 10.0) -> dict[str, Any]:
        """非同步向 NodeODM /info 查詢節點系統資訊與狀態。"""
        resp = await self._client.get(f"{self.base_url}/info", timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    async def create_task(
        self,
        files: list[tuple[str, bytes, str]],
        name: str | None = None,
        options: list[dict[str, Any]] | None = None,
        timeout: float = 120.0,
    ) -> str:
        """非同步上傳航拍影像資料包至 NodeODM /task/new，派送拼圖任務並取得回傳之任務 UUID。"""
        _validate_files_payload(files)
        multipart_files = _build_multipart_payload(files)
        data_payload = _build_data_payload(name, options)

        resp = await self._client.post(
            f"{self.base_url}/task/new",
            files=multipart_files,
            data=data_payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        return _parse_task_uuid(resp.json())

    async def get_task_info(
        self, task_id: str, timeout: float = 10.0
    ) -> dict[str, Any]:
        """非同步向 NodeODM /task/{uuid}/info 查詢指定任務之執行進度與狀態。"""
        _validate_task_id(task_id)
        resp = await self._client.get(
            f"{self.base_url}/task/{task_id}/info", timeout=timeout
        )
        resp.raise_for_status()
        return resp.json()

    async def download_task_assets(
        self, task_id: str, asset: str = "all.zip", timeout: float = 120.0
    ) -> bytes:
        """非同步自 NodeODM /task/{uuid}/download/{asset} 下載產出之壓縮包或成果資產位元組。"""
        _validate_task_id(task_id)
        resp = await self._client.get(
            f"{self.base_url}/task/{task_id}/download/{asset}", timeout=timeout
        )
        resp.raise_for_status()
        return resp.content

    async def remove_task(self, task_id: str, timeout: float = 10.0) -> bool:
        """非同步向 NodeODM /task/remove 發送請求移除指定任務與暫存。"""
        _validate_task_id(task_id)
        resp = await self._client.post(
            f"{self.base_url}/task/remove", json={"uuid": task_id}, timeout=timeout
        )
        resp.raise_for_status()
        return True
