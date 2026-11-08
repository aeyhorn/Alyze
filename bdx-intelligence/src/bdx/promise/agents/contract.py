"""Contract agent – draft contract body from living offer (Phase C)."""
from __future__ import annotations

from typing import Any

from bdx.promise.agents.base import AgentResult
from bdx.promise.models import GapStatus, Offer


def run_contract_agent(offer: Offer, *, open_gaps: list[Any]) -> AgentResult:
    blocking = [
        g
        for g in open_gaps
        if (getattr(g, "status", None) or g.get("status"))
        in (GapStatus.OPEN.value, GapStatus.IN_PROGRESS.value, "open", "in_progress")
    ]
    firm = offer.confidence >= offer.confidence_threshold and not blocking

    body: dict[str, Any] = {
        "parties": {
            "supplier": "Leisinger / Alyze Promise Platform",
            "customer_ref": offer.customer_ref,
            "customer_name": offer.customer_name,
        },
        "scope": {
            "item_code": offer.item_code,
            "qty": float(offer.qty),
            "requested_date": offer.requested_date,
        },
        "commercial": {
            "price_low_eur": offer.price_low_eur,
            "price_high_eur": offer.price_high_eur,
            "currency": "EUR",
            "firm": firm,
            "confidence": offer.confidence,
        },
        "schedule": {
            "date_early": offer.date_early,
            "date_late": offer.date_late,
        },
        "open_conditions": [
            {
                "gap_id": getattr(g, "id", None) or g.get("id"),
                "title": getattr(g, "title", None) or g.get("title"),
                "type": getattr(g, "gap_type", None) or g.get("gap_type"),
            }
            for g in blocking
        ],
        "change_order_policy": "Änderungen >5% Scope → neuer Contract-Version",
        "acceptance": {
            "mode": "portal",
            "portal_token_required": True,
        },
    }

    gaps: list[dict[str, Any]] = []
    if not firm:
        gaps.append(
            {
                "gap_type": "recht",
                "title": "Vertrag noch nicht freigabefähig (Konfidenz/Gaps)",
                "owner_role": "vertrieb",
                "source_agent": "contract",
                "extra": {"confidence": offer.confidence, "open_gaps": len(blocking)},
            }
        )

    return AgentResult(
        ok=True,
        summary="Vertragsentwurf erzeugt" if firm else "Vertragsentwurf bedingt",
        gaps=gaps,
        evidence=[
            {
                "kind": "contract",
                "label": "draft_contract",
                "payload": {"firm": firm, "version_hint": offer.version},
            }
        ],
        payload={"body": body, "firm": firm, "title": f"Angebot {offer.item_code} × {offer.qty:g}"},
        needs_human=not firm,
    )
