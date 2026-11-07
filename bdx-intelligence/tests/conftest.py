"""Shared pytest fixtures using in-memory SQLite and mock data."""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Point to in-memory SQLite for tests (no Postgres required)
os.environ.setdefault("POSTGRES_DSN", "sqlite:///:memory:")
os.environ.setdefault("SAP_DB_HOST", "localhost")
os.environ.setdefault("SAP_DB_NAME", "TEST")
os.environ.setdefault("SAP_DB_USER", "test")
os.environ.setdefault("SAP_DB_PASSWORD", "test")

from bdx.db.postgres import Base
from bdx.models.events import DomainEvent, EventType, OrderSnapshot
from bdx.models.sap import WorkOrder


@pytest.fixture(scope="session")
def engine():
    from sqlalchemy.pool import StaticPool
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine):
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.rollback()
    # Clean tables between tests
    for table in reversed(Base.metadata.sorted_tables):
        s.execute(table.delete())
    s.commit()
    s.close()


@pytest.fixture
def sample_orders() -> list[WorkOrder]:
    return [
        WorkOrder(
            doc_entry=1001,
            doc_num=1,
            status="R",
            item_code="PART-A",
            planned_qty=Decimal("100"),
            completed_qty=Decimal("0"),
            rejected_qty=Decimal("0"),
            due_date=date(2026, 12, 1),
            start_date=date(2026, 11, 1),
            post_date=date(2026, 10, 1),
        ),
        WorkOrder(
            doc_entry=1002,
            doc_num=2,
            status="L",
            item_code="PART-B",
            planned_qty=Decimal("50"),
            completed_qty=Decimal("0"),
            rejected_qty=Decimal("0"),
            due_date=date(2026, 12, 15),
            start_date=None,
            post_date=date(2026, 10, 15),
        ),
    ]


@pytest.fixture
def mock_sap_rows() -> list[dict]:
    """Raw dict rows as returned by SQLAlchemy from SAP SQL Server."""
    return [
        {
            "doc_entry": 1001,
            "doc_num": 1,
            "status": "R",
            "item_code": "PART-A",
            "planned_qty": Decimal("100"),
            "completed_qty": Decimal("0"),
            "rejected_qty": Decimal("0"),
            "due_date": date(2026, 12, 1),
            "start_date": date(2026, 11, 1),
            "post_date": date(2026, 10, 1),
            "u_type": None,
            "u_priority": None,
            "comments": None,
            "update_date": None,
            "update_ts": None,
        },
        {
            "doc_entry": 1002,
            "doc_num": 2,
            "status": "L",
            "item_code": "PART-B",
            "planned_qty": Decimal("50"),
            "completed_qty": Decimal("0"),
            "rejected_qty": Decimal("0"),
            "due_date": date(2026, 12, 15),
            "start_date": None,
            "post_date": date(2026, 10, 15),
            "u_type": None,
            "u_priority": None,
            "comments": None,
            "update_date": None,
            "update_ts": None,
        },
    ]
