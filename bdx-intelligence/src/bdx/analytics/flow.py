"""Order flow segments: release-to-start, setup, run, post-process to SAP close."""
from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from bdx.models.analytics import MachineStateHistory, OrderFlowSegment
from bdx.models.events import DomainEvent, EventType, OrderState

logger = structlog.get_logger(__name__)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _hours(start: datetime | None, end: datetime | None) -> float | None:
    start_utc = _as_utc(start)
    end_utc = _as_utc(end)
    if start_utc is None or end_utc is None:
        return None
    delta = (end_utc - start_utc).total_seconds() / 3600
    if delta < 0:
        return None
    return round(delta, 3)


def build_flow_segments(session: Session) -> int:
    """Upsert one flow segment per production order that has a release or close event.

    Returns the number of segment rows written.
    """
    now = datetime.now(UTC)
    doc_entries = {
        row.doc_entry
        for row in session.execute(
            select(DomainEvent.doc_entry)
            .where(DomainEvent.doc_entry.is_not(None))
            .where(DomainEvent.event_type.in_([
                EventType.ORDER_RELEASED,
                EventType.ORDER_CLOSED,
                EventType.MACHINE_ORDER_STARTED,
            ]))
        ).all()
        if row.doc_entry is not None
    }
    if not doc_entries:
        return 0

    item_codes = {
        row.doc_entry: row.item_code
        for row in session.execute(
            select(OrderState.doc_entry, OrderState.item_code)
            .where(OrderState.doc_entry.in_(list(doc_entries)))
        ).all()
    }

    written = 0
    for doc_entry in doc_entries:
        released_at = session.execute(
            select(func.min(DomainEvent.occurred_at))
            .where(DomainEvent.doc_entry == doc_entry)
            .where(DomainEvent.event_type == EventType.ORDER_RELEASED)
        ).scalar()
        closed_at = session.execute(
            select(func.max(DomainEvent.occurred_at))
            .where(DomainEvent.doc_entry == doc_entry)
            .where(DomainEvent.event_type == EventType.ORDER_CLOSED)
        ).scalar()
        first_start = session.execute(
            select(func.min(DomainEvent.occurred_at))
            .where(DomainEvent.doc_entry == doc_entry)
            .where(DomainEvent.event_type == EventType.MACHINE_ORDER_STARTED)
        ).scalar()
        finished_at = session.execute(
            select(func.max(DomainEvent.occurred_at))
            .where(DomainEvent.doc_entry == doc_entry)
            .where(DomainEvent.event_type == EventType.MACHINE_ORDER_FINISHED)
        ).scalar()

        history = session.execute(
            select(MachineStateHistory)
            .where(MachineStateHistory.sap_doc_entry == doc_entry)
        ).scalars().all()
        setup_s = sum((h.duration_s or 0.0) for h in history if h.state == "setup")
        run_s = sum((h.duration_s or 0.0) for h in history if h.state == "running")
        run_ends = [_as_utc(h.ended_at) for h in history if h.state == "running" and h.ended_at is not None]
        last_run_end = max(run_ends) if run_ends else _as_utc(finished_at)

        wait_h = _hours(released_at, first_start)
        setup_h = round(setup_s / 3600, 3) if history else None
        run_h = round(run_s / 3600, 3) if history else None
        post_h = _hours(last_run_end, closed_at)
        total_h = _hours(released_at, closed_at)

        row = session.get(OrderFlowSegment, doc_entry)
        if row is None:
            row = OrderFlowSegment(doc_entry=doc_entry, computed_at=now)
            session.add(row)
        row.item_code = item_codes.get(doc_entry)
        row.released_at = _as_utc(released_at)
        row.first_start_at = _as_utc(first_start)
        row.last_run_end_at = last_run_end
        row.closed_at = _as_utc(closed_at)
        row.wait_h = wait_h
        row.setup_h = setup_h
        row.run_h = run_h
        row.post_process_h = post_h
        row.total_h = total_h
        row.computed_at = now
        written += 1

    session.commit()
    logger.info("flow.segments_built", count=written)
    return written
