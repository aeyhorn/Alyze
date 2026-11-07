"""Service Layer status and mode-switch endpoints.

GET  /api/v1/service-layer          → connection status + current mode
PUT  /api/v1/service-layer/mode     → switch dev | prod (admin action)
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from bdx.api.deps import get_pg_session
from bdx.config import SapMode

router = APIRouter(tags=["service-layer"])


# ── Response / request schemas ────────────────────────────────────────────────

class ServiceLayerStatus(BaseModel):
    mode: str
    company_db: str
    sql_database: str
    configured: bool
    dry_run: bool
    write_enabled: bool
    session_active: bool


class ModeSwitch(BaseModel):
    mode: Literal["dev", "prod"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_client(request: Request):  # noqa: ANN201
    client = getattr(request.app.state, "sl_client", None)
    if client is None:
        raise HTTPException(503, "Service Layer client not initialised")
    return client


def _get_registry(request: Request):  # noqa: ANN201
    registry = getattr(request.app.state, "sap_mode_registry", None)
    if registry is None:
        raise HTTPException(503, "SAP mode registry not initialised")
    return registry


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/service-layer", response_model=ServiceLayerStatus)
def get_service_layer_status(
    request: Request,
    session: Session = Depends(get_pg_session),
):
    """Return current Service Layer connection status."""
    client = _get_client(request)
    registry = _get_registry(request)

    mode = registry.resolve(session)
    return ServiceLayerStatus(
        mode=mode.value,
        company_db=registry.company_db(mode),
        sql_database=registry.sql_database(mode),
        configured=client.configured,
        dry_run=client.dry_run,
        write_enabled=client.write_enabled,
        session_active=bool(client._cookies),  # noqa: SLF001
    )


@router.put("/service-layer/mode", response_model=ServiceLayerStatus)
def set_service_layer_mode(
    body: ModeSwitch,
    request: Request,
    session: Session = Depends(get_pg_session),
):
    """Switch SAP mode (dev | prod).  Clears the current SL session."""
    client = _get_client(request)
    registry = _get_registry(request)

    new_mode = SapMode(body.mode)
    registry.switch(session, new_mode)
    client.switch_mode(new_mode)

    return ServiceLayerStatus(
        mode=new_mode.value,
        company_db=registry.company_db(new_mode),
        sql_database=registry.sql_database(new_mode),
        configured=client.configured,
        dry_run=client.dry_run,
        write_enabled=client.write_enabled,
        session_active=False,
    )
