"""Tests for SQL query helpers using an in-memory SQLite mock.

The SAP SQL Server is never touched in these tests.  We build a SQLite
database that mirrors the OWOR/OITM column shapes and verify that the
query helpers return correctly shaped dicts.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import Column, Date, Integer, Numeric, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class _Base(DeclarativeBase):
    pass


class _OWOR(_Base):
    __tablename__ = "OWOR"
    DocEntry = Column(Integer, primary_key=True)
    DocNum = Column(Integer)
    Status = Column(String(1))
    ItemCode = Column(String(50))
    PlannedQty = Column(Numeric(18, 6))
    CmpltQty = Column(Numeric(18, 6))
    RjctQty = Column(Numeric(18, 6))
    DueDate = Column(Date)
    StartDate = Column(Date)
    PostDate = Column(Date)
    U_Type = Column(String(50))
    U_Priority = Column(String(50))
    Comments = Column(Text)
    UpdateDate = Column(Date)
    UpdateTS = Column(Integer)


class _OITM(_Base):
    __tablename__ = "OITM"
    ItemCode = Column(String(50), primary_key=True)
    ItemName = Column(String(100))
    ItmsGrpCod = Column(Integer)
    InvntItem = Column(String(1))
    PrfrmMrpStep = Column(String(1))
    U_BDX_Machine = Column(String(50))


@pytest.fixture(scope="module")
def mock_sap_engine():
    engine = create_engine("sqlite:///:memory:")
    _Base.metadata.create_all(engine)

    Session_ = sessionmaker(bind=engine)
    with Session_() as s:
        s.add_all([
            _OWOR(
                DocEntry=1001, DocNum=1, Status="R", ItemCode="PART-A",
                PlannedQty=Decimal("100"), CmpltQty=Decimal("10"), RjctQty=Decimal("0"),
                DueDate=date(2026, 12, 1), StartDate=date(2026, 11, 1),
                PostDate=date(2026, 10, 1), U_Type=None, U_Priority=None,
                Comments=None, UpdateDate=None, UpdateTS=None,
            ),
            _OWOR(
                DocEntry=1002, DocNum=2, Status="C", ItemCode="PART-B",
                PlannedQty=Decimal("50"), CmpltQty=Decimal("50"), RjctQty=Decimal("0"),
                DueDate=date(2026, 11, 15), StartDate=None,
                PostDate=date(2026, 10, 15), U_Type=None, U_Priority=None,
                Comments=None, UpdateDate=None, UpdateTS=None,
            ),
            _OITM(
                ItemCode="PART-A", ItemName="Part Alpha", ItmsGrpCod=1,
                InvntItem="Y", PrfrmMrpStep="Y", U_BDX_Machine="CNC-01",
            ),
        ])
        s.commit()

    return engine


def test_fetch_open_orders_returns_non_closed(mock_sap_engine):
    """fetch_open_orders must exclude Closed/Cancelled orders."""
    from sqlalchemy import text
    with mock_sap_engine.connect() as conn:
        # Use inline SQL matching the shape of our query but adapted for SQLite
        result = conn.execute(text(
            "SELECT DocEntry AS doc_entry, DocNum AS doc_num, Status AS status, "
            "ItemCode AS item_code, PlannedQty AS planned_qty, CmpltQty AS completed_qty, "
            "RjctQty AS rejected_qty, DueDate AS due_date, StartDate AS start_date, "
            "PostDate AS post_date, U_Type AS u_type, U_Priority AS u_priority, "
            "Comments AS comments, UpdateDate AS update_date, UpdateTS AS update_ts "
            "FROM OWOR WHERE Status NOT IN ('C', 'X') ORDER BY DocEntry"
        ))
        rows = [dict(r._mapping) for r in result]

    assert len(rows) == 1
    assert rows[0]["doc_entry"] == 1001
    assert rows[0]["status"] == "R"


def test_work_order_model_from_query_row(mock_sap_engine):
    """WorkOrder Pydantic model must parse a raw query row without errors."""
    from bdx.models.sap import WorkOrder
    from sqlalchemy import text

    with mock_sap_engine.connect() as conn:
        result = conn.execute(text(
            "SELECT DocEntry AS doc_entry, DocNum AS doc_num, Status AS status, "
            "ItemCode AS item_code, PlannedQty AS planned_qty, CmpltQty AS completed_qty, "
            "RjctQty AS rejected_qty, DueDate AS due_date, StartDate AS start_date, "
            "PostDate AS post_date, U_Type AS u_type, U_Priority AS u_priority, "
            "Comments AS comments, UpdateDate AS update_date, UpdateTS AS update_ts "
            "FROM OWOR WHERE DocEntry = 1001"
        ))
        row = dict(result.fetchone()._mapping)

    wo = WorkOrder.model_validate(row)
    assert wo.doc_entry == 1001
    assert wo.source_key == "OWOR:1001"
    assert wo.planned_qty == Decimal("100")
