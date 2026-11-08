"""Tests for the /api/v1/analytics/weaknesses endpoint."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("POSTGRES_DSN", "sqlite:///:memory:")

from bdx.db.postgres import Base
from bdx.models.events import DomainEvent, MachineState, OrderState, SnapshotRun

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def test_engine():
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="module")
def test_session_factory(test_engine):
    return sessionmaker(bind=test_engine)


@pytest.fixture(scope="module")
def client(test_session_factory):
    from bdx.api.main import create_app

    app = create_app(pg_session_factory=test_session_factory, api_key="")
    app.state.sap_ok = False
    app.state.machine_adapter = None
    app.state.bde_adapter = None
    with TestClient(app) as c:
        yield c


def _now() -> datetime:
    return datetime.now(UTC)


def _order(
    doc_entry: int,
    status: str = "R",
    due_date: str | None = None,
    planned_qty: float = 100.0,
    completed_qty: float = 0.0,
    last_changed_at: datetime | None = None,
) -> OrderState:
    now = _now()
    return OrderState(
        source_key=f"OWOR:{doc_entry}",
        doc_entry=doc_entry,
        doc_num=doc_entry,
        status=status,
        item_code=f"PART-{doc_entry}",
        planned_qty=planned_qty,
        completed_qty=completed_qty,
        rejected_qty=0.0,
        due_date=due_date,
        start_date=None,
        u_type=None,
        u_priority=None,
        comments=None,
        sap_update_date=None,
        sap_update_ts=None,
        captured_at=now,
        snapshot_run_id="run-test",
        fingerprint="fp",
        first_seen_at=now,
        last_changed_at=last_changed_at or now,
    )


def _event(
    event_type: str,
    doc_entry: int | None = None,
    machine_id: str | None = None,
    occurred_at: datetime | None = None,
) -> DomainEvent:
    return DomainEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        source_key=f"OWOR:{doc_entry}" if doc_entry else "machine",
        doc_entry=doc_entry,
        doc_num=doc_entry,
        item_code=f"PART-{doc_entry}" if doc_entry else None,
        machine_id=machine_id,
        payload={},
        occurred_at=occurred_at or _now(),
        snapshot_run_id="run-test",
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_weaknesses_empty(client):
    """Endpoint returns expected keys even with no data."""
    resp = client.get("/api/v1/analytics/weaknesses")
    assert resp.status_code == 200
    data = resp.json()
    for key in (
        "summary",
        "overdue_orders",
        "stuck_orders",
        "plan_changes",
        "idle_machines",
        "machine_offlines_24h",
        "collector_errors_7d",
        "run_trend",
    ):
        assert key in data, f"missing key: {key}"
    s = data["summary"]
    assert s["overdue_orders"] == 0
    assert s["stuck_orders"] == 0


def test_analytics_page_served(client):
    """GET /analytics serves the HTML dashboard."""
    resp = client.get("/analytics")
    assert resp.status_code == 200
    assert "Schwachstellen" in resp.text


def test_overdue_orders(client, test_session_factory):
    """Orders with due_date in the past and open status appear in overdue_orders."""
    session = test_session_factory()
    yesterday = (datetime.now(UTC) - timedelta(days=2)).date().isoformat()
    future = (datetime.now(UTC) + timedelta(days=30)).date().isoformat()
    session.add(_order(2001, status="R", due_date=yesterday))
    session.add(_order(2002, status="R", due_date=future))
    session.add(_order(2003, status="L", due_date=yesterday))  # closed - must NOT appear
    session.commit()
    session.close()

    resp = client.get("/api/v1/analytics/weaknesses")
    assert resp.status_code == 200
    data = resp.json()

    overdue_entries = data["overdue_orders"]
    doc_entries = [o["doc_entry"] for o in overdue_entries]
    assert 2001 in doc_entries, "overdue open order should be listed"
    assert 2002 not in doc_entries, "future-due order must not be listed"
    assert 2003 not in doc_entries, "closed order must not be listed"

    # days_overdue should be a positive integer
    for o in overdue_entries:
        if o["doc_entry"] == 2001:
            assert o["days_overdue"] is not None and o["days_overdue"] >= 1

    assert data["summary"]["overdue_orders"] == len(overdue_entries)


def test_stuck_orders(client, test_session_factory):
    """Released orders with <10% completion unchanged for >3 days appear in stuck_orders."""
    session = test_session_factory()
    old_ts = _now() - timedelta(days=5)
    recent_ts = _now() - timedelta(hours=1)
    # Stuck: R, 0% done, unchanged 5 days
    session.add(
        _order(3001, status="R", planned_qty=100.0, completed_qty=0.0, last_changed_at=old_ts)
    )
    # Not stuck: recently changed
    session.add(
        _order(3002, status="R", planned_qty=100.0, completed_qty=0.0, last_changed_at=recent_ts)
    )
    # Not stuck: >10% done
    session.add(
        _order(3003, status="R", planned_qty=100.0, completed_qty=50.0, last_changed_at=old_ts)
    )
    session.commit()
    session.close()

    resp = client.get("/api/v1/analytics/weaknesses")
    data = resp.json()
    stuck = {o["doc_entry"] for o in data["stuck_orders"]}
    assert 3001 in stuck
    assert 3002 not in stuck
    assert 3003 not in stuck
    assert data["summary"]["stuck_orders"] == len(data["stuck_orders"])


def test_plan_changes(client, test_session_factory):
    """QUANTITY_CHANGED and DUE_DATE_CHANGED events within 7 days appear in plan_changes."""
    session = test_session_factory()
    recent = _now() - timedelta(days=3)
    old = _now() - timedelta(days=10)

    session.add(_order(4001, status="R"))
    session.add(_order(4002, status="R"))
    session.add(_event("QUANTITY_CHANGED", doc_entry=4001, occurred_at=recent))
    session.add(_event("DUE_DATE_CHANGED", doc_entry=4001, occurred_at=recent - timedelta(hours=1)))
    session.add(_event("QUANTITY_CHANGED", doc_entry=4002, occurred_at=old))  # too old
    session.commit()
    session.close()

    resp = client.get("/api/v1/analytics/weaknesses")
    data = resp.json()
    plan_entries = {o["doc_entry"]: o for o in data["plan_changes"]}
    assert 4001 in plan_entries
    assert 4002 not in plan_entries
    assert plan_entries[4001]["latest_change_type"] in ("QUANTITY_CHANGED", "DUE_DATE_CHANGED")
    assert data["summary"]["plan_changes_7d"] == len(data["plan_changes"])


def test_idle_machines(client, test_session_factory):
    """Online machines that are not in 'running' state appear in idle_machines."""
    session = test_session_factory()
    now = _now()
    session.add(
        MachineState(
            machine_id="M-IDLE",
            online=True,
            mde_enabled=True,
            state="idle",
            exec_state="Bereit",
            order_ref=None,
            first_seen_at=now,
            last_seen_at=now,
            last_changed_at=now,
        )
    )
    session.add(
        MachineState(
            machine_id="M-RUN",
            online=True,
            mde_enabled=True,
            state="running",
            exec_state="Fertigen",
            order_ref="1234",
            first_seen_at=now,
            last_seen_at=now,
            last_changed_at=now,
        )
    )
    session.add(
        MachineState(
            machine_id="M-OFF",
            online=False,
            mde_enabled=True,
            state=None,
            exec_state=None,
            order_ref=None,
            first_seen_at=now,
            last_seen_at=now,
            last_changed_at=now,
        )
    )
    session.commit()
    session.close()

    resp = client.get("/api/v1/analytics/weaknesses")
    data = resp.json()
    idle_ids = {m["machine_id"] for m in data["idle_machines"]}
    assert "M-IDLE" in idle_ids
    assert "M-RUN" not in idle_ids
    assert "M-OFF" not in idle_ids  # offline ≠ idle
    assert data["summary"]["idle_machines"] == len(data["idle_machines"])


def test_machine_offlines_24h(client, test_session_factory):
    """MACHINE_OFFLINE events in the last 24h are grouped per machine."""
    session = test_session_factory()
    recent = _now() - timedelta(hours=12)
    old = _now() - timedelta(hours=36)

    session.add(_event("MACHINE_OFFLINE", machine_id="M-A", occurred_at=recent))
    session.add(
        _event("MACHINE_OFFLINE", machine_id="M-A", occurred_at=recent - timedelta(minutes=30))
    )
    session.add(_event("MACHINE_OFFLINE", machine_id="M-B", occurred_at=old))  # outside window
    session.commit()
    session.close()

    resp = client.get("/api/v1/analytics/weaknesses")
    data = resp.json()
    offlines = data["machine_offlines_24h"]
    assert "M-A" in offlines
    assert len(offlines["M-A"]) == 2
    assert "M-B" not in offlines
    assert data["summary"]["machines_with_offlines_24h"] == len(offlines)


def test_collector_errors_7d(client, test_session_factory):
    """Snapshot runs with errors within 7 days appear in collector_errors_7d."""
    session = test_session_factory()
    recent = _now() - timedelta(days=2)
    old = _now() - timedelta(days=10)

    session.add(
        SnapshotRun(
            run_id="run-err-recent",
            started_at=recent,
            finished_at=recent + timedelta(seconds=5),
            mode="incremental",
            orders_read=10,
            orders_changed=0,
            events_created=0,
            error="connection timeout",
        )
    )
    session.add(
        SnapshotRun(
            run_id="run-err-old",
            started_at=old,
            finished_at=old + timedelta(seconds=5),
            mode="full",
            orders_read=100,
            orders_changed=0,
            events_created=0,
            error="old error",
        )
    )
    session.add(
        SnapshotRun(
            run_id="run-ok",
            started_at=recent,
            finished_at=recent + timedelta(seconds=3),
            mode="incremental",
            orders_read=5,
            orders_changed=0,
            events_created=0,
            error=None,
        )
    )
    session.commit()
    session.close()

    resp = client.get("/api/v1/analytics/weaknesses")
    data = resp.json()
    err_ids = {r["run_id"] for r in data["collector_errors_7d"]}
    assert "run-err-recent" in err_ids
    assert "run-err-old" not in err_ids
    assert "run-ok" not in err_ids
    assert data["summary"]["collector_errors_7d"] == len(data["collector_errors_7d"])


def test_run_trend(client, test_session_factory):
    """run_trend contains up to 20 recent collector runs with expected fields."""
    resp = client.get("/api/v1/analytics/weaknesses")
    data = resp.json()
    trend = data["run_trend"]
    assert isinstance(trend, list)
    if trend:
        r = trend[0]
        for field in ("run_id", "started_at", "mode", "has_error"):
            assert field in r, f"missing field in run_trend entry: {field}"
