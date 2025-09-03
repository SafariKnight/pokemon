import enum
from typing import Any
from uuid import uuid4
from sqlalchemy import ForeignKey, String, Enum, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship


class Base(DeclarativeBase):
    uuid: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )


class Player(Base):
    __tablename__: str = "player"
    username: Mapped[str] = mapped_column(nullable=False, unique=True)
    password: Mapped[str] = mapped_column(nullable=False)
    salt: Mapped[str] = mapped_column(String, nullable=False)
    matches: Mapped[list["PlayerMatch"]] = relationship(back_populates="player")


class MatchStatus(enum.Enum):
    WAITING = "WAITING"
    READY = "READY"
    FINISHED = "FINISHED"


class Match(Base):
    __tablename__: str = "match"
    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus), default=MatchStatus.WAITING
    )
    players: Mapped[list["PlayerMatch"]] = relationship(back_populates="match")


class PlayerMatch(Base):
    __tablename__: str = "player_match"
    __table_args__: Any = (UniqueConstraint("player_id", "match_id"),)  # pyright: ignore[reportExplicitAny, reportAny]
    player_id: Mapped[str] = mapped_column(ForeignKey("player.uuid"), nullable=False)
    match_id: Mapped[str] = mapped_column(ForeignKey("match.uuid"), nullable=False)

    player: Mapped["Player"] = relationship("Player", back_populates="matches")
    match: Mapped["Match"] = relationship("Match", back_populates="players")
