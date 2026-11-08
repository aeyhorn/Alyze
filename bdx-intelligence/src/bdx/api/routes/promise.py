"""Promise Platform API – living offers, gaps, contracts (internal)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from bdx.adapters.quoter import NullQuoterClient, build_quoter_client
from bdx.api.deps import get_pg_session, require_api_key
from bdx.config import load_quoter_settings
from bdx.promise import engine as pe
from bdx.promise.models import (
    ContractDTO,
    ContractPublish,
    GapDTO,
    GapResolve,
    OfferCreate,
    OfferDecide,
    OfferDTO,
)

router = APIRouter(tags=["promise"], dependencies=[Depends(require_api_key)])


def _sap(request: Request):
    return getattr(request.app.state, "sap_engine", None)


def _quoter(request: Request):
    q = getattr(request.app.state, "quoter_client", None)
    if q is not None:
        return q
    try:
        cfg = load_quoter_settings()
        return build_quoter_client(cfg) if cfg.configured else NullQuoterClient()
    except Exception:  # noqa: BLE001
        return NullQuoterClient()


@router.post("/promise/offers", response_model=OfferDTO, summary="Create living offer (+ recompute)")
def post_offer(
    body: OfferCreate,
    request: Request,
    session: Session = Depends(get_pg_session),
) -> OfferDTO:
    offer = pe.create_offer(
        session, body, sap_engine=_sap(request), quoter=_quoter(request)
    )
    return pe.to_offer_dto(session, offer)


@router.get("/promise/offers", response_model=list[OfferDTO], summary="List offers")
def get_offers(
    status: Optional[str] = Query(None),
    customer_ref: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_pg_session),
) -> list[OfferDTO]:
    rows = pe.list_offers(session, status=status, customer_ref=customer_ref, limit=limit)
    return [pe.to_offer_dto(session, r, include_children=False) for r in rows]


@router.get("/promise/offers/{offer_id}", response_model=OfferDTO, summary="Get offer detail")
def get_offer(offer_id: str, session: Session = Depends(get_pg_session)) -> OfferDTO:
    offer = pe.get_offer(session, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="offer not found")
    return pe.to_offer_dto(session, offer)


@router.post(
    "/promise/offers/{offer_id}/recompute",
    response_model=OfferDTO,
    summary="Re-run quote/purchase/capacity/contract agents",
)
def post_recompute(
    offer_id: str,
    request: Request,
    session: Session = Depends(get_pg_session),
) -> OfferDTO:
    offer = pe.get_offer(session, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="offer not found")
    if offer.status == "cancelled":
        raise HTTPException(status_code=409, detail="offer cancelled")
    offer = pe.recompute_offer(
        session, offer, sap_engine=_sap(request), quoter=_quoter(request)
    )
    return pe.to_offer_dto(session, offer)


@router.post(
    "/promise/offers/{offer_id}/decide",
    response_model=OfferDTO,
    summary="Record accept / reject / counter",
)
def post_decide(
    offer_id: str,
    body: OfferDecide,
    session: Session = Depends(get_pg_session),
) -> OfferDTO:
    offer = pe.get_offer(session, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="offer not found")
    return pe.to_offer_dto(session, pe.decide_offer(session, offer, body))


@router.post(
    "/promise/offers/{offer_id}/gaps/{gap_id}/resolve",
    response_model=GapDTO,
    summary="Resolve or waive a gap",
)
def post_resolve_gap(
    offer_id: str,
    gap_id: str,
    body: GapResolve,
    session: Session = Depends(get_pg_session),
) -> GapDTO:
    offer = pe.get_offer(session, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="offer not found")
    try:
        gap = pe.resolve_gap(session, offer, gap_id, body)
    except KeyError:
        raise HTTPException(status_code=404, detail="gap not found") from None
    return GapDTO.model_validate(gap)


@router.post(
    "/promise/offers/{offer_id}/contract/publish",
    response_model=ContractDTO,
    summary="Publish latest contract to customer portal",
)
def post_publish_contract(
    offer_id: str,
    body: ContractPublish,
    session: Session = Depends(get_pg_session),
) -> ContractDTO:
    offer = pe.get_offer(session, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="offer not found")
    try:
        c = pe.publish_contract(
            session, offer, customer_visible=body.customer_visible, title=body.title
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="no contract") from None
    return ContractDTO.model_validate(c)
