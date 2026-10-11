from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4
from typing import Protocol
from copy import deepcopy

from src.entity import Conversation, Message


class ConversationNotFoundError(Exception):
    pass


class ConversationRepository(Protocol):
    def __init__(self, session) -> None: ...
    def save(
        self, id: uuid4, data: dict, updated_at: datetime | None = None
    ) -> None: ...
    def load(self, id: uuid4) -> Conversation | None: ...


@dataclass(frozen=True)
class CreateConversationInput:
    data: dict = field(default_factory=dict)


@dataclass(frozen=True)
class CreateConversationOutput:
    conversation_id: UUID


class CreateConversationUsecase:
    def __init__(self, repo: ConversationRepository) -> None:
        self._repo = repo

    def execute(
        self, input_: CreateConversationInput | None = None
    ) -> CreateConversationOutput:
        data = input_.data if input_ else {}
        conversation_id = uuid4()
        self._repo.save(id=conversation_id, data=data)
        return CreateConversationOutput(conversation_id=conversation_id)


@dataclass(frozen=True)
class ReadConversationInput:
    conversation_id: UUID


@dataclass(frozen=True)
class ReadConversationOutput:
    conversation: Conversation


class ReadConversationUsecase:
    def __init__(self, repo: ConversationRepository) -> None:
        self._repo = repo

    def execute(
        self, input_: ReadConversationInput | None = None
    ) -> ReadConversationOutput:
        conversation = self._repo.load(input_.conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(
                f"Conversation not found: {input_.conversation_id}"
            )
        return ReadConversationOutput(conversation=conversation)


@dataclass(frozen=True)
class UpdateConversationInput:
    conversation_id: UUID
    data: dict


@dataclass(frozen=True)
class UpdateConversationOutput:
    conversation_id: UUID


class UpdateConversationUsecase:
    def __init__(self, repo: ConversationRepository) -> None:
        self._repo = repo

    def execute(self, input_: UpdateConversationInput) -> UpdateConversationOutput:
        if self._repo.load(input_.conversation_id) is None:
            raise ConversationNotFoundError(
                f"Conversation not found: {input_.conversation_id}"
            )
        self._repo.save(
            id=input_.conversation_id,
            data=input_.data,
            updated_at=datetime.now(UTC),
        )
        return UpdateConversationOutput(conversation_id=input_.conversation_id)
