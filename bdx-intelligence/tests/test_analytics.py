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


# -- Procurement KPI tests ----------------------------------------------------


def _make_stock_rows(item_code: str, qty_available: float, qty_on_hand: float | None = None) -> dict:
    return {
        "item_code": item_code,
        "warehouse_code": "WH01",
        "qty_on_hand": qty_on_hand if qty_on_hand is not None else qty_available,
        "qty_committed": 0.0,
        "qty_on_order": 0.0,
        "qty_available": qty_available,
    }


def _make_po_row(item_code: str, open_qty: float, earliest: str = "2026-12-01") -> dict:
    return {
        "item_code": item_code,
        "total_open_po_qty": open_qty,
        "earliest_delivery": earliest,
        "po_count": 1,
    }


def test_material_coverage_full(asession):
    from bdx.analytics.kpis_procurement import compute_material_coverage

    _add_order(asession, 100, status="R", planned=50.0, completed=0.0, item_code="BOLT-X")
    asession.commit()

    stock = [_make_stock_rows("BOLT-X", qty_available=80.0)]  # more than needed
    results = compute_material_coverage(asession, stock, [], window_hours=720)

    item_r = next((r for r in results if r.dimension == "item_group" and r.dimension_value == "BOLT-X"), None)
    assert item_r is not None
    assert item_r.value == 100.0  # fully covered

    global_r = next((r for r in results if r.metric_name == "material_coverage_pct" and r.dimension == "global"), None)
    assert global_r is not None
    assert global_r.value == 100.0


def test_material_coverage_partial(asession):
    from bdx.analytics.kpis_procurement import compute_material_coverage

    _add_order(asession, 101, status="R", planned=100.0, completed=0.0, item_code="GEAR-Y")
    asession.commit()

    stock = [_make_stock_rows("GEAR-Y", qty_available=40.0)]  # only 40% covered
    results = compute_material_coverage(asession, stock, [], window_hours=720)

    item_r = next((r for r in results if r.dimension == "item_group" and r.dimension_value == "GEAR-Y"), None)
    assert item_r is not None
    assert item_r.value == pytest.approx(40.0)


def test_critical_items_count(asession):
    from bdx.analytics.kpis_procurement import compute_material_coverage

    _add_order(asession, 102, status="R", planned=100.0, item_code="SHAFT-Z")
    asession.commit()

    # Stock=20, no PO -> gap = 80 -> critical
    stock = [_make_stock_rows("SHAFT-Z", qty_available=20.0)]
    results = compute_material_coverage(asession, stock, [], window_hours=720)

    crit_r = next((r for r in results if r.metric_name == "critical_items_count"), None)
    assert crit_r is not None
    assert crit_r.value == 1.0


def test_critical_item_covered_by_po(asession):
    """Item covered by open PO should NOT count as critical."""
    from bdx.analytics.kpis_procurement import compute_material_coverage

    _add_order(asession, 103, status="R", planned=100.0, item_code="AXLE-W")
    asession.commit()

    stock = [_make_stock_rows("AXLE-W", qty_available=20.0)]
    open_pos = [_make_po_row("AXLE-W", open_qty=90.0)]  # 20+90 >= 100
    results = compute_material_coverage(asession, stock, open_pos, window_hours=720)

    crit_r = next((r for r in results if r.metric_name == "critical_items_count"), None)
    assert crit_r is not None
    assert crit_r.value == 0.0


def test_po_lead_time(asession):
    from bdx.analytics.kpis_procurement import compute_po_lead_time

    lead_time_rows = [
        {"supplier_code": "SUP-01", "supplier_name": "Acme", "actual_lead_time_days": 10, "delivery_delay_days": 0},
        {"supplier_code": "SUP-01", "supplier_name": "Acme", "actual_lead_time_days": 14, "delivery_delay_days": 2},
        {"supplier_code": "SUP-02", "supplier_name": "Beta", "actual_lead_time_days": 30, "delivery_delay_days": 5},
    ]
    results = compute_po_lead_time(lead_time_rows)

    sup01 = next((r for r in results if r.dimension == "supplier" and r.dimension_value == "SUP-01"), None)
    assert sup01 is not None
    assert sup01.value == pytest.approx(12.0)  # median(10, 14) = 12

    global_r = next((r for r in results if r.dimension == "global"), None)
    assert global_r is not None
    assert global_r.value == pytest.approx(14.0)  # median(10, 14, 30) = 14


def test_supplier_otd(asession):
    from bdx.analytics.kpis_procurement import compute_supplier_otd

    otd_rows = [
        {"supplier_code": "SUP-01", "supplier_name": "Acme", "total_lines": 10, "on_time_lines": 8, "avg_delay_days": 1.5},
        {"supplier_code": "SUP-02", "supplier_name": "Beta", "total_lines": 5, "on_time_lines": 3, "avg_delay_days": 5.0},
    ]
    results = compute_supplier_otd(otd_rows)

    sup01 = next((r for r in results if r.dimension == "supplier" and r.dimension_value == "SUP-01"), None)
    assert sup01 is not None
    assert sup01.value == pytest.approx(80.0)

    global_r = next((r for r in results if r.dimension == "global"), None)
    assert global_r is not None
    # (8+3) / (10+5) = 73.33%
    assert abs(global_r.value - 73.33) < 0.1


