from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .battle import router as battle_router
from .auth.auth import router as auth_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PlayerCreateRequest(BaseModel):
    name: str


app.include_router(battle_router, prefix="/match")
app.include_router(auth_router)
