from dataclasses import asdict
import json
from typing import Any

from pydantic_ai import ModelMessage, ModelMessagesTypeAdapter
from sqlmodel import Field, Session, SQLModel, select

from src.entities.task import Plot, Task
from src.usecases.ports import TaskPort


def _plots_to_json(plots: list[Plot]) -> str:
    """將小區實體列表序列化為 JSON 字串。"""
    if not plots:
        return ""
    return json.dumps([asdict(p) for p in plots], ensure_ascii=False)


def _json_to_plots(plots_json: str) -> list[Plot]:
    """將 JSON 字串反序列化為小區實體列表。"""
    if not plots_json or plots_json.strip() in ("", "[]"):
        return []
    try:
        raw_list = json.loads(plots_json)
        return [
            Plot(
                plot_number=item.get("plot_number", 0),
                coords=item.get("coords", ""),
                is_control=item.get("is_control", False),
                treatment=item.get("treatment", ""),
                dose=item.get("dose", ""),
                metrics=item.get("metrics", {}),
            )
            for item in raw_list
        ]
    except Exception:
        return []


class TaskModel(SQLModel, table=True):
    """NodeODM 航拍任務持久化資料表模型。"""
    __tablename__ = "tasks"

    id: str = Field(primary_key=True)
    name: str
    images: int
    progress: int = Field(default=0)
    messages: str = Field(default="")
    plots: str = Field(default="")


class TaskRepository(TaskPort):
    """NodeODM 航拍任務倉儲類別：實作 TaskPort 介面，由外部注入 Session。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def _to_entity(self, model: TaskModel) -> Task:
        return Task(
            id=model.id,
            name=model.name,
            images=model.images,
            progress=model.progress,
            messages=model.messages,
            plots=_json_to_plots(model.plots),
        )

    async def add_task(self, task: Task) -> None:
        """非同步新增或更新任務記錄。"""
        plots_json = _plots_to_json(task.plots)
        existing = self.session.get(TaskModel, task.id)
        if existing:
            existing.name = task.name
            existing.images = task.images
            existing.progress = task.progress
            existing.messages = task.messages
            existing.plots = plots_json
            self.session.add(existing)
        else:
            model = TaskModel(
                id=task.id,
                name=task.name,
                images=task.images,
                progress=task.progress,
                messages=task.messages,
                plots=plots_json,
            )
            self.session.add(model)
        self.session.commit()

    async def get_task(self, task_id: str) -> Task:
        """非同步依據 task_id 查詢任務實體，若不存在則拋出 KeyError。"""
        model = self.session.get(TaskModel, task_id)
        if not model:
            raise KeyError(f"任務不存在: {task_id}")
        return self._to_entity(model)

    async def get_tasks(self) -> list[Task]:
        """非同步查詢所有任務實體清單。"""
        statement = select(TaskModel)
        models = self.session.exec(statement).all()
        return [self._to_entity(m) for m in models]

    async def update_task(self, task_id: str, data: dict[str, Any]) -> None:
        """非同步更新任務進度與照片數量。"""
        model = self.session.get(TaskModel, task_id)
        if model:
            if "imagesCount" in data:
                model.images = int(data["imagesCount"])
            elif "images" in data:
                model.images = int(data["images"])
            if "progress" in data:
                model.progress = int(data["progress"])
            self.session.add(model)
            self.session.commit()

    async def delete_task(self, task_id: str) -> None:
        """非同步刪除任務實體。"""
        model = self.session.get(TaskModel, task_id)
        if model:
            self.session.delete(model)
            self.session.commit()

    async def get_plots(self, task_id: str) -> list[Plot]:
        """非同步查詢指定任務之小區列表。"""
        model = self.session.get(TaskModel, task_id)
        if not model or not model.plots:
            return []
        return _json_to_plots(model.plots)

    async def update_plots(self, task_id: str, plots: list[Plot]) -> None:
        """非同步更新指定任務之小區列表。"""
        model = self.session.get(TaskModel, task_id)
        if model:
            model.plots = _plots_to_json(plots)
            self.session.add(model)
            self.session.commit()

    async def get_messages(self, task_id: str) -> list[ModelMessage]:
        """非同步查詢指定任務之對話歷史列表。"""
        model = self.session.get(TaskModel, task_id)
        if not model or not model.messages:
            return []
        return ModelMessagesTypeAdapter.validate_json(model.messages)

    async def add_messages(self, task_id: str, new_messages: str | bytes) -> None:
        """非同步新增序列化之對話歷史記錄至任務。"""
        model = self.session.get(TaskModel, task_id)
        if not model:
            return
        new_str = new_messages.decode("utf-8") if isinstance(new_messages, bytes) else str(new_messages)
        if not new_str:
            return
        if not model.messages or model.messages.strip() in ("", "[]"):
            model.messages = new_str
        else:
            existing_msgs = ModelMessagesTypeAdapter.validate_json(model.messages)
            new_msgs = ModelMessagesTypeAdapter.validate_json(new_str)
            merged = existing_msgs + new_msgs
            model.messages = ModelMessagesTypeAdapter.dump_json(merged).decode("utf-8")
        self.session.add(model)
        self.session.commit()

    async def clear_messages(self, task_id: str) -> None:
        """非同步清空指定任務之對話歷史。"""
        model = self.session.get(TaskModel, task_id)
        if model:
            model.messages = ""
            self.session.add(model)
            self.session.commit()
