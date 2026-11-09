"""Bottleneck rank: shift utilization times hours of released work still waiting."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from bdx.analytics.kpis import compute_machine_utilization
from bdx.models.analytics import BottleneckRank
from bdx.models.events import DomainEvent, EventType, MachineState, OrderState

logger = structlog.get_logger(__name__)

CAPACITY_UTIL = 70.0
STEERING_UTIL = 50.0
QUEUE_HOURS_MIN = 8.0


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _interpretation(utilization: float, queue_hours: float) -> str:
    if utilization >= CAPACITY_UTIL and queue_hours >= QUEUE_HOURS_MIN:
        return "capacity"
    if utilization < STEERING_UTIL and queue_hours >= QUEUE_HOURS_MIN:
        return "steering"
    return "balanced"


def rank_bottlenecks(session: Session, window_hours: int = 24 * 7) -> list[BottleneckRank]:
    """Replace bottleneck_rank with the current ranking and return the rows.

    Waiting released orders are attributed to the machine that most recently
    ran the same item. Orders without that history stay out of every queue.
    """
    now = datetime.now(UTC)
    since = now - timedelta(hours=window_hours)

    utils = {
        r.dimension_value: r.value
        for r in compute_machine_utilization(session, window_hours=window_hours)
        if r.dimension == "machine" and r.dimension_value
    }
    machines = [
        row.machine_id
        for row in session.execute(select(MachineState.machine_id)).all()
    ]
    for machine_id in machines:
        utils.setdefault(machine_id, 0.0)

    # Latest machine that started each item.
    item_machine: dict[str, tuple[datetime, str]] = {}
    starts = session.execute(
        select(DomainEvent.item_code, DomainEvent.machine_id, DomainEvent.occurred_at)
        .where(DomainEvent.event_type == EventType.MACHINE_ORDER_STARTED)
        .where(DomainEvent.machine_id.is_not(None))
        .where(DomainEvent.item_code.is_not(None))
        .order_by(DomainEvent.occurred_at)
    ).all()
    for item_code, machine_id, occurred_at in starts:
        occurred = _as_utc(occurred_at)
        if item_code and machine_id and occurred is not None:
            item_machine[item_code] = (occurred, machine_id)

    started_orders = {
        row.doc_entry
        for row in session.execute(
            select(DomainEvent.doc_entry)
            .where(DomainEvent.event_type == EventType.MACHINE_ORDER_STARTED)
            .where(DomainEvent.doc_entry.is_not(None))
        ).all()
        if row.doc_entry is not None
    }
    released_at = {
        row.doc_entry: _as_utc(row.occurred_at)
        for row in session.execute(
            select(DomainEvent.doc_entry, DomainEvent.occurred_at)
            .where(DomainEvent.event_type == EventType.ORDER_RELEASED)
            .where(DomainEvent.doc_entry.is_not(None))
            .where(DomainEvent.occurred_at >= since)
        ).all()
    }
    open_released = session.execute(
        select(OrderState.doc_entry, OrderState.item_code)
        .where(OrderState.status == "R")
    ).all()

    queue_hours: dict[str, float] = dict.fromkeys(machines, 0.0)
    waiting_orders: dict[str, int] = dict.fromkeys(machines, 0)
    for doc_entry, item_code in open_released:
        if doc_entry in started_orders:
            continue
        machine_id = item_machine.get(item_code, (None, None))[1]
        if machine_id not in queue_hours:
            continue
        released = released_at.get(doc_entry)
        if released is None:
            continue
        hours = max(0.0, (now - released).total_seconds() / 3600)
        queue_hours[machine_id] += hours
        waiting_orders[machine_id] += 1

    session.execute(delete(BottleneckRank))
    rows: list[BottleneckRank] = []
    for machine_id, utilization in utils.items():
        qh = round(queue_hours.get(machine_id, 0.0), 3)
        util = round(float(utilization), 2)
        row = BottleneckRank(
            machine_id=machine_id,
            utilization_pct=util,
            queue_hours=qh,
            score=round((util / 100.0) * qh, 4),
            waiting_orders=waiting_orders.get(machine_id, 0),
            interpretation=_interpretation(util, qh),
            computed_at=now,
        )
        session.add(row)
        rows.append(row)
    session.commit()
    rows.sort(key=lambda r: r.score, reverse=True)
    logger.info("bottleneck.ranked", machines=len(rows))
    return rows
