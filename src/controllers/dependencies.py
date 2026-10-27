from fastapi import Request
from src.database import Database


async def get_db(request: Request) -> Database:
    """從 FastAPI request.state 提取已初始化的 Database 實例。"""
    return request.state.db
