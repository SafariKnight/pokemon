from typing import Annotated
from uuid import uuid4
from argon2.exceptions import VerifyMismatchError
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketException,
    status,
)
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from argon2 import PasswordHasher
from jwt import InvalidTokenError
from pydantic import BaseModel
from sqlalchemy import select
import secrets

from sqlalchemy.orm import Session

from ..models import Player

from .jwt import create_jwt_access_token, create_jwt_refresh_token, decode_jwt_token

from ..deps import Database

password_context = PasswordHasher()


def get_hashed_password(password: str, salt: str) -> str:
    return password_context.hash(salt + password)


def verify_password(hash: str, password: str, salt: str) -> bool:
    try:
        return password_context.verify(hash, salt + password)
    except VerifyMismatchError:
        return False


def get_player(db: Session, username: str) -> Player | None:
    player = db.execute(
        select(Player).where(Player.username == username).limit(1)
    ).scalar_one_or_none()

    return player


router = APIRouter()


class SignupRequest(BaseModel):
    username: str
    password: str
    ...


class SignupResponse(BaseModel):
    message: str
    username: str
    id: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


@router.post("/signup", summary="Create new User")
async def create_user(data: SignupRequest, db: Database):
    player = get_player(db, data.username)

    if player is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User already exists")

    salt = secrets.token_hex(32)

    new_player = Player(
        username=data.username,
        password=get_hashed_password(data.password, salt),
        uuid=str(uuid4()),
        salt=salt,
    )

    response = SignupResponse(
        message="succesfully created user",
        username=new_player.username,
        id=new_player.uuid,
    )

    db.add(new_player)
    db.commit()

    return response


@router.post("/login")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Database
):
    player = get_player(db, form_data.username)

    if player is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )

    if not verify_password(player.password, form_data.password, player.salt):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )

    response = LoginResponse(
        access_token=create_jwt_access_token({"sub": player.username}),
        refresh_token=create_jwt_refresh_token({"sub": player.username}),
        token_type="bearer",
    )

    return response


oauth_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def get_current_user(
    token: Annotated[str, Depends(oauth_scheme)], db: Database
) -> Player:
    try:
        payload = decode_jwt_token(token)
        username = payload.get("sub")
        if username is None or not isinstance(username, str):
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "Invalid username in token",
                {"WWW-Authenticate": "Bearer"},
            )
    except InvalidTokenError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid token",
            {"WWW-Authenticate": "Bearer"},
        )

    player = get_player(db, username)

    if player is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "User not found",
            {"WWW-Authenticate": "Bearer"},
        )

    return player


async def get_current_user_ws(ws: WebSocket, db: Database) -> Player:
    token = ws.query_params.get("token")

    if token is None:
        raise WebSocketException(
            status.WS_1008_POLICY_VIOLATION,
            reason="Provide a token in the path paramters",
        )

    try:
        payload = decode_jwt_token(token)
        username = payload.get("sub")

        if username is None or not isinstance(username, str):
            raise WebSocketException(
                status.WS_1008_POLICY_VIOLATION, "Invalid username in token"
            )
    except InvalidTokenError:
        raise WebSocketException(status.WS_1008_POLICY_VIOLATION, "Invalid token")

    player = get_player(db, username)

    if player is None:
        raise WebSocketException(status.WS_1008_POLICY_VIOLATION, "User not found")

    return player


LoggedInPlayer = Annotated[Player, Depends(get_current_user)]
LoggedInPlayerWs = Annotated[Player, Depends(get_current_user_ws)]
# @router.get("/me")
# def get_user_data(player: LoggedInPlayer):
#     return {
#         "name": player.username,
#         "match": player.match_id,
#         "password": player.password,
#         "salt": player.salt,
#     }
