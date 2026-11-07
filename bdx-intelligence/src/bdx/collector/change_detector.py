"""Idempotent change detection between two snapshots.

Compares a previous snapshot (from PostgreSQL) against the current SAP state
and produces domain events.  Running the same comparison twice must yield the
same events (idempotency is enforced by the caller when persisting events).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Sequence

import structlog

from bdx.models.events import DomainEvent, EventType
from bdx.models.sap import (
    CLOSED_STATUSES,
    OPEN_STATUSES,
    STATUS_PLANNED,
    STATUS_RELEASED,
    WorkOrder,
)

logger = structlog.get_logger(__name__)

# Tolerance for float-based quantity comparisons stored via NUMERIC in Postgres
_QTY_EPSILON = Decimal("0.000001")


def _qty_changed(a: Decimal, b: Decimal) -> bool:
    return abs(a - b) > _QTY_EPSILON


def _get(prev, key: str, default=None):  # noqa: ANN001
    """Read a field from a previous-state dict or ORM row."""
    if isinstance(prev, dict):
        return prev.get(key, default)
    return getattr(prev, key, default)


def _dec(v) -> Decimal:  # noqa: ANN001
    return Decimal(str(v if v is not None else 0))


def detect_changes(
    previous: dict[str, dict],
    current: Sequence[WorkOrder],
    run_id: str,
    occurred_at: datetime | None = None,
) -> list[DomainEvent]:
    """Compare current WorkOrders against the previous snapshot dict.

    Args:
        previous: mapping {source_key: snapshot_dict} from the last stored snapshot.
                  Keys/values come from OrderSnapshot ORM rows converted to dicts.
        current:  current list of WorkOrder objects read from SAP.
        run_id:   the snapshot run_id being processed.
        occurred_at: timestamp for all produced events (default: utcnow).

    Returns:
        A list of DomainEvent ORM instances (not yet persisted).
    """
    occurred_at = occurred_at or datetime.now(timezone.utc)
    events: list[DomainEvent] = []

    current_map: dict[str, WorkOrder] = {wo.source_key: wo for wo in current}

    # Detect created orders and field changes
    for source_key, wo in current_map.items():
        prev = previous.get(source_key)

        if prev is None:
            events.append(_make_event(EventType.ORDER_CREATED, wo, run_id, occurred_at, payload={
                "status": wo.status,
                "planned_qty": str(wo.planned_qty),
                "due_date": wo.due_date.isoformat() if wo.due_date else None,
            }))
            logger.info("event.detected", type="ORDER_CREATED", source_key=source_key)
            continue

        prev_status = _get(prev, "status")
        prev_planned = _dec(_get(prev, "planned_qty", 0))
        prev_completed = _dec(_get(prev, "completed_qty", 0))
        prev_due = _get(prev, "due_date")

        # ORDER_RELEASED: status changed from Planned (P) to Released (R)
        if prev_status == STATUS_PLANNED and wo.status == STATUS_RELEASED:
            events.append(_make_event(EventType.ORDER_RELEASED, wo, run_id, occurred_at, payload={
                "prev_status": prev_status,
                "new_status": wo.status,
            }))
            logger.info("event.detected", type="ORDER_RELEASED", source_key=source_key)

        # ORDER_CLOSED: status became Closed (L) or Cancelled (C)
        if prev_status in OPEN_STATUSES and wo.status in CLOSED_STATUSES:
            events.append(_make_event(EventType.ORDER_CLOSED, wo, run_id, occurred_at, payload={
                "prev_status": prev_status,
                "new_status": wo.status,
                "completed_qty": str(wo.completed_qty),
                "planned_qty": str(wo.planned_qty),
            }))
            logger.info("event.detected", type="ORDER_CLOSED", source_key=source_key)

        # ORDER_PARTIAL_COMPLETE: completed quantity increased while still open
        if wo.status in OPEN_STATUSES and wo.completed_qty > prev_completed + _QTY_EPSILON:
            events.append(_make_event(EventType.ORDER_PARTIAL_COMPLETE, wo, run_id, occurred_at, payload={
                "prev_completed_qty": str(prev_completed),
                "new_completed_qty": str(wo.completed_qty),
                "planned_qty": str(wo.planned_qty),
            }))
            logger.info("event.detected", type="ORDER_PARTIAL_COMPLETE", source_key=source_key)

        # QUANTITY_CHANGED
        if _qty_changed(prev_planned, wo.planned_qty):
            events.append(_make_event(EventType.QUANTITY_CHANGED, wo, run_id, occurred_at, payload={
                "prev_planned_qty": str(prev_planned),
                "new_planned_qty": str(wo.planned_qty),
            }))
            logger.info("event.detected", type="QUANTITY_CHANGED", source_key=source_key)

        # DUE_DATE_CHANGED
        prev_due_str = prev_due.isoformat() if hasattr(prev_due, "isoformat") else str(prev_due or "")
        new_due_str = wo.due_date.isoformat() if wo.due_date else ""
        if prev_due_str != new_due_str:
            events.append(_make_event(EventType.DUE_DATE_CHANGED, wo, run_id, occurred_at, payload={
                "prev_due_date": prev_due_str,
                "new_due_date": new_due_str,
            }))
            logger.info("event.detected", type="DUE_DATE_CHANGED", source_key=source_key)

    # Note: orders that disappear from SAP entirely are not detected here
    # because they may just be filtered (incremental reads only return open or
    # recently updated orders).  ORDER_CLOSED is detected above by status change,
    # which is the reliable signal; the collector re-reads vanished open orders.

    logger.info("change_detection.complete", events_found=len(events))
    return events


def _make_event(
    event_type: EventType,
    wo: WorkOrder,
    run_id: str,
    occurred_at: datetime,
    payload: dict | None = None,
) -> DomainEvent:
    return DomainEvent(
        event_id=str(uuid.uuid4()),
        event_type=getattr(event_type, "value", event_type),
        source_key=wo.source_key,
        doc_entry=wo.doc_entry,
        doc_num=wo.doc_num,
        item_code=wo.item_code,
        payload=payload,
        occurred_at=occurred_at,
        snapshot_run_id=run_id,
    )


def persist_events(session, events: list[DomainEvent]) -> list[DomainEvent]:
    """Save events to PostgreSQL, skipping duplicates by event_id (idempotent).

    Returns the events that were actually inserted.
    """
    from sqlalchemy import select

    if not events:
        return []

    existing_ids = set(
        session.execute(
            select(DomainEvent.event_id).where(
                DomainEvent.event_id.in_([e.event_id for e in events])
            )
        ).scalars().all()
    )

    new_events = [e for e in events if e.event_id not in existing_ids]
    if new_events:
        session.bulk_save_objects(new_events)
        session.commit()
        logger.info("events.persisted", count=len(new_events))
    else:
        logger.debug("events.all_duplicate", skipped=len(events))
    return new_events
