from __future__ import annotations

from sqlmodel import Field, Session, SQLModel, select

from src.entities.plot import PlotGrid
from src.usecases.ports import PlotPort


class PlotGridModel(SQLModel, table=True):
    """試驗小區網格持久化資料表模型。"""
    __tablename__ = "plots"

    id: int | None = Field(default=None, primary_key=True)
    task_id: str = Field(index=True)
    plot_number: int
    coords: str
    is_control: bool = Field(default=False)
    treatment: str = Field(default="")
    dose: str = Field(default="")


class PlotGridRepository(PlotPort):
    """小區網格倉儲類別：實作 PlotPort 介面，由外部注入 Session。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def _to_entity(self, model: PlotGridModel) -> PlotGrid:
        return PlotGrid(
            id=model.id or 0,
            task_id=model.task_id,
            plot_number=model.plot_number,
            coords=model.coords,
            is_control=model.is_control,
            treatment=model.treatment,
            dose=model.dose,
        )

    async def add_plot_grid(self, plot: PlotGrid) -> None:
        """非同步新增或更新小區網格記錄。"""
        existing = self.session.get(PlotGridModel, plot.id) if plot.id else None
        if existing:
            existing.plot_number = plot.plot_number
            existing.coords = plot.coords
            existing.is_control = plot.is_control
            existing.treatment = plot.treatment
            existing.dose = plot.dose
            self.session.add(existing)
        else:
            model = PlotGridModel(
                id=plot.id if plot.id else None,
                task_id=plot.task_id,
                plot_number=plot.plot_number,
                coords=plot.coords,
                is_control=plot.is_control,
                treatment=plot.treatment,
                dose=plot.dose,
            )
            self.session.add(model)
        self.session.commit()

    async def get_plot_grids_by_task(self, task_id: str) -> list[PlotGrid]:
        """非同步查詢指定任務 ID 下之所有小區網格清單。"""
        statement = select(PlotGridModel).where(PlotGridModel.task_id == task_id).order_by(PlotGridModel.plot_number)
        models = self.session.exec(statement).all()
        return [self._to_entity(m) for m in models]

    async def delete_plot_grids_by_task(self, task_id: str) -> None:
        """非同步刪除指定任務 ID 下之所有小區網格。"""
        statement = select(PlotGridModel).where(PlotGridModel.task_id == task_id)
        models = self.session.exec(statement).all()
        for m in models:
            self.session.delete(m)
        self.session.commit()
