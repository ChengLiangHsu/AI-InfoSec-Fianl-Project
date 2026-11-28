from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from PIL import Image
from pydantic_ai import ModelRequest, UserPromptPart
from pydantic_ai.messages import ModelMessagesTypeAdapter
from pydantic_ai.models.test import TestModel
from sqlmodel import Session, SQLModel, create_engine

from src.agents.pydantic_agent import (
    ChatDeps,
    DynamicFieldInput,
    TrialGroupInput,
    get_selected_plots_spectral_stats,
    spectral_agent,
    upsert_trial_scenario_form,
)
from src.controllers.task import _stream_agent_dialogue
from src.entities.task import Plot, Task
from src.repositories.task_repo import TaskRepository
from src.usecases.ports.task import TaskPort
from src.usecases.task import _normalize_scenario_data
from src.utility.region_statistics import calculate_plots_statistics


class _InMemoryChannelTaskPort(TaskPort):
    def __init__(self, task: Task) -> None:
        self.task = task
        self.channel_messages: dict[str, list[Any]] = {"default": [], "spectral": []}

    async def add_task(self, task: Task) -> None:
        self.task = task

    async def get_task(self, task_id: str) -> Task:
        if task_id != self.task.id:
            raise KeyError(task_id)
        return self.task

    async def get_tasks(self) -> list[Task]:
        return [self.task]

    async def update_task(self, task_id: str, data: dict[str, Any]) -> None:
        pass

    async def delete_task(self, task_id: str) -> None:
        pass

    async def get_plots(self, task_id: str) -> list[Plot]:
        return self.task.plots

    async def update_plots(self, task_id: str, plots: list[Plot]) -> None:
        self.task.plots = plots

    async def update_scenario(self, task_id: str, scenario: dict[str, Any]) -> None:
        self.task.scenario = scenario

    async def get_messages(self, task_id: str, channel: str = "default") -> list[Any]:
        return list(self.channel_messages.get(channel, []))

    async def add_messages(
        self, task_id: str, new_messages: str | bytes, channel: str = "default"
    ) -> None:
        parsed = ModelMessagesTypeAdapter.validate_json(new_messages)
        self.channel_messages.setdefault(channel, []).extend(parsed)

    async def clear_messages(self, task_id: str, channel: str = "default") -> None:
        self.channel_messages[channel] = []


class _DummyChannelUseCase:
    def __init__(self, port: _InMemoryChannelTaskPort) -> None:
        self.port = port

    async def get_messages(self, task_id: str, channel: str = "default") -> list[Any]:
        return await self.port.get_messages(task_id, channel=channel)

    async def append_messages(
        self, task_id: str, new_messages: str | bytes, channel: str = "default"
    ) -> None:
        await self.port.add_messages(task_id, new_messages, channel=channel)


def _create_synthetic_ortho(path: Path) -> None:
    """Create a 40x20 RGBA image: left half reddish-brown (soil/low vigor), right half lush green."""
    img = Image.new("RGBA", (40, 20), (0, 0, 0, 255))
    for y in range(20):
        for x in range(20):
            img.putpixel((x, y), (160, 100, 60, 255))
        for x in range(20, 40):
            img.putpixel((x, y), (50, 200, 60, 255))
    img.save(path, format="PNG")


def test_normalize_scenario_preserves_canonical_recommended_formulas() -> None:
    raw = {
        "version": 2,
        "type": "pesticide",
        "title": "藥效試驗",
        "recommended_formulas": ["vari", "GLI", "VARI", "NDVI", "exg"],
        "categories": [{"name": "CK", "is_control": True}],
    }
    normalized = _normalize_scenario_data(raw)
    assert normalized["recommended_formulas"] == ["VARI", "GLI", "EXG"]


def test_upsert_trial_scenario_form_populates_recommended_formulas() -> None:
    task = Task(id="proj-rec", name="殺蟲試驗", images=6, progress=100)
    port = _InMemoryChannelTaskPort(task)
    deps = ChatDeps(project_id="proj-rec", task_port=port)

    class _FakeCtx:
        def __init__(self, d: ChatDeps) -> None:
            self.deps = d

    res = asyncio.run(
        upsert_trial_scenario_form(
            _FakeCtx(deps),  # type: ignore[arg-type]
            scenario_type="pesticide",
            title="水稻殺蟲劑試驗",
            group_fields=[DynamicFieldInput(key="treatment", label="藥劑", type="text")],
            groups=[TrialGroupInput(values={"treatment": "快得寧"})],
            recommended_formulas=["vari", "GLI"],
        )
    )
    assert res["status"] == "saved"
    assert res["recommended_formulas"] == ["VARI", "GLI"]
    assert port.task.scenario["recommended_formulas"] == ["VARI", "GLI"]


