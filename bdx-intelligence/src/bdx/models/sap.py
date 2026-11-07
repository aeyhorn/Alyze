"""Pydantic models representing SAP Business One entities (read-only DTOs)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class WorkOrder(BaseModel):
    """Reflects a row from dbo.OWOR (Production / Work Order)."""

    doc_entry: int = Field(..., description="SAP primary key (DocEntry)")
    doc_num: int = Field(..., description="Human-readable order number")
    status: str = Field(..., description="R=Released, L=Planned, C=Closed, X=Cancelled")
    item_code: str
    planned_qty: Decimal
    completed_qty: Decimal
    rejected_qty: Decimal
    due_date: Optional[date]
    start_date: Optional[date]
    post_date: Optional[date]
    u_type: Optional[str] = None
    u_priority: Optional[str] = None
    comments: Optional[str] = None
    update_date: Optional[date] = None
    update_ts: Optional[int] = None

    model_config = {"from_attributes": True}

    @property
    def source_key(self) -> str:
        """Unique, stable identifier for this order across snapshots."""
        return f"OWOR:{self.doc_entry}"

    @property
    def is_open(self) -> bool:
        return self.status not in ("C", "X")

    @model_validator(mode="before")
    @classmethod
    def _coerce_decimals(cls, values: dict) -> dict:
        for field in ("planned_qty", "completed_qty", "rejected_qty"):
            v = values.get(field)
            if v is None:
                values[field] = Decimal("0")
        return values


class ItemMaster(BaseModel):
    """Reflects a row from dbo.OITM (Item Master Data)."""

    item_code: str
    item_name: str
    item_group_code: Optional[int] = None
    inventory_item: Optional[str] = None
    mrp_item: Optional[str] = None
    machine_id: Optional[str] = None

    model_config = {"from_attributes": True}
