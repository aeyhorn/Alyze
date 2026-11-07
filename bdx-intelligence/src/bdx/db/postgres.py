"""PostgreSQL connection and session factory for the BDX event store."""
from __future__ import annotations

import structlog
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = structlog.get_logger(__name__)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


def create_pg_engine(dsn: str):  # noqa: ANN201
    """Create a SQLAlchemy engine for the local PostgreSQL event store."""
    is_sqlite = dsn.startswith("sqlite")
    kwargs: dict = {"pool_pre_ping": True, "echo": False}
    if not is_sqlite:
        kwargs["pool_size"] = 5
        kwargs["max_overflow"] = 10
    engine = create_engine(dsn, **kwargs)
    logger.info("postgres.engine.created", dsn=_redact_dsn(dsn))
    return engine


def make_session_factory(engine) -> sessionmaker[Session]:  # noqa: ANN001
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _redact_dsn(dsn: str) -> str:
    """Remove password from DSN string for safe logging."""
    import re
    return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", dsn)
