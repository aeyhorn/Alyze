"""bdx-quoter HTTP adapter + Q2P pricing integration."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal
import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("POSTGRES_DSN", "sqlite:///:memory:")

from bdx.adapters.quoter import HttpQuoterClient, NullQuoterClient, QuoterQuote, _normalise
from bdx.config import QuoterSettings
from bdx.db.postgres import Base
from bdx.models.events import MachineState
from bdx.q2p.models import DomainStatus, Q2PInquiry  # noqa: F401
from bdx.q2p.service import evaluate_promise


@pytest.fixture()
def session():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    s = sessionmaker(bind=eng)()
    now = datetime.now(timezone.utc)
    s.add(
        MachineState(
            machine_id="M1",
            online=True,
            mde_enabled=True,
            state="Bereit",
            exec_state="Bereit",
            first_seen_at=now,
            last_seen_at=now,
            last_changed_at=now,
        )
    )
    s.commit()
    yield s
    s.close()


def test_normalise_projekt_json():
    data = {
        "datenraum": "/data/kunde/a",
        "kalkulation": {
            "netto_eur": 1234.5,
            "brutto_eur": 1470.0,
            "offen": ["Dicke Pos 3 unklar"],
            "positionen": [{"nr": 1}, {"nr": 2}],
        },
    }
    q = _normalise(data, source_path="/api/projekt")
    assert q.ok is True
    assert q.netto_eur == 1234.5
    assert q.position_count == 2
    assert q.offen == ["Dicke Pos 3 unklar"]


def test_http_quoter_posts_run():
    settings = QuoterSettings(
        enabled=True,
        base_url="http://quoter.test",
        run_path="/api/run",
        projekt_path="/api/projekt",
        health_path="/api/health",
        timeout_seconds=5,
    )

    def router(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/projekt":
            return httpx.Response(404)
        if request.url.path == "/api/run":
            return httpx.Response(
                200,
                json={
                    "kalkulation": {
                        "netto_eur": 99.0,
                        "offen": [],
                        "positionen": [{"nr": 1}],
                    }
                },
            )
        return httpx.Response(404)

    client2 = httpx.Client(transport=httpx.MockTransport(router), base_url="http://quoter.test")
    q = HttpQuoterClient(settings, client=client2)
    result = q.quote(datenraum="/mnt/001 KUNDEN/Test")
    assert result.ok is True
    assert result.netto_eur == 99.0


def test_evaluate_uses_quoter_offen(session):
    class FakeQuoter:
        def health(self) -> bool:
            return True

        def quote(self, **kwargs):
            return QuoterQuote(
                ok=True,
                netto_eur=500.0,
                brutto_eur=595.0,
                offen=["Werkstoff Pos 2 fehlt", "Masse unklar"],
                position_count=3,
                source_path="/api/run",
                status="done",
            )

    result = evaluate_promise(
        item_code="PE-1",
        qty=Decimal("1"),
        sap_engine=None,
        pg_session=session,
        quoter=FakeQuoter(),
        datenraum="/data/x",
    )
    pricing = next(d for d in result.domains if d.domain == "pricing")
    assert pricing.status == DomainStatus.WARN
    assert pricing.details["netto_eur"] == 500.0
    questions = [q["question"] for q in result.open_questions if q["domain"] == "pricing"]
    assert "Werkstoff Pos 2 fehlt" in questions
    assert "Masse unklar" in questions


def test_null_quoter():
    n = NullQuoterClient()
    assert n.health() is False
    assert n.quote(datenraum="/x").ok is False
