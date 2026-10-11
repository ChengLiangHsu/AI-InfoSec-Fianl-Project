from fastapi import FastAPI

from src.router.message import router

app = FastAPI()
app.include_router(router)
