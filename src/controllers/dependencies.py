from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import Depends
from sqlmodel import Session

from src.database import get_session
from src.repositories.task_repo import TaskRepository
from src.requesters.odm import OdmRequester
from src.usecases.ports.odm import OdmPort
from src.usecases.ports.task import TaskPort
from src.usecases.task import TaskUseCase

load_dotenv()
NODEODM_URL = os.getenv("NODEODM_URL", "http://localhost:3002")


def get_task_repo(session: Session = Depends(get_session)) -> TaskPort:
    """依賴注入工廠：建立依賴當前 Request-Scoped Session 之 TaskRepository 倉儲實例。"""
    return TaskRepository(session)


def get_odm_requester() -> OdmPort:
    """依賴注入工廠：建立與 NodeODM 伺服器通訊之 OdmRequester 適配器實例。"""
    return OdmRequester(base_url=NODEODM_URL)


def get_task_usecase(
    task_repo: TaskPort = Depends(get_task_repo),
) -> TaskUseCase:
    """依賴注入工廠：注入 TaskPort 契約介面，建構領域應用層 TaskUseCase 用例實例。"""
    return TaskUseCase(task_port=task_repo)
