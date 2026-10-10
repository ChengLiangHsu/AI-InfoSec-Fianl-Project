from typing import Protocol

from src.entity.conversation import Conversation
from src.entity.message import Message


class AgentGateway(Protocol):
    def reply_to(self, conversation: Conversation) -> Message: ...
