"""Tests for snapshot persistence and retrieval."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from bdx.collector.snapshots import load_latest_snapshot, save_snapshot
from bdx.models.sap import WorkOrder


def _make_wo(doc_entry: int) -> WorkOrder:
    return WorkOrder(
        doc_entry=doc_entry,
        doc_num=doc_entry * 10,
        status="R",
        item_code=f"ITEM-{doc_entry}",
        planned_qty=Decimal("100"),
        completed_qty=Decimal("0"),
        rejected_qty=Decimal("0"),
        due_date=date(2026, 12, 1),
        start_date=None,
        post_date=None,
    )


def test_save_and_load_snapshot(session):
    orders = [_make_wo(1), _make_wo(2)]
    run_id = save_snapshot(session, orders)
    assert run_id is not None

    latest = load_latest_snapshot(session)
    assert len(latest) == 2
    assert "OWOR:1" in latest
    assert "OWOR:2" in latest


def test_load_empty_when_no_snapshots(session):
    result = load_latest_snapshot(session)
    assert result == {}


def test_snapshot_overwrites_on_second_run(session):
    """The latest snapshot should reflect the most recent run."""
    orders_v1 = [_make_wo(1)]
    save_snapshot(session, orders_v1, run_id="run-1")

    orders_v2 = [_make_wo(1), _make_wo(2)]
    save_snapshot(session, orders_v2, run_id="run-2")

    latest = load_latest_snapshot(session)
    # run-2 is more recent, should have 2 orders
    assert len(latest) == 2


def test_save_snapshot_returns_run_id(session):
    orders = [_make_wo(10)]
    custom_run_id = "my-run-id"
    returned = save_snapshot(session, orders, run_id=custom_run_id)
    assert returned == custom_run_id
