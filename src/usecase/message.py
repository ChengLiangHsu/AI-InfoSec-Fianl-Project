from dataclasses import dataclass

from src.entity.message import Message
from src.usecase.port.agent import Agent


@dataclass(frozen=True)
class AskInput:
    message: Message


@dataclass(frozen=True)
class AskOutput:
    message: Message


class AskUsecase:
    def __init__(self, agent: Agent) -> None:
        self._agent = agent

    def execute(self, input_: AskInput) -> AskOutput:
        return AskOutput(message=self._agent.reply(input_.message))
