"""Parallel Quote-to-Promise evaluation.

Fans out domain checks (item, material, BOM, capacity, pricing, personnel)
against SAP (when an engine is available) and the local event store, then
collapses the answers into one promise result + an explicit open-question list
for anything that still needs a human.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from bdx.adapters.quoter import NullQuoterClient, QuoterClient, QuoterQuote
from bdx.db import queries as sap_queries
from bdx.models.events import MachineState, OrderState
from bdx.models.sap import OPEN_STATUSES
from bdx.q2p.models import DomainResult, DomainStatus, PromiseResult

logger = structlog.get_logger(__name__)

_IDLE_STATES = frozenset({"idle", "bereit", "ready", "setup", "ruesten", "rüsten", "auftrag"})
_RUNNING_STATES = frozenset({"running", "fertigen", "auto", "produktion"})


def evaluate_promise(
    *,
    item_code: str,
    qty: Decimal | float,
    requested_date: Optional[date] = None,
    sap_engine: Engine | None = None,
    pg_session: Session | None = None,
    quoter: QuoterClient | None = None,
    datenraum: str | None = None,
    kunde: str | None = None,
    use_llm: bool = False,
) -> PromiseResult:
    """Run all domain checks and return a consolidated promise result."""
    qty_d = Decimal(str(qty))
    item_code = item_code.strip()
    domains: list[DomainResult] = []
    quoter_client: QuoterClient = quoter or NullQuoterClient()

    # Capacity always from PG (shop floor) – main thread (session not thread-safe).
    if pg_session is not None:
        domains.append(_check_capacity(pg_session, item_code, qty_d))
    else:
        domains.append(
            DomainResult(
                domain="capacity",
                status=DomainStatus.UNKNOWN,
                summary="Keine Verbindung zum Shop-Floor-Store",
                needs_human=True,
                question="Kapazität manuell prüfen (Maschinen + offene FAs)",
                source="human",
            )
        )

    # Pricing: prefer bdx-quoter when a datenraum is set; else SAP price list.
    pricing = _check_pricing_combined(
        sap_engine=sap_engine,
        quoter=quoter_client,
        item_code=item_code,
        qty=float(qty_d),
        datenraum=datenraum,
        kunde=kunde,
        use_llm=use_llm,
    )
    domains.append(pricing)

    # Remaining SAP domains in parallel (each task opens its own connection).
    sap_jobs = {
        "item": lambda conn: _check_item(conn, item_code),
        "material": lambda conn: _check_material(conn, item_code, qty_d),
        "bom": lambda conn: _check_bom(conn, item_code, qty_d),
    }

    if sap_engine is None:
        for name in sap_jobs:
            domains.append(
                DomainResult(
                    domain=name,
                    status=DomainStatus.UNKNOWN,
                    summary="SAP-Engine nicht an die API angebunden",
                    needs_human=True,
                    question=f"{name}: manuell in SAP klären",
                    source="human",
                )
            )
    else:
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {
                pool.submit(_run_sap_domain, sap_engine, name, fn): name
                for name, fn in sap_jobs.items()
            }
            for fut in as_completed(futures):
                domains.append(fut.result())

    # Personnel: no data source yet – explicit gap, not silent omit.
    domains.append(
        DomainResult(
            domain="personnel",
            status=DomainStatus.UNKNOWN,
            summary="Kein Schicht-/Qualifikations-Feed angebunden",
            details={"planned": False},
            needs_human=True,
            question="Personal / Qualifikation für den Slot verfügbar?",
            source="human",
        )
    )

    # Stable order for UI
    order = ["item", "material", "bom", "capacity", "personnel", "pricing"]
    domains.sort(key=lambda d: order.index(d.domain) if d.domain in order else 99)

    return _collapse(domains, requested_date)


def _run_sap_domain(engine: Engine, name: str, fn: Any) -> DomainResult:
    try:
        with engine.connect() as conn:
            return fn(conn)
    except Exception as exc:  # noqa: BLE001
        logger.warning("q2p.domain_failed", domain=name, error=str(exc))
        return DomainResult(
            domain=name,
            status=DomainStatus.UNKNOWN,
            summary=f"Fehler: {exc}",
            needs_human=True,
            question=f"{name}: manuell klären (Systemfehler)",
            source="human",
        )


def _check_item(conn: Any, item_code: str) -> DomainResult:
    row = sap_queries.fetch_item_by_code(conn, item_code)
    if not row:
        return DomainResult(
            domain="item",
            status=DomainStatus.BAD,
            summary=f"Artikel {item_code} nicht in OITM gefunden",
            needs_human=True,
            question="Artikelnummer prüfen oder Neuanlage in SAP",
            source="human",
        )
    name = row.get("ItemName") or row.get("item_name") or ""
    return DomainResult(
        domain="item",
        status=DomainStatus.OK,
        summary=f"{item_code} – {name}".strip(" –"),
        details={
            "item_code": item_code,
            "item_name": name,
            "inventory_item": row.get("InvntItem") or row.get("inventory_item"),
            "mrp_item": row.get("PrfrmMrpStep") or row.get("mrp_item"),
        },
        source="system",
    )


def _check_material(conn: Any, item_code: str, qty: Decimal) -> DomainResult:
    stock_rows, stock_err = sap_queries.fetch_warehouse_stock(conn, item_code)
    po_rows, po_err = sap_queries.fetch_open_purchase_lines(conn, item_code)

    if stock_err and not stock_rows:
        return DomainResult(
            domain="material",
            status=DomainStatus.UNKNOWN,
            summary="Lagerbestand nicht lesbar (SELECT auf OITW fehlt?)",
            details={"error": stock_err},
            needs_human=True,
            question="Materialbestand und Bestellstatus manuell klären",
            source="human",
        )

    on_hand = sum(Decimal(str(r.get("on_hand") or 0)) for r in stock_rows)
    committed = sum(Decimal(str(r.get("is_committed") or 0)) for r in stock_rows)
    on_order = sum(Decimal(str(r.get("on_order") or 0)) for r in stock_rows)
    available = on_hand - committed
    shortage = qty - available

    warehouses = [
        {
            "warehouse": r.get("warehouse"),
            "on_hand": float(r.get("on_hand") or 0),
            "committed": float(r.get("is_committed") or 0),
            "on_order": float(r.get("on_order") or 0),
        }
        for r in stock_rows
    ]
    open_pos = [
        {
            "doc_num": r.get("doc_num"),
            "vendor": r.get("vendor_name") or r.get("vendor_code"),
            "open_qty": float(r.get("open_qty") or 0),
            "due_date": _date_str(r.get("due_date")),
            "price": float(r.get("price") or 0),
        }
        for r in po_rows
    ]

    details: dict[str, Any] = {
        "on_hand": float(on_hand),
        "committed": float(committed),
        "on_order": float(on_order),
        "available": float(available),
        "requested_qty": float(qty),
        "shortage": float(max(shortage, Decimal("0"))),
        "warehouses": warehouses,
        "open_pos": open_pos,
    }
    if po_err:
        details["po_error"] = po_err

    if available >= qty:
        return DomainResult(
            domain="material",
            status=DomainStatus.OK,
            summary=f"Verfügbar {available:g} (Bedarf {qty:g})",
            details=details,
            source="system",
        )

    inbound = sum(Decimal(str(p["open_qty"])) for p in open_pos)
    if available + inbound >= qty:
        next_due = next((p["due_date"] for p in open_pos if p["due_date"]), None)
        return DomainResult(
            domain="material",
            status=DomainStatus.WARN,
            summary=f"Lager {available:g} + offene Bestellung {inbound:g} deckt Bedarf {qty:g}",
            details=details,
            needs_human=False,
            source="system",
            question=None if next_due else "Liefertermin der offenen Bestellung bestätigen",
        )

    return DomainResult(
        domain="material",
        status=DomainStatus.BAD,
        summary=f"Fehlt {float(shortage):g} Stück (verfügbar {available:g})",
        details=details,
        needs_human=True,
        question="Material bestellen: Lieferant, Termin und Preis klären",
        source="human",
    )


def _check_bom(conn: Any, item_code: str, qty: Decimal) -> DomainResult:
    components, err = sap_queries.fetch_bom_components(conn, item_code)
    if err and not components:
        return DomainResult(
            domain="bom",
            status=DomainStatus.UNKNOWN,
            summary="Stückliste nicht lesbar (SELECT auf OITT/ITT1 fehlt?)",
            details={"error": err},
            needs_human=True,
            question="Stückliste / Komponenten manuell prüfen",
            source="human",
        )
    if not components:
        return DomainResult(
            domain="bom",
            status=DomainStatus.WARN,
            summary="Keine Produktstruktur in OITT – Fertigteil oder fehlende Stückliste",
            details={"components": []},
            needs_human=False,
            source="system",
        )

    shortages: list[dict[str, Any]] = []
    enriched: list[dict[str, Any]] = []
    for c in components:
        code = c.get("component_code") or ""
        per = Decimal(str(c.get("quantity") or 0))
        need = per * qty
        stock_rows, _ = sap_queries.fetch_warehouse_stock(conn, code)
        available = sum(
            Decimal(str(r.get("on_hand") or 0)) - Decimal(str(r.get("is_committed") or 0))
            for r in stock_rows
        )
        entry = {
            "component_code": code,
            "component_name": c.get("component_name"),
            "qty_per": float(per),
            "qty_needed": float(need),
            "available": float(available),
        }
        enriched.append(entry)
        if available < need:
            shortages.append({**entry, "shortage": float(need - available)})

    if shortages:
        return DomainResult(
            domain="bom",
            status=DomainStatus.BAD,
            summary=f"{len(shortages)} Komponenten mit Fehlmenge",
            details={"components": enriched, "shortages": shortages},
            needs_human=True,
            question="Fehlende BOM-Komponenten beschaffen oder Alternativen klären",
            source="human",
        )
    return DomainResult(
        domain="bom",
        status=DomainStatus.OK,
        summary=f"{len(enriched)} Komponenten verfügbar",
        details={"components": enriched},
        source="system",
    )


def _check_pricing_combined(
    *,
    sap_engine: Engine | None,
    quoter: QuoterClient,
    item_code: str,
    qty: float,
    datenraum: str | None,
    kunde: str | None,
    use_llm: bool,
) -> DomainResult:
    """Prefer bdx-quoter kalkulation; fall back to SAP ITM1 list price."""
    quoter_result: DomainResult | None = None
    if datenraum:
        quoter_result = _check_quoter_pricing(
            quoter,
            datenraum=datenraum,
            kunde=kunde,
            use_llm=use_llm,
            item_code=item_code,
            qty=qty,
        )
        if quoter_result.status in (DomainStatus.OK, DomainStatus.WARN):
            return quoter_result

    sap_result: DomainResult | None = None
    if sap_engine is not None:
        try:
            with sap_engine.connect() as conn:
                sap_result = _check_pricing_sap(conn, item_code)
        except Exception as exc:  # noqa: BLE001
            sap_result = DomainResult(
                domain="pricing",
                status=DomainStatus.UNKNOWN,
                summary=f"SAP-Preisfehler: {exc}",
                needs_human=True,
                question="Verkaufspreis / Kalkulation manuell ermitteln",
                source="human",
            )

    if quoter_result and sap_result and sap_result.status == DomainStatus.OK:
        # Quoter failed but SAP has a list price – keep SAP, attach quoter error
        details = dict(sap_result.details)
        details["quoter"] = {
            "status": quoter_result.status.value,
            "summary": quoter_result.summary,
            "error": quoter_result.details.get("error"),
        }
        return DomainResult(
            domain="pricing",
            status=sap_result.status,
            summary=sap_result.summary + " (Quoter nicht nutzbar)",
            details=details,
            needs_human=sap_result.needs_human or quoter_result.needs_human,
            question=quoter_result.question or sap_result.question,
            source="system",
        )

    if sap_result is not None:
        return sap_result
    if quoter_result is not None:
        return quoter_result

    return DomainResult(
        domain="pricing",
        status=DomainStatus.UNKNOWN,
        summary="Weder Quoter (Datenraum) noch SAP-Preisliste angebunden",
        needs_human=True,
        question="Preis kalkulieren – Datenraum setzen oder SAP ITM1 freigeben",
        source="human",
    )


def _check_quoter_pricing(
    quoter: QuoterClient,
    *,
    datenraum: str,
    kunde: str | None,
    use_llm: bool,
    item_code: str,
    qty: float,
) -> DomainResult:
    quote: QuoterQuote = quoter.quote(
        datenraum=datenraum,
        kunde=kunde,
        llm=use_llm,
        item_code=item_code,
        qty=qty,
    )
    details: dict[str, Any] = {
        "provider": "bdx-quoter",
        "datenraum": datenraum,
        "kunde": kunde,
        "source_path": quote.source_path,
        "netto_eur": quote.netto_eur,
        "brutto_eur": quote.brutto_eur,
        "position_count": quote.position_count,
        "offen": quote.offen,
        "status": quote.status,
    }
    if quote.error:
        details["error"] = quote.error

    if quote.status == "running":
        return DomainResult(
            domain="pricing",
            status=DomainStatus.WARN,
            summary="Quoter-Job läuft noch",
            details=details,
            needs_human=True,
            question="Kalkulation im Quoter abwarten und neu bewerten",
            source="system",
        )

    if not quote.ok:
        return DomainResult(
            domain="pricing",
            status=DomainStatus.UNKNOWN,
            summary=quote.error or "Quoter ohne Ergebnis",
            details=details,
            needs_human=True,
            question="Quoter-Endpunkt/Datenraum prüfen oder manuell kalkulieren",
            source="human",
        )

    offen_q = quote.offen
    summary = f"Quoter Netto {quote.netto_eur:g} EUR" if quote.netto_eur is not None else "Quoter-Kalkulation"
    if quote.position_count:
        summary += f" · {quote.position_count} Positionen"
    if offen_q:
        summary += f" · {len(offen_q)} offene Punkte"
        return DomainResult(
            domain="pricing",
            status=DomainStatus.WARN,
            summary=summary,
            details=details,
            needs_human=True,
            question=offen_q[0],
            source="system",
        )
    return DomainResult(
        domain="pricing",
        status=DomainStatus.OK,
        summary=summary,
        details=details,
        source="system",
    )


def _check_pricing_sap(conn: Any, item_code: str) -> DomainResult:
    prices, err = sap_queries.fetch_item_prices(conn, item_code)
    if err and not prices:
        return DomainResult(
            domain="pricing",
            status=DomainStatus.UNKNOWN,
            summary="Preisliste nicht lesbar (SELECT auf ITM1 fehlt?)",
            details={"error": err, "provider": "sap-itm1"},
            needs_human=True,
            question="Verkaufspreis / Kalkulation manuell ermitteln",
            source="human",
        )
    if not prices:
        return DomainResult(
            domain="pricing",
            status=DomainStatus.UNKNOWN,
            summary="Kein Listenpreis > 0 in ITM1",
            details={"provider": "sap-itm1"},
            needs_human=True,
            question="Preis kalkulieren (kein SAP-Listenpreis) – Datenraum für Quoter setzen",
            source="human",
        )
    normalised = [
        {
            "price_list": r.get("price_list"),
            "list_name": r.get("list_name"),
            "price": float(r.get("price") or 0),
        }
        for r in prices
    ]
    return DomainResult(
        domain="pricing",
        status=DomainStatus.OK,
        summary=f"{len(normalised)} Listenpreis(e) – Basis {normalised[0]['price']:g}",
        details={"prices": normalised, "provider": "sap-itm1"},
        source="system",
    )


def _check_capacity(session: Session, item_code: str, qty: Decimal) -> DomainResult:
    machines = list(session.scalars(select(MachineState)))
    open_same = list(
        session.scalars(
            select(OrderState).where(
                OrderState.status.in_(tuple(OPEN_STATUSES)),
                OrderState.item_code == item_code,
            )
        )
    )
    open_all = list(
        session.scalars(select(OrderState).where(OrderState.status.in_(tuple(OPEN_STATUSES))))
    )

    online = [m for m in machines if m.online]
    idle = [
        m
        for m in online
        if (m.state or "").lower() in _IDLE_STATES
        or (m.exec_state or "").lower() in _IDLE_STATES
        or not m.order_ref
    ]
    running = [
        m
        for m in online
        if (m.state or "").lower() in _RUNNING_STATES
        or (m.exec_state or "").lower() in {"fertigen", "auto"}
    ]
    on_item = [m for m in online if m.sap_item_code == item_code]

    machine_rows = [
        {
            "machine_id": m.machine_id,
            "online": m.online,
            "state": m.state,
            "exec_state": m.exec_state,
            "order_ref": m.order_ref,
            "sap_item_code": m.sap_item_code,
            "operator": m.operator,
        }
        for m in machines
    ]

    backlog_qty = sum(
        max(float(o.planned_qty) - float(o.completed_qty), 0.0) for o in open_same
    )
    details = {
        "machines_total": len(machines),
        "machines_online": len(online),
        "machines_idle": len(idle),
        "machines_running": len(running),
        "machines_on_same_item": len(on_item),
        "open_orders_same_item": len(open_same),
        "open_backlog_qty_same_item": backlog_qty,
        "open_orders_all": len(open_all),
        "requested_qty": float(qty),
        "machines": machine_rows,
        "idle_machine_ids": [m.machine_id for m in idle],
    }

    if not machines:
        return DomainResult(
            domain="capacity",
            status=DomainStatus.UNKNOWN,
            summary="Keine Maschinenstände im Event-Store",
            details=details,
            needs_human=True,
            question="Maschinenkapazität manuell disponieren",
            source="human",
        )

    if idle:
        return DomainResult(
            domain="capacity",
            status=DomainStatus.OK,
            summary=f"{len(idle)} Maschine(n) frei · {len(open_same)} offene FA(s) gleiches Teil",
            details=details,
            source="system",
        )

    if online:
        return DomainResult(
            domain="capacity",
            status=DomainStatus.WARN,
            summary=f"Keine freie Maschine · {len(running)} aktiv · Backlog gleiches Teil {backlog_qty:g}",
            details=details,
            needs_human=True,
            question="Fertigungsslots gegen aktuelle Belegung abstimmen",
            source="human",
        )

    return DomainResult(
        domain="capacity",
        status=DomainStatus.BAD,
        summary="Keine Maschine online",
        details=details,
        needs_human=True,
        question="Verfügbarkeit der Maschinen klären",
        source="human",
    )


def _collapse(domains: list[DomainResult], requested_date: Optional[date]) -> PromiseResult:
    open_questions: list[dict[str, str]] = []
    blockers: list[str] = []
    for d in domains:
        # Quoter returns many offen[] items – surface each as a human question
        offen_list = d.details.get("offen") if isinstance(d.details, dict) else None
        if isinstance(offen_list, list) and offen_list:
            for item in offen_list:
                open_questions.append({"domain": d.domain, "question": str(item)})
        elif d.needs_human and d.question:
            open_questions.append({"domain": d.domain, "question": d.question})
        if d.status == DomainStatus.BAD:
            blockers.append(f"{d.domain}: {d.summary}")

    statuses = {d.domain: d.status for d in domains}
    hard = statuses.get("item") == DomainStatus.BAD or statuses.get("material") == DomainStatus.BAD
    soft = any(s == DomainStatus.WARN for s in statuses.values())
    unknown = any(s == DomainStatus.UNKNOWN for s in statuses.values())

    if hard:
        overall = DomainStatus.BAD
        can_promise = False
        confidence = "low"
    elif soft or unknown or open_questions:
        overall = DomainStatus.WARN
        can_promise = not hard and statuses.get("item") == DomainStatus.OK
        confidence = "medium" if not unknown else "low"
    else:
        overall = DomainStatus.OK
        can_promise = True
        confidence = "high"

    earliest = None
    mat = next((d for d in domains if d.domain == "material"), None)
    if mat and mat.details.get("open_pos"):
        dates = [p.get("due_date") for p in mat.details["open_pos"] if p.get("due_date")]
        if dates:
            earliest = min(dates)
    if requested_date and can_promise and overall == DomainStatus.OK:
        earliest = earliest or requested_date.isoformat()

    return PromiseResult(
        overall=overall,
        can_promise=can_promise,
        confidence=confidence,
        earliest_hint=earliest,
        blockers=blockers,
        domains=domains,
        open_questions=open_questions,
        evaluated_at=datetime.now(UTC),
    )


def _date_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]
