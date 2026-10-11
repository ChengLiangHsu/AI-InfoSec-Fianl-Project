from nanoid import generate

from src.entity.message import Message, MessageVersion, Sender
from src.usecase.port.agent import AgentGateway

FAKE_REPLY = "這是固定的假回應。"


class FakeAgentGateway(AgentGateway):
    def reply_to(self, message: Message) -> Message:
        return Message(
            key=generate(),
            from_=Sender.ASSISTANT,
            versions=(MessageVersion(id=generate(), content=FAKE_REPLY),),
        )
