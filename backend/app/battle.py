from __future__ import annotations
import asyncio
from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
    status,
)
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .auth.auth import LoggedInPlayer, LoggedInPlayerWs

from .deps import Database
from .models import Match, Player

router = APIRouter()


def get_match(db: Session, match_id: str) -> Match | None:
    match = db.get(Match, match_id)
    return match


class MatchResponse(BaseModel):
    ws_url: str


@router.get("/make")
def matchmake(request: Request, db: Database, player: LoggedInPlayer):
    if player.current_match_id is not None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="You're already in a match"
        )

    match = db.scalar(
        select(Match)
        .join(Player, Player.current_match_id == Match.uuid)
        .group_by(Match.uuid)
        .having(func.count(Player.uuid) < 2)
    )

    if match is None:
        match = Match()
        db.add(match)
        db.commit()
        db.refresh(match)

    scheme = "wss" if request.url.scheme == "https" else "ws"
    host = request.headers.get("host")
    ws_url = f"{scheme}://{host}/match/{match.uuid}"

    return MatchResponse(ws_url=ws_url)


class GameMatch:
    def __init__(self) -> None:
        self.players: list[WebSocket] = []
        self.ready: asyncio.Event = asyncio.Event()
        self.over: asyncio.Event = asyncio.Event()
        self.started: bool = False

    def join_match(self, player: WebSocket):
        if len(self.players) >= 2:
            raise ValueError("More than two players in match")
        self.players.append(player)

    def leave_match(self, player: WebSocket):
        if player in self.players:
            self.players.remove(player)
            if not self.players:
                del self

    async def broadcast(self, message: str):
        for player in self.players:
            await player.send_text(message)


class GameMatchManager:
    def __init__(self) -> None:
        self.matches: dict[str, GameMatch] = {}


game_match_manager = GameMatchManager()


@router.websocket("/{match_id}")
async def before_match(
    player: WebSocket,
    player_acc: LoggedInPlayerWs,
    database: Database,
    match_id: str,
):
    match = database.get(Match, match_id)
    if match is None:
        raise WebSocketException(
            status.WS_1008_POLICY_VIOLATION, reason="Match not found"
        )

    try:
        if game_match_manager.matches.get(match_id) is None:
            game_match_manager.matches[match_id] = GameMatch()

        game_match = game_match_manager.matches[match_id]

        game_match.join_match(player)
        player_acc.match = match
        database.commit()

        await player.accept()

        if len(game_match.players) == 2 and not game_match.started:
            game_match.started = True
            game_match.ready.set()
            _ = asyncio.create_task(in_match(match_id))

    except ValueError:
        raise WebSocketException(
            status.WS_1008_POLICY_VIOLATION, "Too many players in match"
        )

    def cleanup():
        player_acc.current_match_id = None
        game_match.leave_match(player)
        database.commit()

    try:
        _ = await game_match.ready.wait()
        await player.send_text("Match Started")
        _ = await game_match.over.wait()
        await player.close()
        cleanup()
    except WebSocketDisconnect:
        cleanup()


async def in_match(match_id: str):
    game_match = game_match_manager.matches[match_id]

    blue = game_match.players[0]
    red = game_match.players[1]

    async with asyncio.TaskGroup() as tg:
        first_text = tg.create_task(blue.receive_text())
        second_text = tg.create_task(red.receive_text())

    async with asyncio.TaskGroup() as tg:
        _ = tg.create_task(blue.send_text(second_text.result()))
        _ = tg.create_task(red.send_text(first_text.result()))

    game_match.over.set()
