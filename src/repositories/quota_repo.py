from datetime import datetime, timezone

from sqlalchemy import text
from sqlmodel import Field, Session, SQLModel

from src.config import MAX_CHAT_REQUESTS_PER_DAY


class UsageCounter(SQLModel, table=True):
    __tablename__ = "usage_counters"
    key: str = Field(primary_key=True)
    count: int = 0


def reserve_chat_request(session: Session) -> bool:
    """使用原子更新保留每日全站 AI 額度，重啟後仍維持累計。"""
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = session.execute(text(
        "INSERT INTO usage_counters (key, count) VALUES (:key, 1) "
        "ON CONFLICT(key) DO UPDATE SET count = count + 1 "
        "WHERE count < :limit RETURNING count"
    ), {"key": f"chat:{day}", "limit": MAX_CHAT_REQUESTS_PER_DAY}).first()
    session.commit()
    return row is not None
