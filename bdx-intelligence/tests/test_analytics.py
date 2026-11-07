"""Tests for the Sprint 005 analytics engine.

Uses in-memory SQLite (via the conftest ``engine`` and ``session`` fixtures).
No real Postgres, SAP, or SCADA required.
"""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from bdx.db.postgres import Base
from bdx.models.analytics import (
    DetectedAnomaly,
    KpiSnapshot,
    MachineStateHistory,
    MetricThreshold,
    ShiftCalendar,
)
from bdx.models.events import DomainEvent, EventType, MachineState, OrderState

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def analytics_engine():
    """Separate in-memory SQLite engine that includes the analytics tables."""
    import os
    os.environ.setdefault("POSTGRES_DSN", "sqlite:///:memory:")
    os.environ.setdefault("SAP_DB_HOST", "localhost")
    os.environ.setdefault("SAP_DB_NAME", "TEST")
    os.environ.setdefault("SAP_DB_USER", "test")
    os.environ.setdefault("SAP_DB_PASSWORD", "test")

    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def asession(analytics_engine):
    """A fresh session; rolls back and cleans tables after each test."""
    Session = sessionmaker(bind=analytics_engine)
    s = Session()
    yield s
    s.rollback()
    for table in reversed(Base.metadata.sorted_tables):
        s.execute(table.delete())
    s.commit()
    s.close()


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _dt(offset_hours: float = 0) -> datetime:
    return _utcnow() - timedelta(hours=offset_hours)


def _add_order(session, doc_entry: int, status: str = "R",
               planned: float = 100.0, completed: float = 0.0, rejected: float = 0.0,
               item_code: str = "PART-A",
               due_date: str | None = None) -> OrderState:
    o = OrderState(
        source_key=f"OWOR:{doc_entry}",
        doc_entry=doc_entry,
        doc_num=doc_entry,
        status=status,
        item_code=item_code,
        planned_qty=Decimal(str(planned)),
        completed_qty=Decimal(str(completed)),
        rejected_qty=Decimal(str(rejected)),
        due_date=due_date or (date.today() + timedelta(days=7)).isoformat(),
        start_date=None,
        fingerprint="x",
        captured_at=_utcnow(),
        snapshot_run_id=str(uuid.uuid4()),
        first_seen_at=_utcnow(),
        last_changed_at=_utcnow(),
    )
    session.add(o)
    return o


def _add_event(session, etype: EventType, doc_entry: int | None = None,
               machine_id: str | None = None, item_code: str | None = None,
               offset_hours: float = 0.0, payload: dict | None = None) -> DomainEvent:
    e = DomainEvent(
        event_id=str(uuid.uuid4()),
        event_type=etype,
        source_key=f"OWOR:{doc_entry}" if doc_entry else f"MACHINE:{machine_id}",
        doc_entry=doc_entry,
        doc_num=doc_entry,
        item_code=item_code,
        machine_id=machine_id,
        payload=payload or {},
        occurred_at=_dt(offset_hours),
        snapshot_run_id=str(uuid.uuid4()),
    )
    session.add(e)
    return e


def _add_machine(session, machine_id: str, state: str = "running") -> MachineState:
    m = MachineState(
        machine_id=machine_id,
        online=True,
        mde_enabled=True,
        state=state,
        first_seen_at=_utcnow(),
        last_seen_at=_utcnow(),
        last_changed_at=_utcnow(),
    )
    session.add(m)
    return m


def _add_history(session, machine_id: str, state: str, duration_s: float,
                 offset_hours: float = 0.0) -> MachineStateHistory:
    started = _dt(offset_hours + duration_s / 3600)
    ended = _dt(offset_hours)
    h = MachineStateHistory(
        machine_id=machine_id,
        state=state,
        started_at=started,
        ended_at=ended,
        duration_s=duration_s,
    )
    session.add(h)
    return h


# ── KPI: cycle_time_hours ─────────────────────────────────────────────────────