def test_task_repository_isolates_default_and_spectral_channels() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        repo = TaskRepository(session)
        asyncio.run(repo.add_task(Task(id="t-iso", name="隔離測試", images=4, progress=100)))

        msg_default = ModelMessagesTypeAdapter.dump_json(
            [ModelRequest(parts=[UserPromptPart(content="步驟2情境討論")])]
        )
        msg_spectral = ModelMessagesTypeAdapter.dump_json(
            [ModelRequest(parts=[UserPromptPart(content="步驟4光譜分析")])]
        )

        asyncio.run(repo.add_messages("t-iso", msg_default, channel="default"))
        asyncio.run(repo.add_messages("t-iso", msg_spectral, channel="spectral"))

        default_history = asyncio.run(repo.get_messages("t-iso", channel="default"))
        spectral_history = asyncio.run(repo.get_messages("t-iso", channel="spectral"))
        assert len(default_history) == 1
        assert len(spectral_history) == 1
        assert default_history[0].parts[0].content == "步驟2情境討論"
        assert spectral_history[0].parts[0].content == "步驟4光譜分析"

        # Clearing spectral channel must NOT affect default channel
        asyncio.run(repo.clear_messages("t-iso", channel="spectral"))
        assert asyncio.run(repo.get_messages("t-iso", channel="spectral")) == []
        assert len(asyncio.run(repo.get_messages("t-iso", channel="default"))) == 1


def test_calculate_plots_statistics_computes_ck_baseline_and_groups(tmp_path: Path) -> None:
    ortho = tmp_path / "ortho.png"
    _create_synthetic_ortho(ortho)

    plots = [
        {
            "plot_number": 1,
            "coords": json.dumps([[0.05, 0.1], [0.45, 0.1], [0.45, 0.9], [0.05, 0.9]]),
            "is_control": True,
            "treatment": "",
            "dose": "",
        },
        {
            "plot_number": 2,
            "coords": json.dumps([[0.55, 0.1], [0.95, 0.1], [0.95, 0.9], [0.55, 0.9]]),
            "is_control": False,
            "treatment": "快得寧",
            "dose": "500x",
        },
    ]

    result = calculate_plots_statistics(ortho, plots)
    assert len(result["plots"]) == 2
    assert result["control_baseline"] is not None
    assert result["control_baseline"]["plot_count"] == 1
    assert len(result["treatment_groups"]) == 2
    assert result["treatment_groups"][0]["is_control"] is True

    ck_vari = next(a["index_mean"] for a in result["plots"][0]["algorithms"] if a["id"] == "VARI")
    trt_vari = next(a["index_mean"] for a in result["plots"][1]["algorithms"] if a["id"] == "VARI")
    assert trt_vari is not None and ck_vari is not None
    assert trt_vari > ck_vari


