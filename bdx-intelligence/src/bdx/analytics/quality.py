"""Measurement quality: link rate, history depth, shift calendar, Little's Law."""
from __future__ import annotations

import statistics
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from bdx.analytics.kpis import DEFAULT_WINDOW_HOURS
from bdx.models.analytics import MeasurementQuality, OrderFlowSegment, ShiftCalendar
from bdx.models.events import DomainEvent, EventType, MachineState, OrderState

logger = structlog.get_logger(__name__)

LINK_RATE_MIN = 0.8
HISTORY_DAYS_MIN = 7.0
LITTLES_DEVIATION_MAX = 0.30

# KPI names the API must flag when the corresponding gate fails.
UTILIZATION_METRICS = frozenset({
    "machine_utilization_pct",
    "oee_availability_pct",
    "setup_ratio_pct",
})
CYCLE_TIME_METRICS = frozenset({"cycle_time_hours"})


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _median_cycle_hours(session: Session, since: datetime) -> tuple[float | None, int]:
    segments = session.execute(
        select(OrderFlowSegment.total_h, OrderFlowSegment.closed_at)
        .where(OrderFlowSegment.total_h.is_not(None))
    ).all()
    hours: list[float] = []
    for total_h, closed_at in segments:
        closed = _as_utc(closed_at)
        if closed is not None and closed >= since and total_h is not None:
            hours.append(float(total_h))
    if hours:
        return statistics.median(hours), len(hours)

    released = {
        row.doc_entry: _as_utc(row.occurred_at)
        for row in session.execute(
            select(DomainEvent.doc_entry, DomainEvent.occurred_at)
            .where(DomainEvent.event_type == EventType.ORDER_RELEASED)
            .where(DomainEvent.doc_entry.is_not(None))
        ).all()
    }
    for row in session.execute(
        select(DomainEvent.doc_entry, DomainEvent.occurred_at)
        .where(DomainEvent.event_type == EventType.ORDER_CLOSED)
        .where(DomainEvent.doc_entry.is_not(None))
    ).all():
        closed = _as_utc(row.occurred_at)
        started = released.get(row.doc_entry)
        if closed is None or started is None or closed < since:
            continue
        delta = (closed - started).total_seconds() / 3600
        if delta >= 0:
            hours.append(delta)
    if not hours:
        return None, 0
    return statistics.median(hours), len(hours)


def record_measurement_quality(
    session: Session,
    window_hours: int = DEFAULT_WINDOW_HOURS,
) -> MeasurementQuality:
    """Persist one quality snapshot and return it."""
    now = datetime.now(UTC)
    since = now - timedelta(hours=window_hours)

    machines = session.execute(select(MachineState)).scalars().all()
    with_order = [m for m in machines if m.order_ref]
    linked = [m for m in with_order if m.sap_doc_entry is not None]
    link_rate = (len(linked) / len(with_order)) if with_order else None

    first_event = session.execute(select(func.min(DomainEvent.occurred_at))).scalar()
    first_utc = _as_utc(first_event)
    history_days = ((now - first_utc).total_seconds() / 86400) if first_utc else 0.0

    shift_rows = session.execute(select(func.count()).select_from(ShiftCalendar)).scalar() or 0

    wip = float(session.execute(
        select(func.count()).select_from(OrderState).where(OrderState.status.in_(["P", "R"]))
    ).scalar() or 0)
    closed_n = session.execute(
        select(func.count())
        .select_from(DomainEvent)
        .where(DomainEvent.event_type == EventType.ORDER_CLOSED)
        .where(DomainEvent.occurred_at >= since)
    ).scalar() or 0
    throughput = float(closed_n) / float(window_hours) if window_hours else 0.0
    median_ct, _samples = _median_cycle_hours(session, since)

    predicted: float | None = None
    deviation: float | None = None
    if median_ct is not None:
        predicted = throughput * median_ct
        if wip > 0:
            deviation = abs(wip - predicted) / wip
        elif predicted == 0:
            deviation = 0.0

    utilization_reliable = bool(
        link_rate is not None and link_rate >= LINK_RATE_MIN and shift_rows > 0
    )
    cycle_time_reliable = bool(
        history_days >= HISTORY_DAYS_MIN
        and deviation is not None
        and deviation <= LITTLES_DEVIATION_MAX
    )

    row = MeasurementQuality(
        computed_at=now,
        link_rate=round(link_rate, 4) if link_rate is not None else None,
        linked_orders=len(linked),
        machine_orders_total=len(with_order),
        event_history_days=round(history_days, 2),
        shift_calendar_rows=int(shift_rows),
        wip=wip,
        throughput_per_hour=round(throughput, 6),
        median_cycle_time_h=round(median_ct, 3) if median_ct is not None else None,
        littles_law_predicted_wip=round(predicted, 3) if predicted is not None else None,
        littles_law_deviation=round(deviation, 4) if deviation is not None else None,
        utilization_reliable=utilization_reliable,
        cycle_time_reliable=cycle_time_reliable,
    )
    session.add(row)
    session.commit()
    logger.info(
        "quality.recorded",
        link_rate=row.link_rate,
        utilization_reliable=utilization_reliable,
        cycle_time_reliable=cycle_time_reliable,
    )
    return row


def latest_quality(session: Session) -> MeasurementQuality | None:
    return session.execute(
        select(MeasurementQuality).order_by(MeasurementQuality.computed_at.desc(), MeasurementQuality.id.desc())
    ).scalars().first()


def reliability_for_metric(session: Session, metric_name: str) -> bool | None:
    """Return False when the metric is gated and the latest snapshot says it is not reliable.

    None means the metric is not gated.
    """
    if metric_name not in UTILIZATION_METRICS and metric_name not in CYCLE_TIME_METRICS:
        return None
    row = latest_quality(session)
    if row is None:
        return None
    if metric_name in UTILIZATION_METRICS:
        return bool(row.utilization_reliable)
    return bool(row.cycle_time_reliable)
