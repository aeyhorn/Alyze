"""Polling loop: reads SAP (and optionally the machine feed) with retry and backoff.

SAP cycle (``run_once``)
------------------------
* **full** mode      – first run (empty ``order_state``) or every
                       ``FULL_RELOAD_EVERY_CYCLES``: read the whole OWOR table.
* **incremental**    – read open orders (P/R) plus everything created/updated
                       since ``max(sap_update_date) - INCREMENTAL_LOOKBACK_DAYS``.
                       Open orders known to BDX that vanished from the result
                       are re-read by DocEntry so that closures are never missed.

Machine cycle (``run_machine_cycle``) runs on its own, shorter interval.
"""
from __future__ import annotations

import signal
import time
from datetime import date, datetime, timedelta, timezone
from typing import Callable

import structlog
from tenacity import (
    RetryError,
    before_sleep_log,
    retry,
    stop_after_attempt,
    wait_exponential,
)

from bdx.collector.change_detector import detect_changes, persist_events
from bdx.collector.snapshots import (
    apply_orders,
    finish_run,
    load_open_state,
    load_state,
    max_sap_update_date,
    start_run,
    state_is_empty,
)
from bdx.config import CollectorSettings, MachineSettings
from bdx.db.queries import (
    fetch_all_orders_snapshot,
    fetch_orders_by_docentries,
    fetch_orders_incremental,
)
from bdx.models.events import DomainEvent
from bdx.models.sap import WorkOrder

logger = structlog.get_logger(__name__)

_SHUTDOWN = False
_CYCLE_COUNTER = 0


def _handle_signal(signum: int, frame) -> None:  # noqa: ANN001
    global _SHUTDOWN
    logger.info("collector.shutdown_requested", signal=signum)
    _SHUTDOWN = True


def _state_to_dict(row) -> dict:  # noqa: ANN001
    """Convert an OrderState ORM row to the plain dict used by detect_changes."""
    return {
        "status": row.status,
        "planned_qty": row.planned_qty,
        "completed_qty": row.completed_qty,
        "due_date": row.due_date,
    }


def _decide_mode(session, settings: CollectorSettings | None, force_full: bool) -> tuple[str, date | None]:  # noqa: ANN001
    global _CYCLE_COUNTER
    _CYCLE_COUNTER += 1
    if force_full or state_is_empty(session):
        return "full", None
    if settings and settings.full_reload_every_cycles and _CYCLE_COUNTER % settings.full_reload_every_cycles == 0:
        return "full", None
    lookback = settings.incremental_lookback_days if settings else 2
    newest = max_sap_update_date(session)
    base = date.fromisoformat(newest) if newest else datetime.now(timezone.utc).date()
    since = min(base, datetime.now(timezone.utc).date()) - timedelta(days=lookback)
    return "incremental", since


def run_once(
    sap_engine,  # noqa: ANN001
    pg_session_factory,  # noqa: ANN001
    settings: CollectorSettings | None = None,
    force_full: bool = False,
    publisher=None,  # noqa: ANN001
) -> tuple[list[WorkOrder], list[DomainEvent]]:
    """Execute a single SAP collector cycle: read → compare → persist → publish.

    Returns (orders_read, new_events).
    """
    with pg_session_factory() as session:
        mode, since = _decide_mode(session, settings, force_full)
        run = start_run(session, mode, since.isoformat() if since else None)
        run_id = run.run_id
        logger.info("collector.cycle.start", run_id=run_id, mode=mode, since=str(since))

        try:
            with sap_engine.connect() as sap_conn:
                if mode == "full":
                    raw_rows = fetch_all_orders_snapshot(sap_conn)
                else:
                    raw_rows = fetch_orders_incremental(sap_conn, since)  # type: ignore[arg-type]

                orders = [WorkOrder.model_validate(row) for row in raw_rows]

                if mode == "incremental":
                    # Open orders we know about that are missing from the result
                    returned = {wo.source_key for wo in orders}
                    vanished = [
                        row.doc_entry
                        for key, row in load_open_state(session).items()
                        if key not in returned
                    ]
                    if vanished:
                        logger.info("collector.reread_vanished", count=len(vanished))
                        extra = fetch_orders_by_docentries(sap_conn, vanished)
                        orders.extend(WorkOrder.model_validate(r) for r in extra)

            logger.info("sap.read.complete", mode=mode, order_count=len(orders))

            previous = load_state(session, [wo.source_key for wo in orders]) if mode == "incremental" else load_state(session)
            prev_as_dicts = {k: _state_to_dict(v) for k, v in previous.items()}

            events = detect_changes(prev_as_dicts, orders, run_id=run_id)
            changed = apply_orders(session, orders, run_id, previous=previous)
            new_events = persist_events(session, events)
            finish_run(session, run, len(orders), changed, len(new_events))
        except Exception as exc:
            session.rollback()
            finish_run(session, run, 0, 0, 0, error=str(exc)[:2000])
            raise

    if publisher is not None and new_events:
        try:
            publisher.publish(new_events)
        except Exception as exc:  # noqa: BLE001
            logger.warning("publish.failed", error=str(exc))

    return orders, new_events


