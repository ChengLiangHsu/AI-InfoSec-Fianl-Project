from __future__ import annotations

import asyncio
import json
from typing import Any

from pydantic_ai import ModelRequest, ModelResponse, ToolCallPart, UserPromptPart
from pydantic_ai.models.test import TestModel

from src.agents.pydantic_agent import (
    ChatDeps,
    DynamicFieldInput,
    InterviewQuestionOption,
    TrialGroupInput,
    ask_clarifying_question,
    scenario_agent,
    upsert_trial_scenario_form,
)
from src.controllers.task import _extract_pending_interview_question, _stream_agent_dialogue
from src.entities.task import Plot, Task
from src.usecases.ports.task import TaskPort
from src.usecases.task import SCENARIO_CONTROL_COLOR, _normalize_scenario_data


class _InMemoryTaskPort(TaskPort):
    def __init__(self, task: Task) -> None:
        self.task = task
        self.saved_scenarios: list[dict[str, Any]] = []
        self.messages_log: list[Any] = []

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
        self.saved_scenarios.append(scenario)

    async def get_messages(self, task_id: str) -> list[Any]:
        return []

    async def add_messages(self, task_id: str, new_messages: str | bytes) -> None:
        self.messages_log.append(new_messages)

    async def clear_messages(self, task_id: str) -> None:
        self.messages_log.clear()


class _DummyUseCase:
    def __init__(self, port: _InMemoryTaskPort) -> None:
        self.port = port

    async def get_messages(self, task_id: str) -> list[Any]:
        return await self.port.get_messages(task_id)

    async def append_messages(self, task_id: str, new_messages: str | bytes) -> None:
        await self.port.add_messages(task_id, new_messages)


def test_normalize_v2_pesticide_scenario_enforces_locked_ck_and_units() -> None:
    raw = {
        "version": 2,
        "type": "pesticide",
        "title": "稻熱病藥效試驗",
        "metadata_fields": [
            {"key": "crop", "label": "作物", "type": "text"},
            {"key": "spray_date", "label": "施藥日期", "type": "date"},
        ],
        "metadata_values": {"crop": "水稻", "spray_date": "2026-11-20"},
        "group_fields": [
            {"key": "treatment", "label": "藥劑名稱", "type": "text", "required": True},
            {"key": "dose", "label": "稀釋倍數", "type": "number", "unit": "倍", "required": True},
            {"key": "method", "label": "噴施方式", "type": "select", "options": ["葉面噴灑", "無人機"]},
        ],
        "categories": [
            {
                "name": "",
                "is_control": False,
                "values": {"treatment": "快得寧", "dose": 500, "method": "葉面噴灑"},
            },
            {
                "name": "未施藥對照 (CK)",
                "color": "#ff0000",
                "is_control": True,
                "values": {"treatment": "should_clear"},
            },
            {
                "name": "重複對照",
                "is_control": True,
                "values": {"treatment": "亞托敏", "dose": 1000, "method": "無人機"},
            },
        ],
    }

    normalized = _normalize_scenario_data(raw)
    assert normalized["version"] == 2
    cats = normalized["categories"]
    assert len(cats) == 3

    # CK must always be index 0 with fixed color and empty values
    assert cats[0]["is_control"] is True
    assert cats[0]["name"] == "未施藥對照 (CK)"
    assert cats[0]["color"] == SCENARIO_CONTROL_COLOR
    assert cats[0]["values"] == {}
    assert cats[0]["treatment"] == ""
    assert cats[0]["dose"] == ""

    # Remaining categories must not be control and derive name/treatment/dose
    assert cats[1]["is_control"] is False
    assert cats[1]["name"] == "快得寧 500倍"
    assert cats[1]["treatment"] == "快得寧"
    assert cats[1]["dose"] == "500倍"

    assert cats[2]["is_control"] is False
    assert cats[2]["treatment"] == "亞托敏"
    assert cats[2]["dose"] == "1000倍"


def test_normalize_v2_variety_scenario_without_dose_field() -> None:
    raw = {
        "version": 2,
        "type": "variety",
        "title": "水稻品種比較試驗",
        "group_fields": [
            {"key": "variety", "label": "品種名稱", "type": "text", "required": True},
            {"key": "organic", "label": "有機栽培", "type": "boolean"},
        ],
        "categories": [
            {"name": "標準對照 (CK)", "is_control": True},
            {"values": {"variety": "台農71號", "organic": True}},
            {"values": {"variety": "台南11號", "organic": False}},
        ],
    }

    normalized = _normalize_scenario_data(raw)
    cats = normalized["categories"]
    assert cats[0]["is_control"] is True
    assert cats[1]["name"] == "台農71號"
    assert cats[1]["treatment"] == "台農71號"
    assert cats[1]["dose"] == ""
    assert cats[2]["name"] == "台南11號"
    assert cats[2]["dose"] == ""


