from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.adapter.gateway.agent.fake import FakeAgent
from src.adapter.presenter.message_presenter import present_reply
from src.usecase import PostMessageInput, PostMessageUsecase, PostMessageOutput
from src.entity import (
    Message,
    MessageReasoning,
    MessageSource,
    MessageTool,
    MessageVersion,
    Sender,
)


class MessageController:
    def __init__(self, post_message_usecase: PostMessageUsecase):
        self.post_message_usecase = post_message_usecase

    def post_message(self, request: MessageRequest) -> dict:
        input_ = PostMessageInput(**request.model_dump())
        output = self.post_message_usecase.execute(input_)
        return present_reply(output.message)
