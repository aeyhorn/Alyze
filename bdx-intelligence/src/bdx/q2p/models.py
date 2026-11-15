"""Q2P domain models – inquiry case + promise evaluation DTOs."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, Numeric, String, Text
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
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=InquiryStatus.DRAFT.value, index=True
    )

    customer_ref: Mapped[str | None] = mapped_column(String(128))
    item_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    qty: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    requested_date: Mapped[str | None] = mapped_column(String(10))  # ISO date
    notes: Mapped[str | None] = mapped_column(Text)
    owner: Mapped[str | None] = mapped_column(String(64))
    # bdx-quoter: path inside the container/SMB datenraum + optional kundenprofil
    datenraum: Mapped[str | None] = mapped_column(Text)
    kunde: Mapped[str | None] = mapped_column(String(64))
    use_llm: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    decision: Mapped[str | None] = mapped_column(String(16))
    decision_note: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Last parallel evaluation snapshot (domains + open_questions + promise)
    promise_snapshot: Mapped[dict | None] = mapped_column(JSON)
    open_questions: Mapped[list | None] = mapped_column(JSON)


# ── Request / response DTOs ───────────────────────────────────────────────────


class InquiryCreate(BaseModel):
    item_code: str = Field(..., min_length=1, max_length=50)
    qty: Decimal = Field(..., gt=0)
    requested_date: date | None = None
    customer_ref: str | None = Field(None, max_length=128)
    notes: str | None = None
    owner: str | None = Field(None, max_length=64)
    datenraum: str | None = Field(
        None,
        description="Pfad zum Quoter-Datenraum (SMB/Container), triggert bdx-quoter",
    )
    kunde: str | None = Field(None, max_length=64, description="Quoter-Kundenprofil")
    use_llm: bool = Field(False, description="Quoter-LLM-Extraktion")
    evaluate: bool = Field(True, description="Run parallel domain checks immediately")


class InquiryDecision(BaseModel):
    decision: Decision
    decision_note: str | None = None
    owner: str | None = None


class InquiryUpdate(BaseModel):
    customer_ref: str | None = None
    notes: str | None = None
    owner: str | None = None
    requested_date: date | None = None
    qty: Decimal | None = Field(None, gt=0)
    datenraum: str | None = None
    kunde: str | None = None
    use_llm: bool | None = None


class DomainResult(BaseModel):
    domain: str
    status: DomainStatus
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)
    source: str = "system"  # system | human
    needs_human: bool = False
    question: str | None = None  # posed to a person when needs_human


class PromiseResult(BaseModel):
    overall: DomainStatus
    can_promise: bool
    confidence: str  # high | medium | low
    earliest_hint: str | None = None
    blockers: list[str] = Field(default_factory=list)
    domains: list[DomainResult] = Field(default_factory=list)
    open_questions: list[dict[str, str]] = Field(default_factory=list)
    evaluated_at: datetime


class InquiryDTO(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    status: str
    customer_ref: str | None = None
    item_code: str
    qty: float
    requested_date: str | None = None
    notes: str | None = None
    owner: str | None = None
    datenraum: str | None = None
    kunde: str | None = None
    use_llm: bool = False
    decision: str | None = None
    decision_note: str | None = None
    decided_at: datetime | None = None
    promise_snapshot: dict[str, Any] | None = None
    open_questions: list[Any] | None = None

    model_config = {"from_attributes": True}
