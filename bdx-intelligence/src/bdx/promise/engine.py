"""Offer Engine – create, recompute, decide, portal projections."""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from bdx.adapters.quoter import QuoterClient
from bdx.promise import agents as agent_mod
from bdx.promise.confidence import compute_confidence, date_band, price_band_from_evaluation
from bdx.promise.models import (
    AgentJob,
    AgentJobStatus,
    AgentKind,
    Contract,
    ContractStatus,
    Evidence,
    Gap,
    GapResolve,
    GapStatus,
    Offer,
    OfferCreate,
    OfferDecide,
    OfferDTO,
    OfferStatus,
    PortalAccept,
    PortalOfferDTO,
    PortalReject,
)

logger = structlog.get_logger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def _fp(*parts: str) -> str:
    raw = "|".join(parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:32]


def create_offer(
    session: Session,
    body: OfferCreate,
    *,
    sap_engine: Engine | None = None,
    quoter: QuoterClient | None = None,
) -> Offer:
    now = _now()
    offer = Offer(
        id=str(uuid.uuid4()),
        created_at=now,
        updated_at=now,
        status=OfferStatus.DRAFT.value,
        version=1,
        customer_ref=body.customer_ref,
        customer_name=body.customer_name,
        item_code=body.item_code.strip(),
        qty=float(body.qty),
        requested_date=body.requested_date.isoformat() if body.requested_date else None,
        notes=body.notes,
        owner=body.owner,
        datenraum=body.datenraum.strip() if body.datenraum else None,
        kunde=body.kunde.strip() if body.kunde else None,
        use_llm=bool(body.use_llm),
        confidence=0.0,
        confidence_threshold=float(body.confidence_threshold),
        portal_token=str(uuid.uuid4()),
    )
    session.add(offer)
    session.commit()
    session.refresh(offer)
    if body.recompute:
        return recompute_offer(session, offer, sap_engine=sap_engine, quoter=quoter)
    return offer


def get_offer(session: Session, offer_id: str) -> Offer | None:
    return session.get(Offer, offer_id)


def get_offer_by_portal_token(session: Session, token: str) -> Offer | None:
    return session.scalars(select(Offer).where(Offer.portal_token == token)).first()


def list_offers(
    session: Session,
    *,
    status: str | None = None,
    customer_ref: str | None = None,
    limit: int = 50,
) -> list[Offer]:
    q = select(Offer).order_by(Offer.created_at.desc()).limit(min(limit, 200))
    if status:
        q = q.where(Offer.status == status)
    if customer_ref:
        q = q.where(Offer.customer_ref == customer_ref)
    return list(session.scalars(q))


def _gaps_for(session: Session, offer_id: str) -> list[Gap]:
    return list(session.scalars(select(Gap).where(Gap.offer_id == offer_id)))


def _evidence_for(session: Session, offer_id: str) -> list[Evidence]:
    return list(
        session.scalars(
            select(Evidence).where(Evidence.offer_id == offer_id).order_by(Evidence.created_at.desc()).limit(100)
        )
    )


def _jobs_for(session: Session, offer_id: str) -> list[AgentJob]:
    return list(
        session.scalars(
            select(AgentJob).where(AgentJob.offer_id == offer_id).order_by(AgentJob.created_at.desc()).limit(50)
        )
    )


def _latest_contract(session: Session, offer_id: str) -> Contract | None:
    return session.scalars(
        select(Contract).where(Contract.offer_id == offer_id).order_by(Contract.version.desc())
    ).first()


