"""Tests for Pydantic SAP models."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from bdx.models.sap import WorkOrder


def test_work_order_source_key():
    wo = WorkOrder(
        doc_entry=42,
        doc_num=100,
        status="R",
        item_code="PART-X",
        planned_qty=Decimal("10"),
        completed_qty=Decimal("0"),
        rejected_qty=Decimal("0"),
        due_date=None,
        start_date=None,
        post_date=None,
    )
    assert wo.source_key == "OWOR:42"


def test_work_order_is_open():
    wo = WorkOrder(
        doc_entry=1,
        doc_num=1,
        status="R",
        item_code="X",
        planned_qty=Decimal("1"),
        completed_qty=Decimal("0"),
        rejected_qty=Decimal("0"),
        due_date=None,
        start_date=None,
        post_date=None,
    )
    assert wo.is_open is True


@pytest.mark.parametrize("status", ["C", "X"])
def test_work_order_not_open(status: str):
    wo = WorkOrder(
        doc_entry=1,
        doc_num=1,
        status=status,
        item_code="X",
        planned_qty=Decimal("1"),
        completed_qty=Decimal("0"),
        rejected_qty=Decimal("0"),
        due_date=None,
        start_date=None,
        post_date=None,
    )
    assert wo.is_open is False


def test_work_order_from_dict(mock_sap_rows):
    row = mock_sap_rows[0]
    wo = WorkOrder.model_validate(row)
    assert wo.doc_entry == 1001
    assert wo.item_code == "PART-A"
    assert wo.planned_qty == Decimal("100")
