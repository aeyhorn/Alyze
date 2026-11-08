"""Tests for the diagnosis layer: quality, flow segments, causes, bottleneck."""
from __future__ import annotations

import os
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("POSTGRES_DSN", "sqlite:///:memory:")
os.environ.setdefault("SAP_DB_HOST", "localhost")
os.environ.setdefault("SAP_DB_NAME", "TEST")
os.environ.setdefault("SAP_DB_USER", "test")
os.environ.setdefault("SAP_DB_PASSWORD", "test")

from bdx.db.postgres import Base
from bdx.models.analytics import (
    BottleneckRank,
    LatenessCause,
    MachineStateHistory,
    MeasurementQuality,
    OrderFlowSegment,
    ShiftCalendar,
)
from bdx.models.events import DomainEvent, EventType, MachineState, OrderState


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()


def _now() -> datetime:
    return datetime.now(UTC)


def _ago(hours: float) -> datetime:
    return _now() - timedelta(hours=hours)


def _order(session, doc_entry: int, status: str = "R", item_code: str = "PART-A",
           planned: float = 100, rejected: float = 0, due_days: int = -2) -> None:
    now = _now()
    session.add(OrderState(
        source_key=f"OWOR:{doc_entry}",
        doc_entry=doc_entry,
        doc_num=doc_entry,
        status=status,
        item_code=item_code,
        planned_qty=Decimal(str(planned)),
        completed_qty=Decimal("0"),
        rejected_qty=Decimal(str(rejected)),
        due_date=(date.today() + timedelta(days=due_days)).isoformat(),
        fingerprint="x",
        captured_at=now,
        snapshot_run_id=str(uuid.uuid4()),
        first_seen_at=now,
        last_changed_at=now,
    ))


def _event(session, etype: EventType, doc_entry: int | None = None, machine_id: str | None = None,
           item_code: str | None = None, hours_ago: float = 0, payload: dict | None = None) -> None:
    session.add(DomainEvent(
        event_id=str(uuid.uuid4()),
        event_type=etype,
        source_key=f"OWOR:{doc_entry}" if doc_entry else f"MACHINE:{machine_id}",
        doc_entry=doc_entry,
        doc_num=doc_entry,
        item_code=item_code,
        machine_id=machine_id,
        payload=payload or {},
        occurred_at=_ago(hours_ago),
        snapshot_run_id=str(uuid.uuid4()),
    ))


def test_flow_segments_four_parts(session):
    from bdx.analytics.flow import build_flow_segments

    _order(session, 1, status="L", due_days=1)
    _event(session, EventType.ORDER_RELEASED, doc_entry=1, hours_ago=10)
    _event(session, EventType.MACHINE_ORDER_STARTED, doc_entry=1, machine_id="M1", hours_ago=6)
    _event(session, EventType.ORDER_CLOSED, doc_entry=1, hours_ago=1)
    session.add(MachineStateHistory(
        machine_id="M1",
        state="setup",
        sap_doc_entry=1,
        started_at=_ago(6),
        ended_at=_ago(5),
        duration_s=3600,
    ))
    session.add(MachineStateHistory(
        machine_id="M1",
        state="running",
        sap_doc_entry=1,
        started_at=_ago(5),
        ended_at=_ago(2),
        duration_s=3 * 3600,
    ))
    session.commit()

    assert build_flow_segments(session) == 1
    row = session.get(OrderFlowSegment, 1)
    assert row is not None
    assert row.wait_h == pytest.approx(4.0, abs=0.05)
    assert row.setup_h == pytest.approx(1.0, abs=0.05)
    assert row.run_h == pytest.approx(3.0, abs=0.05)
    assert row.post_process_h == pytest.approx(1.0, abs=0.05)
    assert row.total_h == pytest.approx(9.0, abs=0.05)


def test_cycle_time_reads_segments(session):
    from bdx.analytics.kpis import compute_cycle_time

    session.add(OrderFlowSegment(
        doc_entry=7,
        item_code="PART-A",
        closed_at=_ago(1),
        total_h=3.0,
        computed_at=_now(),
    ))
    _event(session, EventType.ORDER_RELEASED, doc_entry=7, hours_ago=20)
    _event(session, EventType.ORDER_CLOSED, doc_entry=7, hours_ago=1)
    session.commit()

    results = compute_cycle_time(session)
    global_row = next(r for r in results if r.dimension == "global")
    assert global_row.value == pytest.approx(3.0)
    assert global_row.extra["source"] == "segments"


def test_quality_marks_utilization_unreliable_without_calendar(session):
    from bdx.analytics.quality import record_measurement_quality

    session.add(MachineState(
        machine_id="M1",
        online=True,
        mde_enabled=True,
        order_ref="100",
        sap_doc_entry=100,
        first_seen_at=_now(),
        last_seen_at=_now(),
        last_changed_at=_now(),
    ))
    _event(session, EventType.MACHINE_ONLINE, machine_id="M1", hours_ago=1)
    session.commit()

    row = record_measurement_quality(session)
    assert row.link_rate == pytest.approx(1.0)
    assert row.utilization_reliable is False
    assert row.shift_calendar_rows == 0


def test_quality_reliable_when_linked_and_calendar_present(session):
    from bdx.analytics.quality import record_measurement_quality

    session.add(MachineState(
        machine_id="M1",
        online=True,
        mde_enabled=True,
        order_ref="100",
        sap_doc_entry=100,
        first_seen_at=_ago(24 * 10),
        last_seen_at=_now(),
        last_changed_at=_now(),
    ))
    session.add(ShiftCalendar(
        machine_id=None,
        weekday=0,
        shift_start="06:00",
        shift_end="14:00",
        valid_from="2000-01-01",
    ))
    _event(session, EventType.ORDER_RELEASED, doc_entry=1, hours_ago=24 * 10)
    session.commit()

    row = record_measurement_quality(session)
    assert isinstance(row, MeasurementQuality)
    assert row.utilization_reliable is True