def _upsert_gaps(session: Session, offer: Offer, incoming: list[dict[str, Any]], *, agent: str) -> None:
    existing = {g.fingerprint: g for g in _gaps_for(session, offer.id)}
    seen: set[str] = set()
    now = _now()
    for raw in incoming:
        title = str(raw.get("title") or "").strip()
        if not title:
            continue
        gtype = str(raw.get("gap_type") or "vertrieb")
        fp = _fp(offer.id, gtype, title)
        seen.add(fp)
        if fp in existing:
            g = existing[fp]
            if g.status == GapStatus.RESOLVED.value:
                continue  # keep human resolution
            g.updated_at = now
            g.detail = raw.get("detail")
            g.extra = raw.get("extra")
            g.source_agent = agent
            continue
        session.add(
            Gap(
                id=str(uuid.uuid4()),
                offer_id=offer.id,
                created_at=now,
                updated_at=now,
                gap_type=gtype,
                status=GapStatus.OPEN.value,
                title=title[:256],
                detail=raw.get("detail"),
                owner_role=str(raw.get("owner_role") or gtype),
                source_domain=raw.get("source_domain"),
                source_agent=agent,
                fingerprint=fp,
                extra=raw.get("extra"),
            )
        )
    # Auto-resolve gaps from this agent that disappeared
    for fp, g in existing.items():
        if g.source_agent == agent and fp not in seen and g.status == GapStatus.OPEN.value:
            g.status = GapStatus.RESOLVED.value
            g.resolution_note = "auto: nicht mehr gemeldet"
            g.resolved_at = now
            g.resolved_by = "system"
            g.updated_at = now


def _add_evidence(session: Session, offer_id: str, items: list[dict[str, Any]]) -> None:
    now = _now()
    for e in items:
        session.add(
            Evidence(
                id=str(uuid.uuid4()),
                offer_id=offer_id,
                created_at=now,
                kind=str(e.get("kind") or "system"),
                label=str(e.get("label") or "evidence")[:256],
                payload=e.get("payload"),
                external_ref=e.get("external_ref"),
            )
        )


def _run_job(
    session: Session,
    offer: Offer,
    kind: AgentKind,
    runner,
) -> AgentJob:
    now = _now()
    job = AgentJob(
        id=str(uuid.uuid4()),
        offer_id=offer.id,
        created_at=now,
        kind=kind.value,
        status=AgentJobStatus.RUNNING.value,
    )
    session.add(job)
    session.flush()
    try:
        result = runner()
        job.status = (
            AgentJobStatus.NEEDS_APPROVAL.value
            if result.needs_human
            else AgentJobStatus.DONE.value
        )
        job.result_payload = {
            "summary": result.summary,
            "payload": result.payload,
            "needs_human": result.needs_human,
        }
        job.error = result.error
        job.needs_human = result.needs_human
        job.finished_at = _now()
        _upsert_gaps(session, offer, result.gaps, agent=kind.value)
        _add_evidence(session, offer.id, result.evidence)
        return job
    except Exception as exc:  # noqa: BLE001
        logger.exception("agent.failed", kind=kind.value, offer_id=offer.id)
        job.status = AgentJobStatus.FAILED.value
        job.error = str(exc)
        job.finished_at = _now()
        return job


