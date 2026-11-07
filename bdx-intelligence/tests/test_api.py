"""Tests for the FastAPI application using TestClient."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("POSTGRES_DSN", "sqlite:///:memory:")

from bdx.db.postgres import Base
from bdx.models.events import DomainEvent, EventType, OrderSnapshot


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
    app = create_app(pg_session_factory=test_session_factory)
    app.state.sap_ok = False

    with TestClient(app) as c:
        yield c


def test_liveness(client):
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json()["alive"] is True


def test_health_degraded_without_sap(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["checks"]["sap_sqlserver"] == "error"


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
    now = datetime.now(timezone.utc)
    snap = OrderSnapshot(
        source_key="OWOR:1001",
        doc_entry=1001,
        doc_num=1,
        status="R",
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
    )
    session.add(snap)
    session.commit()
    session.close()

    resp = client.get("/api/v1/orders")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["orders"][0]["source_key"] == "OWOR:1001"


def test_events_with_data(client, test_session_factory):
    session = test_session_factory()
    ev = DomainEvent(
        event_id="evt-001",
        event_type=EventType.ORDER_CREATED,
        source_key="OWOR:1001",
        doc_entry=1001,
        doc_num=1,
        item_code="PART-A",
        payload={"status": "R"},
        occurred_at=datetime.now(timezone.utc),
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
