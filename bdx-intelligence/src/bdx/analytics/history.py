"""Machine state history builder (Sprint 005).

Reads ``MACHINE_STATE_CHANGED`` domain events that have not yet been
materialised into ``machine_state_history`` and fills the gap.  Designed
to run incrementally - tracks the newest ``started_at`` per machine so it
never re-processes already-materialised intervals.
"""
from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from bdx.models.analytics import MachineStateHistory
from bdx.models.events import DomainEvent, EventType, MachineState

logger = structlog.get_logger(__name__)


def _now_utc() -> datetime:
    return datetime.now(UTC)


def build_machine_state_history(session: Session) -> int:
    """Materialise MACHINE_STATE_CHANGED events into machine_state_history.

    For each machine processes events newer than the latest materialised row
    and creates one history row per consecutive state interval.

    Returns the total number of new rows inserted.
    """
    machines = [
        row.machine_id
        for row in session.execute(select(MachineState.machine_id)).all()
    ]

    total_inserted = 0
    for machine_id in machines:
        total_inserted += _build_for_machine(session, machine_id)

    session.commit()
    if total_inserted:
        logger.info("machine_state_history.built", rows=total_inserted)
    return total_inserted


def _latest_materialised_at(session: Session, machine_id: str) -> datetime | None:
    """Return the ``started_at`` of the newest history row for this machine."""
    result = session.execute(
        select(func.max(MachineStateHistory.started_at))
        .where(MachineStateHistory.machine_id == machine_id)
    ).scalar()
    return result


def _build_for_machine(session: Session, machine_id: str) -> int:
    """Build state history for a single machine from domain events."""
    latest = _latest_materialised_at(session, machine_id)

    query = (
        select(DomainEvent)
        .where(DomainEvent.machine_id == machine_id)
        .where(DomainEvent.event_type == EventType.MACHINE_STATE_CHANGED)
        .order_by(DomainEvent.occurred_at)
    )
    if latest is not None:
        query = query.where(DomainEvent.occurred_at > latest)

    events = session.execute(query).scalars().all()
    if not events:
        return 0

    inserted = 0
    # Each MACHINE_STATE_CHANGED event marks the START of a new state.
    # The END of that state is the next event's occurred_at (or NULL for the last).
    for idx, event in enumerate(events):
        payload = event.payload or {}
        new_state: str | None = payload.get("new_state") or payload.get("state")
        if not new_state:
            continue

        started_at = event.occurred_at
        next_event = events[idx + 1] if idx + 1 < len(events) else None
        ended_at: datetime | None = next_event.occurred_at if next_event else None
        duration_s: float | None = (
            (ended_at - started_at).total_seconds() if ended_at else None
        )

        session.add(MachineStateHistory(
            machine_id=machine_id,
            state=new_state,
            started_at=started_at,
            ended_at=ended_at,
            duration_s=duration_s,
            sap_doc_entry=event.doc_entry,
            sap_item_code=event.item_code,
        ))
        inserted += 1

    return inserted
