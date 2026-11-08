"""Q2P domain models – inquiry case + promise evaluation DTOs."""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from bdx.db.postgres import Base


class InquiryStatus(str, enum.Enum):
    DRAFT = "draft"
    EVALUATING = "evaluating"
    READY = "ready"  # all system domains answered; open_questions may remain
    BLOCKED = "blocked"  # hard blockers (no item, material shortage without PO, …)
    DECIDED = "decided"
    CANCELLED = "cancelled"


class Decision(str, enum.Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    COUNTER = "counter"


class DomainStatus(str, enum.Enum):
    OK = "ok"
    WARN = "warn"
    BAD = "bad"
    UNKNOWN = "unknown"  # no data source / no grant yet
    SKIPPED = "skipped"


# ── ORM ──────────────────────────────────────────────────────────────────────

class Q2PInquiry(Base):
    """One customer/internal inquiry – the single case that replaces email threads."""

    __tablename__ = "q2p_inquiries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=InquiryStatus.DRAFT.value, index=True)

    customer_ref: Mapped[Optional[str]] = mapped_column(String(128))
    item_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    qty: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    requested_date: Mapped[Optional[str]] = mapped_column(String(10))  # ISO date
    notes: Mapped[Optional[str]] = mapped_column(Text)
    owner: Mapped[Optional[str]] = mapped_column(String(64))
    # bdx-quoter: path inside the container/SMB datenraum + optional kundenprofil
    datenraum: Mapped[Optional[str]] = mapped_column(Text)
    kunde: Mapped[Optional[str]] = mapped_column(String(64))
    use_llm: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    decision: Mapped[Optional[str]] = mapped_column(String(16))
    decision_note: Mapped[Optional[str]] = mapped_column(Text)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Last parallel evaluation snapshot (domains + open_questions + promise)
    promise_snapshot: Mapped[Optional[dict]] = mapped_column(JSON)
    open_questions: Mapped[Optional[list]] = mapped_column(JSON)


# ── Request / response DTOs ───────────────────────────────────────────────────

class InquiryCreate(BaseModel):
    item_code: str = Field(..., min_length=1, max_length=50)
    qty: Decimal = Field(..., gt=0)
    requested_date: Optional[date] = None
    customer_ref: Optional[str] = Field(None, max_length=128)
    notes: Optional[str] = None
    owner: Optional[str] = Field(None, max_length=64)
    datenraum: Optional[str] = Field(
        None,
        description="Pfad zum Quoter-Datenraum (SMB/Container), triggert bdx-quoter",
    )
    kunde: Optional[str] = Field(None, max_length=64, description="Quoter-Kundenprofil")
    use_llm: bool = Field(False, description="Quoter-LLM-Extraktion")
    evaluate: bool = Field(True, description="Run parallel domain checks immediately")


class InquiryDecision(BaseModel):
    decision: Decision
    decision_note: Optional[str] = None
    owner: Optional[str] = None


class InquiryUpdate(BaseModel):
    customer_ref: Optional[str] = None
    notes: Optional[str] = None
    owner: Optional[str] = None
    requested_date: Optional[date] = None
    qty: Optional[Decimal] = Field(None, gt=0)
    datenraum: Optional[str] = None
    kunde: Optional[str] = None
    use_llm: Optional[bool] = None


class DomainResult(BaseModel):
    domain: str
    status: DomainStatus
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)
    source: str = "system"  # system | human
    needs_human: bool = False
    question: Optional[str] = None  # posed to a person when needs_human


class PromiseResult(BaseModel):
    overall: DomainStatus
    can_promise: bool
    confidence: str  # high | medium | low
    earliest_hint: Optional[str] = None
    blockers: list[str] = Field(default_factory=list)
    domains: list[DomainResult] = Field(default_factory=list)
    open_questions: list[dict[str, str]] = Field(default_factory=list)
    evaluated_at: datetime


class InquiryDTO(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    status: str
    customer_ref: Optional[str] = None
    item_code: str
    qty: float
    requested_date: Optional[str] = None
    notes: Optional[str] = None
    owner: Optional[str] = None
    datenraum: Optional[str] = None
    kunde: Optional[str] = None
    use_llm: bool = False
    decision: Optional[str] = None
    decision_note: Optional[str] = None
    decided_at: Optional[datetime] = None
    promise_snapshot: Optional[dict[str, Any]] = None
    open_questions: Optional[list[Any]] = None

    model_config = {"from_attributes": True}
