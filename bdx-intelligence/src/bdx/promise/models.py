"""Promise Platform domain models – Offer, Gap, Evidence, Contract, AgentJob."""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, Float, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from bdx.db.postgres import Base


class OfferStatus(str, enum.Enum):
    DRAFT = "draft"
    COMPUTING = "computing"
    OPEN = "open"  # gaps remain
    PROMISABLE = "promisable"  # confidence >= threshold
    DECIDED = "decided"
    CONTRACTED = "contracted"
    CANCELLED = "cancelled"


class GapType(str, enum.Enum):
    TECHNIK = "technik"
    EINKAUF = "einkauf"
    FERTIGUNG = "fertigung"
    VERTRIEB = "vertrieb"
    RECHT = "recht"
    KALKULATION = "kalkulation"
    PERSONAL = "personal"


class GapStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    WAIVED = "waived"


class AgentKind(str, enum.Enum):
    QUOTE = "quote"
    PURCHASE = "purchase"
    CAPACITY = "capacity"
    CONTRACT = "contract"


class AgentJobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    NEEDS_APPROVAL = "needs_approval"


class ContractStatus(str, enum.Enum):
    DRAFT = "draft"
    INTERNAL_REVIEW = "internal_review"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


# ── ORM ──────────────────────────────────────────────────────────────────────

class Offer(Base):
    """Living offer object – system of record for promises."""

    __tablename__ = "promise_offers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=OfferStatus.DRAFT.value, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    customer_ref: Mapped[Optional[str]] = mapped_column(String(128), index=True)
    customer_name: Mapped[Optional[str]] = mapped_column(String(128))
    item_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    qty: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    requested_date: Mapped[Optional[str]] = mapped_column(String(10))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    owner: Mapped[Optional[str]] = mapped_column(String(64))
    datenraum: Mapped[Optional[str]] = mapped_column(Text)
    kunde: Mapped[Optional[str]] = mapped_column(String(64))
    use_llm: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Promise band
    price_low_eur: Mapped[Optional[float]] = mapped_column(Float)
    price_high_eur: Mapped[Optional[float]] = mapped_column(Float)
    date_early: Mapped[Optional[str]] = mapped_column(String(10))
    date_late: Mapped[Optional[str]] = mapped_column(String(10))
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.75)

    decision: Mapped[Optional[str]] = mapped_column(String(16))
    decision_note: Mapped[Optional[str]] = mapped_column(Text)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Last domain evaluation payload + portal token
    evaluation: Mapped[Optional[dict]] = mapped_column(JSON)
    portal_token: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    q2p_inquiry_id: Mapped[Optional[str]] = mapped_column(String(36))


class Gap(Base):
    __tablename__ = "promise_gaps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    offer_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    gap_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=GapStatus.OPEN.value, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    detail: Mapped[Optional[str]] = mapped_column(Text)
    owner_role: Mapped[str] = mapped_column(String(32), nullable=False, default="vertrieb")
    source_domain: Mapped[Optional[str]] = mapped_column(String(32))
    source_agent: Mapped[Optional[str]] = mapped_column(String(32))
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resolution_note: Mapped[Optional[str]] = mapped_column(Text)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[Optional[str]] = mapped_column(String(64))
    extra: Mapped[Optional[dict]] = mapped_column(JSON)


class Evidence(Base):
    __tablename__ = "promise_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    offer_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # sap|quoter|machine|human|contract
    label: Mapped[str] = mapped_column(String(256), nullable=False)
    payload: Mapped[Optional[dict]] = mapped_column(JSON)
    external_ref: Mapped[Optional[str]] = mapped_column(String(256))


class AgentJob(Base):
    __tablename__ = "promise_agent_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    offer_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    kind: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=AgentJobStatus.QUEUED.value)
    input_payload: Mapped[Optional[dict]] = mapped_column(JSON)
    result_payload: Mapped[Optional[dict]] = mapped_column(JSON)
    error: Mapped[Optional[str]] = mapped_column(Text)
    needs_human: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Contract(Base):
    __tablename__ = "promise_contracts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    offer_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=ContractStatus.DRAFT.value, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    body: Mapped[dict] = mapped_column(JSON, nullable=False)
    customer_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    accepted_by: Mapped[Optional[str]] = mapped_column(String(128))
    reject_reason: Mapped[Optional[str]] = mapped_column(Text)


