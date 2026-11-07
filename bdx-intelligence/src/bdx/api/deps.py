"""FastAPI dependency injection helpers."""
from __future__ import annotations

import secrets
from typing import Generator, Optional

from fastapi import Header, HTTPException, Query, Request
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


def require_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    api_key: Optional[str] = Query(None, include_in_schema=False),
) -> None:
    """Optional API-key protection.

    Active only when ``API_KEY`` is configured (``app.state.api_key``).  The key
    may be sent as ``X-API-Key`` header or – for the browser dashboard – as
    ``?api_key=`` query parameter.
    """
    expected = getattr(request.app.state, "api_key", "") or ""
    if not expected:
        return
    provided = x_api_key or api_key or ""
    if not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="invalid or missing API key")
