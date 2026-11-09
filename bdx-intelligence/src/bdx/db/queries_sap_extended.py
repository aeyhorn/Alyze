"""Extended SAP B1 read-only queries for the Sprint 005 analytics engine.

All statements are SELECT-only and strictly parameterized (no f-string SQL).
The MSSQL channel is read-only by convention and enforced by the SQLAlchemy
event listener in ``src/bdx/db/sap.py``.

Tables covered:
  WOR1  - Production order component lines (ItemCode, PlannedQty, IssuedQty)
  OIVL  - Inventory value ledger (stock movements, current qty)
  OITW  - Item warehouse stock (current qty per warehouse)
  ORDR  - Sales / customer orders header
  RDR1  - Sales order line items
  OPOR  - Purchase order headers (Einkaufsbestellung)
  POR1  - Purchase order line items
  OPDN  - Goods receipt PO headers (Wareneingang)
  PDN1  - Goods receipt PO line items
  OIVL  - Inventory value ledger (consumption/movements)
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

# ── WOR1 - Production order component lines ──────────────────────────────────
#
# In SAP Business One, WOR1 is the component list of a production order, not a
# routing with setup times. ItemType 4 = inventory item, 290 = resource.
# Remaining demand is PlannedQty - IssuedQty.

_WOR1_COMPONENT_COLUMNS = """
        r.DocEntry          AS doc_entry,
        r.LineNum           AS line_num,
        r.VisOrder          AS vis_order,
        r.ItemCode          AS item_code,
        r.ItemType          AS item_type,
        r.PlannedQty        AS planned_qty,
        r.IssuedQty         AS issued_qty,
        r.BaseQty           AS base_qty,
        r.wareHouse         AS warehouse_code,
        r.IssueType         AS issue_type