def build_retry_run_once(
    sap_engine,  # noqa: ANN001
    pg_session_factory,  # noqa: ANN001
    settings: CollectorSettings,
    publisher=None,  # noqa: ANN001
) -> Callable:
    """Wrap run_once with tenacity retry logic."""

    @retry(
        stop=stop_after_attempt(settings.retry_max_attempts),
        wait=wait_exponential(
            min=settings.retry_wait_min_seconds,
            max=settings.retry_wait_max_seconds,
        ),
        before_sleep=before_sleep_log(logger, "warning"),  # type: ignore[arg-type]
        reraise=True,
    )
    def _retried() -> tuple:
        return run_once(sap_engine, pg_session_factory, settings, publisher=publisher)

    return _retried


def run_polling_loop(
    sap_engine,  # noqa: ANN001
    pg_session_factory,  # noqa: ANN001
    settings: CollectorSettings,
    machine_adapter=None,  # noqa: ANN001
    machine_settings: MachineSettings | None = None,
    publisher=None,  # noqa: ANN001
) -> None:
    """Block and poll SAP (and the machine feed) until SIGTERM/SIGINT."""
    global _SHUTDOWN
    _SHUTDOWN = False

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    retried_run = build_retry_run_once(sap_engine, pg_session_factory, settings, publisher)

    machine_enabled = machine_adapter is not None and machine_settings is not None
    machine_interval = machine_settings.poll_interval_seconds if machine_enabled else settings.poll_interval_seconds
    tick = min(settings.poll_interval_seconds, machine_interval)

    logger.info(
        "collector.started",
        poll_interval=settings.poll_interval_seconds,
        machine_poll_interval=machine_interval if machine_enabled else None,
    )

    next_sap = time.monotonic()
    next_machine = time.monotonic()

    while not _SHUTDOWN:
        now = time.monotonic()

        if now >= next_sap:
            try:
                orders, events = retried_run()
                logger.info("collector.cycle.ok", orders=len(orders), events=len(events))
            except RetryError as exc:
                logger.error("collector.cycle.failed", error=str(exc))
            except Exception as exc:
                logger.error("collector.cycle.unexpected", error=str(exc), exc_info=True)
            next_sap = time.monotonic() + settings.poll_interval_seconds

        if machine_enabled and time.monotonic() >= next_machine:
            from bdx.collector.machines import run_machine_cycle

            try:
                run_machine_cycle(
                    machine_adapter,
                    pg_session_factory,
                    offline_after_seconds=machine_settings.offline_after_seconds,  # type: ignore[union-attr]
                    publisher=publisher,
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("machine.cycle.failed", error=str(exc))
            next_machine = time.monotonic() + machine_interval

        # Sleep until the next due cycle, in short increments for fast shutdown
        due = min(next_sap, next_machine if machine_enabled else next_sap)
        deadline = min(due, time.monotonic() + tick)
        while not _SHUTDOWN and time.monotonic() < deadline:
            time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))

    logger.info("collector.stopped")