# ── DTOs ──────────────────────────────────────────────────────────────────────

class OfferCreate(BaseModel):
    item_code: str = Field(..., min_length=1, max_length=50)
    qty: Decimal = Field(..., gt=0)
    requested_date: Optional[date] = None
    customer_ref: Optional[str] = None
    customer_name: Optional[str] = None
    notes: Optional[str] = None
    owner: Optional[str] = None
    datenraum: Optional[str] = None
    kunde: Optional[str] = None
    use_llm: bool = False
    confidence_threshold: float = Field(0.75, ge=0.0, le=1.0)
    recompute: bool = True


class OfferDecide(BaseModel):
    decision: str = Field(..., pattern="^(accept|reject|counter)$")
    decision_note: Optional[str] = None
    owner: Optional[str] = None


class GapResolve(BaseModel):
    resolution_note: str = Field(..., min_length=1)
    resolved_by: Optional[str] = None
    waive: bool = False


class ContractPublish(BaseModel):
    customer_visible: bool = True
    title: Optional[str] = None


class PortalAccept(BaseModel):
    accepted_by: str = Field(..., min_length=1)
    note: Optional[str] = None


class PortalReject(BaseModel):
    rejected_by: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1)


class GapDTO(BaseModel):
    id: str
    offer_id: str
    created_at: datetime
    updated_at: datetime
    gap_type: str
    status: str
    title: str
    detail: Optional[str] = None
    owner_role: str
    source_domain: Optional[str] = None
    source_agent: Optional[str] = None
    resolution_note: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    extra: Optional[dict[str, Any]] = None

    model_config = {"from_attributes": True}


class EvidenceDTO(BaseModel):
    id: str
    offer_id: str
    created_at: datetime
    kind: str
    label: str
    payload: Optional[dict[str, Any]] = None
    external_ref: Optional[str] = None

    model_config = {"from_attributes": True}


class AgentJobDTO(BaseModel):
    id: str
    offer_id: str
    created_at: datetime
    finished_at: Optional[datetime] = None
    kind: str
    status: str
    result_payload: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    needs_human: bool = False

    model_config = {"from_attributes": True}


class ContractDTO(BaseModel):
    id: str
    offer_id: str
    created_at: datetime
    updated_at: datetime
    version: int
    status: str
    title: str
    body: dict[str, Any]
    customer_visible: bool
    accepted_at: Optional[datetime] = None
    accepted_by: Optional[str] = None
    reject_reason: Optional[str] = None

    model_config = {"from_attributes": True}


class OfferDTO(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    status: str
    version: int
    customer_ref: Optional[str] = None
    customer_name: Optional[str] = None
    item_code: str
    qty: float
    requested_date: Optional[str] = None
    notes: Optional[str] = None
    owner: Optional[str] = None
    datenraum: Optional[str] = None
    kunde: Optional[str] = None
    use_llm: bool = False
    price_low_eur: Optional[float] = None
    price_high_eur: Optional[float] = None
    date_early: Optional[str] = None
    date_late: Optional[str] = None
    confidence: float
    confidence_threshold: float
    decision: Optional[str] = None
    decision_note: Optional[str] = None
    decided_at: Optional[datetime] = None
    portal_token: str
    evaluation: Optional[dict[str, Any]] = None
    open_gap_count: int = 0
    gaps: list[GapDTO] = Field(default_factory=list)
    evidence: list[EvidenceDTO] = Field(default_factory=list)
    jobs: list[AgentJobDTO] = Field(default_factory=list)
    contract: Optional[ContractDTO] = None

    model_config = {"from_attributes": True}


class PortalOfferDTO(BaseModel):
    """Customer-visible projection – no internal margins / raw supplier data."""

    id: str
    status: str
    customer_ref: Optional[str] = None
    customer_name: Optional[str] = None
    item_code: str
    qty: float
    requested_date: Optional[str] = None
    price_low_eur: Optional[float] = None
    price_high_eur: Optional[float] = None
    date_early: Optional[str] = None
    date_late: Optional[str] = None
    confidence: float
    confidence_threshold: float
    customer_gaps: list[dict[str, str]] = Field(default_factory=list)
    contract: Optional[ContractDTO] = None
