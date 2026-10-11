import uuid
from datetime import UTC, datetime

from sqlmodel import Field, Session, SQLModel, Column, JSON
from pydantic import NaiveDatetime

from src.entity import Conversation


class ConversationModel(SQLModel, table=True):
    __tablename__ = "conversation"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    messages: list[dict] = Field(sa_column=Column(JSON))
    created_at: NaiveDatetime = Field(default_factory=lambda: datetime.now())
    updated_at: NaiveDatetime = Field(default_factory=lambda: datetime.now())


class SQLiteConversationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(
        self,
        id: uuid.UUID,
        messages: list[dict] | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        if isinstance(id, str):
            id = uuid.UUID(id)
        row = self._session.get(ConversationModel, id)
        if row is None:
            row = ConversationModel(id=id)
        row.updated_at = updated_at or datetime.now(UTC)
        row.messages = messages or []
        self._session.add(row)
        self._session.commit()

    def load(self, id: uuid.UUID | str) -> Conversation | None:
        if isinstance(id, str):
            id = uuid.UUID(id)
        row = self._session.get(ConversationModel, id)
        if row is None:
            return None
        return Conversation(
            id=row.id,
            messages=row.messages,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

