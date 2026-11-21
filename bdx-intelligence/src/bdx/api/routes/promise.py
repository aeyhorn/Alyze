"""Promise Platform API – living offers, gaps, contracts (internal)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from bdx.adapters.quoter import (
    NullQuoterClient,
    build_promise_return_url,
    build_quoter_client,
    build_quoter_work_url,
)
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


class QuoterLinkRequest(BaseModel):
    promise_origin: str = Field(
        ...,
        description="Browser origin of the Promise UI, e.g. http://192.168.82.33:8085",
    )
    gap_id: Optional[str] = None


class QuoterLinkResponse(BaseModel):
    enabled: bool
    url: Optional[str] = None
    return_url: Optional[str] = None
    ui_url: Optional[str] = None
    detail: Optional[str] = None


@router.post(
    "/promise/offers/{offer_id}/quoter-link",
    response_model=QuoterLinkResponse,
    summary="Build Quoter Deep Link (work + return_url)",
)
def post_quoter_link(
    offer_id: str,
    body: QuoterLinkRequest,
    session: Session = Depends(get_pg_session),
) -> QuoterLinkResponse:
    """Return the navigable Quoter Deep Link for an offer (and optional gap)."""
    offer = pe.get_offer(session, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="offer not found")

    cfg = load_quoter_settings()
    ui = cfg.resolved_ui_url
    if not ui:
        return QuoterLinkResponse(
            enabled=False,
            detail="QUOTER_UI_URL / QUOTER_BASE_URL not configured",
        )

    gap_title: str | None = None
    gap_id = body.gap_id
    if gap_id:
        from bdx.promise.models import Gap

        match = session.get(Gap, gap_id)
        if match is None or match.offer_id != offer.id:
            raise HTTPException(status_code=404, detail="gap not found")
        gap_title = match.title

    if not (offer.datenraum or "").strip():
        return QuoterLinkResponse(
            enabled=False,
            ui_url=ui,
            detail="Offer has no datenraum – set one before opening Quoter",
        )

    return_url = build_promise_return_url(
        promise_origin=body.promise_origin,
        offer_id=str(offer.id),
        gap_id=gap_id,
    )
    try:
        url = build_quoter_work_url(
            settings=cfg,
            datenraum=offer.datenraum,
            offer_id=str(offer.id),
            return_url=return_url,
            gap_id=gap_id,
            gap_title=gap_title,
            item_code=offer.item_code,
            qty=float(offer.qty) if offer.qty is not None else None,
            kunde=offer.kunde or offer.customer_name or offer.customer_ref,
        )
    except ValueError as exc:
        return QuoterLinkResponse(enabled=False, ui_url=ui, detail=str(exc))

    return QuoterLinkResponse(
        enabled=True,
        url=url,
        return_url=return_url,
        ui_url=ui,
    )
