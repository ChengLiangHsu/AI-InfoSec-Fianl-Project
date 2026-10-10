from fastapi import FastAPI

from src.adapter.controller.conversation_controller import router

app = FastAPI()
app.include_router(router)