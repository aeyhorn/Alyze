"""Machine state collector: XMSK feed → machine_state table → machine events.

Events (all carry ``source_key = "MACHINE:<machine_id>"`` and ``machine_id``):

* MACHINE_ONLINE / MACHINE_OFFLINE   – machine (dis)appeared in the feed / feed stale
* MACHINE_STATE_CHANGED              – normalised state or Exec changed
* MACHINE_ORDER_STARTED              – a new order reference appeared on the machine
* MACHINE_ORDER_FINISHED             – the order reference was removed / replaced
* MACHINE_PIECES_REPORTED            – piece counter increased

When the order reference is numeric and matches an ``order_state.doc_num`` the
event is linked to the SAP production order (``doc_entry``, ``item_code``).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from bdx.adapters.machine import MachineAdapter, MachineStatus
from bdx.collector.change_detector import persist_events
from bdx.models.events import DomainEvent, EventType, MachineState, OrderState

logger = structlog.get_logger(__name__)


def machine_source_key(machine_id: str) -> str:
    return f"MACHINE:{machine_id}"


def _resolve_sap_order(
    session: Session, status: MachineStatus
) -> tuple[int | None, int | None, str | None]:
    """Return (doc_entry, doc_num, item_code) for the machine's order reference."""
    doc_num = status.sap_doc_num
    if doc_num is None:
        return None, None, None
    row = session.execute(select(OrderState).where(OrderState.doc_num == doc_num)).scalars().first()
    if row is None:
        return None, doc_num, None
    return row.doc_entry, row.doc_num, row.item_code


def _event(
    event_type: EventType,
    status: MachineStatus,
    run_id: str,
    occurred_at: datetime,
    sap: tuple[int | None, int | None, str | None],
    payload: dict,
) -> DomainEvent:
    doc_entry, doc_num, item_code = sap
    return DomainEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type.value,
        source_key=machine_source_key(status.machine_id),
        machine_id=status.machine_id,
        doc_entry=doc_entry,
        doc_num=doc_num,
        item_code=item_code,
        payload=payload,
        occurred_at=occurred_at,
        snapshot_run_id=run_id,
    )


def _apply_status(row: MachineState, st: MachineStatus, now: datetime, sap) -> None:
    row.online = True
    row.mde_enabled = st.mde_enabled
    row.exec_state = st.exec_state
    row.state = st.state
    row.mode = st.mode
    row.order_ref = st.order_ref
    row.operation = st.operation
    row.part = st.part
    row.nc_program = st.program_name
    row.pieces = st.pieces
    row.pieces_raw = st.pieces_raw
    row.operator = st.operator
    row.feed_override = st.feed_override
    row.spindle_override = st.spindle_override
    row.rapid_override = st.rapid_override
    row.load_spindle = st.load_spindle
    row.load_axis_1 = st.load_axis_1
    row.load_axis_2 = st.load_axis_2
    row.last_message = st.last_message
    row.last_prod_end = st.last_prod_end
    row.sap_doc_entry = sap[0]
    row.sap_item_code = sap[2]
    row.source_timestamp = st.timestamp
    row.last_seen_at = now


