from typing import Annotated

from fastapi import APIRouter, Depends
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


router = APIRouter(prefix="/api/message", tags=["訊息"])


def build_controller() -> MessageController:
    return MessageController(FakeAgentGateway())


class PostMessageRequest(BaseModel):
    key: str
    from_: Sender = Field(alias="from")
    versions: list[MessageVersion]
    sources: list[MessageSource] | None = None
    reasoning: MessageReasoning | None = None
    tools: list[MessageTool] | None = None


class PostMessageResponse(BaseModel):
    result: bool
    data: dict | None = None


@router.post("/", response_model=PostMessageResponse)
def post_message(
    request: PostMessageRequest,
    controller: Annotated[MessageController, Depends(build_controller)],
) -> PostMessageResponse:
    message = Message(
        key=request.key,
        from_=request.from_,
        versions=tuple(request.versions),
        sources=None if request.sources is None else tuple(request.sources),
        reasoning=request.reasoning,
        tools=None if request.tools is None else tuple(request.tools),
    )
    result = controller.post_message(request)
    return PostMessageResponse(result=True, data=result)
