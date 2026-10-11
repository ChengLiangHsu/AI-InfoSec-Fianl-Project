from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.router.agent import router

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)
app.include_router(router)
