from src.entity.message import Message
from src.usecase.port.agent import AgentGateway


class MessageUsecase:
    def __init__(self, gateway: AgentGateway) -> None:
        self._gateway = gateway

    def reply(self, message: Message) -> Message:
        return self._gateway.reply_to(message)
