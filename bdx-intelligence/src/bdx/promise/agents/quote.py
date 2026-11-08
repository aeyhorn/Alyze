"""Quote agent – runs Q2P evaluation (+ optional bdx-quoter via datenraum)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from bdx.adapters.quoter import NullQuoterClient, QuoterClient
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
    result = evaluate_promise(
        item_code=offer.item_code,
        qty=Decimal(str(offer.qty)),
        requested_date=req,
        sap_engine=sap_engine,
        pg_session=session,
    )
    payload = result.model_dump(mode="json")

    # If datenraum set and quoter available, enrich pricing via quoter
    quoter_client = quoter or NullQuoterClient()
    if offer.datenraum and not isinstance(quoter_client, NullQuoterClient):
        q = quoter_client.quote(
            datenraum=offer.datenraum,
            kunde=offer.kunde,
            llm=bool(offer.use_llm),
            item_code=offer.item_code,
            qty=float(offer.qty),
        )
        payload["quoter"] = {
            "ok": q.ok,
            "netto_eur": q.netto_eur,
            "brutto_eur": q.brutto_eur,
            "offen": q.offen,
            "position_count": q.position_count,
            "error": q.error,
            "source_path": q.source_path,
            "status": q.status,
        }
        # Replace/augment pricing domain
        domains = list(payload.get("domains") or [])
        domains = [d for d in domains if d.get("domain") != "pricing"]
        if q.ok:
            status = "warn" if q.offen else "ok"
            domains.append(
                {
                    "domain": "pricing",
                    "status": status,
                    "summary": (
                        f"Quoter Netto {q.netto_eur:g} EUR"
                        if q.netto_eur is not None
                        else "Quoter-Kalkulation"
                    ),
                    "details": {
                        "provider": "bdx-quoter",
                        "netto_eur": q.netto_eur,
                        "brutto_eur": q.brutto_eur,
                        "offen": q.offen,
                        "position_count": q.position_count,
                    },
                    "source": "system",
                    "needs_human": bool(q.offen),
                    "question": q.offen[0] if q.offen else None,
                }
            )
            for o in q.offen:
                payload.setdefault("open_questions", []).append(
                    {"domain": "pricing", "question": o}
                )
        else:
            domains.append(
                {
                    "domain": "pricing",
                    "status": "unknown",
                    "summary": q.error or "Quoter ohne Ergebnis",
                    "details": {"provider": "bdx-quoter", "error": q.error},
                    "source": "human",
                    "needs_human": True,
                    "question": "Quoter-/Datenraum prüfen",
                }
            )
        payload["domains"] = domains

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
