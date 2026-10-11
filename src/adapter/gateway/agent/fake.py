from uuid import uuid4


from src.entity import Message, MessageReasoning, MessageVersion, Sender

from src.usecase.port.agent import BaseAgent


class FakeAgent(BaseAgent):
    def reply(self, message: Message) -> Message:
        return Message(
            key=str(uuid4()),
            from_=Sender.ASSISTANT,
            versions=(MessageVersion(id=str(uuid4()), content="這是假的回應"),),
        )