def test_component_coverage_ignores_finished_good(session):
    from bdx.analytics.kpis_procurement import compute_material_coverage

    _order(session, 5, item_code="FINISHED", planned=100)
    session.commit()
    components = [{
        "doc_entry": 5,
        "item_code": "BOLT",
        "planned_qty": 10,
        "issued_qty": 0,
    }]
    stock = [{
        "item_code": "BOLT",
        "qty_available": 0,
        "qty_on_hand": 0,
    }]
    results = compute_material_coverage(session, stock, [], component_rows=components)
    item = next(r for r in results if r.dimension == "item_group")
    assert item.dimension_value == "BOLT"
    assert item.value == pytest.approx(0.0)
    assert "FINISHED" not in {r.dimension_value for r in results}
    global_row = next(r for r in results if r.metric_name == "material_coverage_pct" and r.dimension == "global")
    assert 5 in global_row.extra["critical_doc_entries"]


def test_lateness_material_gap_beats_scrap(session):
    from bdx.analytics.causes import classify_lateness

    _order(session, 9, status="R", planned=100, rejected=20, due_days=-3)
    session.commit()

    assert classify_lateness(session, material_gap_orders={9}) == 1
    row = session.get(LatenessCause, 9)
    assert row is not None
    assert row.cause == "material_gap"


def test_lateness_scrap_when_no_material_context(session):
    from bdx.analytics.causes import classify_lateness

    _order(session, 10, status="L", planned=100, rejected=10, due_days=-1)
    _event(session, EventType.ORDER_CLOSED, doc_entry=10, hours_ago=1)
    session.commit()

    classify_lateness(session)
    assert session.get(LatenessCause, 10).cause == "scrap"


def test_lateness_waiting_idle(session):
    from bdx.analytics.causes import classify_lateness
    from bdx.analytics.flow import build_flow_segments

    _order(session, 11, status="L", due_days=-1)
    _event(session, EventType.ORDER_RELEASED, doc_entry=11, hours_ago=20)
    _event(session, EventType.MACHINE_ORDER_STARTED, doc_entry=11, machine_id="M1", item_code="PART-A", hours_ago=2)
    _event(session, EventType.ORDER_CLOSED, doc_entry=11, hours_ago=1)
    session.add(MachineStateHistory(
        machine_id="M2",
        state="idle",
        started_at=_ago(18),
        ended_at=_ago(4),
        duration_s=14 * 3600,
    ))
    session.commit()
    build_flow_segments(session)

    classify_lateness(session)
    assert session.get(LatenessCause, 11).cause == "waiting_idle"


def test_bottleneck_capacity_vs_steering(session):
    from bdx.analytics.bottleneck import rank_bottlenecks

    now = _now()
    for machine_id in ("BUSY", "IDLE"):
        session.add(MachineState(
            machine_id=machine_id,
            online=True,
            mde_enabled=True,
            first_seen_at=now,
            last_seen_at=now,
            last_changed_at=now,
        ))
    session.add(MachineStateHistory(
        machine_id="BUSY",
        state="running",
        started_at=_ago(20),
        ended_at=_ago(1),
        duration_s=19 * 3600,
    ))
    _order(session, 21, status="R", item_code="BUSY-PART", due_days=2)
    _order(session, 22, status="R", item_code="IDLE-PART", due_days=2)
    _event(session, EventType.ORDER_RELEASED, doc_entry=21, item_code="BUSY-PART", hours_ago=12)
    _event(session, EventType.ORDER_RELEASED, doc_entry=22, item_code="IDLE-PART", hours_ago=12)
    _event(session, EventType.MACHINE_ORDER_STARTED, doc_entry=99, machine_id="BUSY",
           item_code="BUSY-PART", hours_ago=30)
    _event(session, EventType.MACHINE_ORDER_STARTED, doc_entry=98, machine_id="IDLE",
           item_code="IDLE-PART", hours_ago=30)
    session.commit()

    rows = rank_bottlenecks(session, window_hours=24)
    by_machine = {r.machine_id: r for r in rows}
    assert by_machine["BUSY"].interpretation == "capacity"
    assert by_machine["BUSY"].queue_hours == pytest.approx(12.0, abs=0.2)
    assert by_machine["IDLE"].interpretation == "steering"
    stored = session.execute(select(BottleneckRank).where(BottleneckRank.machine_id == "BUSY")).scalar_one()
    assert stored.score > 0


def test_anomaly_cites_cause(session):
    from bdx.analytics.anomalies import detect_and_persist
    from bdx.analytics.causes import classify_lateness
    from bdx.analytics.kpis import KpiResult
    from bdx.analytics.thresholds import seed_fixed_thresholds
    from bdx.models.analytics import DetectedAnomaly

    _order(session, 30, status="R", planned=100, rejected=15, due_days=-4)
    session.commit()
    seed_fixed_thresholds(session)
    classify_lateness(session)
    detect_and_persist(session, [KpiResult("backlog_overdue_count", "global", None, 12.0, 720)])

    row = session.execute(
        select(DetectedAnomaly).where(DetectedAnomaly.metric_name == "backlog_overdue_count")
    ).scalar_one()
    assert "Belegte Ursachen" in row.recommendation
