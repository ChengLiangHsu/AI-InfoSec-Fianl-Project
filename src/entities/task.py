from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


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
class ScenarioCategory:
    """試驗情境處理分類領域實體。"""
    name: str  # 分類/劑量名稱，如 "500x", "1000x", "CK"
    color: str  # 視覺標籤色彩代碼，如 "#10b981"
    is_control: bool = False  # 是否為未施藥對照組


@dataclass
class Plot:
    """試驗小區實體"""
    plot_number: int  # 網格編號
    coords: str  # 坐標
    is_control: bool = False  # 是否為對照組
    treatment: str = ""  # 處理方式
    dose: str = ""  # 劑量
    metrics: dict[str, float] = field(default_factory=dict)


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
    plots: list[Plot] = field(default_factory=list)
    scenario: dict[str, Any] = field(default_factory=dict)
