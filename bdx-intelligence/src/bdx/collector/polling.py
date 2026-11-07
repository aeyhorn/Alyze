"""Polling loop: reads SAP every POLL_INTERVAL_SECONDS with retry and backoff."""
from __future__ import annotations

import signal
import time
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
from bdx.collector.snapshots import load_latest_snapshot, save_snapshot
from bdx.config import CollectorSettings
from bdx.db.queries import fetch_all_orders_snapshot
from bdx.models.sap import WorkOrder

logger = structlog.get_logger(__name__)

_SHUTDOWN = False


def _handle_signal(signum: int, frame) -> None:  # noqa: ANN001
    global _SHUTDOWN
    logger.info("collector.shutdown_requested", signal=signum)
    _SHUTDOWN = True


def _snapshot_to_dict(snap) -> dict:  # noqa: ANN001
    """Convert an OrderSnapshot ORM row to a plain dict for change detection."""
    return {
        "status": snap.status,
        "planned_qty": snap.planned_qty,
        "due_date": snap.due_date,
    }


def run_once(sap_engine, pg_session_factory) -> tuple[list[WorkOrder], list]:  # noqa: ANN001
    """Execute a single collector cycle: read SAP → compare → persist events.

    Returns (current_orders, new_events).
    """
    with sap_engine.connect() as sap_conn:
        raw_rows = fetch_all_orders_snapshot(sap_conn)

    orders = [WorkOrder.model_validate(row) for row in raw_rows]
    logger.info("sap.read.complete", order_count=len(orders))

    with pg_session_factory() as session:
        prev_map = load_latest_snapshot(session)
        prev_as_dicts = {k: _snapshot_to_dict(v) for k, v in prev_map.items()}

        events = detect_changes(prev_as_dicts, orders, run_id="")  # run_id assigned after save
        run_id = save_snapshot(session, orders)

        # Backfill run_id into events before persisting
        for ev in events:
            ev.snapshot_run_id = run_id

        persist_events(session, events)

    return orders, events


def build_retry_run_once(
    sap_engine,  # noqa: ANN001
    pg_session_factory,  # noqa: ANN001
    settings: CollectorSettings,
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
        return run_once(sap_engine, pg_session_factory)

    return _retried


def run_polling_loop(
    sap_engine,  # noqa: ANN001
    pg_session_factory,  # noqa: ANN001
    settings: CollectorSettings,
) -> None:
    """Block and poll SAP until a SIGTERM/SIGINT is received."""
    global _SHUTDOWN
    _SHUTDOWN = False

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    retried_run = build_retry_run_once(sap_engine, pg_session_factory, settings)

    logger.info("collector.started", poll_interval=settings.poll_interval_seconds)

    while not _SHUTDOWN:
        cycle_start = time.monotonic()
        try:
            orders, events = retried_run()
            logger.info(
                "collector.cycle.ok",
                orders=len(orders),
                events=len(events),
            )
        except RetryError as exc:
            logger.error("collector.cycle.failed", error=str(exc))
        except Exception as exc:
            logger.error("collector.cycle.unexpected", error=str(exc), exc_info=True)

        elapsed = time.monotonic() - cycle_start
        sleep_for = max(0.0, settings.poll_interval_seconds - elapsed)
        logger.debug("collector.sleeping", seconds=round(sleep_for, 1))

        # Sleep in short increments to allow fast shutdown
        deadline = time.monotonic() + sleep_for
        while not _SHUTDOWN and time.monotonic() < deadline:
            time.sleep(min(1.0, deadline - time.monotonic()))

    logger.info("collector.stopped")
