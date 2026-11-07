"""Procurement and inventory KPIs (Sprint 005 extension).

These KPIs combine SAP data (read via MSSQL at analytics time) with the
PostgreSQL event store to correlate inventory levels, purchase orders, and
goods receipts with production times and delivery lead times.

All compute functions accept pre-fetched SAP rows as plain dicts so they
can be unit-tested without a real SAP connection.

KPIs produced:
  material_coverage_pct      - open FA demand covered by available stock (%)
  critical_items_count       - items where demand > stock AND no open PO covers the gap
  po_lead_time_days          - actual PO -> GR lead time per supplier (median, days)
  supplier_otd_rate          - supplier on-time delivery rate (%)
  po_overdue_count           - open PO lines whose promised date has passed
  gr_delay_days              - median days late for overdue GR receipts
  stock_coverage_days        - on-hand stock / avg daily consumption (days)
"""
from __future__ import annotations

import statistics
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from bdx.analytics.kpis import DEFAULT_WINDOW_HOURS, KpiResult, _percentile
from bdx.models.events import OrderState

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# 1. Material coverage - can open FAs be started with current stock?
# ---------------------------------------------------------------------------

def compute_material_coverage(
    session: Session,
    stock_rows: list[dict[str, Any]],
    open_po_rows: list[dict[str, Any]],
    window_hours: int = DEFAULT_WINDOW_HOURS,
) -> list[KpiResult]:
    """Materialdeckung: % of open FA remaining demand covered by available stock.

    Args:
        stock_rows:   rows from fetch_stock_for_open_orders (OITW)
        open_po_rows: rows from fetch_open_po_qty_by_item   (POR1 aggregated)
    """
    # Build available stock dict: item_code -> total qty_available across warehouses
    stock: dict[str, float] = {}
    for row in stock_rows:
        ic = row["item_code"]
        stock[ic] = stock.get(ic, 0.0) + float(row.get("qty_available") or 0.0)

    # Build open PO incoming qty: item_code -> total_open_po_qty
    incoming: dict[str, float] = {}
    for row in open_po_rows:
        ic = row["item_code"]
        incoming[ic] = float(row.get("total_open_po_qty") or 0.0)

    # Open FA remaining demand: item_code -> total needed
    open_orders = session.execute(
        select(OrderState.item_code, OrderState.planned_qty, OrderState.completed_qty)
        .where(OrderState.status.in_(["P", "R"]))
    ).all()

    demand: dict[str, float] = {}
    for item_code, planned, completed in open_orders:
        remaining = max(0.0, float(planned or 0) - float(completed or 0))
        demand[item_code] = demand.get(item_code, 0.0) + remaining

    if not demand:
        return []

    results: list[KpiResult] = []
    critical_items: list[str] = []
    total_demand = total_covered = 0.0

    for item_code, needed in demand.items():
        if needed <= 0:
            continue
        available = stock.get(item_code, 0.0)
        po_incoming = incoming.get(item_code, 0.0)
        covered = min(needed, available)
        total_demand += needed
        total_covered += covered

        coverage_pct = round(100.0 * covered / needed, 2) if needed > 0 else 100.0
        results.append(KpiResult(
            metric_name="material_coverage_pct",
            dimension="item_group",
            dimension_value=item_code,
            value=coverage_pct,
            window_hours=window_hours,
            extra={
                "demand": round(needed, 3),
                "available": round(available, 3),
                "po_incoming": round(po_incoming, 3),
                "gap": round(max(0.0, needed - available - po_incoming), 3),
            },
        ))

        # Item is "critical" when stock + open PO does not cover demand
        if available + po_incoming < needed:
            critical_items.append(item_code)

    # Global coverage
    if total_demand > 0:
        global_pct = round(100.0 * total_covered / total_demand, 2)
        results.append(KpiResult(
            metric_name="material_coverage_pct",
            dimension="global",
            dimension_value=None,
            value=global_pct,
            window_hours=window_hours,
            extra={"items_checked": len(demand), "critical_items": critical_items[:50]},
        ))

    # Critical items count as a separate KPI
    results.append(KpiResult(
        metric_name="critical_items_count",
        dimension="global",
        dimension_value=None,
        value=float(len(critical_items)),
        window_hours=window_hours,
        extra={"items": critical_items[:50]},
    ))

    return results


# ---------------------------------------------------------------------------
# 2. PO lead time (actual) and supplier on-time delivery
# ---------------------------------------------------------------------------

