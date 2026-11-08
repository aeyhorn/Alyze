"""Pydantic models representing SAP Business One entities (read-only DTOs)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

# SAP Business One OWOR.Status codes (verified against DEV_SBO_LEISINGER):
#   P = Planned, R = Released, L = Closed, C = Cancelled
STATUS_PLANNED = "P"
STATUS_RELEASED = "R"
STATUS_CLOSED = "L"
STATUS_CANCELLED = "C"
OPEN_STATUSES = frozenset({STATUS_PLANNED, STATUS_RELEASED})
CLOSED_STATUSES = frozenset({STATUS_CLOSED, STATUS_CANCELLED})
STATUS_LABELS = {
    STATUS_PLANNED: "Planned",
    STATUS_RELEASED: "Released",
    STATUS_CLOSED: "Closed",
    STATUS_CANCELLED: "Cancelled",
}


class WorkOrder(BaseModel):
    """Reflects a row from dbo.OWOR (Production / Work Order)."""

    doc_entry: int = Field(..., description="SAP primary key (DocEntry)")
    doc_num: int = Field(..., description="Human-readable order number")
    status: str = Field(..., description="P=Planned, R=Released, L=Closed, C=Cancelled")
    item_code: str
    planned_qty: Decimal
    completed_qty: Decimal
    rejected_qty: Decimal
    due_date: date | None
    start_date: date | None
    post_date: date | None
    u_type: str | None = None
    u_priority: str | None = None
    comments: str | None = None
    update_date: date | None = None
    update_ts: int | None = None

    model_config = {"from_attributes": True}

    @property
    def source_key(self) -> str:
        """Unique, stable identifier for this order across snapshots."""
        return f"OWOR:{self.doc_entry}"

    @property
    def is_open(self) -> bool:
        return self.status in OPEN_STATUSES

    @property
    def fingerprint(self) -> str:
        """Stable string of all change-relevant fields (used to skip unchanged rows)."""
        return "|".join(
            str(x)
            for x in (
                self.status,
                self.item_code,
                self.planned_qty,
                self.completed_qty,
                self.rejected_qty,
                self.due_date,
                self.start_date,
                self.comments,
                self.update_date,
                self.update_ts,
            )
        )

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
    item_group_code: int | None = None
    inventory_item: str | None = None
    mrp_item: str | None = None
    machine_id: str | None = None

    model_config = {"from_attributes": True}
