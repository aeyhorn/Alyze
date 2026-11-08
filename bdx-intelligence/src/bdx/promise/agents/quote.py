"""Quote agent – runs Q2P evaluation (+ optional bdx-quoter via datenraum)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from bdx.adapters.quoter import QuoterClient
from bdx.promise.agents.base import AgentResult
from bdx.promise.models import Offer
from bdx.q2p.service import evaluate_promise


_DOMAIN_TO_GAP: dict[str, str] = {
    "item": "technik",
    "material": "einkauf",
    "bom": "einkauf",
    "capacity": "fertigung",
    "pricing": "kalkulation",
    "personnel": "personal",
}


def run_quote_agent(
    offer: Offer,
    *,
    session: Session,
    sap_engine: Engine | None = None,
    quoter: QuoterClient | None = None,
) -> AgentResult:
    req = date.fromisoformat(offer.requested_date) if offer.requested_date else None
    # Quoter pricing is owned by evaluate_promise when datenraum is set (#39).
    result = evaluate_promise(
        item_code=offer.item_code,
        qty=Decimal(str(offer.qty)),
        requested_date=req,
        sap_engine=sap_engine,
        pg_session=session,
        quoter=quoter,
        datenraum=offer.datenraum,
        kunde=offer.kunde,
        use_llm=bool(offer.use_llm),
    )
    payload = result.model_dump(mode="json")

    # Surface quoter details from the pricing domain for Offer.evaluation.quoter
    for d in payload.get("domains") or []:
        if d.get("domain") == "pricing":
            details = d.get("details") or {}
            if details.get("provider") == "bdx-quoter" or "netto_eur" in details:
                payload["quoter"] = {
                    "ok": d.get("status") in ("ok", "warn"),
                    "netto_eur": details.get("netto_eur"),
                    "brutto_eur": details.get("brutto_eur"),
                    "offen": details.get("offen") or [],
                    "position_count": details.get("position_count") or 0,
                    "error": details.get("error"),
                    "status": d.get("status"),
                }
            break

    gaps: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    for d in payload.get("domains") or []:
        evidence.append(
            {
                "kind": "evaluation",
                "label": f"domain:{d.get('domain')}={d.get('status')}",
                "payload": d,
            }
        )
        if d.get("needs_human") or d.get("status") in ("bad", "unknown", "warn"):
            offen = (d.get("details") or {}).get("offen")
            if isinstance(offen, list) and offen:
                for item in offen:
                    gaps.append(
                        {
                            "gap_type": _DOMAIN_TO_GAP.get(str(d.get("domain")), "vertrieb"),
                            "title": str(item)[:256],
                            "detail": d.get("summary"),
                            "owner_role": _DOMAIN_TO_GAP.get(str(d.get("domain")), "vertrieb"),
                            "source_domain": d.get("domain"),
                            "source_agent": "quote",
                        }
                    )
            elif d.get("question"):
                gaps.append(
                    {
                        "gap_type": _DOMAIN_TO_GAP.get(str(d.get("domain")), "vertrieb"),
                        "title": str(d.get("question"))[:256],
                        "detail": d.get("summary"),
                        "owner_role": _DOMAIN_TO_GAP.get(str(d.get("domain")), "vertrieb"),
                        "source_domain": d.get("domain"),
                        "source_agent": "quote",
                    }
                )

    return AgentResult(
        ok=True,
        summary=f"Evaluate overall={payload.get('overall')} gaps={len(gaps)}",
        gaps=gaps,
        evidence=evidence,
        payload=payload,
        needs_human=bool(gaps),
    )
