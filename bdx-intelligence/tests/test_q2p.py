"""Quote-to-Promise cockpit – service + API tests (no real SAP)."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("POSTGRES_DSN", "sqlite:///:memory:")

from bdx.db.postgres import Base
from bdx.models.events import MachineState, OrderState
from bdx.q2p.models import DomainStatus, Q2PInquiry  # noqa: F401 – register ORM
from bdx.q2p.service import evaluate_promise


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(bind=engine)


@pytest.fixture()
def session(session_factory):
    s = session_factory()
    yield s
    s.close()


@pytest.fixture()
def client(session_factory):
    from bdx.api.main import create_app

    app = create_app(pg_session_factory=session_factory, api_key="", sap_engine=None)
    with TestClient(app) as c:
        yield c


def _seed_capacity(session):
    now = datetime.now(timezone.utc)
    session.add(
        MachineState(
            machine_id="M1",
            online=True,
            mde_enabled=True,
            exec_state="Bereit",
            state="Bereit",
            order_ref=None,
            first_seen_at=now,
            last_seen_at=now,
            last_changed_at=now,
        )
    )
    session.add(
        OrderState(
            source_key="OWOR:1",
            doc_entry=1,
            doc_num=1,
            status="R",
            item_code="PART-A",
            planned_qty=10,
            completed_qty=0,
            rejected_qty=0,
            captured_at=now,
            snapshot_run_id="r1",
            fingerprint="x",
            first_seen_at=now,
            last_changed_at=now,
        )
    )
    session.commit()


def test_evaluate_without_sap_lists_human_questions(session):
    _seed_capacity(session)
    result = evaluate_promise(
        item_code="PART-A",
        qty=Decimal("5"),
        sap_engine=None,
        pg_session=session,
    )
    domains = {d.domain: d for d in result.domains}
    assert domains["capacity"].status == DomainStatus.OK
    assert domains["item"].status == DomainStatus.UNKNOWN
    assert domains["personnel"].needs_human is True
    assert any(q["domain"] == "personnel" for q in result.open_questions)
    assert result.overall in (DomainStatus.WARN, DomainStatus.BAD, DomainStatus.OK)


def test_evaluate_capacity_warn_when_busy(session):
    now = datetime.now(timezone.utc)
    session.add(
        MachineState(
            machine_id="M1",
            online=True,
            mde_enabled=True,
            exec_state="Fertigen",
            state="Fertigen",
            order_ref="1001",
            first_seen_at=now,
            last_seen_at=now,
            last_changed_at=now,
        )
    )
    session.commit()
    result = evaluate_promise(item_code="X", qty=1, sap_engine=None, pg_session=session)
    cap = next(d for d in result.domains if d.domain == "capacity")
    assert cap.status == DomainStatus.WARN
    assert cap.needs_human is True


def test_material_ok_with_mocked_sap():
    from bdx.q2p import service as svc

    conn = MagicMock()
    # Patch query helpers used inside _check_material
    original_stock = svc.sap_queries.fetch_warehouse_stock
    original_po = svc.sap_queries.fetch_open_purchase_lines
    svc.sap_queries.fetch_warehouse_stock = MagicMock(
        return_value=([{"warehouse": "01", "on_hand": 20, "is_committed": 2, "on_order": 0}], None)
    )
    svc.sap_queries.fetch_open_purchase_lines = MagicMock(return_value=([], None))
    try:
        result = svc._check_material(conn, "PART-A", Decimal("5"))
        assert result.status == DomainStatus.OK
        assert result.needs_human is False
        assert result.details["available"] == 18.0
    finally:
        svc.sap_queries.fetch_warehouse_stock = original_stock
        svc.sap_queries.fetch_open_purchase_lines = original_po


def test_q2p_page_served(client):
    resp = client.get("/q2p")
    assert resp.status_code == 200
    assert "Quote to Promise" in resp.text


def test_create_inquiry_and_decide(client, session_factory):
    # seed capacity into the same DB the app uses
    s = session_factory()
    _seed_capacity(s)
    s.close()

    resp = client.post(
        "/api/v1/q2p/inquiries",
        json={"item_code": "PART-A", "qty": 3, "customer_ref": "RFQ-1", "evaluate": True},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["item_code"] == "PART-A"
    assert body["status"] in ("ready", "blocked")
    assert body["promise_snapshot"] is not None
    assert "domains" in body["promise_snapshot"]
    inquiry_id = body["id"]

    listed = client.get("/api/v1/q2p/inquiries").json()
    assert any(r["id"] == inquiry_id for r in listed)

    one = client.get(f"/api/v1/q2p/inquiries/{inquiry_id}").json()
    assert one["customer_ref"] == "RFQ-1"

    decided = client.post(
        f"/api/v1/q2p/inquiries/{inquiry_id}/decide",
        json={"decision": "accept", "decision_note": "ok für KW46"},
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "decided"
    assert decided.json()["decision"] == "accept"


def test_adhoc_promise(client, session_factory):
    s = session_factory()
    _seed_capacity(s)
    s.close()
    resp = client.get("/api/v1/q2p/promise", params={"item_code": "PART-A", "qty": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert "domains" in data
    assert "open_questions" in data
    assert data["overall"] in ("ok", "warn", "bad", "unknown")


def test_reevaluate_endpoint(client, session_factory):
    s = session_factory()
    _seed_capacity(s)
    s.close()
    created = client.post(
        "/api/v1/q2p/inquiries",
        json={"item_code": "PART-A", "qty": 1, "evaluate": False},
    ).json()
    assert created["status"] == "draft"
    again = client.post(f"/api/v1/q2p/inquiries/{created['id']}/evaluate")
    assert again.status_code == 200
    assert again.json()["promise_snapshot"] is not None
