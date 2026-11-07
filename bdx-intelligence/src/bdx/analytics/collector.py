"""Analytics background collector (Sprint 005).

Integrates into the existing ``run_polling_loop`` by adding two new timers:

  * **KPI cycle** (every ``ANALYTICS_INTERVAL_SECONDS``, default 600 s / 10 min):
    1. Build/refresh ``machine_state_history`` from new events.
    2. Compute all KPIs via ``kpis.compute_all_kpis``.
    3. Persist computed values as ``KpiSnapshot`` rows.
    4. Run anomaly detection and upsert ``DetectedAnomaly`` rows.

  * **Threshold tuning cycle** (every ``THRESHOLD_TUNE_INTERVAL_SECONDS``,
    default 86 400 s / 24 h):
    1. Ensure seed thresholds exist.
    2. Re-derive percentile thresholds from the last 30 days of snapshots.

This module is also usable standalone (e.g. from the CLI):

    from bdx.analytics.collector import run_analytics_once
    run_analytics_once(pg_session_factory)
"""
from __future__ import annotations

import time
from datetime import UTC, datetime

import structlog
from sqlalchemy.orm import Session

from bdx.analytics.anomalies import detect_and_persist
from bdx.analytics.history import build_machine_state_history
from bdx.analytics.kpis import compute_all_kpis
from bdx.analytics.thresholds import seed_fixed_thresholds, tune_thresholds
from bdx.models.analytics import KpiSnapshot

logger = structlog.get_logger(__name__)

# Default intervals (overridable via config / env)
ANALYTICS_INTERVAL_SECONDS: int = 600      # 10 minutes
THRESHOLD_TUNE_INTERVAL_SECONDS: int = 86_400  # 24 hours


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _persist_kpi_results(session: Session, results: list) -> int:
    """Write KpiResult objects into the kpi_snapshots table."""
    now = _now_utc()
    for r in results:
        session.add(KpiSnapshot(
            metric_name=r.metric_name,
            dimension=r.dimension,
            dimension_value=r.dimension_value,
            value=r.value,
            window_hours=r.window_hours,
            computed_at=now,
            extra=r.extra or {},
        ))
    session.commit()
    return len(results)


def run_analytics_once(pg_session_factory) -> dict:
    """Execute one full analytics cycle.

    1. Build machine_state_history from pending domain events.
    2. Compute all KPIs.
    3. Persist KPI snapshots.
    4. Run anomaly detection.

    Returns a summary dict with counts.
    """
    summary: dict = {}
    with pg_session_factory() as session:
        # Step 1: materialise machine state intervals
        history_rows = build_machine_state_history(session)
        summary["history_rows"] = history_rows

        # Step 2 + 3: compute and persist KPIs
        kpi_results = compute_all_kpis(session)
        persisted = _persist_kpi_results(session, kpi_results)
        summary["kpis_computed"] = len(kpi_results)
        summary["kpi_snapshots_written"] = persisted

        # Step 4: anomaly detection
        new_a, upd_a, res_a = detect_and_persist(session, kpi_results)
        summary["anomalies_new"] = new_a
        summary["anomalies_updated"] = upd_a
        summary["anomalies_resolved"] = res_a

    logger.info("analytics.cycle_complete", **summary)
    return summary


def run_threshold_tune(pg_session_factory) -> dict:
    """Ensure seeds exist and recompute percentile thresholds."""
    with pg_session_factory() as session:
        seeded = seed_fixed_thresholds(session)
        tuned = tune_thresholds(session)
    summary = {"seeds_written": seeded, "thresholds_tuned": tuned}
    logger.info("analytics.threshold_tune_complete", **summary)
    return summary


def run_analytics_loop(
    pg_session_factory,
    shutdown_flag: list[bool] | None = None,
    analytics_interval: int = ANALYTICS_INTERVAL_SECONDS,
    tune_interval: int = THRESHOLD_TUNE_INTERVAL_SECONDS,
) -> None:
    """Block and run the analytics + threshold-tuning loop.

    ``shutdown_flag`` is a 1-element list so the parent loop can signal stop:
        flag = [False]
        ...
        flag[0] = True  # → loop exits after current sleep tick
    """
    if shutdown_flag is None:
        shutdown_flag = [False]

    # Ensure seeds exist before the first KPI cycle
    try:
        run_threshold_tune(pg_session_factory)
    except Exception as exc:
        logger.warning("analytics.seed_failed", error=str(exc))

    next_analytics = time.monotonic()
    next_tune = time.monotonic() + tune_interval

    logger.info(
        "analytics.loop_started",
        analytics_interval_s=analytics_interval,
        tune_interval_s=tune_interval,
    )

    while not shutdown_flag[0]:
        now = time.monotonic()

        if now >= next_analytics:
            try:
                run_analytics_once(pg_session_factory)
            except Exception as exc:
                logger.error("analytics.cycle_failed", error=str(exc), exc_info=True)
            next_analytics = time.monotonic() + analytics_interval

        if now >= next_tune:
            try:
                run_threshold_tune(pg_session_factory)
            except Exception as exc:
                logger.error("analytics.tune_failed", error=str(exc), exc_info=True)
            next_tune = time.monotonic() + tune_interval

        # Sleep in short increments for fast shutdown
        due = min(next_analytics, next_tune)
        deadline = min(due, time.monotonic() + 30.0)
        while not shutdown_flag[0] and time.monotonic() < deadline:
            time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))

    logger.info("analytics.loop_stopped")
