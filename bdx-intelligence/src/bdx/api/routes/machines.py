"""REST endpoints for machine state, BDE records and collector runs."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from bdx.api.deps import get_pg_session, require_api_key
from bdx.models.events import DomainEvent, DomainEventDTO, MachineState, OrderState, SnapshotRun
from bdx.models.sap import STATUS_LABELS

router = APIRouter(tags=["machines"], dependencies=[Depends(require_api_key)])


def _iso(v: Optional[datetime]) -> Optional[str]:
    return v.isoformat() if v else None


def _machine_to_dict(m: MachineState) -> dict:
    return {
        "machine_id": m.machine_id,
        "online": m.online,
        "mde_enabled": m.mde_enabled,
        "exec_state": m.exec_state,
        "state": m.state,
        "mode": m.mode,
        "order_ref": m.order_ref,
        "operation": m.operation,
        "part": m.part,
        "nc_program": m.nc_program,
        "pieces": m.pieces,
        "pieces_raw": m.pieces_raw,
        "operator": m.operator,
        "feed_override": m.feed_override,
        "spindle_override": m.spindle_override,
        "rapid_override": m.rapid_override,
        "load_spindle": m.load_spindle,
        "load_axis_1": m.load_axis_1,
        "load_axis_2": m.load_axis_2,
        "last_message": m.last_message,
        "last_prod_end": m.last_prod_end,
        "sap_doc_entry": m.sap_doc_entry,
        "sap_item_code": m.sap_item_code,
        "source_timestamp": _iso(m.source_timestamp),
        "first_seen_at": _iso(m.first_seen_at),
        "last_seen_at": _iso(m.last_seen_at),
        "last_changed_at": _iso(m.last_changed_at),
    }


@router.get("/machines", summary="Current state of all machines")
def list_machines(session: Session = Depends(get_pg_session)):
    rows = session.execute(select(MachineState).order_by(MachineState.machine_id)).scalars().all()
    # attach linked SAP order (if any)
    doc_entries = [r.sap_doc_entry for r in rows if r.sap_doc_entry is not None]
    orders = {}
    if doc_entries:
        for o in session.execute(select(OrderState).where(OrderState.doc_entry.in_(doc_entries))).scalars():
            orders[o.doc_entry] = o
    result = []
    for r in rows:
        d = _machine_to_dict(r)
        o = orders.get(r.sap_doc_entry)
        d["sap_order"] = (
            {
                "doc_entry": o.doc_entry,
                "doc_num": o.doc_num,
                "status": o.status,
                "status_label": STATUS_LABELS.get(o.status, o.status),
                "item_code": o.item_code,
                "planned_qty": float(o.planned_qty),
                "completed_qty": float(o.completed_qty),
                "due_date": o.due_date,
            }
            if o
            else None
        )
        result.append(d)
    return {
        "count": len(result),
        "online": sum(1 for r in rows if r.online),
        "running": sum(1 for r in rows if r.online and r.state == "running"),
        "machines": result,
    }


@router.get("/machines/{machine_id}", summary="Single machine with recent events")
def get_machine(
    machine_id: str,
    limit: int = Query(100, ge=1, le=1000),
    session: Session = Depends(get_pg_session),
):
    row = session.get(MachineState, machine_id)
    if row is None:
        raise HTTPException(status_code=404, detail="machine not found")
    events = session.execute(
        select(DomainEvent)
        .where(DomainEvent.machine_id == machine_id)
        .order_by(DomainEvent.occurred_at.desc(), DomainEvent.id.desc())
        .limit(limit)
    ).scalars().all()
    return {
        "machine": _machine_to_dict(row),
        "events": [DomainEventDTO.model_validate(e).model_dump(mode="json") for e in events],
    }


@router.get("/machines/{machine_id}/live", summary="Live status straight from the machine feed")
def machine_live(machine_id: str, request: Request):
    adapter = getattr(request.app.state, "machine_adapter", None)
    if adapter is None:
        raise HTTPException(status_code=503, detail="machine adapter not configured")
    st = adapter.get_status(machine_id)
    if st is None:
        raise HTTPException(status_code=404, detail="machine not in feed")
    from dataclasses import asdict

    d = asdict(st)
    d["timestamp"] = st.timestamp.isoformat()
    return d


@router.get("/bde/records", summary="BDE records derived from the shop-floor telemetry")
def bde_records(
    request: Request,
    hours: int = Query(24, ge=1, le=24 * 14),
    machine_id: Optional[str] = Query(None),
):
    adapter = getattr(request.app.state, "bde_adapter", None)
    if adapter is None:
        raise HTTPException(status_code=503, detail="BDE adapter not configured")
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    records = adapter.fetch_recent(since)
    if machine_id:
        records = [r for r in records if r.machine_id == machine_id]
    return {
        "since": since.isoformat(),
        "count": len(records),
        "records": [
            {
                "machine_id": r.machine_id,
                "order_id": r.order_id,
                "sap_doc_num": r.sap_doc_num,
                "operation_id": r.operation_id,
                "start_time": r.start_time.isoformat(),
                "end_time": _iso(r.end_time),
                "duration_seconds": r.duration_seconds,
                "quantity_good": r.quantity_good,
                "quantity_scrap": r.quantity_scrap,
                "operator_id": r.operator_id,
                "sample_count": r.sample_count,
                "last_state": r.last_state,
            }
            for r in sorted(records, key=lambda x: x.start_time, reverse=True)
        ],
    }


@router.get("/runs", summary="Collector runs (newest first)")
def list_runs(
    limit: int = Query(50, ge=1, le=1000),
    session: Session = Depends(get_pg_session),
):
    rows = session.execute(select(SnapshotRun).order_by(SnapshotRun.started_at.desc()).limit(limit)).scalars().all()
    return {
        "count": len(rows),
        "runs": [
            {
                "run_id": r.run_id,
                "mode": r.mode,
                "started_at": _iso(r.started_at),
                "finished_at": _iso(r.finished_at),
                "duration_seconds": (r.finished_at - r.started_at).total_seconds() if r.finished_at else None,
                "orders_read": r.orders_read,
                "orders_changed": r.orders_changed,
                "events_created": r.events_created,
                "since_date": r.since_date,
                "error": r.error,
            }
            for r in rows
        ],
    }
