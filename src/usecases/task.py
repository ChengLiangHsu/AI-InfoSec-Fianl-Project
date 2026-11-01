from __future__ import annotations

from pathlib import Path
from typing import Any

from src.entities.task import Plot, Task
from src.usecases.ports import TaskPort
from src.usecases.ports.odm import OdmPort
from src.utility.imagery import extract_orthophoto_from_zip
from src.utility.spectral import generate_spectral_image

SRC_DIR = Path(__file__).resolve().parents[1]
ODM_DIR = SRC_DIR / "odm"
ODM_DIR.mkdir(parents=True, exist_ok=True)


def _validate_task_id(task_id: str) -> None:
    """校驗任務 ID 是否有效。"""
    if not task_id or not isinstance(task_id, str) or not task_id.strip():
        raise ValueError("任務 ID 不得為空")


def _validate_task_name(name: str) -> None:
    """校驗任務名稱是否有效。"""
    if not name or not isinstance(name, str) or not name.strip():
        raise ValueError("任務名稱不得為空")


def _validate_task_creation(id: str, name: str, images: int) -> None:
    """校驗任務建立參數合法性。"""
    _validate_task_id(id)
    _validate_task_name(name)
    if images < 0:
        raise ValueError("相片數量不得小於 0")


def _validate_progress(progress: int) -> None:
    """校驗進度數值合法性。"""
    if not isinstance(progress, int) or progress < 0 or progress > 100:
        raise ValueError("進度值必須介於 0 至 100 之間")


def _validate_plots_payload(plots_data: Any) -> None:
    """校驗前端傳入之整包小區資料結構。"""
    if not isinstance(plots_data, list):
        raise ValueError("小區資料必須為列表清單")


def _parse_plot_item(item: dict[str, Any] | Plot) -> Plot:
    """解析並正規化單一小區資料結構。"""
    if isinstance(item, Plot):
        plot_number = item.plot_number
        coords = str(item.coords).strip()
        is_control = bool(item.is_control)
        treatment = "" if is_control else str(item.treatment).strip()
        dose = "" if is_control else str(item.dose).strip()
        metrics = dict(item.metrics) if item.metrics else {}
    elif isinstance(item, dict):
        plot_number = int(item.get("plot_number", 0))
        coords = str(item.get("coords", "")).strip()
        is_control = bool(item.get("is_control", False))
        treatment = "" if is_control else str(item.get("treatment", "")).strip()
        dose = "" if is_control else str(item.get("dose", "")).strip()
        metrics = dict(item.get("metrics", {}))
    else:
        raise ValueError(f"不支援的小區資料型別: {type(item)}")

    if plot_number <= 0:
        raise ValueError(f"小區編號必須為大於 0 之整數，當前為: {plot_number}")
    if not coords:
        raise ValueError(f"小區 [{plot_number}] 座標不得為空")

    return Plot(
        plot_number=plot_number,
        coords=coords,
        is_control=is_control,
        treatment=treatment,
        dose=dose,
        metrics=metrics,
    )


def _validate_plots_uniqueness(plots: list[Plot]) -> None:
    """校驗小區列表之編號唯一性。"""
    seen_numbers: set[int] = set()
    for p in plots:
        if p.plot_number in seen_numbers:
            raise ValueError(f"小區編號不可重複: {p.plot_number}")
        seen_numbers.add(p.plot_number)


def _merge_plot_metrics(
    incoming_plots: list[Plot], existing_plots: list[Plot]
) -> list[Plot]:
    """增量保護既有小區指標：若傳入小區未帶指標，自動保留舊有已計算之 metrics。"""
    existing_metrics_map = {
        p.plot_number: p.metrics for p in existing_plots if p.metrics
    }
    merged: list[Plot] = []
    for incoming in incoming_plots:
        final_metrics = incoming.metrics or existing_metrics_map.get(
            incoming.plot_number, {}
        )
        merged.append(
            Plot(
                plot_number=incoming.plot_number,
                coords=incoming.coords,
                is_control=incoming.is_control,
                treatment=incoming.treatment,
                dose=incoming.dose,
                metrics=final_metrics,
            )
        )
    return merged


def _validate_messages_content(new_messages: str | bytes) -> None:
    """校驗新增對話訊息內容。"""
    if not new_messages:
        raise ValueError("對話內容不得為空")


