"""Read-only integration tests against DEV SAP Business One.

These tests verify the real SAP SQL Server connection and the query
contracts (open orders, incremental read, by-DocEntry). They never write.

Expected on DEV (per docs/PROJECT_STATUS.md, 2026-11-07):
  * 871 open orders (status P or R)
  * incremental cycle ~2 s
  * status codes P/R/L/C
"""

from __future__ import annotations

import time

import pytest

from bdx.db.queries import (
    fetch_all_orders_snapshot,
    fetch_orders_incremental,
)

pytestmark = [pytest.mark.integration, pytest.mark.sap_read]


def test_open_orders_count_on_dev(sap_engine):
    """Full snapshot must return the documented ~871 open orders on DEV."""
    with sap_engine.connect() as conn:
        rows = fetch_all_orders_snapshot(conn)
    statuses = {r["status"] for r in rows}
    # Valid SAP status codes only.
    assert statuses.issubset({"P", "R", "L", "C"}), f"unexpected statuses: {statuses}"
    open_orders = [r for r in rows if r["status"] in ("P", "R")]
    # Documented value is 871; allow drift but fail on gross deviation.
    assert 700 < len(open_orders) < 1500, f"open order count drifted: {len(open_orders)}"


def test_incremental_read_is_fast(sap_engine):
    """Incremental read against DEV must complete in < 10 s (documented ~2 s)."""
    from datetime import date, timedelta

    since = date.today() - timedelta(days=2)
    t0 = time.monotonic()
    with sap_engine.connect() as conn:
        rows = fetch_orders_incremental(conn, since)
    elapsed = time.monotonic() - t0
    assert elapsed < 10.0, f"incremental read too slow: {elapsed:.1f}s"
    # Every returned row must carry the core fields.
    for r in rows:
        assert r["doc_entry"] and r["status"] in {"P", "R", "L", "C"}


def test_read_only_guard_blocks_writes(sap_engine):
    """The application-layer write guard must reject any DML against SAP."""
    from sqlalchemy import text

    with sap_engine.connect() as conn, pytest.raises(PermissionError):
        conn.execute(text("UPDATE OWOR SET Status='P' WHERE 1=0"))
        conn.commit()