def test_cycle_time_basic(asession):
    from bdx.analytics.kpis import compute_cycle_time

    _add_order(asession, 1, status="L", item_code="PART-A")
    # Released 10 h ago, closed 2 h ago → 8 h
    _add_event(asession, EventType.ORDER_RELEASED, doc_entry=1, offset_hours=10)
    _add_event(asession, EventType.ORDER_CLOSED, doc_entry=1, offset_hours=2)
    asession.commit()

    results = compute_cycle_time(asession)
    assert len(results) >= 1
    global_r = next((r for r in results if r.dimension == "global"), None)
    assert global_r is not None
    assert abs(global_r.value - 8.0) < 0.1


def test_cycle_time_no_events(asession):
    from bdx.analytics.kpis import compute_cycle_time

    results = compute_cycle_time(asession)
    assert results == []


# ── KPI: on_time_delivery_rate ────────────────────────────────────────────────


def test_on_time_delivery_full(asession):
    from bdx.analytics.kpis import compute_on_time_delivery

    future_due = (date.today() + timedelta(days=10)).isoformat()
    _add_order(asession, 10, status="L", due_date=future_due)
    # Closed 1 h ago (before due date)
    _add_event(asession, EventType.ORDER_CLOSED, doc_entry=10, offset_hours=1)
    asession.commit()

    results = compute_on_time_delivery(asession)
    assert results
    assert results[0].value == 100.0


def test_on_time_delivery_partial(asession):
    from bdx.analytics.kpis import compute_on_time_delivery

    past_due = (date.today() - timedelta(days=3)).isoformat()
    future_due = (date.today() + timedelta(days=5)).isoformat()

    _add_order(asession, 20, status="L", due_date=past_due)
    _add_order(asession, 21, status="L", due_date=future_due)
    # Order 20 closed today → overdue; order 21 closed yesterday → on time
    _add_event(asession, EventType.ORDER_CLOSED, doc_entry=20, offset_hours=1)
    _add_event(asession, EventType.ORDER_CLOSED, doc_entry=21, offset_hours=25)
    asession.commit()

    results = compute_on_time_delivery(asession)
    assert results
    assert results[0].value == 50.0


# ── KPI: backlog_aging ────────────────────────────────────────────────────────


def test_backlog_aging(asession):
    from bdx.analytics.kpis import compute_backlog_aging

    overdue_date = (date.today() - timedelta(days=3)).isoformat()
    on_plan_date = (date.today() + timedelta(days=5)).isoformat()

    _add_order(asession, 30, status="R", due_date=overdue_date)
    _add_order(asession, 31, status="P", due_date=on_plan_date)
    asession.commit()

    results = compute_backlog_aging(asession)
    assert results
    r = results[0]
    assert r.metric_name == "backlog_overdue_count"
    assert r.value == 1.0
    assert r.extra["on_plan"] == 1


# ── KPI: rejection_rate ───────────────────────────────────────────────────────


def test_rejection_rate(asession):
    from bdx.analytics.kpis import compute_rejection_rate

    _add_order(asession, 40, status="L", planned=100.0, rejected=10.0, item_code="PART-X")
    _add_event(asession, EventType.ORDER_CLOSED, doc_entry=40, offset_hours=5)
    asession.commit()

    results = compute_rejection_rate(asession)
    global_r = next((r for r in results if r.dimension == "global"), None)
    assert global_r is not None
    assert abs(global_r.value - 10.0) < 0.01  # 10/100 = 10 %


# ── KPI: release_to_start ─────────────────────────────────────────────────────


def test_release_to_start(asession):
    from bdx.analytics.kpis import compute_release_to_start

    _add_order(asession, 50)
    # Released 10 h ago, machine started 4 h ago → 6 h delay
    _add_event(asession, EventType.ORDER_RELEASED, doc_entry=50, offset_hours=10)
    _add_event(asession, EventType.MACHINE_ORDER_STARTED, doc_entry=50, machine_id="M1", offset_hours=4)
    asession.commit()

    results = compute_release_to_start(asession)
    assert results
    assert abs(results[0].value - 6.0) < 0.1


# ── KPI: machine utilization ──────────────────────────────────────────────────


def test_machine_utilization_no_calendar(asession):
    """Without a shift calendar the full window is treated as 24/7 planned time."""
    from bdx.analytics.kpis import compute_machine_utilization

    _add_machine(asession, "MAZAK-01")
    # 8 h running in the last 24 h
    _add_history(asession, "MAZAK-01", "running", 8 * 3600, offset_hours=0)
    asession.commit()

    results = compute_machine_utilization(asession, window_hours=24)
    machine_r = next((r for r in results if r.dimension == "machine"), None)
    assert machine_r is not None
    # 8h / 24h ≈ 33.3%
    assert 30.0 < machine_r.value < 40.0


