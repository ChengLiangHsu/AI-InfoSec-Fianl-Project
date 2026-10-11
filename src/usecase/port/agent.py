from typing import Protocol

from src.entity.message import Message


class AgentGateway(Protocol):
    def reply_to(self, message: Message) -> Message: ...
