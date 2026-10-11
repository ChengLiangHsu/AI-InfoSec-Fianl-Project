from uuid import uuid4
from enum import StrEnum


from pydantic_ai import Agent


from src.entity import Message, MessageVersion, Sender

from src.usecase.port.agent import BaseAgent

from pydantic_ai import (
    Agent,
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    TextPart,
    UnexpectedModelBehavior,
    UserPromptPart,
)
from pydantic_ai.usage import UsageLimits


def add_numbers(a: float, b: float) -> float:
    """將兩個數字相加。"""
    return a + b


class GoogleGeminiModel(StrEnum):
    GEMINI_3_7_FLASH = "google:gemini-3.7-flash"


class GoogleGeminiAgent(BaseAgent):
    def __init__(self, model: str) -> None:

        self._agent = Agent(
            model,
            instructions="你是無人機田間試驗評估助理。不可捏造分析結果。",
            tools=[add_numbers],
        )

    def reply(self, message: Message, context: list[Message] = []) -> Message:
        prompt = message.versions[-1].content
        history: list[ModelMessage] = [
            (
                ModelRequest(parts=[UserPromptPart(content=m.versions[-1].content)])
                if m.from_ == Sender.USER
                else ModelResponse(parts=[TextPart(content=m.versions[-1].content)])
            )
            for m in context
        ]
        result = self._agent.run_sync(
            prompt,
            message_history=history,
            usage_limits=UsageLimits(
                request_limit=4,
                tool_calls_limit=2,
                output_tokens_limit=1000,
            ),
        )

        return Message(
            key=str(uuid4()),
            from_=Sender.ASSISTANT,
            versions=(
                MessageVersion(
                    id=str(uuid4()),
                    content=result.output,
                ),
            ),
        )
