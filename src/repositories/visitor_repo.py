from __future__ import annotations

import hashlib
import secrets
import time
from dataclasses import dataclass
from uuid import uuid4

from sqlmodel import Field, Session, SQLModel, select

from src.config import VISITOR_MAX_AGE


class VisitorModel(SQLModel, table=True):
    __tablename__ = "visitors"

    id: str = Field(primary_key=True)
    token_hash: str = Field(unique=True, index=True)
    expires_at: int


@dataclass(frozen=True)
class VisitorIdentity:
    owner_id: str
    token: str


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _find_visitor(session: Session, token: str, now: int) -> VisitorModel | None:
    if len(token) != 43:
        return None
    return session.exec(
        select(VisitorModel).where(
            VisitorModel.token_hash == _hash_token(token),
            VisitorModel.expires_at > now,
        )
    ).first()


def resolve_visitor(session: Session, token: str) -> VisitorIdentity:
    """查驗既有憑證或建立匿名身分，延長有效期限。"""
    now = int(time.time())
    visitor = _find_visitor(session, token, now)
    if visitor is None:
        token = secrets.token_urlsafe(32)
        visitor = VisitorModel(
            id=str(uuid4()), token_hash=_hash_token(token),
            expires_at=now + VISITOR_MAX_AGE,
        )
    visitor.expires_at = now + VISITOR_MAX_AGE
    session.add(visitor)
    session.commit()
    return VisitorIdentity(owner_id=visitor.id, token=token)
