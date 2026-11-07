"""Order state persistence.

Two tables work together:

* ``order_state``     – current state, exactly one row per production order
                        (upserted; ``fingerprint`` lets us skip unchanged rows)
* ``order_snapshots`` – history; a row is appended whenever an order is first
                        seen or its fingerprint changed (never a full copy of
                        all orders per cycle)
* ``snapshot_runs``   – bookkeeping, one row per collector cycle
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Iterable, Sequence

import structlog
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from bdx.models.events import OrderSnapshot, OrderState, SnapshotRun
from bdx.models.sap import WorkOrder

logger = structlog.get_logger(__name__)


def fingerprint_of(wo: WorkOrder) -> str:
    return hashlib.sha1(wo.fingerprint.encode("utf-8")).hexdigest()


def _order_columns(wo: WorkOrder, captured_at: datetime, run_id: str) -> dict:
    return {
        "source_key": wo.source_key,
        "doc_entry": wo.doc_entry,
        "doc_num": wo.doc_num,
        "status": wo.status,
        "item_code": wo.item_code,
        "planned_qty": float(wo.planned_qty),
        "completed_qty": float(wo.completed_qty),
        "rejected_qty": float(wo.rejected_qty),
        "due_date": wo.due_date.isoformat() if wo.due_date else None,
        "start_date": wo.start_date.isoformat() if wo.start_date else None,
        "u_type": wo.u_type,
        "u_priority": wo.u_priority,
        "comments": wo.comments,
        "sap_update_date": wo.update_date.isoformat() if wo.update_date else None,
        "sap_update_ts": wo.update_ts,
        "captured_at": captured_at,
        "snapshot_run_id": run_id,
    }


# ── Runs ─────────────────────────────────────────────────────────────────────

def start_run(session: Session, mode: str, since_date: str | None = None) -> SnapshotRun:
    run = SnapshotRun(
        run_id=str(uuid.uuid4()),
        started_at=datetime.now(timezone.utc),
        mode=mode,
        since_date=since_date,
    )
    session.add(run)
    session.commit()
    return run


def finish_run(
    session: Session,
    run: SnapshotRun,
    orders_read: int,
    orders_changed: int,
    events_created: int,
    error: str | None = None,
) -> None:
    run.finished_at = datetime.now(timezone.utc)
    run.orders_read = orders_read
    run.orders_changed = orders_changed
    run.events_created = events_created
    run.error = error
    session.add(run)
    session.commit()


# ── State ────────────────────────────────────────────────────────────────────

def load_state(session: Session, source_keys: Iterable[str] | None = None) -> dict[str, OrderState]:
    """Return current order state as {source_key: OrderState}.

    With *source_keys* only those rows are loaded (chunked IN query).
    """
    if source_keys is None:
        rows = session.execute(select(OrderState)).scalars().all()
        return {r.source_key: r for r in rows}

    keys = list(source_keys)
    result: dict[str, OrderState] = {}
    for i in range(0, len(keys), 1000):
        chunk = keys[i : i + 1000]
        rows = session.execute(select(OrderState).where(OrderState.source_key.in_(chunk))).scalars().all()
        result.update({r.source_key: r for r in rows})
    return result


def load_open_state(session: Session) -> dict[str, OrderState]:
    """Return all orders that BDX currently believes to be open (P/R)."""
    from bdx.models.sap import OPEN_STATUSES

    rows = session.execute(select(OrderState).where(OrderState.status.in_(list(OPEN_STATUSES)))).scalars().all()
    return {r.source_key: r for r in rows}


def state_is_empty(session: Session) -> bool:
    return session.execute(select(OrderState.source_key).limit(1)).first() is None


def max_sap_update_date(session: Session) -> str | None:
    from sqlalchemy import func

    return session.execute(select(func.max(OrderState.sap_update_date))).scalar()


def apply_orders(
    session: Session,
    orders: Sequence[WorkOrder],
    run_id: str,
    previous: dict[str, OrderState] | None = None,
    captured_at: datetime | None = None,
) -> int:
    """Upsert *orders* into order_state and append history rows for changes.

    Returns the number of orders that were new or changed.
    """
    captured_at = captured_at or datetime.now(timezone.utc)
    previous = previous if previous is not None else load_state(session, [wo.source_key for wo in orders])

    changed = 0
    history: list[OrderSnapshot] = []
    unchanged_keys: list[str] = []
    for wo in orders:
        fp = fingerprint_of(wo)
        cols = _order_columns(wo, captured_at, run_id)
        prev = previous.get(wo.source_key)
        if prev is None:
            session.add(
                OrderState(**cols, fingerprint=fp, first_seen_at=captured_at, last_changed_at=captured_at)
            )
            history.append(OrderSnapshot(**cols))
            changed += 1
        elif prev.fingerprint != fp:
            for k, v in cols.items():
                setattr(prev, k, v)
            prev.fingerprint = fp
            prev.last_changed_at = captured_at
            history.append(OrderSnapshot(**cols))
            changed += 1
        else:
            unchanged_keys.append(wo.source_key)

    if history:
        session.bulk_save_objects(history)
    session.flush()

    # Unchanged rows: refresh bookkeeping with a handful of bulk UPDATEs instead
    # of one UPDATE per row (matters with a remote PostgreSQL: ~30 ms RTT each).
    for i in range(0, len(unchanged_keys), 1000):
        chunk = unchanged_keys[i : i + 1000]
        session.execute(
            update(OrderState)
            .where(OrderState.source_key.in_(chunk))
            .values(captured_at=captured_at, snapshot_run_id=run_id)
            .execution_options(synchronize_session=False)
        )
    session.commit()
    logger.info("state.applied", run_id=run_id, orders=len(orders), changed=changed)
    return changed


# ── Backwards-compatible helpers (used by tests / older callers) ─────────────

def save_snapshot(session: Session, orders: Sequence[WorkOrder], run_id: str | None = None) -> str:
    """Apply *orders* to the state tables and return the run_id."""
    run_id = run_id or str(uuid.uuid4())
    apply_orders(session, orders, run_id)
    return run_id


def load_latest_snapshot(session: Session) -> dict[str, OrderState]:
    """Return the current state (kept for API compatibility with Sprint 001)."""
    return load_state(session)


def load_snapshot_by_run_id(session: Session, run_id: str) -> dict[str, OrderSnapshot]:
    """Load the history rows written by a specific run."""
    rows = session.execute(select(OrderSnapshot).where(OrderSnapshot.snapshot_run_id == run_id)).scalars().all()
    return {row.source_key: row for row in rows}