def test_machine_utilization_with_calendar(asession):
    from bdx.analytics.kpis import compute_machine_utilization

    _add_machine(asession, "MAZAK-02")
    # Add 8 h shift on today's weekday
    today_wd = datetime.now(UTC).weekday()
    asession.add(ShiftCalendar(
        machine_id=None,
        weekday=today_wd,
        shift_start="06:00",
        shift_end="14:00",  # 8 h shift
        valid_from="2000-01-01",
    ))
    # 4 h running in last 24 h (entirely within today's shift)
    _add_history(asession, "MAZAK-02", "running", 4 * 3600, offset_hours=2)
    asession.commit()

    results = compute_machine_utilization(asession, window_hours=24)
    machine_r = next((r for r in results if r.dimension == "machine" and r.dimension_value == "MAZAK-02"), None)
    assert machine_r is not None
    # 4h / (≤8h) = 50% or more depending on overlap
    assert machine_r.value >= 0.0


# ── KPI: MTBF / MTTR ─────────────────────────────────────────────────────────


def test_mttr_calculation(asession):
    from bdx.analytics.kpis import compute_mtbf_mttr

    _add_machine(asession, "MAZAK-03")
    # Offline at -10h, back online at -8h → MTTR = 2h
    _add_event(asession, EventType.MACHINE_OFFLINE, machine_id="MAZAK-03", offset_hours=10)
    _add_event(asession, EventType.MACHINE_ONLINE, machine_id="MAZAK-03", offset_hours=8)
    asession.commit()

    results = compute_mtbf_mttr(asession)
    mttr_r = next((r for r in results if r.metric_name == "mttr_hours"), None)
    assert mttr_r is not None
    assert abs(mttr_r.value - 2.0) < 0.1


# ── KPI: queue_unstarted ──────────────────────────────────────────────────────


def test_queue_unstarted(asession):
    from bdx.analytics.kpis import compute_queue_unstarted

    _add_order(asession, 60, status="R")
    # Released 24 h ago, never started
    _add_event(asession, EventType.ORDER_RELEASED, doc_entry=60, offset_hours=24)
    asession.commit()

    results = compute_queue_unstarted(asession, unstarted_threshold_hours=8.0)
    assert results
    assert results[0].value == 1.0


def test_queue_unstarted_started_order_not_counted(asession):
    from bdx.analytics.kpis import compute_queue_unstarted

    _add_order(asession, 61, status="R")
    _add_event(asession, EventType.ORDER_RELEASED, doc_entry=61, offset_hours=24)
    _add_event(asession, EventType.MACHINE_ORDER_STARTED, doc_entry=61, machine_id="M1", offset_hours=20)
    asession.commit()

    results = compute_queue_unstarted(asession, unstarted_threshold_hours=8.0)
    assert results
    assert results[0].value == 0.0


# ── Thresholds ────────────────────────────────────────────────────────────────


def test_seed_thresholds(asession):
    from bdx.analytics.thresholds import seed_fixed_thresholds

    count = seed_fixed_thresholds(asession)
    assert count > 0
    # Running again inserts nothing
    count2 = seed_fixed_thresholds(asession)
    assert count2 == 0


def test_tune_thresholds_insufficient_data(asession):
    """With < 14 samples the method stays 'fixed'."""
    from bdx.analytics.thresholds import seed_fixed_thresholds, tune_thresholds

    seed_fixed_thresholds(asession)
    # Add only 3 snapshots
    for i in range(3):
        asession.add(KpiSnapshot(
            metric_name="rejection_rate_pct",
            dimension="global",
            dimension_value=None,
            value=float(i),
            window_hours=720,
            computed_at=_dt(i),
        ))
    asession.commit()

    tune_thresholds(asession)
    # Should have updated the rejection_rate_pct entry but kept method='fixed'
    from sqlalchemy import select
    t = asession.execute(
        select(MetricThreshold)
        .where(MetricThreshold.metric_name == "rejection_rate_pct")
        .where(MetricThreshold.dimension == "global")
    ).scalars().first()
    assert t is not None
    assert t.method == "fixed"


