"""Fixed parameterized SQL queries against SAP Business One tables.

Only SELECT statements are defined here.  All queries are parameterized to
prevent SQL injection.  Table/column names follow SAP B1 conventions.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Sequence

from sqlalchemy import text
from sqlalchemy.engine import Connection

# NOTE: The custom fields U_Type / U_Priority (OWOR) and U_BDX_Machine (OITM)
# from docs/SAP_MAPPING.md do not exist in the Leisinger company databases
# (verified against DEV_SBO_LEISINGER, 2026-11-07).  They are selected as NULL
# placeholders so the model shape stays stable until the UDFs are created in SAP.

# ── OWOR – Production/Work Orders ────────────────────────────────────────────
#
# OWOR.Status codes: P = Planned, R = Released, L = Closed, C = Cancelled.

_OWOR_COLUMNS = """
        wo.DocEntry          AS doc_entry,
        wo.DocNum            AS doc_num,
        wo.Status            AS status,
        wo.ItemCode          AS item_code,
        wo.PlannedQty        AS planned_qty,
        wo.CmpltQty          AS completed_qty,
        wo.RjctQty           AS rejected_qty,
        wo.DueDate           AS due_date,
        wo.StartDate         AS start_date,
        wo.PostDate          AS post_date,
        CAST(NULL AS NVARCHAR(50)) AS u_type,
        CAST(NULL AS NVARCHAR(50)) AS u_priority,
        wo.Comments          AS comments,
        wo.UpdateDate        AS update_date,
        wo.UpdateTS          AS update_ts
"""

OWOR_OPEN_ORDERS_SQL = text(
    f"""
    SELECT {_OWOR_COLUMNS}
    FROM dbo.OWOR wo
    WHERE wo.Status IN ('P', 'R')       -- Planned + Released = open
    ORDER BY wo.DocEntry
    """
)

OWOR_SNAPSHOT_SQL = text(
    f"""
    SELECT {_OWOR_COLUMNS}
    FROM dbo.OWOR wo
    ORDER BY wo.DocEntry
    """
)

# Incremental read: every open order plus everything created or updated since
# :since (date).  Orders that were closed/cancelled since the last run carry a
# fresh UpdateDate and are therefore included; the collector additionally
# re-reads open orders from its own state that vanished from this result.
OWOR_INCREMENTAL_SQL = text(
    f"""
    SELECT {_OWOR_COLUMNS}
    FROM dbo.OWOR wo
    WHERE wo.Status IN ('P', 'R')
       OR wo.UpdateDate >= :since
       OR wo.CreateDate >= :since
    ORDER BY wo.DocEntry
    """
)

OWOR_BY_DOCENTRY_SQL = text(
    f"""
    SELECT {_OWOR_COLUMNS}
    FROM dbo.OWOR wo
    WHERE wo.DocEntry = :doc_entry
    """
)

OWOR_BY_DOCENTRIES_SQL_TEMPLATE = f"""
    SELECT {_OWOR_COLUMNS}
    FROM dbo.OWOR wo
    WHERE wo.DocEntry IN ({{placeholders}})
