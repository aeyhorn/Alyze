"""REST endpoints for production orders and domain events."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from bdx.api.deps import get_pg_session
from bdx.models.events import DomainEvent, DomainEventDTO, EventType, OrderSnapshot

router = APIRouter(tags=["orders"])


@router.get("/orders", summary="List latest snapshot of production orders")
def list_orders(
    status: Optional[str] = Query(None, description="Filter by SAP status (R, L, C, X)"),
    item_code: Optional[str] = Query(None),
    session: Session = Depends(get_pg_session),
):
    """Return the most recent snapshot of all production orders."""
    from sqlalchemy import func

    latest_ts = session.execute(select(func.max(OrderSnapshot.captured_at))).scalar()
    if latest_ts is None:
        return {"orders": [], "snapshot_at": None}

    q = select(OrderSnapshot).where(OrderSnapshot.captured_at == latest_ts)
    if status:
        q = q.where(OrderSnapshot.status == status.upper())
    if item_code:
        q = q.where(OrderSnapshot.item_code == item_code)

    rows = session.execute(q).scalars().all()
    return {
        "snapshot_at": latest_ts.isoformat() if latest_ts else None,
        "count": len(rows),
        "orders": [_order_to_dict(r) for r in rows],
    }


@router.get("/events", summary="List domain events")
def list_events(
    event_type: Optional[str] = Query(None, description="e.g. ORDER_CREATED"),
    source_key: Optional[str] = Query(None),
    since: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    session: Session = Depends(get_pg_session),
):
    """Return domain events, newest first."""
    q = select(DomainEvent).order_by(DomainEvent.occurred_at.desc())
    if event_type:
        q = q.where(DomainEvent.event_type == event_type.upper())
    if source_key:
        q = q.where(DomainEvent.source_key == source_key)
    if since:
        q = q.where(DomainEvent.occurred_at >= since)

    q = q.limit(limit)
    rows = session.execute(q).scalars().all()
    return {
        "count": len(rows),
        "events": [DomainEventDTO.model_validate(r).model_dump(mode="json") for r in rows],
    }


def _order_to_dict(snap: OrderSnapshot) -> dict:
    return {
        "source_key": snap.source_key,
        "doc_entry": snap.doc_entry,
        "doc_num": snap.doc_num,
        "status": snap.status,
        "item_code": snap.item_code,
        "planned_qty": float(snap.planned_qty),
        "completed_qty": float(snap.completed_qty),
        "rejected_qty": float(snap.rejected_qty),
        "due_date": snap.due_date,
        "start_date": snap.start_date,
        "u_type": snap.u_type,
        "u_priority": snap.u_priority,
        "captured_at": snap.captured_at.isoformat() if snap.captured_at else None,
    }
