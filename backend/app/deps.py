from typing import Annotated
from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


engine = create_engine("sqlite:///./database.sqlite")

session_maker = sessionmaker(engine)


def get_db():
    session = session_maker()

    try:
        yield session
    finally:
        session.close()


Database = Annotated[Session, Depends(get_db)]
