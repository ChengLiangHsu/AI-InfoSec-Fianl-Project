from dataclasses import dataclass, field

from src.entity.message import Message


@dataclass(frozen=True)
class Conversation:
    messages: tuple[Message, ...] = field(default_factory=tuple)
