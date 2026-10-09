"""
使用 Pydantic AI 處理需要依序調用多個工具來回答問題的場景。

在這個範例中，我們建立了一個「天氣」代理（agent）。使用者可以查詢多個城市的的天氣，
該代理會先使用 `get_lat_lng` 工具取得地點的經緯度，然後再使用 `get_weather` 工具取得實際的天氣資訊。

執行方式：

    uv run examples/weather_agent.py
"""

from __future__ import annotations as _annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
load_dotenv()

import logfire
from httpx import AsyncClient
from pydantic import BaseModel

from pydantic_ai import Agent, RunContext

# 'if-token-present' means nothing will be sent (and the example will work) if you don't have logfire configured
logfire.configure(send_to_logfire='if-token-present')
logfire.instrument_pydantic_ai()


@dataclass
class Deps:
    client: AsyncClient

model = os.getenv('PYDANTIC_AI_MODEL', 'google:gemini-3.7-flash')
weather_agent = Agent(
    model,
    # '請言簡意賅，用一句話回覆即可。' 對某些模型（如 OpenAI）來說就足夠了，但其他模型（如 Anthropic 和 Gemini）需要更多的指引。
    instructions='請言簡意賅，用一句話回覆即可。',
    deps_type=Deps,
    retries=2,
)


class LatLng(BaseModel):
    lat: float
    lng: float


@weather_agent.tool
async def get_lat_lng(ctx: RunContext[Deps], location_description: str) -> LatLng:
    """取得地點的經緯度。

    Args:
        ctx: 執行上下文
        location_description: 地點的描述。
    """
    # NOTE: 這裡的隨機回應與地點描述無關。
    r = await ctx.deps.client.get(
        'https://demo-endpoints.pydantic.workers.dev/latlng',
        params={'location': location_description},
    )
    r.raise_for_status()
    return LatLng.model_validate_json(r.content)


@weather_agent.tool
async def get_weather(ctx: RunContext[Deps], lat: float, lng: float) -> dict[str, Any]:
    """取得指定經緯度的天氣資訊。

    Args:
        ctx: 執行上下文
        lat: 緯度
        lng: 經度
    """
    # NOTE: 這裡的隨機回應與經緯度無關。
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
            '台灣的天氣如何？倫敦的天氣又如何？', deps=deps
        )
        print('Response:', result.output)


if __name__ == '__main__':
    asyncio.run(main())
