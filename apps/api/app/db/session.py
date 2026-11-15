"""Database engine and session construction with SQLite-friendly defaults."""

import os
from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DATABASE_URL = "sqlite:///./mailtrace.db"


def create_engine_from_url(database_url: str | None = None) -> Engine:
    url = database_url or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, future=True)


def get_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    return sessionmaker(
        bind=create_engine_from_url(database_url),
        autoflush=False,
        expire_on_commit=False,
    )


def get_session(database_url: str | None = None) -> Iterator[Session]:
    session = get_session_factory(database_url)()
    try:
        yield session
    finally:
        session.close()
