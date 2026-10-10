from fastapi import APIRouter
from pydantic import BaseModel

from src.adapter.gateway.fake_agent_gateway import FakeAgentGateway
from src.adapter.presenter.conversation_presenter import present_reply
from src.entity.conversation import Conversation
from src.entity.message import Message
from src.usecase.conversation import ConversationUsecase

router = APIRouter(prefix="/api/conversation")
usecase = ConversationUsecase(FakeAgentGateway())


class ConversationRequest(BaseModel):
    messages: list[Message]


@router.post("")
def post_conversation(request: ConversationRequest) -> dict:
    conversation = Conversation(messages=tuple(request.messages))
    return present_reply(usecase.reply(conversation))
