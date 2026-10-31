from typing import Any, Protocol

from src.entities.task import Plot, Task


class TaskPort(Protocol):
    """任務倉儲埠（介面契約）：宣告 UseCase 對航拍任務持久化、小區及訊息操作的全部契約。"""

    async def add_task(self, task: Task) -> None:
        """非同步新增或更新任務記錄。"""
        ...

    async def get_task(self, task_id: str) -> Task:
        """非同步依據 task_id 查詢任務實體。"""
        ...

    async def get_tasks(self) -> list[Task]:
        """非同步查詢所有任務實體清單。"""
        ...

    async def update_task(self, task_id: str, data: dict[str, Any]) -> None:
        """非同步更新任務進度與照片數量。"""
        ...

    async def delete_task(self, task_id: str) -> None:
        """非同步刪除任務實體。"""
        ...

    async def get_plots(self, task_id: str) -> list[Plot]:
        """非同步查詢指定任務之小區列表。"""
        ...

    async def update_plots(self, task_id: str, plots: list[Plot]) -> None:
        """非同步更新指定任務之小區列表。"""
        ...

    async def get_messages(self, task_id: str) -> list[Any]:
        """非同步查詢指定任務之對話歷史列表。"""
        ...

    async def add_messages(self, task_id: str, new_messages: str | bytes) -> None:
        """非同步新增序列化之對話歷史記錄至任務。"""
        ...

    async def clear_messages(self, task_id: str) -> None:
        """非同步清空指定任務之對話歷史。"""
        ...
