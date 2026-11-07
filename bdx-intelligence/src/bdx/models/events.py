"""Domain event models and ORM table definitions."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy import JSON, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from bdx.db.postgres import Base


class EventType(str, enum.Enum):
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_RELEASED = "ORDER_RELEASED"
    QUANTITY_CHANGED = "QUANTITY_CHANGED"
    DUE_DATE_CHANGED = "DUE_DATE_CHANGED"
    ORDER_CLOSED = "ORDER_CLOSED"


# ── ORM models (PostgreSQL tables) ───────────────────────────────────────────

class OrderSnapshot(Base):
    """Persisted snapshot of a single production order at a point in time."""

    __tablename__ = "order_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    doc_entry: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    doc_num: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(1), nullable=False)
    item_code: Mapped[str] = mapped_column(String(50), nullable=False)
    planned_qty: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    completed_qty: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    rejected_qty: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    due_date: Mapped[Optional[str]] = mapped_column(String(10))
    start_date: Mapped[Optional[str]] = mapped_column(String(10))
    u_type: Mapped[Optional[str]] = mapped_column(String(50))
    u_priority: Mapped[Optional[str]] = mapped_column(String(50))
    comments: Mapped[Optional[str]] = mapped_column(Text)
    sap_update_date: Mapped[Optional[str]] = mapped_column(String(10))
    sap_update_ts: Mapped[Optional[int]] = mapped_column(Integer)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    snapshot_run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)


class DomainEvent(Base):
    """An immutable domain event derived from snapshot comparison."""

    __tablename__ = "domain_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, default=lambda: str(uuid.uuid4()))
    event_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )
    source_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    doc_entry: Mapped[int] = mapped_column(Integer, nullable=False)
    doc_num: Mapped[int] = mapped_column(Integer, nullable=False)
    item_code: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[Optional[dict]] = mapped_column(JSON)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    snapshot_run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)


# ── Pydantic DTOs ─────────────────────────────────────────────────────────────

class DomainEventDTO(BaseModel):
    event_id: str
    event_type: EventType
    source_key: str
    doc_entry: int
    doc_num: int
    item_code: str
    payload: Optional[dict[str, Any]] = None
    occurred_at: datetime
    snapshot_run_id: str

    model_config = {"from_attributes": True}
