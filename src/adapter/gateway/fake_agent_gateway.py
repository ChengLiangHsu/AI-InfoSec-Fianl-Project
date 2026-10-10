from src.entity.conversation import Conversation
from src.entity.message import Message
from src.usecase.port import AgentGateway

FAKE_REPLY = "這是固定的假回應。"


class FakeAgentGateway(AgentGateway):
    def reply_to(self, conversation: Conversation) -> Message:
        return Message(role="agent", content=FAKE_REPLY)
