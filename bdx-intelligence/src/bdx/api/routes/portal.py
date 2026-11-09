"""Customer portal API – token-scoped projection (no internal API key)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from bdx.api.deps import get_pg_session
from bdx.promise import engine as pe
from bdx.promise.models import ContractDTO, PortalAccept, PortalOfferDTO, PortalReject

router = APIRouter(tags=["portal"])


@router.get(
    "/portal/{token}",
    response_model=PortalOfferDTO,
    summary="Customer view of an offer (by portal token)",
)
def get_portal(token: str, session: Session = Depends(get_pg_session)) -> PortalOfferDTO:
    offer = pe.get_offer_by_portal_token(session, token)
    if not offer:
        raise HTTPException(status_code=404, detail="offer not found")
    return pe.to_portal_dto(session, offer)


@router.post(
    "/portal/{token}/accept",
    response_model=ContractDTO,
    summary="Customer accepts published contract",
)
def post_accept(
    token: str,
    body: PortalAccept,
    session: Session = Depends(get_pg_session),
) -> ContractDTO:
    offer = pe.get_offer_by_portal_token(session, token)
    if not offer:
        raise HTTPException(status_code=404, detail="offer not found")
    try:
        c = pe.portal_accept(session, offer, body)
    except PermissionError:
        raise HTTPException(status_code=403, detail="contract not visible") from None
    return ContractDTO.model_validate(c)


@router.post(
    "/portal/{token}/reject",
    response_model=ContractDTO,
    summary="Customer rejects published contract",
)
def post_reject(
    token: str,
    body: PortalReject,
    session: Session = Depends(get_pg_session),
) -> ContractDTO:
    offer = pe.get_offer_by_portal_token(session, token)
    if not offer:
        raise HTTPException(status_code=404, detail="offer not found")
    try:
        c = pe.portal_reject(session, offer, body)
    except PermissionError:
        raise HTTPException(status_code=403, detail="contract not visible") from None
    return ContractDTO.model_validate(c)
