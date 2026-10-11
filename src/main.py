import os
import json
from datetime import datetime
from collections.abc import AsyncIterable, Iterable
from typing import Annotated, Any, Literal, TypeVar

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlmodel import Session
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
from typing_extensions import LiteralString, ParamSpec, TypedDict

from .usecase import ReadConversationUsecase, UpdateConversationUsecase
from .adapter.controller import ReadConversationController, UpdateConversationController
from .adapter.gateway.repo import SQLiteConversationRepository
from .database import get_session, create_db_and_tables

app = FastAPI()

model = os.getenv("PYDANTIC_AI_MODEL", "google:gemini-3.7-flash")
agent = Agent(model)

sessionDep = Annotated[Session, Depends(get_session, scope="function")]

def build_controller(session:sessionDep) -> tuple[ReadConversationController, UpdateConversationController]:
    repo = SQLiteConversationRepository(session)
    read_conversation_usecase = ReadConversationUsecase(repo=repo)
    update_conversation_usecase = UpdateConversationUsecase(repo=repo)
    return ReadConversationController(usecase=read_conversation_usecase), UpdateConversationController(usecase=update_conversation_usecase)

origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(TypedDict):
    """Format of messages sent to the browser."""

    role: Literal["user", "model"]
    timestamp: str
    content: str


def to_chat_message(m: ModelMessage) -> ChatMessage:
    first_part = m.parts[0]
    if isinstance(m, ModelRequest):
        if isinstance(first_part, UserPromptPart):
            assert isinstance(first_part.content, str)
            return {
                "role": "user",
                "timestamp": first_part.timestamp.isoformat(),
                "content": first_part.content,
            }
    elif isinstance(m, ModelResponse):
        if isinstance(first_part, TextPart):
            return {
                "role": "model",
                "timestamp": m.timestamp.isoformat(),
                "content": first_part.content,
            }
    raise UnexpectedModelBehavior(f"Unexpected message type for chat app: {m}")


message = """
Rick: (stumbles in drunkenly, and turns on the lights) Morty! You gotta come on. You got--... you gotta come with me.
Morty: (rubs his eyes) What, Rick? What's going on?
Rick: I got a surprise for you, Morty.
Morty: It's the middle of the night. What are you talking about?
Rick: (spills alcohol on Morty's bed) Come on, I got a surprise for you. (drags Morty by the ankle) Come on, hurry up. (pulls Morty out of his bed and into the hall)
Morty: Ow! Ow! You're tugging me too hard!
Rick: We gotta go, gotta get outta here, come on. Got a surprise for you Morty.
"""

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.post("/chat/")
async def post_chat(
    prompt:str, controllers: tuple[ReadConversationController, UpdateConversationController] = Depends(build_controller)
) -> StreamingResponse:
    read_conversation_controller, update_conversation_controller = controllers
    async def stream_messages():
        """Streams new line delimited JSON `Message`s to the client."""
        # stream the user prompt so that can be displayed straight away
        yield (
            json.dumps(
                {
                    "role": "user",
                    "timestamp": datetime.now().isoformat(),
                    "content": prompt,
                }
            ).encode("utf-8")
            + b"\n"
        )
        # get the chat history so far to pass as context to the agent
        messages = read_conversation_controller.handle({"id": "8c1e9ce1ef5741afa774ad101830ef10"}).messages
        messages = ModelMessagesTypeAdapter.validate_python(messages) if messages else None
        # run the agent with the user prompt and the chat history
        async with agent.run_stream(prompt, message_history=messages) as result:
            async for text in result.stream_output(debounce_by=0.01):
                # text here is a `str` and the frontend wants
                # JSON encoded ModelResponse, so we create one
                m = ModelResponse(parts=[TextPart(text)], timestamp=result.timestamp)
                yield json.dumps(to_chat_message(m)).encode("utf-8") + b"\n"

        # add new messages (e.g. the user prompt and the agent response in this case) to the database
        update_conversation_controller.handle({"id": "8c1e9ce1ef5741afa774ad101830ef10", "messages": json.loads(result.new_messages_json())})
    
    return StreamingResponse(stream_messages(), media_type="text/plain")

@app.get("/story/stream", response_class=StreamingResponse)
async def stream_story() -> AsyncIterable[str]:
    for line in message.splitlines():
        yield line + '\n'