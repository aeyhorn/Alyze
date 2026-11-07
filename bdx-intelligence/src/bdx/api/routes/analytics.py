"""Analytics endpoints - process weakness detection."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from bdx.api.deps import get_pg_session, require_api_key
from bdx.models.events import DomainEvent, MachineState, OrderState, SnapshotRun
from bdx.models.sap import OPEN_STATUSES, STATUS_LABELS

router = APIRouter(tags=["analytics"], dependencies=[Depends(require_api_key)])

_STUCK_THRESHOLD_DAYS = 3
_STUCK_COMPLETION_THRESHOLD = 0.10  # < 10 %
_PLAN_CHANGE_WINDOW_DAYS = 7
_OFFLINE_WINDOW_HOURS = 24
_COLLECTOR_ERROR_WINDOW_DAYS = 7
_RUN_TREND_LIMIT = 20


def _order_weakness_dict(o: OrderState, extra: dict | None = None) -> dict:
    d = {
        "source_key": o.source_key,
        "doc_entry": o.doc_entry,
        "doc_num": o.doc_num,
        "status": o.status,
        "status_label": STATUS_LABELS.get(o.status, o.status),
        "item_code": o.item_code,
        "planned_qty": float(o.planned_qty),
        "completed_qty": float(o.completed_qty),
        "due_date": o.due_date,
        "last_changed_at": _as_utc(o.last_changed_at).isoformat() if o.last_changed_at else None,
    }
    if extra:
        d.update(extra)
    return d


def _completion_pct(o: OrderState) -> float:
    pq = float(o.planned_qty)
    cq = float(o.completed_qty)
    return round(cq / pq * 100, 1) if pq > 0 else 0.0


def _as_utc(dt: datetime) -> datetime:
    """Return a timezone-aware UTC datetime regardless of whether *dt* is naive or aware.

    SQLite returns naive datetimes; PostgreSQL returns timezone-aware ones.
    This helper normalises both so subtraction always works.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


