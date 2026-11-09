"""Persistence helpers for Q2P inquiry cases."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from bdx.q2p.models import (
    Decision,
    InquiryCreate,
    InquiryDecision,
    InquiryStatus,
    InquiryUpdate,
    Q2PInquiry,
)


def _now() -> datetime:
    return datetime.now(UTC)


def create_inquiry(session: Session, body: InquiryCreate) -> Q2PInquiry:
    now = _now()
    row = Q2PInquiry(
        id=str(uuid.uuid4()),
        created_at=now,
        updated_at=now,
        status=InquiryStatus.DRAFT.value,
        customer_ref=body.customer_ref,
        item_code=body.item_code.strip(),
        qty=float(body.qty),
        requested_date=body.requested_date.isoformat() if body.requested_date else None,
        notes=body.notes,
        owner=body.owner,
        datenraum=(body.datenraum.strip() if body.datenraum else None),
        kunde=(body.kunde.strip() if body.kunde else None),
        use_llm=bool(body.use_llm),
        open_questions=[],
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_inquiry(session: Session, inquiry_id: str) -> Q2PInquiry | None:
    return session.get(Q2PInquiry, inquiry_id)


def list_inquiries(
    session: Session,
    *,
    status: Optional[str] = None,
    item_code: Optional[str] = None,
    limit: int = 50,
) -> list[Q2PInquiry]:
    q = select(Q2PInquiry).order_by(Q2PInquiry.created_at.desc()).limit(min(limit, 200))
    if status:
        q = q.where(Q2PInquiry.status == status)
    if item_code:
        q = q.where(Q2PInquiry.item_code == item_code)
    return list(session.scalars(q))


def update_inquiry(session: Session, row: Q2PInquiry, body: InquiryUpdate) -> Q2PInquiry:
    data = body.model_dump(exclude_unset=True)
    if "requested_date" in data and data["requested_date"] is not None:
        data["requested_date"] = data["requested_date"].isoformat()
    if "qty" in data and isinstance(data["qty"], Decimal):
        data["qty"] = float(data["qty"])
    for key, value in data.items():
        setattr(row, key, value)
    row.updated_at = _now()
    session.commit()
    session.refresh(row)
    return row


def apply_decision(session: Session, row: Q2PInquiry, body: InquiryDecision) -> Q2PInquiry:
    row.decision = body.decision.value
    row.decision_note = body.decision_note
    if body.owner:
        row.owner = body.owner
    row.decided_at = _now()
    row.status = InquiryStatus.DECIDED.value
    row.updated_at = row.decided_at
    session.commit()
    session.refresh(row)
    return row


def save_evaluation(
    session: Session,
    row: Q2PInquiry,
    *,
    status: InquiryStatus,
    snapshot: dict[str, Any],
    open_questions: list[Any],
) -> Q2PInquiry:
    row.status = status.value
    row.promise_snapshot = snapshot
    row.open_questions = open_questions
    row.updated_at = _now()
    session.commit()
    session.refresh(row)
    return row