def recompute_offer(
    session: Session,
    offer: Offer,
    *,
    sap_engine: Engine | None = None,
    quoter: QuoterClient | None = None,
) -> Offer:
    offer.status = OfferStatus.COMPUTING.value
    offer.updated_at = _now()
    session.commit()

    quote_job = _run_job(
        session,
        offer,
        AgentKind.QUOTE,
        lambda: agent_mod.run_quote_agent(
            offer, session=session, sap_engine=sap_engine, quoter=quoter
        ),
    )
    eval_payload = (quote_job.result_payload or {}).get("payload") or {}
    offer.evaluation = eval_payload

    _run_job(
        session,
        offer,
        AgentKind.PURCHASE,
        lambda: agent_mod.run_purchase_agent(offer, sap_engine=sap_engine),
    )
    _run_job(
        session,
        offer,
        AgentKind.CAPACITY,
        lambda: agent_mod.run_capacity_agent(offer, session=session),
    )

    gaps = _gaps_for(session, offer.id)
    open_gaps = [g for g in gaps if g.status in (GapStatus.OPEN.value, GapStatus.IN_PROGRESS.value)]
    offer.confidence = compute_confidence(gaps=gaps, evaluation=eval_payload)
    low, high = price_band_from_evaluation(eval_payload)
    # Quoter netto overrides band if present
    q = (eval_payload or {}).get("quoter") or {}
    if q.get("netto_eur") is not None:
        n = float(q["netto_eur"])
        low, high = round(n * 0.92, 2), round(n * 1.08, 2)
    offer.price_low_eur, offer.price_high_eur = low, high
    early, late = date_band(requested_date=offer.requested_date, evaluation=eval_payload)
    offer.date_early, offer.date_late = early, late

    contract_result = agent_mod.run_contract_agent(offer, open_gaps=open_gaps)
    _run_job(session, offer, AgentKind.CONTRACT, lambda: contract_result)
    _persist_contract_from_agent(session, offer, contract_result.payload)

    if offer.decision:
        offer.status = OfferStatus.DECIDED.value
    elif offer.confidence >= offer.confidence_threshold and not open_gaps:
        offer.status = OfferStatus.PROMISABLE.value
    elif open_gaps:
        offer.status = OfferStatus.OPEN.value
    else:
        offer.status = OfferStatus.OPEN.value

    offer.version += 1
    offer.updated_at = _now()
    session.commit()
    session.refresh(offer)
    return offer


def _persist_contract_from_agent(session: Session, offer: Offer, payload: dict[str, Any]) -> None:
    body = payload.get("body")
    if not isinstance(body, dict):
        return
    existing = _latest_contract(session, offer.id)
    now = _now()
    title = str(payload.get("title") or f"Angebot {offer.item_code}")
    if existing and existing.status in (ContractStatus.DRAFT.value, ContractStatus.INTERNAL_REVIEW.value):
        existing.body = body
        existing.title = title
        existing.updated_at = now
        existing.status = (
            ContractStatus.INTERNAL_REVIEW.value
            if payload.get("firm")
            else ContractStatus.DRAFT.value
        )
        return
    version = (existing.version + 1) if existing else 1
    if existing and existing.status not in (ContractStatus.SUPERSEDED.value,):
        if existing.status in (ContractStatus.SENT.value, ContractStatus.ACCEPTED.value):
            existing.status = ContractStatus.SUPERSEDED.value
            existing.updated_at = now
    session.add(
        Contract(
            id=str(uuid.uuid4()),
            offer_id=offer.id,
            created_at=now,
            updated_at=now,
            version=version,
            status=ContractStatus.INTERNAL_REVIEW.value if payload.get("firm") else ContractStatus.DRAFT.value,
            title=title,
            body=body,
            customer_visible=False,
        )
    )


def resolve_gap(session: Session, offer: Offer, gap_id: str, body: GapResolve) -> Gap:
    gap = session.get(Gap, gap_id)
    if not gap or gap.offer_id != offer.id:
        raise KeyError("gap not found")
    now = _now()
    gap.status = GapStatus.WAIVED.value if body.waive else GapStatus.RESOLVED.value
    gap.resolution_note = body.resolution_note
    gap.resolved_by = body.resolved_by or offer.owner
    gap.resolved_at = now
    gap.updated_at = now
    offer.updated_at = now
    # Recalc confidence cheaply without full agent run
    gaps = _gaps_for(session, offer.id)
    offer.confidence = compute_confidence(gaps=gaps, evaluation=offer.evaluation)
    open_gaps = [g for g in gaps if g.status in (GapStatus.OPEN.value, GapStatus.IN_PROGRESS.value)]
    if offer.confidence >= offer.confidence_threshold and not open_gaps and not offer.decision:
        offer.status = OfferStatus.PROMISABLE.value
    session.commit()
    session.refresh(gap)
    return gap


def decide_offer(session: Session, offer: Offer, body: OfferDecide) -> Offer:
    offer.decision = body.decision
    offer.decision_note = body.decision_note
    if body.owner:
        offer.owner = body.owner
    offer.decided_at = _now()
    offer.status = OfferStatus.DECIDED.value
    offer.updated_at = offer.decided_at
    session.commit()
    session.refresh(offer)
    return offer


