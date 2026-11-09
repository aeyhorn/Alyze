"""Promise Platform – engine + API tests (no real SAP / quoter)."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("POSTGRES_DSN", "sqlite:///:memory:")

from bdx.db.postgres import Base
from bdx.models.events import MachineState
from bdx.promise.confidence import compute_confidence
from bdx.promise.models import (  # noqa: F401 – register ORM
    Gap,
    GapStatus,
    Offer,
    OfferCreate,
    OfferStatus,
)
from bdx.promise import engine as pe
from bdx.q2p.models import Q2PInquiry  # noqa: F401


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


def _seed_idle_machine(session):
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
    session.commit()


def test_confidence_deducts_open_gaps():
    class G:
        def __init__(self, gap_type, status):
            self.gap_type = gap_type
            self.status = status

    score = compute_confidence(
        gaps=[G("einkauf", "open"), G("kalkulation", "resolved")],
        evaluation={"domains": [{"domain": "pricing", "status": "ok"}]},
    )
    assert 0.0 <= score <= 1.0
    assert score < 0.55 + 0.15  # bonus pricing minus einkauf weight


def test_create_and_recompute_offer(session):
    _seed_idle_machine(session)
    offer = pe.create_offer(
        session,
        OfferCreate(item_code="PART-A", qty=Decimal("3"), recompute=True),
        sap_engine=None,
        quoter=None,
    )
    assert offer.status in (
        OfferStatus.OPEN.value,
        OfferStatus.PROMISABLE.value,
        OfferStatus.COMPUTING.value,
    )
    assert offer.portal_token
    assert offer.version >= 2
    dto = pe.to_offer_dto(session, offer)
    assert dto.open_gap_count >= 1  # no SAP → purchase/human gaps
    assert dto.contract is not None
    assert len(dto.jobs) >= 3


def test_resolve_gap_updates_confidence(session):
    _seed_idle_machine(session)
    offer = pe.create_offer(
        session,
        OfferCreate(item_code="PART-A", qty=Decimal("1"), recompute=True),
        sap_engine=None,
    )
    gaps = [g for g in pe._gaps_for(session, offer.id) if g.status == GapStatus.OPEN.value]
    assert gaps
    from bdx.promise.models import GapResolve

    pe.resolve_gap(
        session,
        offer,
        gaps[0].id,
        GapResolve(resolution_note="manuell geklärt", resolved_by="tester"),
    )
    session.refresh(offer)
    g = session.get(Gap, gaps[0].id)
    assert g.status == GapStatus.RESOLVED.value


def test_api_offer_flow_and_portal(client, session_factory):
    session = session_factory()
    _seed_idle_machine(session)
    session.close()

    r = client.post(
        "/api/v1/promise/offers",
        json={"item_code": "PART-A", "qty": 2, "customer_name": "Acme", "recompute": True},
    )
    assert r.status_code == 200, r.text
    offer = r.json()
    assert offer["item_code"] == "PART-A"
    assert offer["portal_token"]
    offer_id = offer["id"]
    token = offer["portal_token"]

    r = client.get(f"/api/v1/promise/offers/{offer_id}")
    assert r.status_code == 200
    assert "gaps" in r.json()

    r = client.post(f"/api/v1/promise/offers/{offer_id}/recompute")
    assert r.status_code == 200

    # Resolve all open gaps then decide + publish
    detail = client.get(f"/api/v1/promise/offers/{offer_id}").json()
    for g in detail.get("gaps") or []:
        if g["status"] == "open":
            client.post(
                f"/api/v1/promise/offers/{offer_id}/gaps/{g['id']}/resolve",
                json={"resolution_note": "ok", "waive": False},
            )

    r = client.post(
        f"/api/v1/promise/offers/{offer_id}/decide",
        json={"decision": "accept", "decision_note": "go"},
    )
    assert r.status_code == 200
    assert r.json()["decision"] == "accept"

    r = client.post(
        f"/api/v1/promise/offers/{offer_id}/contract/publish",
        json={"customer_visible": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["customer_visible"] is True
    assert r.json()["status"] == "sent"

    # Portal projection – no API key
    r = client.get(f"/api/v1/portal/{token}")
    assert r.status_code == 200
    portal = r.json()
    assert portal["item_code"] == "PART-A"
    assert portal["contract"] is not None
    assert "evaluation" not in portal

    r = client.post(
        f"/api/v1/portal/{token}/accept",
        json={"accepted_by": "Max Mustermann"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"

    # UI shells
    assert client.get("/promise").status_code == 200
    assert client.get(f"/portal/{token}").status_code == 200


def test_portal_404_unknown_token(client):
    r = client.get("/api/v1/portal/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
