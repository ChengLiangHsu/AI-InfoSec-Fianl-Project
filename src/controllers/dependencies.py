from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlmodel import Session

from src.database import get_session
from src.config import NODEODM_URL
from src.repositories.task_repo import TaskRepository
from src.requesters.odm import OdmRequester
from src.usecases.ports.odm import OdmPort
from src.usecases.ports.task import TaskPort
from src.usecases.task import TaskUseCase

def get_task_repo(request: Request, session: Session = Depends(get_session)) -> TaskPort:
    """依賴注入工廠：建立依賴當前 Request-Scoped Session 之 TaskRepository 倉儲實例。"""
    return TaskRepository(session, owner_id=request.state.owner_id)


async def get_odm_requester() -> AsyncGenerator[OdmRequester, None]:
    """依賴注入工廠：建立與 NodeODM 伺服器通訊之 OdmRequester 適配器實例。"""
    requester = OdmRequester(base_url=NODEODM_URL)
    try:
        yield requester
    finally:
        await requester.aclose()


def get_task_usecase(
    task_repo: TaskPort = Depends(get_task_repo),
    odm_requester: OdmPort = Depends(get_odm_requester),
) -> TaskUseCase:
    """依賴注入工廠：注入 TaskPort 與 OdmPort 契約介面，建構領域應用層 TaskUseCase 用例實例。"""
    return TaskUseCase(task_port=task_repo, odm_port=odm_requester)