def test_spectral_agent_stats_tool_and_stream_isolation(tmp_path: Path, monkeypatch: Any) -> None:
    import src.agents.pydantic_agent as agent_mod

    monkeypatch.setattr(agent_mod, "ODM_DIR", tmp_path)
    ortho = tmp_path / "proj-spec.png"
    _create_synthetic_ortho(ortho)

    task = Task(
        id="proj-spec",
        name="光譜專案",
        images=5,
        progress=100,
        scenario={
            "version": 2,
            "type": "pesticide",
            "title": "殺蟲試驗",
            "recommended_formulas": ["VARI", "GLI"],
        },
        plots=[
            Plot(
                plot_number=1,
                coords=json.dumps([[0.05, 0.1], [0.45, 0.1], [0.45, 0.9], [0.05, 0.9]]),
                is_control=True,
            ),
            Plot(
                plot_number=2,
                coords=json.dumps([[0.55, 0.1], [0.95, 0.1], [0.95, 0.9], [0.55, 0.9]]),
                is_control=False,
                treatment="快得寧",
                dose="500x",
            ),
        ],
    )
    port = _InMemoryChannelTaskPort(task)
    deps = ChatDeps(
        project_id="proj-spec",
        task_port=port,
        selected_plot_numbers=[2],
        current_formula="VARI",
    )

    class _FakeCtx:
        def __init__(self, d: ChatDeps) -> None:
            self.deps = d

    stats_res = asyncio.run(get_selected_plots_spectral_stats(_FakeCtx(deps)))  # type: ignore[arg-type]
    assert stats_res["status"] == "success"
    assert stats_res["scope"] == "selected_plots"
    assert stats_res["recommended_formulas"] == ["VARI", "GLI"]
    assert len(stats_res["selected_plots"]) == 1
    assert stats_res["selected_plots"][0]["plot_number"] == 2
    algo_ids = [a["id"] for a in stats_res["selected_plots"][0]["algorithms"]]
    assert algo_ids == ["VARI", "GLI"]
    assert stats_res["selected_plots"][0]["algorithms"][0]["delta_vs_ck"] > 0

    # Verify streaming spectral mode writes ONLY to spectral channel and never touches default channel
    usecase = _DummyChannelUseCase(port)
    test_model = TestModel(
        call_tools=["get_selected_plots_spectral_stats"],
        custom_output_text="小區 #2 的 VARI 明顯高於對照組 CK。",
    )

    async def _collect() -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        with spectral_agent.override(model=test_model):
            async for chunk in _stream_agent_dialogue(
                prompt="分析小區 #2",
                project_id="proj-spec",
                usecase=usecase,  # type: ignore[arg-type]
                task_port=port,
                mode="spectral",
                selected_plot_numbers=[2],
                current_formula="VARI",
            ):
                for line in chunk.decode("utf-8").splitlines():
                    if line.strip():
                        events.append(json.loads(line))
        return events

    events = asyncio.run(_collect())
    assert any(
        e.get("role") == "assistant" and "VARI" in e["versions"][0]["content"]
        for e in events
    )
    assert len(port.channel_messages["spectral"]) > 0
    assert len(port.channel_messages["default"]) == 0


def _create_multi_strip_ortho(path: Path, colors: list[tuple[int, int, int, int]]) -> None:
    """建立多色帶合成正射圖，每條垂直色帶寬度 10 px、高度 20 px，供不同重複小區測試。"""
    width = 10 * len(colors)
    img = Image.new("RGBA", (width, 20), (0, 0, 0, 255))
    for idx, rgba in enumerate(colors):
        for y in range(20):
            for x in range(idx * 10, (idx + 1) * 10):
                img.putpixel((x, y), rgba)
    img.save(path, format="PNG")


def _strip_plot(
    plot_number: int,
    strip_idx: int,
    total_strips: int,
    *,
    is_control: bool = False,
    treatment: str = "",
    dose: str = "",
) -> dict[str, Any]:
    """回傳對應垂直色帶範圍的小區定義。"""
    x0 = (strip_idx + 0.1) / total_strips
    x1 = (strip_idx + 0.9) / total_strips
    return {
        "plot_number": plot_number,
        "coords": json.dumps([[x0, 0.1], [x1, 0.1], [x1, 0.9], [x0, 0.9]]),
        "is_control": is_control,
        "treatment": treatment,
        "dose": dose,
    }


