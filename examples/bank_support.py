"""使用 Pydantic AI 建立銀行客服代理程式的完整範例。

執行方式：

    uv run examples/bank_support.py
"""

import os
from dotenv import load_dotenv

load_dotenv()

import sqlite3
from dataclasses import dataclass

from pydantic import BaseModel

from pydantic_ai import Agent, RunContext


@dataclass
class DatabaseConn:
    """SQLite 連線的包裝類別。"""

    sqlite_conn: sqlite3.Connection

    async def customer_name(self, *, id: int) -> str | None:
        res = cur.execute("SELECT name FROM customers WHERE id=?", (id,))
        row = res.fetchone()
        if row:
            return row[0]
        return None

    async def customer_balance(self, *, id: int) -> float:
        res = cur.execute("SELECT balance FROM customers WHERE id=?", (id,))
        row = res.fetchone()
        if row:
            return row[0]
        else:
            raise ValueError("找不到客戶")


@dataclass
class SupportDependencies:
    customer_id: int
    db: DatabaseConn


class SupportOutput(BaseModel):
    support_advice: str
    """回覆給客戶的支援建議。"""
    block_card: bool
    """是否要封鎖客戶的卡。"""
    risk: int
    """查詢的風險等級。"""


model = os.getenv("PYDANTIC_AI_MODEL", "google:gemini-3.7-flash")
support_agent = Agent(
    model,
    deps_type=SupportDependencies,
    output_type=SupportOutput,
    instructions=(
        "你是我銀行的客服代理程式，請給予客戶支援並判斷他們查詢的風險等級。 "
        "請使用客戶的名字回覆。"
    ),
)


@support_agent.instructions
async def add_customer_name(ctx: RunContext[SupportDependencies]) -> str:
    customer_name = await ctx.deps.db.customer_name(id=ctx.deps.customer_id)
    return f"客戶的名字是 {customer_name!r}"


@support_agent.tool
async def customer_balance(ctx: RunContext[SupportDependencies]) -> str:
    """返回客戶目前帳戶餘額。"""
    balance = await ctx.deps.db.customer_balance(
        id=ctx.deps.customer_id,
    )
    return f"${balance:.2f}"


if __name__ == "__main__":
    with sqlite3.connect(":memory:") as con:
        cur = con.cursor()
        cur.execute("CREATE TABLE customers(id, name, balance)")
        cur.execute("""
            INSERT INTO customers VALUES
                (123, 'John', 123.45)
        """)
        con.commit()

        deps = SupportDependencies(customer_id=123, db=DatabaseConn(sqlite_conn=con))
        result = support_agent.run_sync("我的餘額是多少?", deps=deps)
        print(result.output)
        """
        support_advice='哈摟 John，你的帳戶餘額是 $123.45。' block_card=False risk=1
        """

        result = support_agent.run_sync("我剛把卡弄不見了!", deps=deps)
        print(result.output)
        """
        support_advice="真遺憾聽到這件事, John。我們將暫時封鎖您的卡以防止未經授權的交易。" block_card=True risk=8
        """
