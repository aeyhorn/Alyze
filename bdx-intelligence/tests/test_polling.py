"""Tests for the SAP collector cycle (full + incremental) with a mocked SAP layer."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from bdx.collector import polling
from bdx.config import CollectorSettings
from bdx.models.events import DomainEvent, OrderSnapshot, OrderState, SnapshotRun


def _row(doc_entry: int, status: str = "R", planned="100", completed="0", update_date=None) -> dict:
    return {
        "doc_entry": doc_entry, "doc_num": doc_entry, "status": status, "item_code": "PART-A",
        "planned_qty": Decimal(planned), "completed_qty": Decimal(completed), "rejected_qty": Decimal("0"),
        "due_date": date(2026, 12, 1), "start_date": None, "post_date": None,
        "u_type": None, "u_priority": None, "comments": None,
        "update_date": update_date, "update_ts": None,
    }


class FakeSap:
    """Stands in for the SAP engine + query functions."""

    def __init__(self):
        self.full: list[dict] = []
        self.incremental: list[dict] = []
        self.by_docentry: dict[int, dict] = {}
        self.calls: list[tuple] = []

    @contextmanager
    def connect(self):
        yield self

    # query function replacements
    def fetch_all(self, conn):
        self.calls.append(("full",))
        return list(self.full)

    def fetch_incr(self, conn, since):
        self.calls.append(("incremental", since))
        return list(self.incremental)

    def fetch_by_ids(self, conn, ids):
        self.calls.append(("by_docentries", sorted(ids)))
        return [self.by_docentry[i] for i in ids if i in self.by_docentry]


@pytest.fixture
def sap(monkeypatch):
    fake = FakeSap()
    monkeypatch.setattr(polling, "fetch_all_orders_snapshot", fake.fetch_all)
    monkeypatch.setattr(polling, "fetch_orders_incremental", fake.fetch_incr)
    monkeypatch.setattr(polling, "fetch_orders_by_docentries", fake.fetch_by_ids)
    polling._CYCLE_COUNTER = 0
    return fake


@pytest.fixture
def factory(engine, session):
    # `session` fixture guarantees table cleanup afterwards
    return sessionmaker(bind=engine)


def _settings(**kw) -> CollectorSettings:
    return CollectorSettings(poll_interval_seconds=60, incremental_lookback_days=2, **kw)


def test_first_cycle_is_full_then_incremental(sap, factory):
    sap.full = [_row(1, "R"), _row(2, "P"), _row(3, "L", update_date=date(2026, 11, 1))]
    orders, events = polling.run_once(sap, factory, _settings())
    assert len(orders) == 3
    assert {e.event_type for e in events} == {"ORDER_CREATED"} and len(events) == 3
    assert sap.calls == [("full",)]

    with factory() as s:
        assert s.execute(select(OrderState)).scalars().all().__len__() == 3
        assert s.execute(select(OrderSnapshot)).scalars().all().__len__() == 3
        run = s.execute(select(SnapshotRun)).scalars().one()
        assert run.mode == "full" and run.orders_read == 3 and run.events_created == 3 and run.error is None

    # second cycle: incremental, nothing changed → no events, no history rows
    sap.incremental = [_row(1, "R"), _row(2, "P")]
    sap.by_docentry = {}
    orders, events = polling.run_once(sap, factory, _settings())
    assert events == []
    assert sap.calls[1][0] == "incremental"
    assert sap.calls[1][1] == date(2026, 11, 1) - polling.timedelta(days=2)
    with factory() as s:
        assert s.execute(select(OrderSnapshot)).scalars().all().__len__() == 3
        runs = s.execute(select(SnapshotRun).order_by(SnapshotRun.started_at)).scalars().all()
        assert [r.mode for r in runs] == ["full", "incremental"]


def test_incremental_detects_release_partial_and_vanished_close(sap, factory):
    sap.full = [_row(1, "R", completed="0"), _row(2, "P")]
    polling.run_once(sap, factory, _settings())

    # order 2 released, order 1 produced 40 pcs but… order 1 missing from result → re-read → closed
    sap.incremental = [_row(2, "R")]
    sap.by_docentry = {1: _row(1, "L", completed="100")}
    orders, events = polling.run_once(sap, factory, _settings())

    assert ("by_docentries", [1]) in sap.calls
    types = sorted(e.event_type for e in events)
    assert types == ["ORDER_CLOSED", "ORDER_RELEASED"]
    with factory() as s:
        st = {r.doc_entry: r for r in s.execute(select(OrderState)).scalars()}
        assert st[1].status == "L" and float(st[1].completed_qty) == 100.0
        assert st[2].status == "R"
        # history gets one row per change
        assert s.execute(select(OrderSnapshot)).scalars().all().__len__() == 4
        assert s.execute(select(DomainEvent)).scalars().all().__len__() == 4

    # third cycle: partial completion on order 2
    sap.incremental = [_row(2, "R", completed="30")]
    sap.by_docentry = {}
    _, events = polling.run_once(sap, factory, _settings())
    assert [e.event_type for e in events] == ["ORDER_PARTIAL_COMPLETE"]
    assert events[0].payload["new_completed_qty"] == "30"


def test_full_reload_every_n_cycles_and_force_full(sap, factory):
    sap.full = [_row(1, "R")]
    settings = _settings(full_reload_every_cycles=2)
    polling.run_once(sap, factory, settings)              # cycle 1: full (empty state)
    polling.run_once(sap, factory, settings)              # cycle 2: full (every 2)
    polling.run_once(sap, factory, settings)              # cycle 3: incremental
    polling.run_once(sap, factory, settings, force_full=True)
    modes = [c[0] for c in sap.calls if c[0] != "by_docentries"]
    assert modes == ["full", "full", "incremental", "full"]


def test_error_is_recorded_in_run(sap, factory):
    def boom(conn):
        raise RuntimeError("sap down")
    sap.fetch_all = boom
    polling.fetch_all_orders_snapshot = boom
    with pytest.raises(RuntimeError):
        polling.run_once(sap, factory, _settings())
    with factory() as s:
        run = s.execute(select(SnapshotRun)).scalars().one()
        assert run.error == "sap down" and run.finished_at is not None


def test_publisher_receives_events(sap, factory):
    sap.full = [_row(1, "R")]
    pub = MagicMock()
    polling.run_once(sap, factory, _settings(), publisher=pub)
    pub.publish.assert_called_once()
    assert len(pub.publish.call_args.args[0]) == 1
