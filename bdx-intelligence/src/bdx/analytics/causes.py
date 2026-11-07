"""One dominant lateness cause per late production order.

Priority, first match wins:
  material_gap, overdue_po, waiting_idle, bottleneck, scrap, unstable.
Orders with no evidence are stored as ``unassigned``.
"""
from __future__ import annotations

from datetime import UTC, date, datetime

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from bdx.models.analytics import (
    BottleneckRank,
    LatenessCause,
    MachineStateHistory,
    OrderFlowSegment,
)
from bdx.models.events import DomainEvent, EventType, OrderState

logger = structlog.get_logger(__name__)

CAUSE_PRIORITY = (
    "material_gap",
    "overdue_po",
    "waiting_idle",
    "bottleneck",
    "scrap",
    "unstable",
    "unassigned",
)

CAUSE_LABELS = {
    "material_gap": "Materiallücke",
    "overdue_po": "überfällige Bestellung",
    "waiting_idle": "Warten bei freier Maschine",
    "bottleneck": "Engpassmaschine",
    "scrap": "Ausschuss",
    "unstable": "instabiler Auftrag",
    "unassigned": "ohne belegte Ursache",
}

SCRAP_RATIO = 0.02
UNSTABLE_CHANGES = 2
WAIT_HOURS = 8.0
IDLE_HOURS = 1.0


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _overlap_hours(start: datetime, end: datetime, row_start: datetime, row_end: datetime | None) -> float:
    stop = row_end or end
    lo = max(start, row_start)
    hi = min(end, stop)
    if hi <= lo:
        return 0.0
    return (hi - lo).total_seconds() / 3600


def _idle_hours_between(session: Session, start: datetime | None, end: datetime | None) -> float:
    start_utc = _as_utc(start)
    end_utc = _as_utc(end)
    if start_utc is None or end_utc is None or end_utc <= start_utc:
        return 0.0
    rows = session.execute(
        select(MachineStateHistory)
        .where(MachineStateHistory.state == "idle")
        .where(MachineStateHistory.started_at <= end_utc)
    ).scalars().all()
    total = 0.0
    for row in rows:
        row_start = _as_utc(row.started_at)
        if row_start is None:
            continue
        total += _overlap_hours(start_utc, end_utc, row_start, _as_utc(row.ended_at))
    return total


def _pick_cause(
    *,
    material_gap: bool,
    overdue_po: bool,
    waiting_idle: bool,
    bottleneck: bool,
    scrap: bool,
    unstable: bool,
) -> str:
    flags = {
        "material_gap": material_gap,
        "overdue_po": overdue_po,
        "waiting_idle": waiting_idle,
        "bottleneck": bottleneck,
        "scrap": scrap,
        "unstable": unstable,
    }
    for cause in CAUSE_PRIORITY:
        if flags.get(cause):
            return cause
    return "unassigned"


def classify_lateness(
    session: Session,
    material_gap_orders: set[int] | None = None,
    overdue_po_orders: set[int] | None = None,
) -> int:
    """Rewrite lateness_causes for every currently late order.

    Returns the number of cause rows written.
    """
    now = datetime.now(UTC)
    today = now.date()
    material_gap_orders = material_gap_orders or set()
    overdue_po_orders = overdue_po_orders or set()
    capacity_machines = {
        row.machine_id
        for row in session.execute(
            select(BottleneckRank).where(BottleneckRank.interpretation == "capacity")
        ).scalars().all()
    }

    closed_at = {
        row.doc_entry: _as_utc(row.occurred_at)
        for row in session.execute(
            select(DomainEvent.doc_entry, func.max(DomainEvent.occurred_at).label("occurred_at"))
            .where(DomainEvent.event_type == EventType.ORDER_CLOSED)
            .where(DomainEvent.doc_entry.is_not(None))
            .group_by(DomainEvent.doc_entry)
        ).all()
    }
    change_counts = {
        row.doc_entry: int(row.cnt)
        for row in session.execute(
            select(DomainEvent.doc_entry, func.count().label("cnt"))
            .where(DomainEvent.event_type.in_([
                EventType.QUANTITY_CHANGED,
                EventType.DUE_DATE_CHANGED,
            ]))
            .where(DomainEvent.doc_entry.is_not(None))
            .group_by(DomainEvent.doc_entry)
        ).all()
    }
    start_machine = {}
    for row in session.execute(
        select(DomainEvent.doc_entry, DomainEvent.machine_id, DomainEvent.occurred_at)
        .where(DomainEvent.event_type == EventType.MACHINE_ORDER_STARTED)
        .where(DomainEvent.doc_entry.is_not(None))
        .order_by(DomainEvent.occurred_at)
    ).all():
        if row.doc_entry not in start_machine and row.machine_id:
            start_machine[row.doc_entry] = row.machine_id

    orders = session.execute(select(OrderState)).scalars().all()
    session.execute(delete(LatenessCause))
    written = 0
    for order in orders:
        due = order.due_date
        if not due:
            continue
        due_day = date.fromisoformat(due)
        closed = closed_at.get(order.doc_entry)
        is_closed_late = closed is not None and closed.date() > due_day
        is_open_late = order.status in {"P", "R"} and due_day < today and closed is None
        if not is_closed_late and not is_open_late:
            continue

        segment = session.get(OrderFlowSegment, order.doc_entry)
        planned = float(order.planned_qty or 0)
        rejected = float(order.rejected_qty or 0)
        scrap = planned > 0 and (rejected / planned) >= SCRAP_RATIO
        unstable = change_counts.get(order.doc_entry, 0) >= UNSTABLE_CHANGES
        wait_h = segment.wait_h if segment is not None else None
        idle_h = 0.0
        if segment is not None and wait_h is not None and wait_h >= WAIT_HOURS:
            idle_h = _idle_hours_between(session, segment.released_at, segment.first_start_at)
        waiting_idle = wait_h is not None and wait_h >= WAIT_HOURS and idle_h >= IDLE_HOURS
        machine_id = start_machine.get(order.doc_entry)
        bottleneck = machine_id is not None and machine_id in capacity_machines

        cause = _pick_cause(
            material_gap=order.doc_entry in material_gap_orders,
            overdue_po=order.doc_entry in overdue_po_orders,
            waiting_idle=waiting_idle,
            bottleneck=bottleneck,
            scrap=scrap,
            unstable=unstable,
        )
        session.add(LatenessCause(
            doc_entry=order.doc_entry,
            item_code=order.item_code,
            cause=cause,
            due_date=due,
            closed_at=closed,
            evidence={
                "wait_h": wait_h,
                "idle_h": round(idle_h, 3),
                "machine_id": machine_id,
                "rejected_qty": rejected,
                "planned_qty": planned,
                "change_count": change_counts.get(order.doc_entry, 0),
            },
            computed_at=now,
        ))
        written += 1

    session.commit()
    logger.info("causes.classified", count=written)
    return written


def cause_counts(session: Session) -> list[tuple[str, int]]:
    """Return (cause, count) ordered by the fixed priority."""
    rows = session.execute(
        select(LatenessCause.cause, func.count()).group_by(LatenessCause.cause)
    ).all()
    found = {cause: int(n) for cause, n in rows}
    return [(cause, found[cause]) for cause in CAUSE_PRIORITY if cause in found]


def cause_citation(session: Session) -> str:
    """German clause listing current cause counts, or empty string."""
    counts = [(cause, n) for cause, n in cause_counts(session) if cause != "unassigned"]
    if not counts:
        return ""
    parts = [f"{n} {CAUSE_LABELS[cause]}" for cause, n in counts]
    return " Belegte Ursachen: " + ", ".join(parts) + "."
