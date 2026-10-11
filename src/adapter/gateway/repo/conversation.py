import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field, Session, SQLModel

from src.entity import Conversation


class ConversationModel(SQLModel, table=True):
    __tablename__ = "conversation"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    data: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SQLiteConversationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(
        self,
        id: uuid.UUID,
        data: dict | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        id = uuid.UUID(str(id))
        row = self._session.get(ConversationModel, id)
        if row is None:
            row = ConversationModel(id=id)
        row.updated_at = updated_at or datetime.now(UTC)
        row.data = data or {}
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
            data=row.data,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

