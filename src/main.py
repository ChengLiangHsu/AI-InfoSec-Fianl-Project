import os
import json
import asyncio
from dataclasses import dataclass
from datetime import datetime
from collections.abc import AsyncIterable, Iterable
from typing import Annotated, Any, Literal, TypeVar

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from httpx import AsyncClient
from pydantic import BaseModel
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
    RunContext
)
from typing_extensions import LiteralString, ParamSpec, TypedDict

from .usecase import ReadConversationUsecase, UpdateConversationUsecase
from .adapter.controller import ReadConversationController, UpdateConversationController
from .adapter.gateway.repo import SQLiteConversationRepository
from .database import get_session, create_db_and_tables

app = FastAPI()

model = os.getenv("PYDANTIC_AI_MODEL", "google:gemini-3.7-flash")

@dataclass
class Deps:
    client: AsyncClient

weather_agent = Agent(
    model,
    instructions='以繁體中文回答，天氣的問題',
    deps_type=Deps,
    retries=2,
)

class LatLng(BaseModel):
    lat: float
    lng: float

@weather_agent.tool
async def get_lat_lng(ctx: RunContext[Deps], location_description: str) -> LatLng:
    """Get the latitude and longitude of a location.
    Args:
        ctx: The context.
        location_description: A description of a location.
    """
    # NOTE: the response here will be random, and is not related to the location description.
    r = await ctx.deps.client.get(
        'https://demo-endpoints.pydantic.workers.dev/latlng',
        params={'location': location_description},
    )
    r.raise_for_status()
    return LatLng.model_validate_json(r.content)

@weather_agent.tool
async def get_weather(ctx: RunContext[Deps], lat: float, lng: float) -> dict[str, Any]:
    """Get the weather at a location.
    Args:
        ctx: The context.
        lat: Latitude of the location.
        lng: Longitude of the location.
    """
    # NOTE: the responses here will be random, and are not related to the lat and lng.
    temp_response, descr_response = await asyncio.gather(
        ctx.deps.client.get(
            'https://demo-endpoints.pydantic.workers.dev/number',
            params={'min': 10, 'max': 30},
        ),
        ctx.deps.client.get(
            'https://demo-endpoints.pydantic.workers.dev/weather',
            params={'lat': lat, 'lng': lng},
        ),
    )
    temp_response.raise_for_status()
    descr_response.raise_for_status()
    return {
        'temperature': f'{temp_response.text} °C',
        'description': descr_response.text,
    }

async def main():
    async with AsyncClient() as client:
        logfire.instrument_httpx(client, capture_all=True)
        deps = Deps(client=client)
        result = await weather_agent.run(
            'What is the weather like in London and in Wiltshire?', deps=deps
        )
        print('Response:', result.output)

sessionDep = Annotated[Session, Depends(get_session, scope="function")]


def build_controller(
    session: sessionDep,
) -> tuple[ReadConversationController, UpdateConversationController]:
    repo = SQLiteConversationRepository(session)
    read_conversation_usecase = ReadConversationUsecase(repo=repo)
    update_conversation_usecase = UpdateConversationUsecase(repo=repo)
    return ReadConversationController(
        usecase=read_conversation_usecase
    ), UpdateConversationController(usecase=update_conversation_usecase)


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


class ChatRequest(BaseModel):
    prompt: str


@app.post("/chat", response_class=StreamingResponse)
async def chat(
    request: ChatRequest,
    controllers: tuple[
        ReadConversationController, UpdateConversationController
    ] = Depends(build_controller),
) -> AsyncIterable[str]:
    read_conversation_controller, update_conversation_controller = controllers
    conversation = read_conversation_controller.handle({
        "id": "c6ef5aa80d62417dac43ba0066a20474"
    })
    async with AsyncClient() as client:
        deps = Deps(client=client)
        result = await weather_agent.run(request.prompt, deps=deps)
    for line in result.output.splitlines():
        yield line + "\n"