def detect_machine_changes(
    session: Session,
    statuses: Sequence[MachineStatus],
    run_id: str,
    now: datetime | None = None,
    offline_after_seconds: int = 120,
) -> list[DomainEvent]:
    """Diff *statuses* against machine_state, update the table, return new events.

    The session is flushed but NOT committed; the caller commits together with
    the events (see :func:`run_machine_cycle`).
    """
    now = now or datetime.now(UTC)
    events: list[DomainEvent] = []

    existing = {r.machine_id: r for r in session.execute(select(MachineState)).scalars().all()}
    seen: set[str] = set()

    for st in statuses:
        seen.add(st.machine_id)
        sap = _resolve_sap_order(session, st)
        row = existing.get(st.machine_id)

        if row is None:
            row = MachineState(machine_id=st.machine_id, first_seen_at=now, last_changed_at=now)
            _apply_status(row, st, now, sap)
            session.add(row)
            events.append(
                _event(
                    EventType.MACHINE_ONLINE,
                    st,
                    run_id,
                    now,
                    sap,
                    {
                        "state": st.state,
                        "exec": st.exec_state,
                        "order_ref": st.order_ref,
                    },
                )
            )
            if st.order_ref:
                events.append(
                    _event(
                        EventType.MACHINE_ORDER_STARTED,
                        st,
                        run_id,
                        now,
                        sap,
                        {
                            "order_ref": st.order_ref,
                            "part": st.part,
                            "operation": st.operation,
                            "pieces": st.pieces,
                        },
                    )
                )
            continue

        changed = False

        if not row.online:
            events.append(
                _event(
                    EventType.MACHINE_ONLINE,
                    st,
                    run_id,
                    now,
                    sap,
                    {
                        "state": st.state,
                        "exec": st.exec_state,
                        "offline_since": row.last_seen_at.isoformat(),
                    },
                )
            )
            changed = True

        if (row.state or None) != st.state or (row.exec_state or None) != (st.exec_state or None):
            events.append(
                _event(
                    EventType.MACHINE_STATE_CHANGED,
                    st,
                    run_id,
                    now,
                    sap,
                    {
                        "prev_state": row.state,
                        "new_state": st.state,
                        "prev_exec": row.exec_state,
                        "new_exec": st.exec_state,
                        "raw_state": st.raw_state,
                        "mode": st.mode,
                        "order_ref": st.order_ref,
                    },
                )
            )
            changed = True

        prev_order = row.order_ref or None
        new_order = st.order_ref or None
        if prev_order != new_order:
            if prev_order:
                events.append(
                    _event(
                        EventType.MACHINE_ORDER_FINISHED,
                        st,
                        run_id,
                        now,
                        (row.sap_doc_entry, _safe_int(prev_order), row.sap_item_code),
                        {
                            "order_ref": prev_order,
                            "part": row.part,
                            "pieces": row.pieces,
                            "started_at": row.last_changed_at.isoformat(),
                        },
                    )
                )
            if new_order:
                events.append(
                    _event(
                        EventType.MACHINE_ORDER_STARTED,
                        st,
                        run_id,
                        now,
                        sap,
                        {
                            "order_ref": new_order,
                            "part": st.part,
                            "operation": st.operation,
                            "pieces": st.pieces,
                        },
                    )
                )
            changed = True
        elif (
            new_order
            and st.pieces is not None
            and row.pieces is not None
            and st.pieces > row.pieces
        ):
            events.append(
                _event(
                    EventType.MACHINE_PIECES_REPORTED,
                    st,
                    run_id,
                    now,
                    sap,
                    {
                        "order_ref": new_order,
                        "part": st.part,
                        "prev_pieces": row.pieces,
                        "new_pieces": st.pieces,
                        "delta": st.pieces - row.pieces,
                    },
                )
            )
            changed = True
        elif new_order and st.pieces is not None and row.pieces is None:
            changed = True

        _apply_status(row, st, now, sap)
        if changed:
            row.last_changed_at = now

    # Machines missing from the feed for too long → offline
    stale_before = now - timedelta(seconds=offline_after_seconds)
    for machine_id, row in existing.items():
        if machine_id in seen or not row.online:
            continue
        if _aware(row.last_seen_at) < stale_before:
            row.online = False
            row.last_changed_at = now
            events.append(
                DomainEvent(
                    event_id=str(uuid.uuid4()),
                    event_type=EventType.MACHINE_OFFLINE.value,
                    source_key=machine_source_key(machine_id),
                    machine_id=machine_id,
                    doc_entry=row.sap_doc_entry,
                    doc_num=_safe_int(row.order_ref),
                    item_code=row.sap_item_code,
                    payload={"last_seen_at": row.last_seen_at.isoformat(), "last_state": row.state},
                    occurred_at=now,
                    snapshot_run_id=run_id,
                )
            )

    session.flush()
    if events:
        logger.info("machine.changes", events=len(events))
    return events


def _aware(dt: datetime) -> datetime:
    """SQLite returns naive datetimes; treat them as UTC."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _safe_int(v: str | None) -> int | None:
    try:
        return int(v) if v is not None and str(v).strip().isdigit() else None
    except (TypeError, ValueError):
        return None


def run_machine_cycle(
    adapter: MachineAdapter,
    pg_session_factory,
    offline_after_seconds: int = 120,
    publisher=None,
) -> tuple[list[MachineStatus], list[DomainEvent]]:
    """One machine-collector cycle: fetch → diff → persist → publish."""
    statuses = adapter.get_all_status()
    run_id = str(uuid.uuid4())
    with pg_session_factory() as session:
        events = detect_machine_changes(
            session, statuses, run_id, offline_after_seconds=offline_after_seconds
        )
        new_events = persist_events(session, events) if events else []
        session.commit()
    if publisher is not None and new_events:
        try:
            publisher.publish(new_events)
        except Exception as exc:
            logger.warning("publish.failed", error=str(exc))
    logger.info("machine.cycle.ok", machines=len(statuses), events=len(new_events))
    return statuses, new_events