def test_anova_tukey_cld_and_descriptive_stats(tmp_path: Path) -> None:
    """驗證單因子 ANOVA、Tukey HSD 顯著性字母（a/b）與描述統計（SD/CV%/四分位數）。"""
    # 3 組 × 3 重複：CK（偏紅褐低活力）、藥劑 A（高綠度）、藥劑 B（中綠度）
    colors = [
        # CK 3 重複
        (165, 95, 60, 255),
        (160, 100, 60, 255),
        (155, 102, 60, 255),
        # 藥劑 A 3 重複（明顯高活力）
        (40, 215, 55, 255),
        (45, 210, 58, 255),
        (42, 220, 52, 255),
        # 藥劑 B 3 重複（中等活力）
        (95, 155, 65, 255),
        (98, 150, 62, 255),
        (92, 158, 66, 255),
    ]
    ortho = tmp_path / "anova.png"
    _create_multi_strip_ortho(ortho, colors)
    n = len(colors)
    plots = [
        _strip_plot(1, 0, n, is_control=True),
        _strip_plot(2, 1, n, is_control=True),
        _strip_plot(3, 2, n, is_control=True),
        _strip_plot(4, 3, n, treatment="藥劑A", dose="500x"),
        _strip_plot(5, 4, n, treatment="藥劑A", dose="500x"),
        _strip_plot(6, 5, n, treatment="藥劑A", dose="500x"),
        _strip_plot(7, 6, n, treatment="藥劑B", dose="1000x"),
        _strip_plot(8, 7, n, treatment="藥劑B", dose="1000x"),
        _strip_plot(9, 8, n, treatment="藥劑B", dose="1000x"),
    ]

    result = calculate_plots_statistics(ortho, plots)
    vari_test = result["statistical_tests"]["VARI"]
    assert vari_test["status"] == "ok"
    assert vari_test["significant"] is True
    assert vari_test["anova_p"] is not None and vari_test["anova_p"] < 0.05
    assert vari_test["group_letters"]["藥劑A::500x"] == "a"
    assert vari_test["group_letters"]["藥劑B::1000x"] == "b"
    assert vari_test["group_letters"]["CK"] == "c"

    group_a = next(g for g in result["treatment_groups"] if g["key"] == "藥劑A::500x")
    vari_row = next(a for a in group_a["algorithms"] if a["id"] == "VARI")
    assert vari_row["tukey_group"] == "a"
    assert vari_row["index_std"] is not None and vari_row["index_std"] > 0
    assert vari_row["index_cv_pct"] is not None
    assert vari_row["index_q1"] is not None and vari_row["index_median"] is not None
    assert vari_row["replicate_count"] == 3


def test_anova_graceful_degradation_when_replicates_insufficient(tmp_path: Path) -> None:
    """驗證每組僅 1 重複時優雅降級略過顯著性檢定，不拋出例外。"""
    ortho = tmp_path / "ortho.png"
    _create_synthetic_ortho(ortho)
    plots = [
        {
            "plot_number": 1,
            "coords": json.dumps([[0.05, 0.1], [0.45, 0.1], [0.45, 0.9], [0.05, 0.9]]),
            "is_control": True,
            "treatment": "",
            "dose": "",
        },
        {
            "plot_number": 2,
            "coords": json.dumps([[0.55, 0.1], [0.95, 0.1], [0.95, 0.9], [0.55, 0.9]]),
            "is_control": False,
            "treatment": "快得寧",
            "dose": "500x",
        },
    ]
    result = calculate_plots_statistics(ortho, plots)
    assert result["statistical_tests"]["VARI"]["status"] == "insufficient_replicates"
    assert result["statistical_tests"]["VARI"]["significant"] is False
    assert result["outliers"]["VARI"] == []


def test_adaptive_outlier_detection_n3_cv_and_n4_iqr(tmp_path: Path) -> None:
    """驗證 n=3 採 CV>15% 標記與 n>=4 採 1.5xIQR 標記，且絕不自動刪除小區。"""
    # 組 1（n=3）：兩區高綠、一區嚴重異常偏紅褐 -> 觸發 cv_15_n3 標記小區 #3
    # 組 2（n=4）：三區接近高綠、一區極端異常 -> 觸發 iqr_1.5 標記小區 #7
    colors = [
        (45, 210, 55, 255),
        (48, 205, 58, 255),
        (170, 90, 55, 255),  # plot #3 離群（n=3）
        (50, 200, 60, 255),
        (52, 198, 60, 255),
        (49, 202, 59, 255),
        (175, 85, 55, 255),  # plot #7 離群（n=4）
    ]
    ortho = tmp_path / "outliers.png"
    _create_multi_strip_ortho(ortho, colors)
    n = len(colors)
    plots = [
        _strip_plot(1, 0, n, is_control=True),
        _strip_plot(2, 1, n, is_control=True),
        _strip_plot(3, 2, n, is_control=True),
        _strip_plot(4, 3, n, treatment="處理組", dose="500x"),
        _strip_plot(5, 4, n, treatment="處理組", dose="500x"),
        _strip_plot(6, 5, n, treatment="處理組", dose="500x"),
        _strip_plot(7, 6, n, treatment="處理組", dose="500x"),
    ]

    result = calculate_plots_statistics(ortho, plots)
    # 嚴守雙軌解讀原則：7 個小區必須全數保留，不可自動刪除
    assert len(result["plots"]) == 7

    vari_outliers = result["outliers"]["VARI"]
    by_plot = {o["plot_number"]: o for o in vari_outliers}
    assert 3 in by_plot
    assert by_plot[3]["method"] == "cv_15_n3"
    assert 7 in by_plot
    assert by_plot[7]["method"] == "iqr_1.5"
