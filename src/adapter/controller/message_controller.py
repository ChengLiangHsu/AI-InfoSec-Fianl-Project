from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.adapter.gateway.fake_agent_gateway import FakeAgentGateway
from src.adapter.presenter.message_presenter import present_reply
from src.entity.message import (
    Message,
    MessageReasoning,
    MessageSource,
    MessageTool,
    MessageVersion,
    Sender,
)
from src.usecase.message import MessageUsecase

router = APIRouter(prefix="/api/message", tags=["訊息"])
usecase = MessageUsecase(FakeAgentGateway())


class MessageRequest(BaseModel):
    key: str
    from_: Sender = Field(alias="from")
    versions: list[MessageVersion]
    sources: list[MessageSource] | None = None
    reasoning: MessageReasoning | None = None
    tools: list[MessageTool] | None = None


@router.post("")
def post_message(request: MessageRequest) -> dict:
    message = Message(
        key=request.key,
        from_=request.from_,
        versions=tuple(request.versions),
        sources=None if request.sources is None else tuple(request.sources),
        reasoning=request.reasoning,
        tools=None if request.tools is None else tuple(request.tools),
    )
    return present_reply(usecase.reply(message))