@router.get("/analytics/weaknesses", summary="Aggregated process-weakness indicators")
def get_weaknesses(session: Session = Depends(get_pg_session)) -> dict:
    """Return all process-weakness signals in a single call.

    Covers overdue orders, stuck released orders, recent plan changes,
    idle machines, machine-offline events, and collector errors.
    """
    now = datetime.now(UTC)
    today_str = date.today().isoformat()

    # ── 1. Overdue orders ─────────────────────────────────────────────────────
    overdue_rows = (
        session.execute(
            select(OrderState)
            .where(
                and_(
                    OrderState.status.in_(OPEN_STATUSES),
                    OrderState.due_date.isnot(None),
                    OrderState.due_date < today_str,
                )
            )
            .order_by(OrderState.due_date.asc())
            .limit(200)
        )
        .scalars()
        .all()
    )

    overdue_orders: list[dict] = []
    for o in overdue_rows:
        try:
            days_overdue: int | None = (date.today() - date.fromisoformat(o.due_date)).days
        except (TypeError, ValueError):
            days_overdue = None
        overdue_orders.append(
            _order_weakness_dict(
                o, {"days_overdue": days_overdue, "completion_pct": _completion_pct(o)}
            )
        )

    # ── 2. Stuck released orders (R, < 10 % done, unchanged ≥ N days) ────────
    stuck_cutoff = now - timedelta(days=_STUCK_THRESHOLD_DAYS)
    candidate_rows = (
        session.execute(
            select(OrderState)
            .where(
                and_(
                    OrderState.status == "R",
                    OrderState.last_changed_at < stuck_cutoff,
                )
            )
            .order_by(OrderState.last_changed_at.asc())
            .limit(500)
        )
        .scalars()
        .all()
    )

    stuck_orders: list[dict] = []
    for o in candidate_rows:
        pct_raw = float(o.completed_qty) / float(o.planned_qty) if float(o.planned_qty) > 0 else 0.0
        if pct_raw < _STUCK_COMPLETION_THRESHOLD:
            days_stuck = (now - _as_utc(o.last_changed_at)).days
            stuck_orders.append(
                _order_weakness_dict(
                    o, {"completion_pct": round(pct_raw * 100, 1), "days_stuck": days_stuck}
                )
            )
    stuck_orders = stuck_orders[:200]

    # ── 3. Plan changes (QUANTITY_CHANGED / DUE_DATE_CHANGED, last 7 days) ───
    plan_since = now - timedelta(days=_PLAN_CHANGE_WINDOW_DAYS)
    plan_events = (
        session.execute(
            select(DomainEvent)
            .where(
                and_(
                    DomainEvent.event_type.in_(["QUANTITY_CHANGED", "DUE_DATE_CHANGED"]),
                    DomainEvent.occurred_at >= plan_since,
                )
            )
            .order_by(DomainEvent.occurred_at.desc())
            .limit(500)
        )
        .scalars()
        .all()
    )

    # Latest event per doc_entry
    latest_plan_event: dict[int, DomainEvent] = {}
    for ev in plan_events:
        if ev.doc_entry is not None and ev.doc_entry not in latest_plan_event:
            latest_plan_event[ev.doc_entry] = ev

    order_map: dict[int, OrderState] = {}
    if latest_plan_event:
        for o in session.execute(
            select(OrderState).where(OrderState.doc_entry.in_(list(latest_plan_event)))
        ).scalars():
            order_map[o.doc_entry] = o

    plan_changes: list[dict] = []
    for doc_entry, ev in latest_plan_event.items():
        o = order_map.get(doc_entry)
        if o is None:
            continue
        plan_changes.append(
            {
                **_order_weakness_dict(o, {"completion_pct": _completion_pct(o)}),
                "latest_change_type": ev.event_type,
                "latest_change_at": ev.occurred_at.isoformat(),
                "latest_change_payload": ev.payload,
            }
        )

    # ── 4. Idle machines (online, state ≠ running) ───────────────────────────
    idle_rows = (
        session.execute(
            select(MachineState)
            .where(
                and_(
                    MachineState.online.is_(True),
                    or_(
                        MachineState.state.is_(None),
                        MachineState.state != "running",
                    ),
                )
            )
            .order_by(MachineState.machine_id)
        )
        .scalars()
        .all()
    )

    idle_machines: list[dict] = [
        {
            "machine_id": m.machine_id,
            "state": m.state,
            "exec_state": m.exec_state,
            "order_ref": m.order_ref,
            "last_seen_at": m.last_seen_at.isoformat() if m.last_seen_at else None,
            "last_changed_at": m.last_changed_at.isoformat() if m.last_changed_at else None,
        }
        for m in idle_rows
    ]

    # ── 5. Machine-offline events (last 24 h) ─────────────────────────────────
    offline_since = now - timedelta(hours=_OFFLINE_WINDOW_HOURS)
    offline_events = (
        session.execute(
            select(DomainEvent)
            .where(
                and_(
                    DomainEvent.event_type == "MACHINE_OFFLINE",
                    DomainEvent.occurred_at >= offline_since,
                )
            )
            .order_by(DomainEvent.occurred_at.desc())
            .limit(200)
        )
        .scalars()
        .all()
    )

    machine_offlines_24h: dict[str, list[dict]] = {}
    for ev in offline_events:
        mid = ev.machine_id or "unknown"
        machine_offlines_24h.setdefault(mid, []).append(
            {
                "occurred_at": ev.occurred_at.isoformat(),
                "payload": ev.payload,
            }
        )

    # ── 6. Collector errors (last 7 days) ─────────────────────────────────────
    err_since = now - timedelta(days=_COLLECTOR_ERROR_WINDOW_DAYS)
    error_runs = (
        session.execute(
            select(SnapshotRun)
            .where(
                and_(
                    SnapshotRun.error.isnot(None),
                    SnapshotRun.started_at >= err_since,
                )
            )
            .order_by(SnapshotRun.started_at.desc())
            .limit(50)
        )
        .scalars()
        .all()
    )

    collector_errors_7d: list[dict] = [
        {
            "run_id": r.run_id,
            "started_at": r.started_at.isoformat(),
            "mode": r.mode,
            "error": r.error,
        }
        for r in error_runs
    ]

    # ── 7. Run trend (last N runs for duration / change-rate chart) ───────────
    recent_runs = (
        session.execute(
            select(SnapshotRun).order_by(SnapshotRun.started_at.desc()).limit(_RUN_TREND_LIMIT)
        )
        .scalars()
        .all()
    )

    run_trend: list[dict] = [
        {
            "run_id": r.run_id,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "mode": r.mode,
            "duration_seconds": (
                (_as_utc(r.finished_at) - _as_utc(r.started_at)).total_seconds()
                if r.finished_at and r.started_at
                else None
            ),
            "orders_read": r.orders_read,
            "orders_changed": r.orders_changed,
            "events_created": r.events_created,
            "has_error": r.error is not None,
        }
        for r in recent_runs
    ]

    return {
        "generated_at": now.isoformat(),
        "summary": {
            "overdue_orders": len(overdue_orders),
            "stuck_orders": len(stuck_orders),
            "plan_changes_7d": len(plan_changes),
            "idle_machines": len(idle_machines),
            "machine_offlines_24h": sum(len(v) for v in machine_offlines_24h.values()),
            "machines_with_offlines_24h": len(machine_offlines_24h),
            "collector_errors_7d": len(collector_errors_7d),
        },
        "overdue_orders": overdue_orders,
        "stuck_orders": stuck_orders,
        "plan_changes": plan_changes,
        "idle_machines": idle_machines,
        "machine_offlines_24h": machine_offlines_24h,
        "collector_errors_7d": collector_errors_7d,
        "run_trend": run_trend,
    }