"""

WOR1_BY_DOCENTRY_SQL = text(
    f"""
    SELECT {_WOR1_COMPONENT_COLUMNS}
    FROM dbo.WOR1 r
    WHERE r.DocEntry = :doc_entry
      AND r.ItemType = 4
    ORDER BY r.VisOrder
    """
)

WOR1_FOR_OPEN_ORDERS_SQL = text(
    f"""
    SELECT {_WOR1_COMPONENT_COLUMNS}
    FROM dbo.WOR1 r
    INNER JOIN dbo.OWOR wo ON wo.DocEntry = r.DocEntry
    WHERE wo.Status IN ('P', 'R')
      AND r.ItemType = 4
    ORDER BY r.DocEntry, r.VisOrder
    """
)


def fetch_components_for_order(conn: Connection, doc_entry: int) -> list[dict[str, Any]]:
    """Return component lines for a single production order."""
    result = conn.execute(WOR1_BY_DOCENTRY_SQL, {"doc_entry": doc_entry})
    return [dict(row._mapping) for row in result]


def fetch_components_for_open_orders(conn: Connection) -> list[dict[str, Any]]:
    """Return component lines for all open production orders."""
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
    """Return warehouse stock for finished items referenced by open production orders."""
    result = conn.execute(OITW_FOR_ITEMS_SQL)
    return [dict(row._mapping) for row in result]


OITW_FOR_COMPONENTS_SQL = text(
    """
    SELECT
        w.ItemCode          AS item_code,
        w.WhsCode           AS warehouse_code,
        w.OnHand            AS qty_on_hand,
        w.IsCommited        AS qty_committed,
        w.OnOrder           AS qty_on_order,
        (w.OnHand - w.IsCommited) AS qty_available
    FROM dbo.OITW w
    WHERE w.ItemCode IN (
        SELECT DISTINCT r.ItemCode
        FROM dbo.WOR1 r
        INNER JOIN dbo.OWOR wo ON wo.DocEntry = r.DocEntry
        WHERE wo.Status IN ('P', 'R')
          AND r.ItemType = 4
    )
    ORDER BY w.ItemCode, w.WhsCode
    """
)


def fetch_stock_for_components(conn: Connection) -> list[dict[str, Any]]:
    """Return warehouse stock for components of open production orders.

    Includes zero on-hand rows so a missing quantity is visible as zero
    available stock rather than a missing item.
    """
    result = conn.execute(OITW_FOR_COMPONENTS_SQL)
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


# -- OPOR / POR1 - Purchase orders (Einkaufsbestellung) -----------------------

OPOR_OPEN_SQL = text(
    """
    SELECT
        p.DocEntry          AS doc_entry,
        p.DocNum            AS doc_num,
        p.CardCode          AS supplier_code,
        p.CardName          AS supplier_name,
        p.DocDate           AS order_date,
        p.DocDueDate        AS due_date,
        p.DocStatus         AS doc_status,
        p.Comments          AS comments
    FROM dbo.OPOR p
    WHERE p.DocStatus = 'O'
    ORDER BY p.DocDueDate
    """
)

POR1_OPEN_SQL = text(
    """
    SELECT
        l.DocEntry          AS po_doc_entry,
        l.LineNum           AS line_num,
        l.ItemCode          AS item_code,
        l.Dscription        AS description,
        l.Quantity          AS quantity,
        l.OpenQty           AS open_qty,
        l.Price             AS unit_price,
        l.ShipDate          AS promised_date,
        l.InvQty            AS inventory_qty,
        p.CardCode          AS supplier_code,
        p.CardName          AS supplier_name,
        p.DocDate           AS order_date,
        p.DocDueDate        AS po_due_date
    FROM dbo.POR1 l
    INNER JOIN dbo.OPOR p ON p.DocEntry = l.DocEntry
    WHERE p.DocStatus = 'O'
      AND l.OpenQty > 0
    ORDER BY l.ShipDate, l.ItemCode
    """
)

# Open PO qty by item - for material coverage gap analysis
POR1_OPEN_QTY_BY_ITEM_SQL = text(
    """
    SELECT
        l.ItemCode              AS item_code,
        SUM(l.OpenQty)          AS total_open_po_qty,
        MIN(l.ShipDate)         AS earliest_delivery,
        COUNT(DISTINCT l.DocEntry) AS po_count
    FROM dbo.POR1 l
    INNER JOIN dbo.OPOR p ON p.DocEntry = l.DocEntry
    WHERE p.DocStatus = 'O'
      AND l.OpenQty > 0
    GROUP BY l.ItemCode
    ORDER BY l.ItemCode
    """
)

# Overdue open PO lines - promised date already past
OPOR_OVERDUE_SQL = text(
    """
    SELECT
        l.ItemCode          AS item_code,
        p.CardCode          AS supplier_code,
        p.CardName          AS supplier_name,
        l.ShipDate          AS promised_date,
        l.OpenQty           AS open_qty,
        DATEDIFF(day, l.ShipDate, GETDATE()) AS days_overdue,
        p.DocEntry          AS po_doc_entry,
        p.DocNum            AS po_doc_num
    FROM dbo.POR1 l
    INNER JOIN dbo.OPOR p ON p.DocEntry = l.DocEntry
    WHERE p.DocStatus = 'O'
      AND l.OpenQty > 0
      AND l.ShipDate < CAST(GETDATE() AS DATE)
    ORDER BY days_overdue DESC, l.ItemCode
    """
)


def fetch_open_purchase_orders(conn: Connection) -> list[dict[str, Any]]:
    """Return all open purchase order headers."""
    result = conn.execute(OPOR_OPEN_SQL)
    return [dict(row._mapping) for row in result]


def fetch_open_po_lines(conn: Connection) -> list[dict[str, Any]]:
    """Return all open purchase order lines with supplier info."""
    result = conn.execute(POR1_OPEN_SQL)
    return [dict(row._mapping) for row in result]


def fetch_open_po_qty_by_item(conn: Connection) -> list[dict[str, Any]]:
    """Return open PO quantities aggregated per item code."""
    result = conn.execute(POR1_OPEN_QTY_BY_ITEM_SQL)
    return [dict(row._mapping) for row in result]


def fetch_overdue_po_lines(conn: Connection) -> list[dict[str, Any]]:
    """Return open PO lines whose promised delivery date has passed."""
    result = conn.execute(OPOR_OVERDUE_SQL)
    return [dict(row._mapping) for row in result]


# -- OPDN / PDN1 - Goods receipts (Wareneingang) ------------------------------

OPDN_RECENT_SQL = text(
    """
    SELECT
        g.DocEntry          AS doc_entry,
        g.DocNum            AS doc_num,
        g.CardCode          AS supplier_code,
        g.CardName          AS supplier_name,
        g.DocDate           AS receipt_date,
        g.Comments          AS comments
    FROM dbo.OPDN g
    WHERE g.DocDate >= :since_date
    ORDER BY g.DocDate DESC
    """
)

PDN1_RECENT_SQL = text(
    """
    SELECT
        l.DocEntry          AS gr_doc_entry,
        l.ItemCode          AS item_code,
        l.Dscription        AS description,
        l.Quantity          AS received_qty,
        l.Price             AS unit_price,
        l.BaseEntry         AS base_po_entry,   -- links to OPOR.DocEntry
        l.BaseType          AS base_type,
        g.DocDate           AS receipt_date,
        g.CardCode          AS supplier_code,
        g.CardName          AS supplier_name
    FROM dbo.PDN1 l
    INNER JOIN dbo.OPDN g ON g.DocEntry = l.DocEntry
    WHERE g.DocDate >= :since_date
    ORDER BY g.DocDate DESC, l.ItemCode
    """
)

# Actual lead time per item: days between PO date and GR date, for closed POs
GR_LEAD_TIME_SQL = text(
    """
    SELECT
        l.ItemCode              AS item_code,
        p.CardCode              AS supplier_code,
        p.CardName              AS supplier_name,
        p.DocDate               AS order_date,
        g.DocDate               AS receipt_date,
        DATEDIFF(day, p.DocDate, g.DocDate)  AS actual_lead_time_days,
        l2.ShipDate             AS promised_date,
        DATEDIFF(day, l2.ShipDate, g.DocDate) AS delivery_delay_days
    FROM dbo.PDN1 l
    INNER JOIN dbo.OPDN g ON g.DocEntry = l.DocEntry
    -- Join back to the source PO line via BaseEntry / BaseType
    LEFT JOIN dbo.POR1 l2 ON l2.DocEntry = l.BaseEntry AND l.BaseType = 22
    LEFT JOIN dbo.OPOR p ON p.DocEntry = l.BaseEntry AND l.BaseType = 22
    WHERE g.DocDate >= :since_date
      AND l.BaseType = 22   -- 22 = Purchase Order
      AND p.DocEntry IS NOT NULL
    ORDER BY g.DocDate DESC
    """
)

# Supplier on-time rate: % of GR lines where receipt_date <= promised_date
SUPPLIER_OTD_SQL = text(
    """
    SELECT
        p.CardCode              AS supplier_code,
        p.CardName              AS supplier_name,
        COUNT(*)                AS total_lines,
        SUM(CASE WHEN DATEDIFF(day, l2.ShipDate, g.DocDate) <= 0 THEN 1 ELSE 0 END)
                                AS on_time_lines,
        AVG(CAST(DATEDIFF(day, l2.ShipDate, g.DocDate) AS FLOAT))
                                AS avg_delay_days
    FROM dbo.PDN1 l
    INNER JOIN dbo.OPDN g ON g.DocEntry = l.DocEntry
    LEFT JOIN dbo.POR1 l2 ON l2.DocEntry = l.BaseEntry AND l.BaseType = 22
    LEFT JOIN dbo.OPOR p ON p.DocEntry = l.BaseEntry AND l.BaseType = 22
    WHERE g.DocDate >= :since_date
      AND l.BaseType = 22
      AND p.DocEntry IS NOT NULL
      AND l2.ShipDate IS NOT NULL
    GROUP BY p.CardCode, p.CardName
    ORDER BY avg_delay_days DESC
    """
)


def fetch_recent_goods_receipts(conn: Connection, since_date: str) -> list[dict[str, Any]]:
    """Return goods receipt headers since since_date (YYYY-MM-DD)."""
    result = conn.execute(OPDN_RECENT_SQL, {"since_date": since_date})
    return [dict(row._mapping) for row in result]


def fetch_recent_gr_lines(conn: Connection, since_date: str) -> list[dict[str, Any]]:
    """Return goods receipt lines with supplier info since since_date."""
    result = conn.execute(PDN1_RECENT_SQL, {"since_date": since_date})
    return [dict(row._mapping) for row in result]


def fetch_gr_lead_times(conn: Connection, since_date: str) -> list[dict[str, Any]]:
    """Return actual lead time (PO date -> GR date) per item/supplier pair."""
    result = conn.execute(GR_LEAD_TIME_SQL, {"since_date": since_date})
    return [dict(row._mapping) for row in result]


def fetch_supplier_otd(conn: Connection, since_date: str) -> list[dict[str, Any]]:
    """Return supplier on-time delivery rate since since_date."""
    result = conn.execute(SUPPLIER_OTD_SQL, {"since_date": since_date})
    return [dict(row._mapping) for row in result]


# -- OIVL - Inventory value ledger (consumption movements) -------------------

OIVL_CONSUMPTION_SQL = text(
    """
    SELECT
        v.ItemCode          AS item_code,
        SUM(ABS(v.InQty - v.OutQty))  AS total_movement_qty,
        SUM(CASE WHEN v.OutQty > 0 THEN v.OutQty ELSE 0 END) AS total_issued_qty,
        COUNT(*)            AS movement_count,
        MIN(v.DocDate)      AS first_movement,
        MAX(v.DocDate)      AS last_movement
    FROM dbo.OIVL v
    WHERE v.DocDate >= :since_date
      AND v.TransType IN (60, 59, 202)  -- 60=issue to production, 59=receipt, 202=WO issue
    GROUP BY v.ItemCode
    ORDER BY total_issued_qty DESC
    """
)


def fetch_item_consumption(conn: Connection, since_date: str) -> list[dict[str, Any]]:
    """Return item consumption (issues to production) aggregated per item.

    Used to compute avg daily consumption for stock coverage days calculation.
    """
    result = conn.execute(OIVL_CONSUMPTION_SQL, {"since_date": since_date})
    return [dict(row._mapping) for row in result]
