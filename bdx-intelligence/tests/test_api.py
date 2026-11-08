"""Tests for the FastAPI application using TestClient."""

from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("POSTGRES_DSN", "sqlite:///:memory:")

from bdx.db.postgres import Base
from bdx.models.events import DomainEvent, EventType, MachineState, OrderState, SnapshotRun


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
def client(test_engine, test_session_factory):
    from bdx.api.main import create_app

    # Pass the pre-populated session factory so the app uses the same SQLite
    # database that has tables and test data.
    app = create_app(pg_session_factory=test_session_factory, api_key="")
    app.state.sap_ok = False
    app.state.machine_adapter = None
    app.state.bde_adapter = None

    with TestClient(app) as c:
        yield c


def _order_state(doc_entry: int, status: str = "R", now=None) -> OrderState:
    now = now or datetime.now(UTC)
    return OrderState(
        source_key=f"OWOR:{doc_entry}",
        doc_entry=doc_entry,
        doc_num=doc_entry,
        status=status,
        item_code="PART-A",
        planned_qty=100.0,
        completed_qty=0.0,
        rejected_qty=0.0,
        due_date="2026-12-01",
        start_date=None,
        u_type=None,
        u_priority=None,
        comments=None,
        sap_update_date=None,
        sap_update_ts=None,
        captured_at=now,
        snapshot_run_id="run-test",
        fingerprint="x",
        first_seen_at=now,
        last_changed_at=now,
    )


def test_liveness(client):
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json()["alive"] is True


def test_health_without_sap(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["checks"]["postgres"] == "ok"
    assert data["checks"]["sap_sqlserver"] == "unknown"
    assert data["checks"]["machine_feed"] == "disabled"
    assert data["checks"]["collector"]["status"] == "empty"


def test_dashboard_served(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "BDX Intelligence" in resp.text


def test_orders_empty(client):
    resp = client.get("/api/v1/orders")
    assert resp.status_code == 200
    assert resp.json()["orders"] == []


def test_events_empty(client):
    resp = client.get("/api/v1/events")
    assert resp.status_code == 200
    assert resp.json()["events"] == []


def test_orders_with_data(client, test_session_factory):
    session = test_session_factory()
    session.add(_order_state(1001, "R"))
    session.add(_order_state(1002, "L"))
    session.commit()
    session.close()

    resp = client.get("/api/v1/orders")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1  # open only by default
    assert data["orders"][0]["source_key"] == "OWOR:1001"
    assert data["orders"][0]["status_label"] == "Released"

    resp = client.get("/api/v1/orders?open_only=false")
    assert resp.json()["count"] == 2

    resp = client.get("/api/v1/orders?status=L")
    assert resp.json()["count"] == 1

    resp = client.get("/api/v1/orders/summary")
    assert resp.json()["open"] == 1 and resp.json()["total"] == 2

    resp = client.get("/api/v1/orders/1001")
    assert resp.status_code == 200
    assert resp.json()["order"]["doc_entry"] == 1001
    assert client.get("/api/v1/orders/9999").status_code == 404


def test_events_with_data(client, test_session_factory):
    session = test_session_factory()
    ev = DomainEvent(
        event_id="evt-001",
        event_type=EventType.ORDER_CREATED.value,
        source_key="OWOR:1001",
        doc_entry=1001,
        doc_num=1,
        item_code="PART-A",
        payload={"status": "R"},
        occurred_at=datetime.now(UTC),
        snapshot_run_id="run-test",
    )
    session.add(ev)
    session.commit()
    session.close()

    resp = client.get("/api/v1/events")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    types = [e["event_type"] for e in data["events"]]
    assert "ORDER_CREATED" in types

    resp = client.get("/api/v1/events/summary")
    assert resp.json()["total"]["ORDER_CREATED"] >= 1


def test_machines_and_runs(client, test_session_factory):
    now = datetime.now(UTC)
    session = test_session_factory()
    session.add(
        MachineState(
            machine_id="QT 250MY",
            online=True,
            mde_enabled=True,
            exec_state="Bereit",
            state="running",
            order_ref="1001",
            pieces=5,
            sap_doc_entry=1001,
            sap_item_code="PART-A",
            first_seen_at=now,
            last_seen_at=now,
            last_changed_at=now,
        )
    )
    session.add(
        SnapshotRun(
            run_id="run-test",
            started_at=now,
            finished_at=now,
            mode="full",
            orders_read=2,
            orders_changed=2,
            events_created=1,
        )
    )
    session.commit()
    session.close()

    resp = client.get("/api/v1/machines")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1 and data["running"] == 1
    assert data["machines"][0]["sap_order"]["doc_num"] == 1001

    resp = client.get("/api/v1/machines/QT 250MY")
    assert resp.status_code == 200
    assert resp.json()["machine"]["state"] == "running"
    assert client.get("/api/v1/machines/nope").status_code == 404
    assert client.get("/api/v1/machines/QT 250MY/live").status_code == 503
    assert client.get("/api/v1/bde/records").status_code == 503

    resp = client.get("/api/v1/runs")
    assert resp.json()["runs"][0]["mode"] == "full"

    health = client.get("/health").json()
    assert health["checks"]["collector"]["status"] == "ok"


def test_api_key_protection(test_session_factory):
    from bdx.api.main import create_app

    app = create_app(pg_session_factory=test_session_factory, api_key="s3cret")
    app.state.machine_adapter = None
    with TestClient(app) as c:
        assert c.get("/api/v1/orders").status_code == 401
        assert c.get("/api/v1/orders", headers={"X-API-Key": "wrong"}).status_code == 401
        assert c.get("/api/v1/orders", headers={"X-API-Key": "s3cret"}).status_code == 200
        assert c.get("/api/v1/orders?api_key=s3cret").status_code == 200
        assert c.get("/health/live").status_code == 200  # health stays public
