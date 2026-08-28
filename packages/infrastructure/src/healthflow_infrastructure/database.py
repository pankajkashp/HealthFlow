"""HealthFlow Infrastructure Database Engine and Session Management.

Provides the SQLAlchemy 2.x engine factory, scoped/local sessionmakers,
declarative base class, and transactional session context managers.

Ref: docs/architecture/ARCHITECTURE.md §14
"""

import os
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres@localhost:5432/healthflow_dev"


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy 2.x persistence models."""


def create_db_engine(database_url: str | None = None, echo: bool = False) -> Engine:
    """Create and return a SQLAlchemy 2.x engine.

    Normalizes standard 'postgresql://' connection strings to 'postgresql+psycopg://'.
    """
    raw_url = database_url or os.getenv("DATABASE_URL")
    url = raw_url if raw_url is not None else DEFAULT_DATABASE_URL

    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    return create_engine(
        url,
        echo=echo,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a configured sessionmaker bound to the provided engine."""
    return sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


@contextmanager
def session_scope(
    session_factory: sessionmaker[Session],
) -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
