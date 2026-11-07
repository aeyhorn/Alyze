"""Extended SAP B1 read-only queries for the Sprint 005 analytics engine.

All statements are SELECT-only and strictly parameterized (no f-string SQL).
The MSSQL channel is read-only by convention and enforced by the SQLAlchemy
event listener in ``src/bdx/db/sap.py``.

Tables covered:
  WOR1  - Production order routing / operations (planned op times)
  OIVL  - Inventory value ledger (stock movements, current qty)
  OITW  - Item warehouse stock (current qty per warehouse)
  ORDR  - Sales / customer orders header
  RDR1  - Sales order line items
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

# ── WOR1 - Production order routing operations ───────────────────────────────
#
# Each OWOR can have multiple operations (WOR1 rows) with planned durations.
# PlannedQty = planned production qty; TotalTime + SetupTime in minutes.

WOR1_BY_DOCENTRY_SQL = text(
    """
    SELECT
        r.DocEntry          AS doc_entry,
        r.LineNum           AS line_num,
        r.VisOrder          AS vis_order,
        r.OcrCode           AS resource_code,
        r.OcrName           AS resource_name,
        r.WipAcct           AS wip_account,
        r.PlannedQty        AS planned_qty,
        r.SetupTime         AS setup_time_min,
        r.TotalTime         AS total_time_min,
        r.ActualSetupTime   AS actual_setup_time_min,
        r.ActualTotalTime   AS actual_total_time_min,
        r.ActualQty         AS actual_qty,
        r.CompDate          AS completed_date,
        r.Completed         AS is_completed
    FROM dbo.WOR1 r
    WHERE r.DocEntry = :doc_entry
    ORDER BY r.VisOrder
    """
)

WOR1_FOR_OPEN_ORDERS_SQL = text(
    """
    SELECT
        r.DocEntry          AS doc_entry,
        r.LineNum           AS line_num,
        r.VisOrder          AS vis_order,
        r.OcrCode           AS resource_code,
        r.OcrName           AS resource_name,
        r.PlannedQty        AS planned_qty,
        r.SetupTime         AS setup_time_min,
        r.TotalTime         AS total_time_min,
        r.ActualSetupTime   AS actual_setup_time_min,
        r.ActualTotalTime   AS actual_total_time_min,
        r.ActualQty         AS actual_qty,
        r.Completed         AS is_completed
    FROM dbo.WOR1 r
    INNER JOIN dbo.OWOR wo ON wo.DocEntry = r.DocEntry
    WHERE wo.Status IN ('P', 'R')
    ORDER BY r.DocEntry, r.VisOrder
    """
)


def fetch_routing_for_order(conn: Connection, doc_entry: int) -> list[dict[str, Any]]:
    """Return routing operations for a single production order."""
    result = conn.execute(WOR1_BY_DOCENTRY_SQL, {"doc_entry": doc_entry})
    return [dict(row._mapping) for row in result]


def fetch_routing_for_open_orders(conn: Connection) -> list[dict[str, Any]]:
    """Return routing operations for all open production orders."""
    result = conn.execute(WOR1_FOR_OPEN_ORDERS_SQL)
    return [dict(row._mapping) for row in result]


# ── OITW - Item warehouse stock (current quantities) ─────────────────────────

OITW_FOR_ITEMS_SQL = text(
    """
    SELECT
        w.ItemCode          AS item_code,
        w.WhsCode           AS warehouse_code,
        w.OnHand            AS qty_on_hand,
        w.IsCommited        AS qty_committed,
        w.OnOrder           AS qty_on_order,
        (w.OnHand - w.IsCommited) AS qty_available
    FROM dbo.OITW w
    INNER JOIN dbo.OWOR wo ON wo.ItemCode = w.ItemCode
    WHERE wo.Status IN ('P', 'R')
      AND w.OnHand > 0
    ORDER BY w.ItemCode, w.WhsCode
    """
)

OITW_BY_ITEMCODE_SQL = text(
    """
    SELECT
        w.ItemCode          AS item_code,
        w.WhsCode           AS warehouse_code,
        w.OnHand            AS qty_on_hand,
        w.IsCommited        AS qty_committed,
        w.OnOrder           AS qty_on_order,
        (w.OnHand - w.IsCommited) AS qty_available
    FROM dbo.OITW w
    WHERE w.ItemCode = :item_code
    ORDER BY w.WhsCode
    """
)


def fetch_stock_for_open_orders(conn: Connection) -> list[dict[str, Any]]:
    """Return warehouse stock for items referenced by open production orders."""
    result = conn.execute(OITW_FOR_ITEMS_SQL)
    return [dict(row._mapping) for row in result]


def fetch_stock_by_item(conn: Connection, item_code: str) -> list[dict[str, Any]]:
    """Return warehouse stock for a single item code."""
    result = conn.execute(OITW_BY_ITEMCODE_SQL, {"item_code": item_code})
    return [dict(row._mapping) for row in result]


# ── ORDR / RDR1 - Customer (sales) orders ────────────────────────────────────
# Allows tracing a production order back to the customer demand.

ORDR_OPEN_SQL = text(
    """
    SELECT
        o.DocEntry          AS doc_entry,
        o.DocNum            AS doc_num,
        o.CardCode          AS customer_code,
        o.CardName          AS customer_name,
        o.DocDate           AS doc_date,
        o.DocDueDate        AS due_date,
        o.DocStatus         AS doc_status,
        o.NumAtCard         AS customer_po_num
    FROM dbo.ORDR o
    WHERE o.DocStatus = 'O'           -- open sales orders only
    ORDER BY o.DocDueDate
    """
)

RDR1_FOR_SALES_ORDER_SQL = text(
    """
    SELECT
        l.DocEntry          AS sales_doc_entry,
        l.LineNum           AS line_num,
        l.ItemCode          AS item_code,
        l.Dscription        AS description,
        l.Quantity          AS quantity,
        l.OpenQty           AS open_qty,
        l.ShipDate          AS ship_date,
        l.BaseEntry         AS base_entry,
        l.BaseType          AS base_type
    FROM dbo.RDR1 l
    WHERE l.DocEntry = :doc_entry
    ORDER BY l.LineNum
    """
)

RDR1_DEMAND_FOR_ITEMS_SQL = text(
    """
    SELECT
        l.ItemCode          AS item_code,
        SUM(l.OpenQty)      AS total_open_qty,
        MIN(l.ShipDate)     AS earliest_ship_date,
        COUNT(DISTINCT l.DocEntry) AS sales_order_count
    FROM dbo.RDR1 l
    INNER JOIN dbo.ORDR o ON o.DocEntry = l.DocEntry
    WHERE o.DocStatus = 'O'
      AND l.OpenQty > 0
    GROUP BY l.ItemCode
    ORDER BY earliest_ship_date
    """
)


def fetch_open_sales_orders(conn: Connection) -> list[dict[str, Any]]:
    """Return all open customer sales order headers."""
    result = conn.execute(ORDR_OPEN_SQL)
    return [dict(row._mapping) for row in result]


def fetch_sales_order_lines(conn: Connection, sales_doc_entry: int) -> list[dict[str, Any]]:
    """Return line items for a single sales order."""
    result = conn.execute(RDR1_FOR_SALES_ORDER_SQL, {"doc_entry": sales_doc_entry})
    return [dict(row._mapping) for row in result]


def fetch_demand_summary_by_item(conn: Connection) -> list[dict[str, Any]]:
    """Return open customer demand aggregated per item code.

    Useful for identifying items where production orders may be insufficient
    to cover open customer commitments.
    """
    result = conn.execute(RDR1_DEMAND_FOR_ITEMS_SQL)
    return [dict(row._mapping) for row in result]
