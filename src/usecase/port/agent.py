from typing import Protocol


from src.entity.message import Message


class Agent(Protocol):
    def reply(self, message: Message) -> Message: ...
