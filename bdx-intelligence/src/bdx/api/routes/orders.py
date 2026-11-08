"""REST endpoints for production orders and domain events."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from bdx.api.deps import get_pg_session, require_api_key
from bdx.models.events import DomainEvent, DomainEventDTO, OrderSnapshot, OrderState
from bdx.models.sap import OPEN_STATUSES, STATUS_LABELS

router = APIRouter(tags=["orders"], dependencies=[Depends(require_api_key)])


@router.get("/orders", summary="List current state of production orders")
def list_orders(
    status: str | None = Query(
        None, description="SAP status: P (planned), R (released), L (closed), C (cancelled)"
    ),
    open_only: bool = Query(
        True, description="Only open orders (P/R). Ignored when status is given."
    ),
    item_code: str | None = Query(None),
    doc_num: int | None = Query(None),
    limit: int = Query(1000, ge=1, le=50000),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_pg_session),
):
    """Return the current (last known) state of production orders."""
    q = select(OrderState)
    if status:
        q = q.where(OrderState.status == status.upper())
    elif open_only:
        q = q.where(OrderState.status.in_(OPEN_STATUSES))
    if item_code:
        q = q.where(OrderState.item_code == item_code)
    if doc_num is not None:
        q = q.where(OrderState.doc_num == doc_num)

    total = session.execute(select(func.count()).select_from(q.subquery())).scalar() or 0
    rows = (
        session.execute(q.order_by(OrderState.doc_num.desc()).offset(offset).limit(limit))
        .scalars()
        .all()
    )
    latest_ts = session.execute(select(func.max(OrderState.captured_at))).scalar()
    return {
        "snapshot_at": latest_ts.isoformat() if latest_ts else None,
        "total": total,
        "count": len(rows),
        "orders": [_order_to_dict(r) for r in rows],
    }


@router.get("/orders/summary", summary="Order counts per status")
def orders_summary(session: Session = Depends(get_pg_session)):
    rows = session.execute(
        select(OrderState.status, func.count()).group_by(OrderState.status)
    ).all()
    by_status = {st: n for st, n in rows}
    return {
        "total": sum(by_status.values()),
        "open": sum(n for st, n in by_status.items() if st in OPEN_STATUSES),
        "by_status": [
            {"status": st, "label": STATUS_LABELS.get(st, st), "count": n}
            for st, n in sorted(by_status.items())
        ],
    }


@router.get("/orders/{doc_entry}", summary="Single order with history and events")
def get_order(
    doc_entry: int,
    session: Session = Depends(get_pg_session),
):
    row = (
        session.execute(select(OrderState).where(OrderState.doc_entry == doc_entry))
        .scalars()
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="order not found")
    history = (
        session.execute(
            select(OrderSnapshot)
            .where(OrderSnapshot.doc_entry == doc_entry)
            .order_by(OrderSnapshot.captured_at.desc())
            .limit(50)
        )
        .scalars()
        .all()
    )
    events = (
        session.execute(
            select(DomainEvent)
            .where(DomainEvent.doc_entry == doc_entry)
            .order_by(DomainEvent.occurred_at.desc())
            .limit(100)
        )
        .scalars()
        .all()
    )
    return {
        "order": _order_to_dict(row),
        "history": [_order_to_dict(h) for h in history],
        "events": [DomainEventDTO.model_validate(e).model_dump(mode="json") for e in events],
    }


@router.get("/events", summary="List domain events")
def list_events(
    event_type: str | None = Query(None, description="e.g. ORDER_CREATED, MACHINE_STATE_CHANGED"),
    source_key: str | None = Query(None),
    machine_id: str | None = Query(None),
    doc_entry: int | None = Query(None),
    since: datetime | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    session: Session = Depends(get_pg_session),
):
    """Return domain events, newest first."""
    q = select(DomainEvent).order_by(DomainEvent.occurred_at.desc(), DomainEvent.id.desc())
    if event_type:
        q = q.where(DomainEvent.event_type == event_type.upper())
    if source_key:
        q = q.where(DomainEvent.source_key == source_key)
    if machine_id:
        q = q.where(DomainEvent.machine_id == machine_id)
    if doc_entry is not None:
        q = q.where(DomainEvent.doc_entry == doc_entry)
    if since:
        q = q.where(DomainEvent.occurred_at >= since)

    rows = session.execute(q.limit(limit)).scalars().all()
    return {
        "count": len(rows),
        "events": [DomainEventDTO.model_validate(r).model_dump(mode="json") for r in rows],
    }


@router.get("/events/summary", summary="Event counts per type (last 24h and total)")
def events_summary(
    hours: int = Query(24, ge=1, le=24 * 90),
    session: Session = Depends(get_pg_session),
):
    from datetime import timedelta

    since = datetime.now(UTC) - timedelta(hours=hours)
    recent = session.execute(
        select(DomainEvent.event_type, func.count())
        .where(DomainEvent.occurred_at >= since)
        .group_by(DomainEvent.event_type)
    ).all()
    total = session.execute(
        select(DomainEvent.event_type, func.count()).group_by(DomainEvent.event_type)
    ).all()
    return {
        "hours": hours,
        "recent": {str(getattr(t, "value", t)): n for t, n in recent},
        "total": {str(getattr(t, "value", t)): n for t, n in total},
    }


def _order_to_dict(snap) -> dict:
    d = {
        "source_key": snap.source_key,
        "doc_entry": snap.doc_entry,
        "doc_num": snap.doc_num,
        "status": snap.status,
        "status_label": STATUS_LABELS.get(snap.status, snap.status),
        "is_open": snap.status in OPEN_STATUSES,
        "item_code": snap.item_code,
        "planned_qty": float(snap.planned_qty),
        "completed_qty": float(snap.completed_qty),
        "rejected_qty": float(snap.rejected_qty),
        "due_date": snap.due_date,
        "start_date": snap.start_date,
        "u_type": snap.u_type,
        "u_priority": snap.u_priority,
        "sap_update_date": getattr(snap, "sap_update_date", None),
        "captured_at": snap.captured_at.isoformat() if snap.captured_at else None,
    }
    for extra in ("first_seen_at", "last_changed_at"):
        v = getattr(snap, extra, None)
        if v is not None:
            d[extra] = v.isoformat()
    return d
