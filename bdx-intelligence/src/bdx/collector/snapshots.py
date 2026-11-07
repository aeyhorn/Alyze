"""Snapshot persistence: save SAP work-order snapshots to PostgreSQL."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

import structlog
from sqlalchemy.orm import Session

from bdx.models.events import OrderSnapshot
from bdx.models.sap import WorkOrder

logger = structlog.get_logger(__name__)


def save_snapshot(session: Session, orders: Sequence[WorkOrder], run_id: str | None = None) -> str:
    """Persist a list of WorkOrder objects as a snapshot batch.

    Returns the run_id that identifies this snapshot batch.
    """
    run_id = run_id or str(uuid.uuid4())
    captured_at = datetime.now(timezone.utc)

    rows = [
        OrderSnapshot(
            source_key=wo.source_key,
            doc_entry=wo.doc_entry,
            doc_num=wo.doc_num,
            status=wo.status,
            item_code=wo.item_code,
            planned_qty=float(wo.planned_qty),
            completed_qty=float(wo.completed_qty),
            rejected_qty=float(wo.rejected_qty),
            due_date=wo.due_date.isoformat() if wo.due_date else None,
            start_date=wo.start_date.isoformat() if wo.start_date else None,
            u_type=wo.u_type,
            u_priority=wo.u_priority,
            comments=wo.comments,
            sap_update_date=wo.update_date.isoformat() if wo.update_date else None,
            sap_update_ts=wo.update_ts,
            captured_at=captured_at,
            snapshot_run_id=run_id,
        )
        for wo in orders
    ]

    session.bulk_save_objects(rows)
    session.commit()
    logger.info("snapshot.saved", run_id=run_id, order_count=len(rows))
    return run_id


def load_latest_snapshot(session: Session) -> dict[str, OrderSnapshot]:
    """Return the most recent snapshot as {source_key: OrderSnapshot}.

    Uses the snapshot_run_id with the highest captured_at to identify the latest batch.
    """
    from sqlalchemy import select, func

    latest_run = session.execute(
        select(func.max(OrderSnapshot.captured_at))
    ).scalar()

    if latest_run is None:
        return {}

    rows = session.execute(
        select(OrderSnapshot).where(OrderSnapshot.captured_at == latest_run)
    ).scalars().all()

    result = {row.source_key: row for row in rows}
    logger.debug("snapshot.loaded", run_id_count=len(result))
    return result


def load_snapshot_by_run_id(session: Session, run_id: str) -> dict[str, OrderSnapshot]:
    """Load a specific snapshot batch by run_id."""
    from sqlalchemy import select

    rows = session.execute(
        select(OrderSnapshot).where(OrderSnapshot.snapshot_run_id == run_id)
    ).scalars().all()
    return {row.source_key: row for row in rows}
