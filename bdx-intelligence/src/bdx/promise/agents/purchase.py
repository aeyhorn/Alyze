"""Purchase agent – turns material/BOM shortages into einkauf gaps + proposals."""
from __future__ import annotations

from typing import Any

from sqlalchemy.engine import Engine

from bdx.db import queries as sap_queries
from bdx.promise.agents.base import AgentResult
from bdx.promise.models import Offer


def run_purchase_agent(offer: Offer, *, sap_engine: Engine | None) -> AgentResult:
    if sap_engine is None:
        return AgentResult(
            ok=False,
            summary="SAP nicht angebunden – Einkauf manuell",
            gaps=[
                {
                    "gap_type": "einkauf",
                    "title": "Material-/Bestellstatus manuell klären",
                    "owner_role": "einkauf",
                    "source_agent": "purchase",
                    "source_domain": "material",
                }
            ],
            needs_human=True,
            error="no sap_engine",
        )

    gaps: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    proposals: list[dict[str, Any]] = []

    try:
        with sap_engine.connect() as conn:
            stock, stock_err = sap_queries.fetch_warehouse_stock(conn, offer.item_code)
            pos, po_err = sap_queries.fetch_open_purchase_lines(conn, offer.item_code)
            bom, bom_err = sap_queries.fetch_bom_components(conn, offer.item_code)
    except Exception as exc:  # noqa: BLE001
        return AgentResult(
            ok=False,
            summary=f"Einkauf-Agent Fehler: {exc}",
            needs_human=True,
            error=str(exc),
            gaps=[
                {
                    "gap_type": "einkauf",
                    "title": "SAP-Einkaufsdaten nicht lesbar",
                    "owner_role": "einkauf",
                    "source_agent": "purchase",
                }
            ],
        )

    on_hand = sum(float(r.get("on_hand") or 0) for r in stock)
    committed = sum(float(r.get("is_committed") or 0) for r in stock)
    available = on_hand - committed
    open_po_qty = sum(float(r.get("open_qty") or 0) for r in pos)
    need = float(offer.qty)

    evidence.append(
        {
            "kind": "sap",
            "label": f"stock {offer.item_code}",
            "payload": {
                "available": available,
                "on_hand": on_hand,
                "open_po_qty": open_po_qty,
                "stock_error": stock_err,
                "po_error": po_err,
                "bom_error": bom_err,
            },
        }
    )

    if stock_err and not stock:
        gaps.append(
            {
                "gap_type": "einkauf",
                "title": "Lagerbestand nicht lesbar (OITW-Recht?)",
                "owner_role": "einkauf",
                "source_agent": "purchase",
            }
        )
    elif available + open_po_qty < need:
        shortage = need - (available + open_po_qty)
        proposal = {
            "item_code": offer.item_code,
            "shortage_qty": shortage,
            "action": "create_purchase_requisition",
            "policy": "propose_only",  # Phase B: no auto-order
        }
        proposals.append(proposal)
        gaps.append(
            {
                "gap_type": "einkauf",
                "title": f"Fehlmenge {shortage:g} – Bestellvorschlag erstellt",
                "detail": "Einkaufsmaschine: nur Vorschlag (Policy Phase B)",
                "owner_role": "einkauf",
                "source_agent": "purchase",
                "extra": proposal,
            }
        )
    elif available < need <= available + open_po_qty:
        next_due = next((r.get("due_date") for r in pos if r.get("due_date")), None)
        gaps.append(
            {
                "gap_type": "einkauf",
                "title": f"Deckung über offene Bestellung (ETA {next_due or '?'})",
                "owner_role": "einkauf",
                "source_agent": "purchase",
                "extra": {"open_pos": pos[:5]},
            }
        )

    # BOM component shortages → separate gaps
    for c in bom[:30]:
        code = c.get("component_code") or ""
        if not code:
            continue
        try:
            with sap_engine.connect() as conn:
                c_stock, _ = sap_queries.fetch_warehouse_stock(conn, code)
        except Exception:  # noqa: BLE001
            continue
        c_avail = sum(float(r.get("on_hand") or 0) - float(r.get("is_committed") or 0) for r in c_stock)
        per = float(c.get("quantity") or 0)
        needed = per * need
        if c_avail < needed:
            gaps.append(
                {
                    "gap_type": "einkauf",
                    "title": f"BOM {code}: fehlt {needed - c_avail:g}",
                    "owner_role": "einkauf",
                    "source_agent": "purchase",
                    "source_domain": "bom",
                    "extra": {"component": code, "needed": needed, "available": c_avail},
                }
            )

    return AgentResult(
        ok=True,
        summary=f"Einkauf: {len(proposals)} Vorschläge, {len(gaps)} Gaps",
        gaps=gaps,
        evidence=evidence,
        payload={"proposals": proposals, "available": available, "open_po_qty": open_po_qty},
        needs_human=bool(gaps),
    )
