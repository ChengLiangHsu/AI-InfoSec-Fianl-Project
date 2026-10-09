"""示範如何使用 Pydantic AI，根據使用者的輸入生成 SQL 查詢。

執行方式：

    mkdir postgres-data
    docker run --rm -e POSTGRES_PASSWORD=postgres -p 54320:5432 postgres

    uv run examples/sql_gen.py "給我看昨天 level 為 error 的 log"
"""

import os
from dotenv import load_dotenv

load_dotenv()
import asyncio
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date
from typing import Annotated, Any, TypeAlias

import asyncpg
import logfire
from annotated_types import MinLen
from devtools import debug
from pydantic import BaseModel, Field

from pydantic_ai import Agent, ModelRetry, RunContext, format_as_xml

# 'if-token-present' means nothing will be sent (and the example will work) if you don't have logfire configured
logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_asyncpg()
logfire.instrument_pydantic_ai()

DB_SCHEMA = """
CREATE TABLE records (
    created_at timestamptz,
    start_timestamp timestamptz,
    end_timestamp timestamptz,
    trace_id text,
    span_id text,
    parent_span_id text,
    level log_level,
    span_name text,
    message text,
    attributes_json_schema text,
    attributes jsonb,
    tags text[],
    is_exception boolean,
    otel_status_message text,
    service_name text
);
"""
SQL_EXAMPLES = [
    {
        "request": "給我 foobar 為 false 的記錄",
        "response": "SELECT * FROM records WHERE attributes->>'foobar' = false",
    },
    {
        "request": '給我包含 "foobar" 鍵的記錄',
        "response": "SELECT * FROM records WHERE attributes ? 'foobar'",
    },
    {
        "request": "給我昨天生成的記錄",
        "response": "SELECT * FROM records WHERE start_timestamp::date > CURRENT_TIMESTAMP - INTERVAL '1 day'",
    },
    {
        "request": '給我帶有 "foobar" 標籤的錯誤記錄',
        "response": "SELECT * FROM records WHERE level = 'error' and 'foobar' = ANY(tags)",
    },
]


@dataclass
class Deps:
    conn: asyncpg.Connection


class Success(BaseModel):
    """成功生成 SQL 的回應。"""

    sql_query: Annotated[str, MinLen(1)]
    explanation: str = Field("", description="SQL 查詢的解釋，以 markdown 格式呈現")


class InvalidRequest(BaseModel):
    """使用者輸入不足以生成 SQL 的回應。"""

    error_message: str


Response: TypeAlias = Success | InvalidRequest
model = os.getenv("PYDANTIC_AI_MODEL", "google:gemini-3.7-flash")
agent = Agent[Deps, Response](
    model,
    # Pass the union members directly: a `Response` type alias isn't yet accepted as a `TypeForm` value (PEP-747)
    output_type=Success | InvalidRequest,
    deps_type=Deps,
)


@agent.instructions
async def instructions() -> str:
    return f"""\
根據以下 PostgreSQL 的記錄表，您的工作是編寫 SQL 查詢，以滿足使用者的要求。

資料庫結構：

{DB_SCHEMA}

今天是：{date.today()}

{format_as_xml(SQL_EXAMPLES)}
"""


@agent.output_validator
async def validate_output(ctx: RunContext[Deps], output: Response) -> Response:
    if isinstance(output, InvalidRequest):
        return output

    # gemini often adds extraneous backslashes to SQL
    output.sql_query = output.sql_query.replace("\\", "")
    if not output.sql_query.upper().startswith("SELECT"):
        raise ModelRetry("請生成 SELECT 查詢")

    try:
        await ctx.deps.conn.execute(f"EXPLAIN {output.sql_query}")
    except asyncpg.exceptions.PostgresError as e:
        raise ModelRetry(f"SQL 查詢無效: {e}") from e
    else:
        return output


async def main():
    if len(sys.argv) == 1:
        prompt = '顯示給我昨天帶有 "error" 級別的日誌'
    else:
        prompt = sys.argv[1]

    async with database_connect(
        "postgresql://postgres:postgres@localhost:54320", "pydantic_ai_sql_gen"
    ) as conn:
        deps = Deps(conn)
        result = await agent.run(prompt, deps=deps)
    debug(result.output)


# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
@asynccontextmanager
async def database_connect(server_dsn: str, database: str) -> AsyncGenerator[Any, None]:
    with logfire.span("check and create DB"):
        conn = await asyncpg.connect(server_dsn)
        try:
            db_exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", database
            )
            if not db_exists:
                await conn.execute(f"CREATE DATABASE {database}")
        finally:
            await conn.close()

    conn = await asyncpg.connect(f"{server_dsn}/{database}")
    try:
        with logfire.span("建立資料表"):
            async with conn.transaction():
                if not db_exists:
                    await conn.execute(
                        "CREATE TYPE log_level AS ENUM ('debug', 'info', 'warning', 'error', 'critical')"
                    )
                    await conn.execute(DB_SCHEMA)
        yield conn
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
