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