def publish_contract(
    session: Session,
    offer: Offer,
    *,
    customer_visible: bool = True,
    title: str | None = None,
) -> Contract:
    c = _latest_contract(session, offer.id)
    if not c:
        raise KeyError("no contract")
    c.customer_visible = customer_visible
    c.status = ContractStatus.SENT.value
    if title:
        c.title = title
    c.updated_at = _now()
    offer.status = OfferStatus.CONTRACTED.value if offer.decision == "accept" else offer.status
    offer.updated_at = c.updated_at
    session.commit()
    session.refresh(c)
    return c


def portal_accept(session: Session, offer: Offer, body: PortalAccept) -> Contract:
    c = _latest_contract(session, offer.id)
    if not c or not c.customer_visible:
        raise PermissionError("contract not visible")
    c.status = ContractStatus.ACCEPTED.value
    c.accepted_at = _now()
    c.accepted_by = body.accepted_by
    c.updated_at = c.accepted_at
    offer.status = OfferStatus.CONTRACTED.value
    offer.decision = offer.decision or "accept"
    offer.updated_at = c.accepted_at
    session.commit()
    session.refresh(c)
    return c


def portal_reject(session: Session, offer: Offer, body: PortalReject) -> Contract:
    c = _latest_contract(session, offer.id)
    if not c or not c.customer_visible:
        raise PermissionError("contract not visible")
    c.status = ContractStatus.REJECTED.value
    c.reject_reason = body.reason
    c.updated_at = _now()
    offer.updated_at = c.updated_at
    session.commit()
    session.refresh(c)
    return c


def to_offer_dto(session: Session, offer: Offer, *, include_children: bool = True) -> OfferDTO:
    gaps = _gaps_for(session, offer.id) if include_children else []
    open_count = sum(1 for g in gaps if g.status in (GapStatus.OPEN.value, GapStatus.IN_PROGRESS.value))
    dto = OfferDTO.model_validate(offer)
    dto.open_gap_count = open_count
    if include_children:
        from bdx.promise.models import AgentJobDTO, ContractDTO, EvidenceDTO, GapDTO

        dto.gaps = [GapDTO.model_validate(g) for g in gaps]
        dto.evidence = [EvidenceDTO.model_validate(e) for e in _evidence_for(session, offer.id)]
        dto.jobs = [AgentJobDTO.model_validate(j) for j in _jobs_for(session, offer.id)]
        c = _latest_contract(session, offer.id)
        dto.contract = ContractDTO.model_validate(c) if c else None
    return dto


def to_portal_dto(session: Session, offer: Offer) -> PortalOfferDTO:
    gaps = _gaps_for(session, offer.id)
    # Customer only sees vertrieb/recht/technik gaps that are still open
    visible_types = {"vertrieb", "recht", "technik"}
    customer_gaps = [
        {"type": g.gap_type, "title": g.title}
        for g in gaps
        if g.status == GapStatus.OPEN.value and g.gap_type in visible_types
    ]
    c = _latest_contract(session, offer.id)
    from bdx.promise.models import ContractDTO

    contract_dto = None
    if c and c.customer_visible:
        contract_dto = ContractDTO.model_validate(c)
    return PortalOfferDTO(
        id=offer.id,
        status=offer.status,
        customer_ref=offer.customer_ref,
        customer_name=offer.customer_name,
        item_code=offer.item_code,
        qty=float(offer.qty),
        requested_date=offer.requested_date,
        price_low_eur=offer.price_low_eur,
        price_high_eur=offer.price_high_eur,
        date_early=offer.date_early,
        date_late=offer.date_late,
        confidence=offer.confidence,
        confidence_threshold=offer.confidence_threshold,
        customer_gaps=customer_gaps,
        contract=contract_dto,
    )
