"""FastAPI dependency injection helpers."""
from __future__ import annotations

from typing import Generator

from fastapi import Request
from sqlalchemy.orm import Session


def get_pg_session(request: Request) -> Generator[Session, None, None]:
    """Yield a PostgreSQL session from the app-level session factory."""
    factory = request.app.state.pg_session_factory
    session = factory()
    try:
        yield session
    finally:
        session.close()


def get_sap_status(request: Request) -> bool:
    """Return the last known SAP connectivity status (cached by the collector)."""
    return getattr(request.app.state, "sap_ok", False)
