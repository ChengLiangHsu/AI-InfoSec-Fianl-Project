import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.controllers.odm import _format_sse_data, _is_task_finished
from src.database import Database, Project
from src.main import app


def test_format_sse_data():
    payload = {"id": "task-123", "progress": 50}
    encoded = _format_sse_data(payload)
    assert encoded == b'data: {"id": "task-123", "progress": 50}\n\n'


def test_is_task_finished():
    assert _is_task_finished(100, 20) is True
    assert _is_task_finished(105, None) is True
    assert _is_task_finished(50, 40) is True  # 40: COMPLETED
    assert _is_task_finished(30, 30) is True  # 30: FAILED
    assert _is_task_finished(30, 50) is True  # 50: CANCELED
    assert _is_task_finished(50, 20) is False  # 20: RUNNING
    assert _is_task_finished(0, 10) is False  # 10: QUEUED


@pytest.mark.anyio
async def test_stream_odm_task_progress_completed():
    fake_project = Project(
        id="test-completed-uuid",
        name="Test Completed Project",
        images=5,
        progress=100,
    )

    mock_db = AsyncMock(spec=Database)
    mock_db.get_project.return_value = fake_project
    mock_db.update_project.return_value = None

    # 模擬 NodeODM 回傳 completed 狀態
    fake_nodeodm_info = {
        "progress": 100,
        "imagesCount": 5,
        "status": {"code": 40},
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("src.controllers.odm.NODEODM_URL", "http://fake-nodeodm"):
            with patch("httpx.AsyncClient.get") as mock_http_get:
                mock_resp = AsyncMock()
                mock_resp.status_code = 200
                mock_resp.json = lambda: fake_nodeodm_info
                mock_http_get.return_value = mock_resp

                # 覆蓋資料庫依賴
                from src.controllers.dependencies import get_db

                app.dependency_overrides[get_db] = lambda: mock_db
                try:
                    async with client.stream("GET", "/odm-task-stream/test-completed-uuid") as response:
                        assert response.status_code == 200
                        assert "text/event-stream" in response.headers["content-type"]
                        lines = []
                        async for line in response.aiter_lines():
                            if line.strip():
                                lines.append(line.strip())
                        assert len(lines) >= 1
                        assert lines[0].startswith("data: ")
                        data = json.loads(lines[0][6:])
                        assert data["id"] == "test-completed-uuid"
                        assert data["progress"] == 100
                finally:
                    app.dependency_overrides.pop(get_db, None)


@pytest.mark.anyio
async def test_stream_odm_task_not_found():
    mock_db = AsyncMock(spec=Database)
    mock_db.get_project.side_effect = KeyError("專案不存在")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("src.controllers.odm.NODEODM_URL", "http://fake-nodeodm"):
            with patch("httpx.AsyncClient.get") as mock_http_get:
                mock_resp = AsyncMock()
                mock_resp.status_code = 404
                mock_http_get.return_value = mock_resp

                from src.controllers.dependencies import get_db

                app.dependency_overrides[get_db] = lambda: mock_db
                try:
                    async with client.stream("GET", "/odm-task-stream/nonexistent-id") as response:
                        assert response.status_code == 200
                        lines = []
                        async for line in response.aiter_lines():
                            if line.strip():
                                lines.append(line.strip())
                        assert len(lines) == 1
                        data = json.loads(lines[0][6:])
                        assert "error" in data
                finally:
                    app.dependency_overrides.pop(get_db, None)


@pytest.mark.anyio
async def test_stream_odm_task_progress_step_update():
    # 第一次回傳 30%，第二次回傳 100%
    proj_step1 = Project(id="step-uuid", name="Step Project", images=3, progress=30)
    proj_step2 = Project(id="step-uuid", name="Step Project", images=3, progress=100)

    mock_db = AsyncMock(spec=Database)
    mock_db.get_project.side_effect = [proj_step1, proj_step2]
    mock_db.update_project.return_value = None

    info_step1 = {"progress": 30, "imagesCount": 3, "status": {"code": 20}}
    info_step2 = {"progress": 100, "imagesCount": 3, "status": {"code": 40}}

    resp1 = AsyncMock()
    resp1.status_code = 200
    resp1.json = lambda: info_step1

    resp2 = AsyncMock()
    resp2.status_code = 200
    resp2.json = lambda: info_step2

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("src.controllers.odm.NODEODM_URL", "http://fake-nodeodm"):
            with patch("httpx.AsyncClient.get", side_effect=[resp1, resp2]):
                from src.controllers.dependencies import get_db

                app.dependency_overrides[get_db] = lambda: mock_db
                try:
                    async with client.stream("GET", "/odm-task-stream/step-uuid") as response:
                        assert response.status_code == 200
                        lines = []
                        async for line in response.aiter_lines():
                            if line.strip():
                                lines.append(line.strip())
                        assert len(lines) == 2
                        data1 = json.loads(lines[0][6:])
                        data2 = json.loads(lines[1][6:])
                        assert data1["progress"] == 30
                        assert data2["progress"] == 100
                finally:
                    app.dependency_overrides.pop(get_db, None)

