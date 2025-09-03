from __future__ import annotations
import enum
from uuid import UUID, uuid4
from sqlalchemy import ForeignKey, Enum
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship


class Base(DeclarativeBase): ...


class UUIDMixin:
    uuid: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))


class MatchStatus(enum.Enum):
    WAITING = "WAITING"
    READY = "READY"
    FINISHED = "FINISHED"


class Player(Base, UUIDMixin):
    __tablename__: str = "player"
    username: Mapped[str] = mapped_column(nullable=False, unique=True)
    password: Mapped[str] = mapped_column(nullable=False)
    salt: Mapped[str] = mapped_column(nullable=False)
    current_match_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("match.uuid"), nullable=True
    )
    match: Mapped[Match | None] = relationship(back_populates="players")


class Match(Base, UUIDMixin):
    __tablename__: str = "match"
    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus), default=MatchStatus.WAITING
    )
    players: Mapped[list[Player]] = relationship(back_populates="match")