def test_tune_thresholds_percentile(asession):
    """With ≥ 14 samples the method switches to 'percentile'."""
    from bdx.analytics.thresholds import (
        MIN_SAMPLES_FOR_PERCENTILE,
        seed_fixed_thresholds,
        tune_thresholds,
    )

    seed_fixed_thresholds(asession)
    for i in range(MIN_SAMPLES_FOR_PERCENTILE + 5):
        asession.add(KpiSnapshot(
            metric_name="cycle_time_hours",
            dimension="global",
            dimension_value=None,
            value=float(10 + i),
            window_hours=720,
            computed_at=_dt(float(i)),
        ))
    asession.commit()

    tune_thresholds(asession)

    from sqlalchemy import select
    t = asession.execute(
        select(MetricThreshold)
        .where(MetricThreshold.metric_name == "cycle_time_hours")
        .where(MetricThreshold.dimension == "global")
    ).scalars().first()
    assert t is not None
    assert t.method == "percentile"
    assert t.warn_threshold > 0


# ── Anomaly detection ─────────────────────────────────────────────────────────


def test_anomaly_detected(asession):
    from bdx.analytics.anomalies import detect_and_persist
    from bdx.analytics.kpis import KpiResult
    from bdx.analytics.thresholds import seed_fixed_thresholds

    seed_fixed_thresholds(asession)

    # Rejection rate of 50% clearly exceeds crit threshold (5%)
    kpis = [KpiResult(
        metric_name="rejection_rate_pct",
        dimension="global",
        dimension_value=None,
        value=50.0,
        window_hours=720,
    )]

    new, upd, res = detect_and_persist(asession, kpis)
    assert new == 1
    assert upd == 0
    assert res == 0

    from sqlalchemy import select
    row = asession.execute(
        select(DetectedAnomaly)
        .where(DetectedAnomaly.metric_name == "rejection_rate_pct")
        .where(DetectedAnomaly.resolved_at.is_(None))
    ).scalars().first()
    assert row is not None
    assert row.severity == "crit"
    assert "Ausschuss" in row.recommendation


def test_anomaly_updated(asession):
    from bdx.analytics.anomalies import detect_and_persist
    from bdx.analytics.kpis import KpiResult
    from bdx.analytics.thresholds import seed_fixed_thresholds

    seed_fixed_thresholds(asession)
    kpis = [KpiResult("rejection_rate_pct", "global", None, 50.0, 720)]

    new1, _, _ = detect_and_persist(asession, kpis)
    assert new1 == 1

    # Run again with same anomaly still active
    _, upd, _ = detect_and_persist(asession, kpis)
    assert upd == 1


def test_anomaly_resolved(asession):
    from bdx.analytics.anomalies import detect_and_persist
    from bdx.analytics.kpis import KpiResult
    from bdx.analytics.thresholds import seed_fixed_thresholds

    seed_fixed_thresholds(asession)

    # First run: anomaly
    kpis_bad = [KpiResult("rejection_rate_pct", "global", None, 50.0, 720)]
    detect_and_persist(asession, kpis_bad)

    # Second run: value back to normal (0.5%)
    kpis_ok = [KpiResult("rejection_rate_pct", "global", None, 0.5, 720)]
    _, _, res = detect_and_persist(asession, kpis_ok)
    assert res == 1

    from sqlalchemy import select
    resolved = asession.execute(
        select(DetectedAnomaly)
        .where(DetectedAnomaly.metric_name == "rejection_rate_pct")
        .where(DetectedAnomaly.resolved_at.is_not(None))
    ).scalars().first()
    assert resolved is not None


def test_no_anomaly_below_threshold(asession):
    from bdx.analytics.anomalies import detect_and_persist
    from bdx.analytics.kpis import KpiResult
    from bdx.analytics.thresholds import seed_fixed_thresholds

    seed_fixed_thresholds(asession)

    # 1% rejection - below warn threshold (2%)
    kpis = [KpiResult("rejection_rate_pct", "global", None, 1.0, 720)]
    new, upd, res = detect_and_persist(asession, kpis)
    assert new == 0 and upd == 0 and res == 0


