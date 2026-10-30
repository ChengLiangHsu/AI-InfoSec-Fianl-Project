from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Version:
    """訊息版本領域實體。"""
    id: str
    content: str


@dataclass
class ModelMessageResponse:
    """前端畫布對話訊息領域實體。"""
    key: str
    role: Literal["user", "assistant"]
    versions: list[Version] = field(default_factory=list)


@dataclass
class Task:
    """NodeODM 航拍任務領域實體（純 Python Dataclass，無 ORM 依賴）。"""
    id: str
    name: str
    images: int
    progress: int = 0
    messages: str = ""
    status: int | None = None
    images_count: int | None = None