def compute_po_lead_time(
    lead_time_rows: list[dict[str, Any]],
    window_hours: int = DEFAULT_WINDOW_HOURS,
) -> list[KpiResult]:
    """Tatsaechliche Lieferzeit (PO order date -> GR date) per supplier.

    Args:
        lead_time_rows: rows from fetch_gr_lead_times (OPDN/PDN1 joined to OPOR)
    """
    by_supplier: dict[str, list[float]] = {}
    all_days: list[float] = []

    for row in lead_time_rows:
        days = row.get("actual_lead_time_days")
        if days is None or days < 0:
            continue
        supplier = row.get("supplier_code") or "unknown"
        by_supplier.setdefault(supplier, []).append(float(days))
        all_days.append(float(days))

    results: list[KpiResult] = []

    for supplier, days_list in by_supplier.items():
        results.append(KpiResult(
            metric_name="po_lead_time_days",
            dimension="supplier",
            dimension_value=supplier,
            value=round(statistics.median(days_list), 1),
            window_hours=window_hours,
            extra={
                "p95": round(_percentile(days_list, 95), 1),
                "sample_count": len(days_list),
                "supplier_name": next(
                    (r.get("supplier_name") for r in lead_time_rows if r.get("supplier_code") == supplier),
                    supplier,
                ),
            },
        ))

    if all_days:
        results.append(KpiResult(
            metric_name="po_lead_time_days",
            dimension="global",
            dimension_value=None,
            value=round(statistics.median(all_days), 1),
            window_hours=window_hours,
            extra={"p95": round(_percentile(all_days, 95), 1), "sample_count": len(all_days)},
        ))

    return results


def compute_supplier_otd(
    otd_rows: list[dict[str, Any]],
    window_hours: int = DEFAULT_WINDOW_HOURS,
) -> list[KpiResult]:
    """Liefertermintreue der Lieferanten (supplier on-time delivery rate %).

    Args:
        otd_rows: rows from fetch_supplier_otd
    """
    results: list[KpiResult] = []
    total_lines = total_on_time = 0

    for row in otd_rows:
        lines = int(row.get("total_lines") or 0)
        on_time = int(row.get("on_time_lines") or 0)
        if lines <= 0:
            continue
        total_lines += lines
        total_on_time += on_time
        supplier = row.get("supplier_code") or "unknown"
        rate = round(100.0 * on_time / lines, 2)
        results.append(KpiResult(
            metric_name="supplier_otd_rate",
            dimension="supplier",
            dimension_value=supplier,
            value=rate,
            window_hours=window_hours,
            extra={
                "on_time_lines": on_time,
                "total_lines": lines,
                "avg_delay_days": round(float(row.get("avg_delay_days") or 0), 1),
                "supplier_name": row.get("supplier_name") or supplier,
            },
        ))

    if total_lines > 0:
        global_rate = round(100.0 * total_on_time / total_lines, 2)
        results.append(KpiResult(
            metric_name="supplier_otd_rate",
            dimension="global",
            dimension_value=None,
            value=global_rate,
            window_hours=window_hours,
            extra={"on_time_lines": total_on_time, "total_lines": total_lines},
        ))

    return results


# ---------------------------------------------------------------------------
# 3. Overdue purchase order lines
# ---------------------------------------------------------------------------

def compute_po_overdue(
    overdue_rows: list[dict[str, Any]],
    window_hours: int = DEFAULT_WINDOW_HOURS,
) -> list[KpiResult]:
    """Verzoegerte Bestellungen: open PO lines past their promised delivery date.

    Args:
        overdue_rows: rows from fetch_overdue_po_lines
    """
    if not overdue_rows:
        return [KpiResult(
            metric_name="po_overdue_count",
            dimension="global",
            dimension_value=None,
            value=0.0,
            window_hours=window_hours,
        )]

    # Per supplier counts
    by_supplier: dict[str, int] = {}
    delays: list[float] = []

    for row in overdue_rows:
        supplier = row.get("supplier_code") or "unknown"
        by_supplier[supplier] = by_supplier.get(supplier, 0) + 1
        d = row.get("days_overdue")
        if d is not None:
            delays.append(float(d))

    results: list[KpiResult] = []
    for supplier, count in by_supplier.items():
        results.append(KpiResult(
            metric_name="po_overdue_count",
            dimension="supplier",
            dimension_value=supplier,
            value=float(count),
            window_hours=window_hours,
        ))

    median_delay = round(statistics.median(delays), 1) if delays else 0.0
    results.append(KpiResult(
        metric_name="po_overdue_count",
        dimension="global",
        dimension_value=None,
        value=float(len(overdue_rows)),
        window_hours=window_hours,
        extra={"median_delay_days": median_delay, "max_delay_days": round(max(delays), 1) if delays else 0},
    ))

    # GR delay as its own metric (how late are overdue deliveries?)
    if delays:
        results.append(KpiResult(
            metric_name="gr_delay_days",
            dimension="global",
            dimension_value=None,
            value=round(statistics.median(delays), 1),
            window_hours=window_hours,
            extra={"p95": round(_percentile(delays, 95), 1), "count": len(delays)},
        ))

    return results


