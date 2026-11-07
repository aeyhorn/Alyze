"""Domain event models and ORM table definitions."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel
from sqlalchemy import JSON, DateTime, Float, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from bdx.db.postgres import Base


class EventType(str, enum.Enum):
    # ── SAP production order events (snapshot diff) ──────────────────────────
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_RELEASED = "ORDER_RELEASED"
    QUANTITY_CHANGED = "QUANTITY_CHANGED"
    DUE_DATE_CHANGED = "DUE_DATE_CHANGED"
    ORDER_PARTIAL_COMPLETE = "ORDER_PARTIAL_COMPLETE"
    ORDER_CLOSED = "ORDER_CLOSED"
    # ── Machine events (MDE / XMSK state diff) ───────────────────────────────
    MACHINE_STATE_CHANGED = "MACHINE_STATE_CHANGED"
    MACHINE_ORDER_STARTED = "MACHINE_ORDER_STARTED"
    MACHINE_ORDER_FINISHED = "MACHINE_ORDER_FINISHED"
    MACHINE_PIECES_REPORTED = "MACHINE_PIECES_REPORTED"
    MACHINE_OFFLINE = "MACHINE_OFFLINE"
    MACHINE_ONLINE = "MACHINE_ONLINE"


ORDER_EVENT_TYPES = frozenset(
    {
        EventType.ORDER_CREATED,
        EventType.ORDER_RELEASED,
        EventType.QUANTITY_CHANGED,
        EventType.DUE_DATE_CHANGED,
        EventType.ORDER_PARTIAL_COMPLETE,
        EventType.ORDER_CLOSED,
    }
)
MACHINE_EVENT_TYPES = frozenset(set(EventType) - ORDER_EVENT_TYPES)


# ── ORM models (PostgreSQL tables) ───────────────────────────────────────────

class _OrderColumns:
    """Columns shared by order_state (current) and order_snapshots (history)."""

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


class OrderSnapshot(_OrderColumns, Base):
    """History row: written whenever an order is first seen or has changed."""

    __tablename__ = "order_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)


class OrderState(_OrderColumns, Base):
    """Current state of every production order known to BDX (one row per order)."""

    __tablename__ = "order_state"

    # source_key is the primary key here – override the shared column definition
    source_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SnapshotRun(Base):
    """One row per collector cycle (SAP read)."""

    __tablename__ = "snapshot_runs"

    run_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    mode: Mapped[str] = mapped_column(String(16), nullable=False)  # full | incremental
    orders_read: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    orders_changed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    events_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    since_date: Mapped[Optional[str]] = mapped_column(String(10))
    error: Mapped[Optional[str]] = mapped_column(Text)


class MachineState(Base):
    """Current state of a machine as last reported by the MDE (XMSK) feed."""

    __tablename__ = "machine_state"

    machine_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    online: Mapped[bool] = mapped_column(nullable=False, default=True)
    mde_enabled: Mapped[bool] = mapped_column(nullable=False, default=True)
    exec_state: Mapped[Optional[str]] = mapped_column(String(32))     # XMSK Exec: AUS / Bereit / ...
    state: Mapped[Optional[str]] = mapped_column(String(32))          # XMSK State: Fertigen / Auftrag / Ruesten ...
    mode: Mapped[Optional[str]] = mapped_column(String(16))           # MEM / RAPID / 0 ...
    order_ref: Mapped[Optional[str]] = mapped_column(String(64))      # raw XMSK Order string
    operation: Mapped[Optional[str]] = mapped_column(String(64))
    part: Mapped[Optional[str]] = mapped_column(String(64))
    nc_program: Mapped[Optional[str]] = mapped_column(String(64))
    pieces: Mapped[Optional[int]] = mapped_column(Integer)
    pieces_raw: Mapped[Optional[str]] = mapped_column(String(32))
    operator: Mapped[Optional[str]] = mapped_column(String(64))
    feed_override: Mapped[Optional[int]] = mapped_column(Integer)
    spindle_override: Mapped[Optional[int]] = mapped_column(Integer)
    rapid_override: Mapped[Optional[int]] = mapped_column(Integer)
    load_spindle: Mapped[Optional[float]] = mapped_column(Float)
    load_axis_1: Mapped[Optional[float]] = mapped_column(Float)
    load_axis_2: Mapped[Optional[float]] = mapped_column(Float)
    last_message: Mapped[Optional[str]] = mapped_column(Text)
    last_prod_end: Mapped[Optional[str]] = mapped_column(String(32))
    # Link to SAP (resolved via order_state.doc_num when order_ref is numeric)
    sap_doc_entry: Mapped[Optional[int]] = mapped_column(Integer)
    sap_item_code: Mapped[Optional[str]] = mapped_column(String(50))
    source_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DomainEvent(Base):
    """An immutable domain event derived from snapshot / machine-state comparison."""

    __tablename__ = "domain_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, default=lambda: str(uuid.uuid4()))
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # Order link – nullable for machine events without a resolvable SAP order
    doc_entry: Mapped[Optional[int]] = mapped_column(Integer)
    doc_num: Mapped[Optional[int]] = mapped_column(Integer)
    item_code: Mapped[Optional[str]] = mapped_column(String(50))
    machine_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSON)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    snapshot_run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)


# ── Pydantic DTOs ─────────────────────────────────────────────────────────────

class DomainEventDTO(BaseModel):
    event_id: str
    event_type: EventType
    source_key: str
    doc_entry: Optional[int] = None
    doc_num: Optional[int] = None
    item_code: Optional[str] = None
    machine_id: Optional[str] = None
    payload: Optional[dict[str, Any]] = None
    occurred_at: datetime
    snapshot_run_id: str

    model_config = {"from_attributes": True}


# ── Service Layer write-back audit log ────────────────────────────────────────

class SLOperation(Base):
    """Audit trail for every Service Layer write attempt (success or failure).

    One row per call, regardless of DRY_RUN.  ``dry_run=true`` rows document
    what *would* have been sent.
    """

    __tablename__ = "sl_operations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    operation_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(8), nullable=False)
    company_db: Mapped[str] = mapped_column(String(64), nullable=False)
    doc_entry: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    doc_num: Mapped[Optional[int]] = mapped_column(Integer)
    payload: Mapped[Optional[dict]] = mapped_column(JSON)
    dry_run: Mapped[bool] = mapped_column(nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # success | failed | dry_run
    http_status: Mapped[Optional[int]] = mapped_column(Integer)
    error: Mapped[Optional[str]] = mapped_column(Text)
    operator: Mapped[Optional[str]] = mapped_column(String(64))


class SLOperationDTO(BaseModel):
    operation_id: str
    occurred_at: datetime
    operation: str
    mode: str
    company_db: str
    doc_entry: Optional[int] = None
    doc_num: Optional[int] = None
    payload: Optional[dict[str, Any]] = None
    dry_run: bool
    status: str
    http_status: Optional[int] = None
    error: Optional[str] = None
    operator: Optional[str] = None

    model_config = {"from_attributes": True}
