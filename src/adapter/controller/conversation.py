from src.usecase.conversation import (
    CreateConversationInput,
    CreateConversationUsecase,
    ReadConversationInput,
    ReadConversationUsecase,
    UpdateConversationInput,
    UpdateConversationUsecase,
)
from src.entity.conversation import Conversation


class CreateConversationController:
    def __init__(self, usecase: CreateConversationUsecase) -> None:
        self._usecase = usecase

    def handle(self, request: dict | None = None) -> str:
        request = request or {}
        input_ = CreateConversationInput(
            data=request.get("data") or {},
        )
        output = self._usecase.execute(input_)
        return str(output.conversation_id)


class ReadConversationController:
    def __init__(self, usecase: ReadConversationUsecase) -> None:
        self._usecase = usecase

    def handle(self, request: dict | None = None) -> Conversation:
        request = request or {}
        input_ = ReadConversationInput(
            id=request.get("id"),
        )
        output = self._usecase.execute(input_)
        return output.conversation


class UpdateConversationController:
    def __init__(self, usecase: UpdateConversationUsecase) -> None:
        self._usecase = usecase

    def handle(self, request: dict | None = None) -> str:
        request = request or {}
        input_ = UpdateConversationInput(
            id=request.get("id"),
            messages=request.get("messages") or [],
        )
        output = self._usecase.execute(input_)
        return str(output.conversation_id)
