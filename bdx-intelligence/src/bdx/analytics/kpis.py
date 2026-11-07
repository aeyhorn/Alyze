"""KPI computation functions for Auftragsabwicklung and Fertigungssteuerung.

All functions accept a SQLAlchemy ``Session`` and return a list of
``KpiResult`` named tuples that the analytics collector persists as
``KpiSnapshot`` rows.

Order KPIs (derived from order_state / order_snapshots / domain_events):
  - cycle_time_hours          - Median and P95 FA Durchlaufzeit (Released → Closed)
  - on_time_delivery_rate     - % FAs closed on or before due_date
  - backlog_overdue_count     - Open FAs past their due_date
  - rejection_rate_pct        - rejected_qty / planned_qty for closed FAs
  - completion_rate_pct       - completed_qty / planned_qty for closed FAs
  - release_to_start_hours    - Median hours between ORDER_RELEASED and first MACHINE_ORDER_STARTED
  - order_change_frequency    - Average QUANTITY_CHANGED + DUE_DATE_CHANGED events per FA

Machine KPIs (derived from machine_state_history / domain_events / shift_calendar):
  - machine_utilization_pct   - % time in state "running" during planned shift
  - setup_ratio_pct           - setup time / (running + setup) time
  - mtbf_hours                - Mean time between MACHINE_OFFLINE events
  - mttr_hours                - Mean recovery time (OFFLINE → ONLINE)
  - queue_unstarted_hours     - Released orders waiting > threshold with no machine start
  - override_low_pct          - % of machine_state_history intervals with feed/spindle override < 80
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from bdx.models.analytics import MachineStateHistory, ShiftCalendar
from bdx.models.events import DomainEvent, EventType, MachineState, OrderState

logger = structlog.get_logger(__name__)

# Default window used when computing KPIs unless overridden
DEFAULT_WINDOW_HOURS = 24 * 30  # 30 days


@dataclass
class KpiResult:
    """A single computed KPI value ready to be persisted."""

    metric_name: str
    dimension: str  # "global" | "machine" | "item_group"
    dimension_value: str | None
    value: float
    window_hours: int = DEFAULT_WINDOW_HOURS
    extra: dict[str, Any] = field(default_factory=dict)


# ── helpers ───────────────────────────────────────────────────────────────────


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _since(window_hours: int) -> datetime:
    return _now_utc() - timedelta(hours=window_hours)


def _percentile(values: list[float], p: float) -> float:
    """Return the p-th percentile (0-100) of *values* using linear interpolation."""
    if not values:
        return 0.0
    sorted_v = sorted(values)
    if len(sorted_v) == 1:
        return sorted_v[0]
    idx = (p / 100) * (len(sorted_v) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(sorted_v) - 1)
    return sorted_v[lo] + (sorted_v[hi] - sorted_v[lo]) * (idx - lo)


# ── Order KPIs ────────────────────────────────────────────────────────────────


def compute_cycle_time(session: Session, window_hours: int = DEFAULT_WINDOW_HOURS) -> list[KpiResult]:
    """Durchlaufzeit: elapsed hours from ORDER_RELEASED to ORDER_CLOSED, per item_group."""
    since = _since(window_hours)

    released = {
        row.doc_entry: row.occurred_at
        for row in session.execute(
            select(DomainEvent.doc_entry, DomainEvent.occurred_at)
            .where(DomainEvent.event_type == EventType.ORDER_RELEASED)
            .where(DomainEvent.occurred_at >= since)
            .where(DomainEvent.doc_entry.is_not(None))
        ).all()
    }
    closed = {
        row.doc_entry: row.occurred_at
        for row in session.execute(
            select(DomainEvent.doc_entry, DomainEvent.occurred_at)
            .where(DomainEvent.event_type == EventType.ORDER_CLOSED)
            .where(DomainEvent.occurred_at >= since)
            .where(DomainEvent.doc_entry.is_not(None))
        ).all()
    }

    # item_code lookup
    item_codes: dict[int, str] = {
        row.doc_entry: row.item_code
        for row in session.execute(
            select(OrderState.doc_entry, OrderState.item_code)
        ).all()
    }

    hours_by_group: dict[str, list[float]] = {}
    for doc_entry, released_at in released.items():
        if doc_entry not in closed:
            continue
        elapsed_h = (closed[doc_entry] - released_at).total_seconds() / 3600
        if elapsed_h < 0:
            continue
        group = item_codes.get(doc_entry, "unknown")
        hours_by_group.setdefault(group, []).append(elapsed_h)

    results: list[KpiResult] = []
    all_hours: list[float] = []
    for group, hours in hours_by_group.items():
        all_hours.extend(hours)
        median_h = statistics.median(hours)
        p95_h = _percentile(hours, 95)
        results.append(KpiResult(
            metric_name="cycle_time_hours",
            dimension="item_group",
            dimension_value=group,
            value=round(median_h, 2),
            window_hours=window_hours,
            extra={"p95": round(p95_h, 2), "sample_count": len(hours)},
        ))

    # Global median
    if all_hours:
        results.append(KpiResult(
            metric_name="cycle_time_hours",
            dimension="global",
            dimension_value=None,
            value=round(statistics.median(all_hours), 2),
            window_hours=window_hours,
            extra={"p95": round(_percentile(all_hours, 95), 2), "sample_count": len(all_hours)},
        ))

    return results


def compute_on_time_delivery(session: Session, window_hours: int = DEFAULT_WINDOW_HOURS) -> list[KpiResult]:
    """Termintreue: % of orders closed on or before their due_date."""
    since = _since(window_hours)

    closed_events = session.execute(
        select(DomainEvent.doc_entry, DomainEvent.occurred_at)
        .where(DomainEvent.event_type == EventType.ORDER_CLOSED)
        .where(DomainEvent.occurred_at >= since)
        .where(DomainEvent.doc_entry.is_not(None))
    ).all()

    if not closed_events:
        return []

    due_dates: dict[int, str | None] = {
        row.doc_entry: row.due_date
        for row in session.execute(
            select(OrderState.doc_entry, OrderState.due_date)
        ).all()
    }

    on_time = 0
    total = 0
    for doc_entry, occurred_at in closed_events:
        due = due_dates.get(doc_entry)
        if not due:
            continue
        total += 1
        close_date = occurred_at.date() if isinstance(occurred_at, datetime) else occurred_at
        if close_date <= date.fromisoformat(due):
            on_time += 1

    if total == 0:
        return []

    rate = round(100.0 * on_time / total, 2)
    return [KpiResult(
        metric_name="on_time_delivery_rate",
        dimension="global",
        dimension_value=None,
        value=rate,
        window_hours=window_hours,
        extra={"on_time": on_time, "total": total},
    )]


def compute_backlog_aging(session: Session, window_hours: int = DEFAULT_WINDOW_HOURS) -> list[KpiResult]:
    """Auftragsrückstand: number of open orders past their due_date."""
    today = _now_utc().date()

    open_orders = session.execute(
        select(OrderState.doc_entry, OrderState.due_date, OrderState.status)
        .where(OrderState.status.in_(["P", "R"]))
    ).all()

    overdue = 0
    critical = 0  # > 7 days overdue
    on_plan = 0
    for _, due_str, _ in open_orders:
        if not due_str:
            continue
        due = date.fromisoformat(due_str)
        delta = (today - due).days
        if delta <= 0:
            on_plan += 1
        elif delta <= 7:
            overdue += 1
        else:
            critical += 1

    total_tracked = overdue + critical + on_plan
    return [
        KpiResult(
            metric_name="backlog_overdue_count",
            dimension="global",
            dimension_value=None,
            value=float(overdue + critical),
            window_hours=window_hours,
            extra={"overdue_1_7d": overdue, "critical_gt7d": critical, "on_plan": on_plan, "total": total_tracked},
        )
    ]


def compute_rejection_rate(session: Session, window_hours: int = DEFAULT_WINDOW_HOURS) -> list[KpiResult]:
    """Ausschussquote: rejected_qty / planned_qty for closed orders in window."""
    since = _since(window_hours)

    closed_entries = {
        row.doc_entry
        for row in session.execute(
            select(DomainEvent.doc_entry)
            .where(DomainEvent.event_type == EventType.ORDER_CLOSED)
            .where(DomainEvent.occurred_at >= since)
            .where(DomainEvent.doc_entry.is_not(None))
        ).all()
    }

    if not closed_entries:
        return []

    orders = session.execute(
        select(OrderState.doc_entry, OrderState.item_code, OrderState.planned_qty, OrderState.rejected_qty)
        .where(OrderState.doc_entry.in_(list(closed_entries)))
    ).all()

    by_group: dict[str, tuple[float, float]] = {}  # group → (total_rejected, total_planned)
    total_r = total_p = 0.0

    for _, item_code, planned, rejected in orders:
        p = float(planned) if planned else 0.0
        r = float(rejected) if rejected else 0.0
        if p <= 0:
            continue
        total_p += p
        total_r += r
        prev_r, prev_p = by_group.get(item_code, (0.0, 0.0))
        by_group[item_code] = (prev_r + r, prev_p + p)

    results: list[KpiResult] = []
    for group, (rej, plan) in by_group.items():
        if plan > 0:
            results.append(KpiResult(
                metric_name="rejection_rate_pct",
                dimension="item_group",
                dimension_value=group,
                value=round(100.0 * rej / plan, 4),
                window_hours=window_hours,
                extra={"rejected": rej, "planned": plan},
            ))

    if total_p > 0:
        results.append(KpiResult(
            metric_name="rejection_rate_pct",
            dimension="global",
            dimension_value=None,
            value=round(100.0 * total_r / total_p, 4),
            window_hours=window_hours,
            extra={"rejected": total_r, "planned": total_p},
        ))

    return results


def compute_release_to_start(session: Session, window_hours: int = DEFAULT_WINDOW_HOURS) -> list[KpiResult]:
    """Startversatz: median hours from ORDER_RELEASED to first MACHINE_ORDER_STARTED."""
    since = _since(window_hours)

    released: dict[int, datetime] = {
        row.doc_entry: row.occurred_at
        for row in session.execute(
            select(DomainEvent.doc_entry, DomainEvent.occurred_at)
            .where(DomainEvent.event_type == EventType.ORDER_RELEASED)
            .where(DomainEvent.occurred_at >= since)
            .where(DomainEvent.doc_entry.is_not(None))
        ).all()
    }

    # First machine start per doc_entry
    machine_starts: dict[int, datetime] = {}
    for row in session.execute(
        select(DomainEvent.doc_entry, func.min(DomainEvent.occurred_at).label("first_start"))
        .where(DomainEvent.event_type == EventType.MACHINE_ORDER_STARTED)
        .where(DomainEvent.occurred_at >= since)
        .where(DomainEvent.doc_entry.is_not(None))
        .group_by(DomainEvent.doc_entry)
    ).all():
        machine_starts[row.doc_entry] = row.first_start

    delays: list[float] = []
    for doc_entry, rel_at in released.items():
        if doc_entry not in machine_starts:
            continue
        delay_h = (machine_starts[doc_entry] - rel_at).total_seconds() / 3600
        if delay_h >= 0:
            delays.append(delay_h)

    if not delays:
        return []

    return [KpiResult(
        metric_name="release_to_start_hours",
        dimension="global",
        dimension_value=None,
        value=round(statistics.median(delays), 2),
        window_hours=window_hours,
        extra={"p95": round(_percentile(delays, 95), 2), "sample_count": len(delays)},
    )]


def compute_order_change_frequency(session: Session, window_hours: int = DEFAULT_WINDOW_HOURS) -> list[KpiResult]:
    """Änderungsfrequenz: average number of QUANTITY_CHANGED + DUE_DATE_CHANGED per open order."""
    since = _since(window_hours)

    change_types = [EventType.QUANTITY_CHANGED, EventType.DUE_DATE_CHANGED]
    change_counts = session.execute(
        select(DomainEvent.doc_entry, func.count().label("cnt"))
        .where(DomainEvent.event_type.in_(change_types))
        .where(DomainEvent.occurred_at >= since)
        .where(DomainEvent.doc_entry.is_not(None))
        .group_by(DomainEvent.doc_entry)
    ).all()

    if not change_counts:
        return []

    counts = [row.cnt for row in change_counts]
    avg = statistics.mean(counts)
    return [KpiResult(
        metric_name="order_change_frequency",
        dimension="global",
        dimension_value=None,
        value=round(avg, 3),
        window_hours=window_hours,
        extra={"max": max(counts), "orders_with_changes": len(counts)},
    )]


# ── Machine / Production KPIs ─────────────────────────────────────────────────


def _planned_seconds_for_period(
    session: Session,
    machine_id: str | None,
    period_start: datetime,
    period_end: datetime,
) -> float:
    """Return planned working seconds from shift_calendar for the given period.

    Falls back to machine_id=NULL rows when no machine-specific entry exists.
    Returns the full period length (assumes 24/7) when no shift calendar is configured.
    """
    calendar_rows = session.execute(
        select(ShiftCalendar)
        .where(
            (ShiftCalendar.machine_id == machine_id) | (ShiftCalendar.machine_id.is_(None))
        )
        .where(ShiftCalendar.valid_from <= period_start.strftime("%Y-%m-%d"))
        .order_by(ShiftCalendar.machine_id.desc(), ShiftCalendar.valid_from.desc())
    ).scalars().all()

    if not calendar_rows:
        # No shift calendar: assume 24/7
        return (period_end - period_start).total_seconds()

    # Build a set of (weekday, start_h, end_h) entries, preferring machine-specific
    seen_weekdays: set[int] = set()
    entries: list[tuple[int, float, float]] = []
    for row in calendar_rows:
        if row.weekday in seen_weekdays:
            continue
        seen_weekdays.add(row.weekday)
        sh, sm = map(int, row.shift_start.split(":"))
        eh, em = map(int, row.shift_end.split(":"))
        entries.append((row.weekday, sh * 3600 + sm * 60, eh * 3600 + em * 60))

    planned = 0.0
    current = period_start.replace(hour=0, minute=0, second=0, microsecond=0)
    while current < period_end:
        day_end = current + timedelta(days=1)
        wd = current.weekday()
        for weekday, start_s, end_s in entries:
            if weekday != wd:
                continue
            shift_s = current + timedelta(seconds=start_s)
            shift_e = current + timedelta(seconds=end_s)
            overlap_s = max(shift_s, period_start)
            overlap_e = min(shift_e, period_end)
            if overlap_e > overlap_s:
                planned += (overlap_e - overlap_s).total_seconds()
        current = day_end

    return planned


def compute_machine_utilization(
    session: Session, window_hours: int = DEFAULT_WINDOW_HOURS
) -> list[KpiResult]:
    """Maschinenauslastung: % time in 'running' state vs planned shift hours."""
    since = _since(window_hours)
    now = _now_utc()

    machines = [
        row.machine_id
        for row in session.execute(select(MachineState.machine_id)).all()
    ]

    results: list[KpiResult] = []
    for machine_id in machines:
        history = session.execute(
            select(MachineStateHistory)
            .where(MachineStateHistory.machine_id == machine_id)
            .where(MachineStateHistory.started_at >= since)
        ).scalars().all()

        running_s = sum(
            (h.duration_s or 0.0) for h in history if h.state == "running"
        )
        planned_s = _planned_seconds_for_period(session, machine_id, since, now)

        if planned_s <= 0:
            continue

        utilization = round(100.0 * running_s / planned_s, 2)
        state_breakdown = {}
        for h in history:
            state_breakdown[h.state] = state_breakdown.get(h.state, 0.0) + (h.duration_s or 0.0)

        results.append(KpiResult(
            metric_name="machine_utilization_pct",
            dimension="machine",
            dimension_value=machine_id,
            value=utilization,
            window_hours=window_hours,
            extra={
                "running_hours": round(running_s / 3600, 2),
                "planned_hours": round(planned_s / 3600, 2),
                "state_hours": {k: round(v / 3600, 3) for k, v in state_breakdown.items()},
            },
        ))

    # Global average
    if results:
        avg_util = statistics.mean(r.value for r in results)
        results.append(KpiResult(
            metric_name="machine_utilization_pct",
            dimension="global",
            dimension_value=None,
            value=round(avg_util, 2),
            window_hours=window_hours,
            extra={"machine_count": len(results)},
        ))

    return results


def compute_setup_ratio(
    session: Session, window_hours: int = DEFAULT_WINDOW_HOURS
) -> list[KpiResult]:
    """Rüstzeit-Anteil: setup_time / (running + setup) per machine."""
    since = _since(window_hours)

    machines = [
        row.machine_id
        for row in session.execute(select(MachineState.machine_id)).all()
    ]

    results: list[KpiResult] = []
    for machine_id in machines:
        history = session.execute(
            select(MachineStateHistory.state, MachineStateHistory.duration_s)
            .where(MachineStateHistory.machine_id == machine_id)
            .where(MachineStateHistory.started_at >= since)
        ).all()

        setup_s = sum((d or 0.0) for s, d in history if s == "setup")
        running_s = sum((d or 0.0) for s, d in history if s == "running")
        denominator = setup_s + running_s

        if denominator <= 0:
            continue

        ratio = round(100.0 * setup_s / denominator, 2)
        results.append(KpiResult(
            metric_name="setup_ratio_pct",
            dimension="machine",
            dimension_value=machine_id,
            value=ratio,
            window_hours=window_hours,
            extra={"setup_hours": round(setup_s / 3600, 3), "running_hours": round(running_s / 3600, 3)},
        ))

    if results:
        avg = statistics.mean(r.value for r in results)
        results.append(KpiResult(
            metric_name="setup_ratio_pct",
            dimension="global",
            dimension_value=None,
            value=round(avg, 2),
            window_hours=window_hours,
            extra={"machine_count": len(results)},
        ))

    return results


def compute_mtbf_mttr(
    session: Session, window_hours: int = DEFAULT_WINDOW_HOURS
) -> list[KpiResult]:
    """MTBF and MTTR from MACHINE_OFFLINE / MACHINE_ONLINE domain events."""
    since = _since(window_hours)

    machines = [
        row.machine_id
        for row in session.execute(select(MachineState.machine_id)).all()
    ]

    results: list[KpiResult] = []
    for machine_id in machines:
        events = session.execute(
            select(DomainEvent.event_type, DomainEvent.occurred_at)
            .where(DomainEvent.machine_id == machine_id)
            .where(DomainEvent.event_type.in_([
                EventType.MACHINE_OFFLINE,
                EventType.MACHINE_ONLINE,
            ]))
            .where(DomainEvent.occurred_at >= since)
            .order_by(DomainEvent.occurred_at)
        ).all()

        offline_times: list[datetime] = []
        online_times: list[datetime] = []
        for etype, occurred_at in events:
            if etype == EventType.MACHINE_OFFLINE:
                offline_times.append(occurred_at)
            else:
                online_times.append(occurred_at)

        # MTTR: mean(online_time - offline_time) for matched pairs
        recovery_hours: list[float] = []
        for offline_at in offline_times:
            next_online = next(
                (t for t in online_times if t > offline_at), None
            )
            if next_online:
                recovery_hours.append((next_online - offline_at).total_seconds() / 3600)

        if recovery_hours:
            results.append(KpiResult(
                metric_name="mttr_hours",
                dimension="machine",
                dimension_value=machine_id,
                value=round(statistics.mean(recovery_hours), 3),
                window_hours=window_hours,
                extra={"incidents": len(recovery_hours), "max_mttr": round(max(recovery_hours), 3)},
            ))

        # MTBF: mean gap between OFFLINE events
        if len(offline_times) >= 2:
            gaps = [
                (offline_times[i + 1] - offline_times[i]).total_seconds() / 3600
                for i in range(len(offline_times) - 1)
            ]
            results.append(KpiResult(
                metric_name="mtbf_hours",
                dimension="machine",
                dimension_value=machine_id,
                value=round(statistics.mean(gaps), 3),
                window_hours=window_hours,
                extra={"failures": len(offline_times)},
            ))

    return results


def compute_queue_unstarted(
    session: Session,
    window_hours: int = DEFAULT_WINDOW_HOURS,
    unstarted_threshold_hours: float = 8.0,
) -> list[KpiResult]:
    """Warteschlangenüberlastung: released orders with no machine start after threshold hours."""
    since = _since(window_hours)

    released: dict[int, datetime] = {
        row.doc_entry: row.occurred_at
        for row in session.execute(
            select(DomainEvent.doc_entry, DomainEvent.occurred_at)
            .where(DomainEvent.event_type == EventType.ORDER_RELEASED)
            .where(DomainEvent.occurred_at >= since)
            .where(DomainEvent.doc_entry.is_not(None))
        ).all()
    }

    started: set[int] = {
        row.doc_entry
        for row in session.execute(
            select(DomainEvent.doc_entry)
            .where(DomainEvent.event_type == EventType.MACHINE_ORDER_STARTED)
            .where(DomainEvent.occurred_at >= since)
            .where(DomainEvent.doc_entry.is_not(None))
        ).all()
        if row.doc_entry is not None
    }

    cutoff = _now_utc() - timedelta(hours=unstarted_threshold_hours)
    unstarted = []
    for doc_entry, released_at in released.items():
        if doc_entry in started:
            continue
        # Normalize to UTC-aware for comparison (SQLite returns naive datetimes)
        if released_at.tzinfo is None:
            released_at = released_at.replace(tzinfo=UTC)
        if released_at <= cutoff:
            unstarted.append(doc_entry)

    return [KpiResult(
        metric_name="queue_unstarted_count",
        dimension="global",
        dimension_value=None,
        value=float(len(unstarted)),
        window_hours=window_hours,
        extra={"threshold_hours": unstarted_threshold_hours, "unstarted_doc_entries": unstarted[:50]},
    )]


def compute_oee_components(
    session: Session, window_hours: int = DEFAULT_WINDOW_HOURS
) -> list[KpiResult]:
    """OEE Availability component per machine (Leistung/Qualität need piece-counter data)."""
    # Availability = running_time / planned_time is the most reliably computable
    # component from the current data model (piece counters are not yet in history).
    # We emit oee_availability_pct here; Leistung and Qualität can be added once
    # MACHINE_PIECES_REPORTED events carry cumulative piece counters in their payload.
    since = _since(window_hours)
    now = _now_utc()

    machines = [
        row.machine_id
        for row in session.execute(select(MachineState.machine_id)).all()
    ]

    results: list[KpiResult] = []
    for machine_id in machines:
        history = session.execute(
            select(MachineStateHistory.state, MachineStateHistory.duration_s)
            .where(MachineStateHistory.machine_id == machine_id)
            .where(MachineStateHistory.started_at >= since)
            .where(MachineStateHistory.state.in_(["running", "setup", "idle"]))
        ).all()

        running_s = sum((d or 0.0) for s, d in history if s == "running")
        planned_s = _planned_seconds_for_period(session, machine_id, since, now)

        if planned_s <= 0:
            continue

        availability = round(min(100.0, 100.0 * running_s / planned_s), 2)
        results.append(KpiResult(
            metric_name="oee_availability_pct",
            dimension="machine",
            dimension_value=machine_id,
            value=availability,
            window_hours=window_hours,
            extra={
                "running_hours": round(running_s / 3600, 3),
                "planned_hours": round(planned_s / 3600, 3),
            },
        ))

    if results:
        avg = statistics.mean(r.value for r in results)
        results.append(KpiResult(
            metric_name="oee_availability_pct",
            dimension="global",
            dimension_value=None,
            value=round(avg, 2),
            window_hours=window_hours,
            extra={"machine_count": len(results)},
        ))

    return results


# ── Top-level runner ──────────────────────────────────────────────────────────

# Registry of all KPI compute functions; each returns list[KpiResult]
_KPI_FUNCTIONS = [
    compute_cycle_time,
    compute_on_time_delivery,
    compute_backlog_aging,
    compute_rejection_rate,
    compute_release_to_start,
    compute_order_change_frequency,
    compute_machine_utilization,
    compute_setup_ratio,
    compute_mtbf_mttr,
    compute_queue_unstarted,
    compute_oee_components,
]


def compute_all_kpis(session: Session, window_hours: int = DEFAULT_WINDOW_HOURS) -> list[KpiResult]:
    """Run all KPI functions and return a flat list of KpiResults."""
    results: list[KpiResult] = []
    for fn in _KPI_FUNCTIONS:
        try:
            partial = fn(session, window_hours=window_hours)
            results.extend(partial)
            logger.debug("kpi.computed", metric=fn.__name__, count=len(partial))
        except Exception as exc:
            logger.warning("kpi.compute_failed", metric=fn.__name__, error=str(exc))
    return results
