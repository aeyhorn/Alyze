"""Fixed parameterized SQL queries against SAP Business One tables.

Only SELECT statements are defined here.  All queries are parameterized to
prevent SQL injection.  Table/column names follow SAP B1 conventions.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

# NOTE: The custom fields U_Type / U_Priority (OWOR) and U_BDX_Machine (OITM)
# from docs/SAP_MAPPING.md do not exist in the Leisinger company databases
# (verified against DEV_SBO_LEISINGER, 2026-11-07).  They are selected as NULL
# placeholders so the model shape stays stable until the UDFs are created in SAP.

# ── OWOR – Production/Work Orders ────────────────────────────────────────────

OWOR_OPEN_ORDERS_SQL = text(
    """
    SELECT
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
    FROM dbo.OWOR wo
    WHERE wo.Status NOT IN ('C', 'X')   -- exclude Closed and Cancelled
    ORDER BY wo.DocEntry
    """
)

OWOR_SNAPSHOT_SQL = text(
    """
    SELECT
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
    FROM dbo.OWOR wo
    ORDER BY wo.DocEntry
    """
)

OWOR_BY_DOCENTRY_SQL = text(
    """
    SELECT
        wo.DocEntry, wo.DocNum, wo.Status, wo.ItemCode,
        wo.PlannedQty, wo.CmpltQty, wo.RjctQty,
        wo.DueDate, wo.StartDate, wo.PostDate,
        CAST(NULL AS NVARCHAR(50)) AS U_Type,
        CAST(NULL AS NVARCHAR(50)) AS U_Priority,
        wo.Comments, wo.UpdateDate, wo.UpdateTS
    FROM dbo.OWOR wo
    WHERE wo.DocEntry = :doc_entry
    """
)

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
        SELECT DISTINCT wo.ItemCode FROM dbo.OWOR wo WHERE wo.Status NOT IN ('C', 'X')
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


def fetch_order_by_docentry(conn: Connection, doc_entry: int) -> dict[str, Any] | None:
    """Return a single production order by DocEntry, or None."""
    result = conn.execute(OWOR_BY_DOCENTRY_SQL, {"doc_entry": doc_entry})
    row = result.fetchone()
    return dict(row._mapping) if row else None


def fetch_items_for_open_orders(conn: Connection) -> list[dict[str, Any]]:
    """Return item master data for all items referenced by open orders."""
    result = conn.execute(OITM_FOR_ORDERS_SQL)
    return [dict(row._mapping) for row in result]


def fetch_item_by_code(conn: Connection, item_code: str) -> dict[str, Any] | None:
    """Return a single item by ItemCode, or None."""
    result = conn.execute(OITM_BY_ITEMCODE_SQL, {"item_code": item_code})
    row = result.fetchone()
    return dict(row._mapping) if row else None