class TaskUseCase:
    """任務用例（業務編排層）：協調航拍任務生命週期、小區配置與對話歷史業務流程。"""

    def __init__(self, task_port: TaskPort, odm_port: OdmPort) -> None:
        self.task_port = task_port
        self.odm_port = odm_port

    async def create_task(
        self, name: str, files: list[tuple[str, bytes, str]]
    ) -> Task:
        """主流程：接收空拍相片清單、派送 NodeODM 拼圖並持久化建立任務。"""
        _validate_task_name(name)
        if not files:
            raise ValueError("上傳相片清單不得為空")

        uuid_str = await self.odm_port.create_task(files=files, name=name)
        task = Task(id=uuid_str, name=name, images=len(files), progress=0)
        await self.task_port.add_task(task)
        return task

    async def get_task(self, task_id: str) -> Task:
        """依據 task_id 查詢任務，若不存在則由 Port 拋出 KeyError。"""
        _validate_task_id(task_id)
        return await self.task_port.get_task(task_id)

    async def get_tasks(self) -> list[Task]:
        """查詢所有任務實體清單。"""
        return await self.task_port.get_tasks()

    async def sync_task_progress(self, task_id: str) -> tuple[Task, int | None]:
        """向 NodeODM 查詢最新進度與狀態碼，同步持久化至資料庫並回傳 (Task, status_code)。"""
        _validate_task_id(task_id)
        code = None
        try:
            info = await self.odm_port.get_task_info(task_id)
            progress = int(info.get("progress", 0))
            code = info.get("status", {}).get("code")
            task = await self.update_task_progress(task_id, progress=progress)
            return task, code
        except Exception:
            task = await self.get_task(task_id)
            return task, None

    async def get_task_info(self, task_id: str) -> Task:
        """主流程：查詢任務最新狀態（優先向 NodeODM 同步進度後回傳）。"""
        task, _ = await self.sync_task_progress(task_id)
        return task

    async def update_task_progress(
        self,
        task_id: str,
        progress: int,
        images_count: int | None = None,
    ) -> Task:
        """更新指定任務進度與照片數量，回傳更新後實體。"""
        _validate_task_id(task_id)
        _validate_progress(progress)
        data: dict[str, Any] = {"progress": progress}
        if images_count is not None:
            data["imagesCount"] = images_count
        await self.task_port.update_task(task_id, data)
        return await self.task_port.get_task(task_id)

    async def delete_task(self, task_id: str) -> None:
        """主流程：調度 NodeODM 遠端任務移除、本機影像暫存清除與資料庫任務刪除。"""
        _validate_task_id(task_id)
        await self._cleanup_task_assets(task_id)
        await self.task_port.delete_task(task_id)

    async def _cleanup_task_assets(self, task_id: str) -> None:
        """私有子流程：清理遠端 NodeODM 任務與本地暫存影像檔。"""
        try:
            await self.odm_port.remove_task(task_id)
        except Exception:
            pass

        for f in ODM_DIR.glob(f"{task_id}*.png"):
            try:
                f.unlink()
            except Exception:
                pass

    async def get_orthophoto_path(self, task_id: str) -> Path:
        """主流程：取得航拍正射圖成果路徑，必要時自 NodeODM 下載資產並解壓轉換快取。"""
        _validate_task_id(task_id)
        await self.get_task(task_id)
        file_path = ODM_DIR / f"{task_id}.png"
        if file_path.exists():
            return file_path

        try:
            zip_bytes = await self.odm_port.download_task_assets(task_id, asset="all.zip")
            success = extract_orthophoto_from_zip(zip_bytes, file_path)
            if success and file_path.exists():
                return file_path
        except Exception:
            pass

        raise KeyError(f"任務 [{task_id}] 正射圖尚未生成或無法取得")

    async def get_spectral_image_path(
        self, task_id: str, formula: str = "VARI"
    ) -> Path:
        """主流程：取得或計算指定專案在特定植生指標（如 VARI）下之光譜熱圖路徑。"""
        _validate_task_id(task_id)
        formula_upper = formula.strip().upper()
        spectral_file_path = ODM_DIR / f"{task_id}_{formula_upper}.png"
        if spectral_file_path.exists():
            return spectral_file_path

        ortho_path = await self.get_orthophoto_path(task_id)
        generate_spectral_image(ortho_path, spectral_file_path, formula_upper)
        if spectral_file_path.exists():
            return spectral_file_path
        raise RuntimeError(f"無法產出光譜熱圖指標 [{formula_upper}]")

    async def get_plots(self, task_id: str) -> list[Plot]:
        """查詢指定任務之小區列表（確保任務存在）。"""
        _validate_task_id(task_id)
        await self.task_port.get_task(task_id)
        return await self.task_port.get_plots(task_id)

    async def update_plots(
        self,
        task_id: str,
        plots_data: list[Plot] | list[dict[str, Any]],
    ) -> list[Plot]:
        """接收前端傳送之整包座標與設定 JSON，校驗結構、保護既有指標並儲存。"""
        _validate_task_id(task_id)
        _validate_plots_payload(plots_data)

        # 確保任務存在並取得既有小區以保留既有 metrics
        task = await self.task_port.get_task(task_id)
        parsed_plots = [_parse_plot_item(item) for item in plots_data]
        _validate_plots_uniqueness(parsed_plots)

        merged_plots = _merge_plot_metrics(parsed_plots, task.plots)
        await self.task_port.update_plots(task_id, merged_plots)
        return merged_plots

    async def get_messages(self, task_id: str) -> list[Any]:
        """查詢指定任務之對話歷史列表（確保任務存在）。"""
        _validate_task_id(task_id)
        await self.task_port.get_task(task_id)
        return await self.task_port.get_messages(task_id)

    async def append_messages(self, task_id: str, new_messages: str | bytes) -> None:
        """新增序列化之對話歷史記錄至指定任務（確保任務存在）。"""
        _validate_task_id(task_id)
        _validate_messages_content(new_messages)
        await self.task_port.get_task(task_id)
        await self.task_port.add_messages(task_id, new_messages)

    async def clear_messages(self, task_id: str) -> None:
        """清空指定任務之對話歷史（確保任務存在）。"""
        _validate_task_id(task_id)
        await self.task_port.get_task(task_id)
        await self.task_port.clear_messages(task_id)