def test_upsert_trial_scenario_form_tool_saves_and_records_event() -> None:
    task = Task(id="proj-1", name="水稻田區", images=10, progress=100)
    port = _InMemoryTaskPort(task)
    deps = ChatDeps(project_id="proj-1", task_port=port)

    class _FakeCtx:
        def __init__(self, d: ChatDeps) -> None:
            self.deps = d

    res = asyncio.run(
        upsert_trial_scenario_form(
            _FakeCtx(deps),  # type: ignore[arg-type]
            scenario_type="variety",
            title="水稻品種試驗",
            description="比較不同水稻品種生長勢",
            control_label="標準對照 (CK)",
            metadata_fields=[DynamicFieldInput(key="crop", label="作物", type="text")],
            metadata_values={"crop": "水稻"},
            group_fields=[
                DynamicFieldInput(key="variety", label="品種名稱", type="text", required=True),
                DynamicFieldInput(key="sowing_date", label="播種日期", type="date"),
            ],
            groups=[
                TrialGroupInput(values={"variety": "台農71號", "sowing_date": "2026-08-01"}),
                TrialGroupInput(values={"variety": "高雄147號", "sowing_date": "2026-08-01"}),
            ],
        )
    )

    assert res["status"] == "saved"
    assert len(port.saved_scenarios) == 1
    assert len(deps.scenario_events) == 1
    saved = port.saved_scenarios[0]
    assert saved["categories"][0]["is_control"] is True
    assert saved["categories"][0]["name"] == "標準對照 (CK)"
    assert saved["categories"][1]["treatment"] == "台農71號"
    assert saved["categories"][1]["dose"] == ""


def test_stream_agent_dialogue_scenario_mode_emits_scenario_updated_event() -> None:
    task = Task(id="proj-stream", name="測試專案", images=5, progress=100)
    port = _InMemoryTaskPort(task)
    usecase = _DummyUseCase(port)

    test_model = TestModel(
        call_tools=["upsert_trial_scenario_form"],
        custom_output_text="已幫你建好表單囉！",
    )

    async def _collect() -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        with scenario_agent.override(model=test_model):
            async for chunk in _stream_agent_dialogue(
                prompt="我想做水稻品種比較",
                project_id="proj-stream",
                usecase=usecase,  # type: ignore[arg-type]
                task_port=port,
                mode="scenario",
            ):
                for line in chunk.decode("utf-8").splitlines():
                    if line.strip():
                        events.append(json.loads(line))
        return events

    events = asyncio.run(_collect())
    scenario_events = [e for e in events if e.get("type") == "scenario_updated"]
    assert len(scenario_events) == 1
    assert scenario_events[0]["scenario"]["version"] == 2
    assert scenario_events[0]["scenario"]["categories"][0]["is_control"] is True
    assert any(
        e.get("role") == "assistant" and "已幫你建好表單囉" in e["versions"][0]["content"]
        for e in events
    )


def test_ask_clarifying_question_tool_normalizes_and_records_event() -> None:
    task = Task(id="proj-q", name="玉米田區", images=8, progress=100)
    port = _InMemoryTaskPort(task)
    deps = ChatDeps(project_id="proj-q", task_port=port)

    class _FakeCtx:
        def __init__(self, d: ChatDeps) -> None:
            self.deps = d

    res = asyncio.run(
        ask_clarifying_question(
            _FakeCtx(deps),  # type: ignore[arg-type]
            question="這次試驗的目標作物是什麼？",
            options=[
                InterviewQuestionOption(label="玉米", description="雜糧作物", recommended=False),
                InterviewQuestionOption(label="水稻", description="常見水田試驗", recommended=True),
                InterviewQuestionOption(label="甘藍", description="葉菜類", recommended=True),
            ],
            is_multi_select=False,
            step_label="第 2 步 · 確認作物",
            can_generate_now=False,
        )
    )

    assert res["status"] == "question_rendered"
    assert len(deps.question_events) == 1
    q = deps.question_events[0]
    assert q["question"] == "這次試驗的目標作物是什麼？"
    assert q["step_label"] == "第 2 步 · 確認作物"
    # Recommended option moved to index 0, and single-select enforces at most 1 recommended
    assert q["options"][0]["label"] == "水稻"
    assert q["options"][0]["recommended"] is True
    assert sum(1 for o in q["options"] if o["recommended"]) == 1


def test_stream_agent_dialogue_emits_interview_question_event() -> None:
    task = Task(id="proj-q-stream", name="測試專案", images=5, progress=100)
    port = _InMemoryTaskPort(task)
    usecase = _DummyUseCase(port)

    test_model = TestModel(
        call_tools=["ask_clarifying_question"],
        custom_output_text="好喔，我們先確認一下作物種類～",
    )

    async def _collect() -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        with scenario_agent.override(model=test_model):
            async for chunk in _stream_agent_dialogue(
                prompt="我想做農藥藥效試驗",
                project_id="proj-q-stream",
                usecase=usecase,  # type: ignore[arg-type]
                task_port=port,
                mode="scenario",
            ):
                for line in chunk.decode("utf-8").splitlines():
                    if line.strip():
                        events.append(json.loads(line))
        return events

    events = asyncio.run(_collect())
    q_events = [e for e in events if e.get("type") == "interview_question"]
    assert len(q_events) == 1
    assert "question" in q_events[0]
    assert isinstance(q_events[0]["question"]["options"], list)


def test_extract_pending_interview_question_from_history() -> None:
    q_call = ModelResponse(
        parts=[
            ToolCallPart(
                tool_name="ask_clarifying_question",
                args={
                    "question": "請選擇作物",
                    "options": [{"label": "水稻", "recommended": True}, {"label": "玉米"}],
                    "is_multi_select": False,
                },
            )
        ]
    )
    pending = _extract_pending_interview_question([q_call])
    assert pending is not None
    assert pending["question"] == "請選擇作物"
    assert pending["options"][0]["label"] == "水稻"

    # Once user answers, pending question is cleared
    answered = _extract_pending_interview_question(
        [q_call, ModelRequest(parts=[UserPromptPart(content="水稻")])]
    )
    assert answered is None

    # Once form is upserted, pending question is cleared
    form_saved = _extract_pending_interview_question(
        [
            q_call,
            ModelResponse(parts=[ToolCallPart(tool_name="upsert_trial_scenario_form", args={})]),
        ]
    )
    assert form_saved is None
