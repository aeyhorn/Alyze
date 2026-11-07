"""Shared fixtures for integration tests.

Skips the whole suite unless DEV credentials are present in the environment.
The CI nightly cron sets these secrets; local runs need a `.env` with the
DEV values.
"""
from __future__ import annotations

import os

import pytest


def _required_env(*names: str) -> bool:
    return all(os.environ.get(n) for n in names)


pytestmark = pytest.mark.integration


def pytest_collection_modifyitems(config, items):  # noqa: ANN001
    """Skip integration tests when DEV credentials are not configured."""
    sap_ok = _required_env("SAP_DB_HOST", "SAP_DB_NAME", "SAP_DB_TRUSTED_CONNECTION") or _required_env(
        "SAP_DB_HOST", "SAP_DB_NAME", "SAP_DB_USER", "SAP_DB_PASSWORD"
    )
    sl_ok = _required_env("SL_BASE_URL", "SL_USERNAME", "SL_PASSWORD", "SL_COMPANY_DB_DEV")
    pg_ok = _required_env("POSTGRES_DSN")

    skip_sap = pytest.mark.skip(reason="DEV SAP credentials not set (SAP_DB_*)")
    skip_sl = pytest.mark.skip(reason="DEV Service Layer credentials not set (SL_*)")
    skip_pg = pytest.mark.skip(reason="POSTGRES_DSN not set")

    for item in items:
        if "integration" not in item.keywords:
            continue
        needs_sap = any("sap_read" in m.name or "sap" in m.name.lower() for m in item.iter_markers())
        needs_sl = any("sl" in m.name.lower() for m in item.iter_markers())
        needs_pg = any("pg" in m.name.lower() or "postgres" in m.name.lower() for m in item.iter_markers())
        # Heuristic: tests in this directory that aren't explicitly tagged
        # default to needing SAP + PG. SL contract tests opt in via marker.
        if not needs_sl and not needs_sap and not needs_pg:
            if not sap_ok:
                item.add_marker(skip_sap)
            if not pg_ok:
                item.add_marker(skip_pg)
            continue
        if needs_sap and not sap_ok:
            item.add_marker(skip_sap)
        if needs_sl and not sl_ok:
            item.add_marker(skip_sl)
        if needs_pg and not pg_ok:
            item.add_marker(skip_pg)


@pytest.fixture(scope="session")
def sap_engine():
    from bdx.db.sap import build_sap_engine
    from bdx.config import load_sap_settings

    return build_sap_engine(load_sap_settings())


@pytest.fixture(scope="session")
def pg_session_factory():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from bdx.db.postgres import Base

    dsn = os.environ["POSTGRES_DSN"]
    eng = create_engine(dsn)
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    yield Session
    eng.dispose()


@pytest.fixture
def pg_session(pg_session_factory):  # noqa: ANN001
    s = pg_session_factory()
    yield s
    s.rollback()
    s.close()


@pytest.fixture(scope="session")
def sl_client():
    from bdx.config import load_service_layer_settings, SapMode
    from bdx.sap_sl.client import ServiceLayerClient

    settings = load_service_layer_settings()
    # Force DRY_RUN for integration tests — no real SAP writes ever.
    settings = settings.model_copy(update={"dry_run": True})
    client = ServiceLayerClient(settings)
    client.login(SapMode.DEV)
    yield client
    client.logout()
