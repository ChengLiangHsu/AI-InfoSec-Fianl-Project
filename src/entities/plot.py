from dataclasses import dataclass


@dataclass
class PlotGrid:
    """小區網格領域實體（純 Python Dataclass，無 ORM 依賴）。"""
    id: int
    task_id: str
    plot_number: int
    coords: str
    is_control: bool
    treatment: str
    dose: str
