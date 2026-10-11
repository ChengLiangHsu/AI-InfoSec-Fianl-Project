from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class Sender(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class ToolState(StrEnum):
    INPUT_STREAMING = "input-streaming"
    INPUT_AVAILABLE = "input-available"
    APPROVAL_REQUESTED = "approval-requested"
    APPROVAL_RESPONDED = "approval-responded"
    OUTPUT_AVAILABLE = "output-available"
    OUTPUT_ERROR = "output-error"
    OUTPUT_DENIED = "output-denied"


@dataclass(frozen=True)
class MessageVersion:
    id: str
    content: str


@dataclass(frozen=True)
class MessageSource:
    href: str
    title: str


@dataclass(frozen=True)
class MessageReasoning:
    content: str
    duration: int


@dataclass(frozen=True)
class MessageTool:
    name: str
    description: str
    status: ToolState
    parameters: dict[str, object]
    result: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class Message:
    key: str
    from_: Sender
    versions: tuple[MessageVersion, ...]
    sources: tuple[MessageSource, ...] | None = None
    reasoning: MessageReasoning | None = None
    tools: tuple[MessageTool, ...] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
