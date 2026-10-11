from typing import Annotated


from fastapi import APIRouter, Depends


from pydantic import BaseModel, ConfigDict, Field


from src.adapter.controller.message import AgentController

from src.adapter.gateway.agent.fake import FakeAgent

from src.entity import (
    Message,
    MessageReasoning,
    MessageSource,
    MessageTool,
    MessageVersion,
    Sender,
)


from src.usecase import AskUsecase


router = APIRouter(prefix="/api/message", tags=["message"])


def build_controller() -> AgentController:

    return AgentController(AskUsecase(FakeAgent()))


class AskRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    key: str

    from_: Sender = Field(alias="from")

    versions: list[MessageVersion]

    sources: list[MessageSource] | None = None

    reasoning: MessageReasoning | None = None

    tools: list[MessageTool] | None = None


class AskResponse(BaseModel):
    result: bool

    data: dict | None = None


@router.post("/", response_model=AskResponse)
def post_message(
    request: AskRequest,
    controller: Annotated[AgentController, Depends(build_controller)],
) -> dict:

    message = Message(
        key=request.key,
        from_=request.from_,
        versions=tuple(request.versions),
        sources=None if request.sources is None else tuple(request.sources),
        reasoning=request.reasoning,
        tools=None if request.tools is None else tuple(request.tools),
    )

    return controller.ask(message)
