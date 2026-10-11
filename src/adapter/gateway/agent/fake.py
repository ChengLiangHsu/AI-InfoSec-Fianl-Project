from nanoid import generate

from src.entity import Message, MessageReasoning, MessageVersion, Sender
from src.usecase.port.agent import Agent


class FakeAgent(Agent):
    def reply(self, message: Message) -> Message:
        return Message(
            key=generate(),
            from_=Sender.ASSISTANT,
            versions=(MessageVersion(id=generate(), content="test"),),
        )