"""

# ── OITM – Item Master Data ──────────────────────────────────────────────────

OITM_FOR_ORDERS_SQL = text(
    """
    SELECT
        it.ItemCode          AS item_code,
        it.ItemName          AS item_name,
        it.ItmsGrpCod        AS item_group_code,
        it.InvntItem         AS inventory_item,
        it.PrfrmMrpStep      AS mrp_item,
        CAST(NULL AS NVARCHAR(50)) AS machine_id
    FROM dbo.OITM it
    WHERE it.ItemCode IN (
        SELECT DISTINCT wo.ItemCode FROM dbo.OWOR wo WHERE wo.Status IN ('P', 'R')
    )
    """
)

OITM_BY_ITEMCODE_SQL = text(
    """
    SELECT
        it.ItemCode, it.ItemName, it.ItmsGrpCod,
        it.InvntItem, it.PrfrmMrpStep,
        CAST(NULL AS NVARCHAR(50)) AS U_BDX_Machine
    FROM dbo.OITM it
    WHERE it.ItemCode = :item_code
    """
)


# ── Query helpers ─────────────────────────────────────────────────────────────

def fetch_open_orders(conn: Connection) -> list[dict[str, Any]]:
    """Return all open production orders as a list of dicts."""
    result = conn.execute(OWOR_OPEN_ORDERS_SQL)
    return [dict(row._mapping) for row in result]


def fetch_all_orders_snapshot(conn: Connection) -> list[dict[str, Any]]:
    """Return a full snapshot of all production orders (for change detection)."""
    result = conn.execute(OWOR_SNAPSHOT_SQL)
    return [dict(row._mapping) for row in result]


def fetch_orders_incremental(conn: Connection, since: date) -> list[dict[str, Any]]:
    """Return all open orders plus orders created/updated on or after *since*."""
    result = conn.execute(OWOR_INCREMENTAL_SQL, {"since": since})
    return [dict(row._mapping) for row in result]


def fetch_order_by_docentry(conn: Connection, doc_entry: int) -> dict[str, Any] | None:
    """Return a single production order by DocEntry, or None."""
    result = conn.execute(OWOR_BY_DOCENTRY_SQL, {"doc_entry": doc_entry})
    row = result.fetchone()
    return dict(row._mapping) if row else None


def fetch_orders_by_docentries(conn: Connection, doc_entries: Sequence[int]) -> list[dict[str, Any]]:
    """Return the given orders by DocEntry (chunked, parameterized)."""
    rows: list[dict[str, Any]] = []
    entries = [int(d) for d in doc_entries]
    for i in range(0, len(entries), 500):
        chunk = entries[i : i + 500]
        params = {f"d{j}": d for j, d in enumerate(chunk)}
        placeholders = ", ".join(f":{k}" for k in params)
        stmt = text(OWOR_BY_DOCENTRIES_SQL_TEMPLATE.format(placeholders=placeholders))
        rows.extend(dict(r._mapping) for r in conn.execute(stmt, params))
    return rows


def fetch_items_for_open_orders(conn: Connection) -> list[dict[str, Any]]:
    """Return item master data for all items referenced by open orders."""
    result = conn.execute(OITM_FOR_ORDERS_SQL)
    return [dict(row._mapping) for row in result]


def fetch_item_by_code(conn: Connection, item_code: str) -> dict[str, Any] | None:
    """Return a single item by ItemCode, or None."""
    result = conn.execute(OITM_BY_ITEMCODE_SQL, {"item_code": item_code})
    row = result.fetchone()
    return dict(row._mapping) if row else None


# ── Q2P – Inventory / Purchasing / BOM / Price (read-only) ───────────────────
# These tables need SELECT grants (see docs/sql/create_bdx_readonly.sql).
# Helpers catch permission / missing-object errors so the API can degrade.

OITW_BY_ITEM_SQL = text(
    """
    SELECT
        w.ItemCode   AS item_code,
        w.WhsCode    AS warehouse,
        w.OnHand     AS on_hand,
        w.IsCommited AS is_committed,
        w.OnOrder    AS on_order
    FROM dbo.OITW w
    WHERE w.ItemCode = :item_code
    ORDER BY w.WhsCode
    """
)

OPOR_OPEN_LINES_BY_ITEM_SQL = text(
    """
    SELECT
        h.DocEntry   AS doc_entry,
        h.DocNum     AS doc_num,
        h.CardCode   AS vendor_code,
        h.CardName   AS vendor_name,
        h.DocDueDate AS due_date,
        l.ItemCode   AS item_code,
        l.Quantity   AS quantity,
        l.OpenQty    AS open_qty,
        l.Price      AS price,
        l.LineTotal  AS line_total,
        l.ShipDate   AS ship_date
    FROM dbo.OPOR h
    INNER JOIN dbo.POR1 l ON l.DocEntry = h.DocEntry
    WHERE h.DocStatus = 'O'
      AND l.LineStatus = 'O'
      AND l.ItemCode = :item_code
    ORDER BY h.DocDueDate, h.DocNum
    """
)

OITT_BOM_COMPONENTS_SQL = text(
    """
    SELECT
        t.Code       AS parent_code,
        c.Code       AS component_code,
        c.Quantity   AS quantity,
        c.Warehouse  AS warehouse,
        it.ItemName  AS component_name,
        it.InvntItem AS inventory_item
    FROM dbo.OITT t
    INNER JOIN dbo.ITT1 c ON c.Father = t.Code
    LEFT JOIN dbo.OITM it ON it.ItemCode = c.Code
    WHERE t.Code = :item_code
    ORDER BY c.Code
    """
)

ITM1_PRICES_SQL = text(
    """
    SELECT
        p.ItemCode  AS item_code,
        p.PriceList AS price_list,
        p.Price     AS price,
        pl.ListName AS list_name
    FROM dbo.ITM1 p
    LEFT JOIN dbo.OPLN pl ON pl.ListNum = p.PriceList
    WHERE p.ItemCode = :item_code
      AND p.Price IS NOT NULL
      AND p.Price > 0
    ORDER BY p.PriceList
    """
)


def _safe_fetch(conn: Connection, stmt: Any, params: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    """Execute *stmt*; on permission/object errors return ([], error_message)."""
    try:
        result = conn.execute(stmt, params)
        return [dict(row._mapping) for row in result], None
    except Exception as exc:  # noqa: BLE001 – degrade gracefully for missing grants
        return [], str(exc)


def fetch_warehouse_stock(conn: Connection, item_code: str) -> tuple[list[dict[str, Any]], str | None]:
    """Return OITW rows for *item_code* (on-hand / committed / on-order)."""
    return _safe_fetch(conn, OITW_BY_ITEM_SQL, {"item_code": item_code})


def fetch_open_purchase_lines(conn: Connection, item_code: str) -> tuple[list[dict[str, Any]], str | None]:
    """Return open purchase-order lines (OPOR/POR1) for *item_code*."""
    return _safe_fetch(conn, OPOR_OPEN_LINES_BY_ITEM_SQL, {"item_code": item_code})


def fetch_bom_components(conn: Connection, item_code: str) -> tuple[list[dict[str, Any]], str | None]:
    """Return product-tree components (OITT/ITT1) for *item_code*."""
    return _safe_fetch(conn, OITT_BOM_COMPONENTS_SQL, {"item_code": item_code})


def fetch_item_prices(conn: Connection, item_code: str) -> tuple[list[dict[str, Any]], str | None]:
    """Return price-list entries (ITM1/OPLN) for *item_code*."""
    return _safe_fetch(conn, ITM1_PRICES_SQL, {"item_code": item_code})
