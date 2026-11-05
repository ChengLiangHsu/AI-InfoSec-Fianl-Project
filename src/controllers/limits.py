import asyncio

from fastapi import Depends, HTTPException
from sqlmodel import Session

from src.database import get_session
from src.repositories.quota_repo import reserve_chat_request

SUBMISSION_LOCK = asyncio.Lock()


def consume_chat_quota(session: Session = Depends(get_session)) -> None:
    """在開始串流前檢查全站每日 AI 請求額度。"""
    if not reserve_chat_request(session):
        raise HTTPException(429, "今日 AI 使用額度已用完，請明日再試")
