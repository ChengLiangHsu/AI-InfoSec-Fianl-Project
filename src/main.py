from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
import fastapi
import logfire

from src.controllers import conversation_router, odm_router
from src.database import init_db
from src.presenter import register_error_handlers
from src.utility.nodeodm import ensure_nodeodm_running

load_dotenv()
logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_pydantic_ai()

THIS_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(_app: fastapi.FastAPI):
    """應用程式生命週期管理：確認 NodeODM 就緒並初始化 SQLite 資料庫。"""
    if not ensure_nodeodm_running():
        raise RuntimeError("NodeODM 尚未啟動，中止後端服務。請先執行 'docker run -d -p 3002:3000 --name nodeodm opendronemap/nodeodm' 啟動容器。")
    init_db()
    yield


def create_app() -> fastapi.FastAPI:
    """FastAPI 應用工廠函式：負責初始化實例、整合監控並掛載各模組控制器。"""
    app = fastapi.FastAPI(lifespan=lifespan)
    logfire.instrument_fastapi(app)
    register_error_handlers(app)
    app.include_router(conversation_router, prefix="/api")
    app.include_router(odm_router, prefix="/api")
    app.frontend("/", directory=THIS_DIR.parent / "dist")
    return app


app = create_app()


def main():
    """主流程啟動函式，調度 uvicorn 本地開發伺服器。"""
    import uvicorn

    uvicorn.run("src.main:app", app_dir=str(THIS_DIR.parent), reload=True)


if __name__ == "__main__":
    main()
