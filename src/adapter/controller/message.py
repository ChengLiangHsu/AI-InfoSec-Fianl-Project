from src.adapter.presenter.message_presenter import present_reply
from src.entity import Message
from src.usecase import AskInput, AskUsecase


class AgentController:
    def __init__(self, ask_usecase: AskUsecase) -> None:
        self._ask_usecase = ask_usecase

    def ask(self, message: Message) -> dict:
        output = self._ask_usecase.execute(AskInput(message=message))
        return present_reply(output.message)
