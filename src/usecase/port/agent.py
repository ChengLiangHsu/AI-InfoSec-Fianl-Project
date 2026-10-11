from typing import Protocol


from src.entity.message import Message


class BaseAgent(Protocol):
    def reply(self, message: Message) -> Message: ...
