"""Service Layer status, mode-switch and write-back endpoints.

GET  /api/v1/service-layer                       → connection status + current mode
PUT  /api/v1/service-layer/mode                  → switch dev | prod (admin action)
POST /api/v1/service-layer/orders/{doc_entry}/release
POST /api/v1/service-layer/orders/{doc_entry}/close
POST /api/v1/service-layer/orders/{doc_entry}/cancel
POST /api/v1/service-layer/orders/{doc_entry}/report-production
GET  /api/v1/service-layer/operations            → audit log
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from bdx.api.deps import get_pg_session, require_api_key
from bdx.config import SapMode
from bdx.models.events import SLOperation, SLOperationDTO

router = APIRouter(tags=["service-layer"], dependencies=[Depends(require_api_key)])


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


# ── Write-back ───────────────────────────────────────────────────────────────

class ReportProductionBody(BaseModel):
    completed_quantity: float = Field(..., gt=0)
    warehouse: str = Field(..., min_length=1, max_length=8)
    batch_number: Optional[str] = None
    operator: Optional[str] = None


class WriteResult(BaseModel):
    operation_id: str
    operation: str
    status: str
    http_status: Optional[int] = None
    error: Optional[str] = None
    dry_run: bool


def _run_write(request: Request, session: Session, operation, doc_entry: int) -> WriteResult:
    from bdx.sap_sl import operations as sl_ops

    client = _get_client(request)
    fn = {
        "release": sl_ops.release_order,
        "close": sl_ops.close_order,
        "cancel": sl_ops.cancel_order,
    }[operation]
    res = fn(session, client, doc_entry)
    if res.status == "failed":
        raise HTTPException(status_code=502, detail=res.error or "Service Layer error")
    return WriteResult(
        operation_id=res.operation_id, operation=res.operation, status=res.status,
        http_status=res.http_status, error=res.error, dry_run=res.dry_run,
    )


@router.post("/service-layer/orders/{doc_entry}/release", response_model=WriteResult)
def sl_release_order(doc_entry: int, request: Request, session: Session = Depends(get_pg_session)):
    """Release a planned production order (Status P → R)."""
    return _run_write(request, session, "release", doc_entry)


@router.post("/service-layer/orders/{doc_entry}/close", response_model=WriteResult)
def sl_close_order(doc_entry: int, request: Request, session: Session = Depends(get_pg_session)):
    """Close a production order (Status → L)."""
    return _run_write(request, session, "close", doc_entry)


@router.post("/service-layer/orders/{doc_entry}/cancel", response_model=WriteResult)
def sl_cancel_order(doc_entry: int, request: Request, session: Session = Depends(get_pg_session)):
    """Cancel a production order (Status → C)."""
    return _run_write(request, session, "cancel", doc_entry)


@router.post("/service-layer/orders/{doc_entry}/report-production", response_model=WriteResult)
def sl_report_production(
    doc_entry: int,
    body: ReportProductionBody,
    request: Request,
    session: Session = Depends(get_pg_session),
):
    """Report produced quantity against a production order (Receipt from Production)."""
    from bdx.sap_sl import operations as sl_ops

    client = _get_client(request)
    res = sl_ops.report_production(
        session, client, doc_entry, body.completed_quantity, body.warehouse,
        batch_number=body.batch_number, operator=body.operator,
    )
    if res.status == "failed":
        raise HTTPException(status_code=502, detail=res.error or "Service Layer error")
    return WriteResult(
        operation_id=res.operation_id, operation=res.operation, status=res.status,
        http_status=res.http_status, error=res.error, dry_run=res.dry_run,
    )


@router.get("/service-layer/operations")
def sl_operations(
    operation: Optional[str] = Query(None),
    doc_entry: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    session: Session = Depends(get_pg_session),
):
    """Service Layer write-back audit log (newest first)."""
    q = select(SLOperation).order_by(SLOperation.occurred_at.desc(), SLOperation.id.desc())
    if operation:
        q = q.where(SLOperation.operation == operation)
    if doc_entry is not None:
        q = q.where(SLOperation.doc_entry == doc_entry)
    if status:
        q = q.where(SLOperation.status == status)
    rows = session.execute(q.limit(limit)).scalars().all()
    return {
        "count": len(rows),
        "operations": [SLOperationDTO.model_validate(r).model_dump(mode="json") for r in rows],
    }
