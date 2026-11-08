"""Quote-to-Promise API – inquiry cases + parallel promise evaluation."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from bdx.api.deps import get_pg_session, require_api_key
from bdx.q2p import models as q2p_models
from bdx.q2p.models import (
    InquiryCreate,
    InquiryDecision,
    InquiryDTO,
    InquiryStatus,
    InquiryUpdate,
    PromiseResult,
)
from bdx.q2p.service import evaluate_promise
from bdx.q2p.store import (
    apply_decision,
    create_inquiry,
    get_inquiry,
    list_inquiries,
    save_evaluation,
    update_inquiry,
)

router = APIRouter(tags=["q2p"], dependencies=[Depends(require_api_key)])


def _sap_engine(request: Request):
    return getattr(request.app.state, "sap_engine", None)


def _quoter(request: Request):
    return getattr(request.app.state, "quoter_client", None)


def _to_dto(row: q2p_models.Q2PInquiry) -> InquiryDTO:
    return InquiryDTO.model_validate(row)


def _run_and_persist(request: Request, session: Session, row: q2p_models.Q2PInquiry) -> InquiryDTO:
    from datetime import date as date_cls
    from decimal import Decimal

    req_date = date_cls.fromisoformat(row.requested_date) if row.requested_date else None
    result = evaluate_promise(
        item_code=row.item_code,
        qty=Decimal(str(row.qty)),
        requested_date=req_date,
        sap_engine=_sap_engine(request),
        pg_session=session,
        quoter=_quoter(request),
        datenraum=row.datenraum,
        kunde=row.kunde,
        use_llm=bool(row.use_llm),
    )
    status = _status_from_promise(result)
    save_evaluation(
        session,
        row,
        status=status,
        snapshot=result.model_dump(mode="json"),
        open_questions=result.open_questions,
    )
    return _to_dto(row)


def _status_from_promise(result: PromiseResult) -> InquiryStatus:
    if result.overall.value == "bad":
        return InquiryStatus.BLOCKED
    if result.open_questions:
        return InquiryStatus.READY  # system done; humans still have questions
    if result.overall.value == "ok":
        return InquiryStatus.READY
    return InquiryStatus.READY


@router.post("/q2p/inquiries", response_model=InquiryDTO, summary="Create inquiry case")
def post_inquiry(
    body: InquiryCreate,
    request: Request,
    session: Session = Depends(get_pg_session),
) -> InquiryDTO:
    row = create_inquiry(session, body)
    if body.evaluate:
        return _run_and_persist(request, session, row)
    return _to_dto(row)


@router.get("/q2p/inquiries", response_model=list[InquiryDTO], summary="List inquiry cases")
def get_inquiries(
    status: Optional[str] = Query(None),
    item_code: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_pg_session),
) -> list[InquiryDTO]:
    return [_to_dto(r) for r in list_inquiries(session, status=status, item_code=item_code, limit=limit)]


@router.get("/q2p/inquiries/{inquiry_id}", response_model=InquiryDTO, summary="Get one inquiry")
def get_one(inquiry_id: str, session: Session = Depends(get_pg_session)) -> InquiryDTO:
    row = get_inquiry(session, inquiry_id)
    if not row:
        raise HTTPException(status_code=404, detail="inquiry not found")
    return _to_dto(row)


@router.patch("/q2p/inquiries/{inquiry_id}", response_model=InquiryDTO, summary="Update inquiry fields")
def patch_inquiry(
    inquiry_id: str,
    body: InquiryUpdate,
    session: Session = Depends(get_pg_session),
) -> InquiryDTO:
    row = get_inquiry(session, inquiry_id)
    if not row:
        raise HTTPException(status_code=404, detail="inquiry not found")
    if row.status == InquiryStatus.DECIDED.value:
        raise HTTPException(status_code=409, detail="inquiry already decided")
    return _to_dto(update_inquiry(session, row, body))


@router.post(
    "/q2p/inquiries/{inquiry_id}/evaluate",
    response_model=InquiryDTO,
    summary="Re-run parallel domain evaluation",
)
def post_evaluate(
    inquiry_id: str,
    request: Request,
    session: Session = Depends(get_pg_session),
) -> InquiryDTO:
    row = get_inquiry(session, inquiry_id)
    if not row:
        raise HTTPException(status_code=404, detail="inquiry not found")
    if row.status == InquiryStatus.DECIDED.value:
        raise HTTPException(status_code=409, detail="inquiry already decided")
    return _run_and_persist(request, session, row)


@router.post(
    "/q2p/inquiries/{inquiry_id}/decide",
    response_model=InquiryDTO,
    summary="Record accept / reject / counter decision",
)
def post_decide(
    inquiry_id: str,
    body: InquiryDecision,
    session: Session = Depends(get_pg_session),
) -> InquiryDTO:
    row = get_inquiry(session, inquiry_id)
    if not row:
        raise HTTPException(status_code=404, detail="inquiry not found")
    return _to_dto(apply_decision(session, row, body))


@router.get(
    "/q2p/promise",
    response_model=PromiseResult,
    summary="Ad-hoc promise check without persisting an inquiry",
)
def get_promise(
    request: Request,
    item_code: str = Query(..., min_length=1),
    qty: float = Query(..., gt=0),
    requested_date: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    datenraum: Optional[str] = Query(None, description="bdx-quoter datenraum path"),
    kunde: Optional[str] = Query(None, description="bdx-quoter kundenprofil"),
    use_llm: bool = Query(False),
    session: Session = Depends(get_pg_session),
) -> PromiseResult:
    from datetime import date as date_cls
    from decimal import Decimal

    req = date_cls.fromisoformat(requested_date) if requested_date else None
    return evaluate_promise(
        item_code=item_code,
        qty=Decimal(str(qty)),
        requested_date=req,
        sap_engine=_sap_engine(request),
        pg_session=session,
        quoter=_quoter(request),
        datenraum=datenraum,
        kunde=kunde,
        use_llm=use_llm,
    )