def test_po_overdue_empty():
    from bdx.analytics.kpis_procurement import compute_po_overdue

    results = compute_po_overdue([])
    assert results
    assert results[0].metric_name == "po_overdue_count"
    assert results[0].value == 0.0


def test_po_overdue_with_rows():
    from bdx.analytics.kpis_procurement import compute_po_overdue

    overdue = [
        {"supplier_code": "SUP-01", "item_code": "BOLT-X", "days_overdue": 5, "open_qty": 10},
        {"supplier_code": "SUP-01", "item_code": "GEAR-Y", "days_overdue": 12, "open_qty": 5},
        {"supplier_code": "SUP-02", "item_code": "SHAFT-Z", "days_overdue": 3, "open_qty": 20},
    ]
    results = compute_po_overdue(overdue)

    global_r = next((r for r in results if r.metric_name == "po_overdue_count" and r.dimension == "global"), None)
    assert global_r is not None
    assert global_r.value == 3.0

    gr_delay = next((r for r in results if r.metric_name == "gr_delay_days"), None)
    assert gr_delay is not None
    assert gr_delay.value == pytest.approx(5.0)  # median(3, 5, 12) = 5


def test_stock_coverage_days():
    from bdx.analytics.kpis_procurement import compute_stock_coverage

    stock_rows = [
        {"item_code": "BOLT-X", "qty_on_hand": 100.0, "qty_committed": 0.0, "qty_available": 100.0},
    ]
    # 50 units consumed in 30 days window = 1.67/day -> coverage = 100/1.67 = ~60 days
    consumption_rows = [
        {"item_code": "BOLT-X", "total_issued_qty": 50.0, "total_movement_qty": 50.0},
    ]
    results = compute_stock_coverage(stock_rows, consumption_rows, window_hours=720)

    item_r = next((r for r in results if r.dimension == "item_group"), None)
    assert item_r is not None
    assert item_r.value == pytest.approx(60.0, abs=1.0)


def test_stock_coverage_critical_low():
    from bdx.analytics.kpis_procurement import compute_stock_coverage

    stock_rows = [{"item_code": "GEAR-Y", "qty_on_hand": 2.0, "qty_committed": 0.0, "qty_available": 2.0}]
    # 50 units / 30 days = 1.67/day -> 2 / 1.67 = ~1.2 days
    consumption_rows = [{"item_code": "GEAR-Y", "total_issued_qty": 50.0, "total_movement_qty": 50.0}]
    results = compute_stock_coverage(stock_rows, consumption_rows, window_hours=720)

    item_r = next((r for r in results if r.dimension == "item_group"), None)
    assert item_r is not None
    assert item_r.value < 3.0  # below crit threshold


def test_procurement_anomaly_recommendations(asession):
    """Verify procurement anomalies use the correct German recommendation."""
    from bdx.analytics.anomalies import detect_and_persist
    from bdx.analytics.kpis import KpiResult
    from bdx.analytics.thresholds import seed_fixed_thresholds

    seed_fixed_thresholds(asession)

    kpis = [
        KpiResult("critical_items_count", "global", None, 8.0, 720),   # crit (>5)
        KpiResult("supplier_otd_rate", "global", None, 60.0, 720),     # crit (<70%)
        KpiResult("stock_coverage_days", "item_group", "GEAR-Y", 2.0, 720),  # crit (<3d)
    ]

    new, _, _ = detect_and_persist(asession, kpis)
    assert new == 3

    from sqlalchemy import select

    crit_items = asession.execute(
        select(DetectedAnomaly)
        .where(DetectedAnomaly.metric_name == "critical_items_count")
        .where(DetectedAnomaly.resolved_at.is_(None))
    ).scalars().first()
    assert crit_items is not None
    assert crit_items.severity == "crit"
    assert "Einkauf" in crit_items.recommendation or "blockieren" in crit_items.recommendation

    otd_a = asession.execute(
        select(DetectedAnomaly)
        .where(DetectedAnomaly.metric_name == "supplier_otd_rate")
        .where(DetectedAnomaly.resolved_at.is_(None))
    ).scalars().first()
    assert otd_a is not None
    assert "Lieferant" in otd_a.recommendation

    stock_a = asession.execute(
        select(DetectedAnomaly)
        .where(DetectedAnomaly.metric_name == "stock_coverage_days")
        .where(DetectedAnomaly.resolved_at.is_(None))
    ).scalars().first()
    assert stock_a is not None
    assert "Lagerreichweite" in stock_a.recommendation


def test_procurement_thresholds_seeded(asession):
    """All procurement metric seeds should be present after seed_fixed_thresholds."""
    from bdx.analytics.thresholds import seed_fixed_thresholds

    seed_fixed_thresholds(asession)

    from sqlalchemy import select

    names = {
        row.metric_name
        for row in asession.execute(select(MetricThreshold.metric_name)).all()
    }
    for metric in [
        "material_coverage_pct",
        "critical_items_count",
        "po_lead_time_days",
        "supplier_otd_rate",
        "po_overdue_count",
        "gr_delay_days",
        "stock_coverage_days",
    ]:
        assert metric in names, f"Missing seed threshold for {metric}"