# ---------------------------------------------------------------------------
# 4. Stock coverage days
# ---------------------------------------------------------------------------

def compute_stock_coverage(
    stock_rows: list[dict[str, Any]],
    consumption_rows: list[dict[str, Any]],
    window_hours: int = DEFAULT_WINDOW_HOURS,
) -> list[KpiResult]:
    """Lagerreichweite: on-hand stock / avg daily consumption (days).

    Args:
        stock_rows:       rows from fetch_stock_for_open_orders (OITW)
        consumption_rows: rows from fetch_item_consumption (OIVL)
    """
    window_days = max(1, window_hours / 24)

    # Total on-hand per item across all warehouses
    on_hand: dict[str, float] = {}
    for row in stock_rows:
        ic = row["item_code"]
        on_hand[ic] = on_hand.get(ic, 0.0) + max(0.0, float(row.get("qty_on_hand") or 0.0))

    # Avg daily consumption
    daily_consumption: dict[str, float] = {}
    for row in consumption_rows:
        issued = float(row.get("total_issued_qty") or 0.0)
        if issued > 0:
            ic = row["item_code"]
            daily_consumption[ic] = issued / window_days

    results: list[KpiResult] = []
    all_coverage: list[float] = []

    for item_code, stock_qty in on_hand.items():
        avg_daily = daily_consumption.get(item_code, 0.0)
        if avg_daily <= 0:
            continue  # No consumption -> infinite coverage, skip
        coverage = stock_qty / avg_daily
        all_coverage.append(coverage)
        results.append(KpiResult(
            metric_name="stock_coverage_days",
            dimension="item_group",
            dimension_value=item_code,
            value=round(coverage, 1),
            window_hours=window_hours,
            extra={
                "on_hand": round(stock_qty, 3),
                "avg_daily_consumption": round(avg_daily, 4),
            },
        ))

    if all_coverage:
        results.append(KpiResult(
            metric_name="stock_coverage_days",
            dimension="global",
            dimension_value=None,
            value=round(statistics.median(all_coverage), 1),
            window_hours=window_hours,
            extra={"p10": round(_percentile(all_coverage, 10), 1), "items_tracked": len(all_coverage)},
        ))

    return results


# ---------------------------------------------------------------------------
# Top-level runner (called by analytics collector when SAP connection available)
# ---------------------------------------------------------------------------

def compute_all_procurement_kpis(
    session: Session,
    sap_conn: Any,  # SQLAlchemy Connection to MSSQL
    window_hours: int = DEFAULT_WINDOW_HOURS,
) -> list[KpiResult]:
    """Fetch SAP procurement data and compute all procurement KPIs.

    ``sap_conn`` is a live SQLAlchemy connection to the SAP SQL Server.
    Returns an empty list if the connection is None (SAP not configured).
    """
    if sap_conn is None:
        logger.info("procurement_kpis.skipped", reason="no_sap_connection")
        return []

    from bdx.db.queries_sap_extended import (
        fetch_gr_lead_times,
        fetch_item_consumption,
        fetch_open_po_qty_by_item,
        fetch_overdue_po_lines,
        fetch_stock_for_open_orders,
        fetch_supplier_otd,
    )

    since_date = (datetime.now(UTC) - timedelta(hours=window_hours)).strftime("%Y-%m-%d")

    results: list[KpiResult] = []
    try:
        stock_rows = fetch_stock_for_open_orders(sap_conn)
        open_po_rows = fetch_open_po_qty_by_item(sap_conn)
        lead_time_rows = fetch_gr_lead_times(sap_conn, since_date)
        otd_rows = fetch_supplier_otd(sap_conn, since_date)
        overdue_rows = fetch_overdue_po_lines(sap_conn)
        consumption_rows = fetch_item_consumption(sap_conn, since_date)

        results.extend(compute_material_coverage(session, stock_rows, open_po_rows, window_hours))
        results.extend(compute_po_lead_time(lead_time_rows, window_hours))
        results.extend(compute_supplier_otd(otd_rows, window_hours))
        results.extend(compute_po_overdue(overdue_rows, window_hours))
        results.extend(compute_stock_coverage(stock_rows, consumption_rows, window_hours))

        logger.info("procurement_kpis.computed", count=len(results))
    except Exception as exc:
        logger.warning("procurement_kpis.failed", error=str(exc))

    return results