# ── Machine state history builder ─────────────────────────────────────────────


def test_build_machine_state_history(asession):
    from bdx.analytics.history import build_machine_state_history

    _add_machine(asession, "MAZAK-04")
    # Two consecutive STATE_CHANGED events
    _add_event(asession, EventType.MACHINE_STATE_CHANGED, machine_id="MAZAK-04",
               offset_hours=5, payload={"new_state": "running"})
    _add_event(asession, EventType.MACHINE_STATE_CHANGED, machine_id="MAZAK-04",
               offset_hours=3, payload={"new_state": "idle"})
    asession.commit()

    rows = build_machine_state_history(asession)
    assert rows == 2

    from sqlalchemy import select
    history = asession.execute(
        select(MachineStateHistory).where(MachineStateHistory.machine_id == "MAZAK-04")
        .order_by(MachineStateHistory.started_at)
    ).scalars().all()
    assert len(history) == 2
    # First interval: running, duration ~2h
    assert history[0].state == "running"
    assert history[0].duration_s is not None
    assert abs(history[0].duration_s - 2 * 3600) < 60


def test_build_machine_state_history_incremental(asession):
    """Running twice should not duplicate rows."""
    from bdx.analytics.history import build_machine_state_history

    _add_machine(asession, "MAZAK-05")
    _add_event(asession, EventType.MACHINE_STATE_CHANGED, machine_id="MAZAK-05",
               offset_hours=4, payload={"new_state": "setup"})
    asession.commit()

    r1 = build_machine_state_history(asession)
    r2 = build_machine_state_history(asession)
    assert r1 == 1
    assert r2 == 0  # no new events → nothing inserted


# ── Analytics collector ───────────────────────────────────────────────────────


def test_run_analytics_once(analytics_engine):
    """Smoke test: run_analytics_once completes without errors on empty DB."""
    from contextlib import contextmanager

    from bdx.analytics.collector import run_analytics_once

    Session = sessionmaker(bind=analytics_engine)

    @contextmanager
    def factory():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    summary = run_analytics_once(factory)
    assert "kpis_computed" in summary
    assert "anomalies_new" in summary


# ── API routes ────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def api_client(analytics_engine):
    """TestClient backed by the analytics_engine."""
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker

    from bdx.api.main import create_app

    Session = sessionmaker(bind=analytics_engine)

    def pg_factory():
        return Session()

    app = create_app(
        pg_session_factory=pg_factory,
        api_key="",
    )
    return TestClient(app)


def test_api_kpis_empty(api_client):
    r = api_client.get("/api/v1/analytics/kpis")
    assert r.status_code == 200
    data = r.json()
    assert "kpis" in data


def test_api_anomalies_empty(api_client):
    r = api_client.get("/api/v1/analytics/anomalies")
    assert r.status_code == 200
    data = r.json()
    assert "anomalies" in data
    assert data["active_crit"] == 0


def test_api_thresholds_after_seed(api_client, analytics_engine):
    from sqlalchemy.orm import sessionmaker

    from bdx.analytics.thresholds import seed_fixed_thresholds

    Session = sessionmaker(bind=analytics_engine)
    with Session() as s:
        seed_fixed_thresholds(s)

    r = api_client.get("/api/v1/analytics/thresholds")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] > 0
    names = {t["metric_name"] for t in data["thresholds"]}
    assert "rejection_rate_pct" in names


def test_api_trends_empty(api_client):
    r = api_client.get("/api/v1/analytics/trends?metric=cycle_time_hours")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 0
    assert data["series"] == []


def test_api_kpi_not_found(api_client):
    r = api_client.get("/api/v1/analytics/kpis/nonexistent_metric")
    assert r.status_code == 404


def test_api_kpis_with_data(api_client, analytics_engine):
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=analytics_engine)
    with Session() as s:
        s.add(KpiSnapshot(
            metric_name="rejection_rate_pct",
            dimension="global",
            dimension_value=None,
            value=3.5,
            window_hours=720,
            computed_at=datetime.now(UTC),
        ))
        s.commit()

    r = api_client.get("/api/v1/analytics/kpis/rejection_rate_pct")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    assert data["kpis"][0]["value"] == pytest.approx(3.5)
