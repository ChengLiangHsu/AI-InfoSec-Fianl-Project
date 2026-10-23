import pytest
import asyncio
from pathlib import Path
from src.main import agent, ChatDeps, Database

import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def test_agent_tools_and_vision_with_project():
    async def _run():
        async with Database.connect() as db:
            projects = await db.get_projects()
            if not projects:
                pytest.skip("No projects in database")
            proj_id = projects[0]["id"]
            deps = ChatDeps(project_id=proj_id, database=db)

            # 1. 測試專案資訊與光譜統計 Tool
            res1 = await agent.run(
                "請幫我檢查當前專案的正射圖狀態，並計算 VARI 光譜統計。",
                deps=deps
            )
            assert res1.output
            assert len(res1.output) > 10

            # 2. 測試多模態視覺判讀 Tool
            res2 = await agent.run(
                "請調用視覺檢查工具觀察當前專案的 VARI 光譜圖，簡述作物長勢。",
                deps=deps
            )
            assert res2.output
            assert len(res2.output) > 10

    asyncio.run(_run())





