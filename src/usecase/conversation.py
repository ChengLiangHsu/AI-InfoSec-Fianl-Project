from src.entity.conversation import Conversation
from src.entity.message import Message
from src.usecase.port.agent import AgentGateway


class ConversationUsecase:
    def __init__(self, gateway: AgentGateway) -> None:
        self._gateway = gateway

    def reply(self, conversation: Conversation) -> Message:
        return self._gateway.reply_to(conversation)
