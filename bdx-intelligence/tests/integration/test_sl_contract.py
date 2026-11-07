"""Service Layer contract tests against DEV (DRY_RUN only).

These tests log in to the DEV Service Layer and exercise the write-back
operations in DRY_RUN mode. They verify:
  * Login + session work against DEV.
  * Each operation (release/close/cancel/report-production) is audited to
    `sl_operations` with status `dry_run`.
  * No real SAP write is ever attempted (DryRunError is raised and audited).

The `sl_client` fixture in conftest.py forces `dry_run=True` regardless of
the environment, so these tests are safe to run on any environment.
"""

from __future__ import annotations

import pytest

from bdx.models.events import SLOperation
from bdx.sap_sl.operations import (
    cancel_order,
    close_order,
    release_order,
    report_production,
)

pytestmark = [pytest.mark.integration, pytest.mark.sl]


def test_sl_login_dev(sl_client):
    """Service Layer login against DEV must succeed."""
    assert sl_client.session_id, "no session id after login"


def test_release_dry_run_audited(sl_client, pg_session):
    res = release_order(pg_session, sl_client, 38559)
    assert res.status == "dry_run" and res.dry_run is True
    row = pg_session.query(SLOperation).filter_by(operation="release").first()
    assert row is not None
    assert row.status == "dry_run" and row.doc_entry == 38559
    assert row.payload == {"Status": "R"}


def test_close_dry_run_audited(sl_client, pg_session):
    close_order(pg_session, sl_client, 38559)
    row = pg_session.query(SLOperation).filter_by(operation="close").first()
    assert row and row.status == "dry_run" and row.payload == {"Status": "L"}


def test_cancel_dry_run_audited(sl_client, pg_session):
    cancel_order(pg_session, sl_client, 38559)
    row = pg_session.query(SLOperation).filter_by(operation="cancel").first()
    assert row and row.status == "dry_run" and row.payload == {"Status": "C"}


def test_report_production_dry_run_audited(sl_client, pg_session):
    report_production(pg_session, sl_client, 38559, 5.0, "W01", doc_num=38559)
    row = pg_session.query(SLOperation).filter_by(operation="report_production").first()
    assert row and row.status == "dry_run"
    assert row.payload["BaseEntry"] == 38559
    assert row.payload["Quantity"] == 5.0
    assert row.payload["Warehouse"] == "W01"
    # No real write attempted: dry_run flag must be True in the audit row.
    assert row.dry_run is True
