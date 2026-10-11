from dataclasses import dataclass
from typing import List

from src.entity.message import Message

from src.usecase.port.agent import Agent


@dataclass
class PostMessageInput:
    key: str
    from_: str
    versions: List[MessageVersion]


@dataclass
class PostMessageOutput:
    key: str
    from_: str
    versions: List[MessageVersion]


class PostMessageUsecase:
    def __init__(self, agent: Agent) -> None:
        self._agent = agent

    def execute(self, input_: PostMessageInput) -> PostMessageOutput:
        return self._agent.reply(input_)
