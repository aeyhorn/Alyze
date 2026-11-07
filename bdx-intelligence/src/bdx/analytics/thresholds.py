"""Auto-tuning threshold engine (Sprint 005).

Each night the tuner reads the last 30 days of ``kpi_snapshots`` and computes
rolling percentile thresholds for every metric+dimension combination:

  warn_threshold = P75   (value is elevated but not critical)
  crit_threshold = P90   (value is clearly outside normal range)

When fewer than ``MIN_SAMPLES_FOR_PERCENTILE`` data points exist the tuner
writes conservative fixed-value seeds (defined in ``FIXED_SEED_THRESHOLDS``)
so that anomaly detection can start immediately on a fresh install.

The ``higher_is_worse`` flag is embedded in the seed definition for each
metric:  True → alert when the measured value EXCEEDS the threshold
         False → alert when the measured value FALLS BELOW the threshold
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from bdx.analytics.kpis import _percentile
from bdx.models.analytics import KpiSnapshot, MetricThreshold

logger = structlog.get_logger(__name__)

# Require at least this many historical data points before switching from fixed
# seeds to percentile-derived thresholds.
MIN_SAMPLES_FOR_PERCENTILE = 14  # ~14 hourly snapshots (just under 1 day)

# Rolling window for percentile computation
TUNING_WINDOW_DAYS = 30


# ── Seed definitions ──────────────────────────────────────────────────────────
# Format: metric_name → (warn_fixed, crit_fixed, higher_is_worse)
# These are used as initial thresholds until enough real data accumulates.
FIXED_SEED_THRESHOLDS: dict[str, tuple[float, float, bool]] = {
    # Order KPIs - higher is worse
    "cycle_time_hours":         (72.0,  168.0, True),   # warn >3d, crit >7d
    "on_time_delivery_rate":    (85.0,  70.0,  False),  # warn <85%, crit <70%
    "backlog_overdue_count":    (5.0,   20.0,  True),
    "rejection_rate_pct":       (2.0,   5.0,   True),
    "release_to_start_hours":   (8.0,   24.0,  True),   # warn >8h, crit >24h
    "order_change_frequency":   (2.0,   5.0,   True),
    # Machine KPIs - lower utilization is worse
    "machine_utilization_pct":  (60.0,  40.0,  False),  # warn <60%, crit <40%
    "setup_ratio_pct":          (20.0,  35.0,  True),   # warn >20%, crit >35%
    "mttr_hours":               (2.0,   8.0,   True),
    "mtbf_hours":               (24.0,  8.0,   False),  # want MTBF to be high
    "queue_unstarted_count":    (3.0,   10.0,  True),
    "oee_availability_pct":     (70.0,  50.0,  False),
    # Procurement / inventory KPIs
    "material_coverage_pct":    (80.0,  60.0,  False),  # warn <80%, crit <60%
    "critical_items_count":     (2.0,   5.0,   True),   # warn >2, crit >5 items
    "po_lead_time_days":        (14.0,  30.0,  True),   # warn >14d, crit >30d
    "supplier_otd_rate":        (85.0,  70.0,  False),  # warn <85%, crit <70%
    "po_overdue_count":         (2.0,   5.0,   True),   # warn >2 lines, crit >5
    "gr_delay_days":            (7.0,   21.0,  True),   # warn >7d, crit >21d
    "stock_coverage_days":      (7.0,   3.0,   False),  # warn <7d, crit <3d
}


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _tuning_since() -> datetime:
    return _now_utc() - timedelta(days=TUNING_WINDOW_DAYS)


# ── Core tuning logic ─────────────────────────────────────────────────────────


def _upsert_threshold(
    session: Session,
    metric_name: str,
    dimension: str,
    dimension_value: str | None,
    warn: float,
    crit: float,
    method: str,
    sample_count: int,
    higher_is_worse: bool,
) -> None:
    """Insert or update a MetricThreshold row."""
    existing = session.execute(
        select(MetricThreshold)
        .where(MetricThreshold.metric_name == metric_name)
        .where(MetricThreshold.dimension == dimension)
        .where(
            MetricThreshold.dimension_value == dimension_value
            if dimension_value is not None
            else MetricThreshold.dimension_value.is_(None)
        )
    ).scalars().first()

    now = _now_utc()
    if existing:
        existing.warn_threshold = warn
        existing.crit_threshold = crit
        existing.method = method
        existing.updated_at = now
        existing.sample_count = sample_count
        existing.higher_is_worse = higher_is_worse
    else:
        session.add(MetricThreshold(
            metric_name=metric_name,
            dimension=dimension,
            dimension_value=dimension_value,
            warn_threshold=warn,
            crit_threshold=crit,
            method=method,
            updated_at=now,
            sample_count=sample_count,
            higher_is_worse=higher_is_worse,
        ))


def seed_fixed_thresholds(session: Session) -> int:
    """Write fixed-value seed thresholds for metrics that have no entries yet.

    Safe to call multiple times; only creates rows that are missing.
    Returns the number of rows inserted.
    """
    inserted = 0
    for metric_name, (warn, crit, hiw) in FIXED_SEED_THRESHOLDS.items():
        existing = session.execute(
            select(MetricThreshold).where(MetricThreshold.metric_name == metric_name)
        ).scalars().first()
        if existing is None:
            _upsert_threshold(
                session, metric_name, "global", None,
                warn, crit, "fixed", 0, hiw,
            )
            inserted += 1
    session.commit()
    logger.info("thresholds.seeds_written", count=inserted)
    return inserted


def tune_thresholds(session: Session) -> int:
    """Recompute thresholds from the last 30 days of kpi_snapshots.

    For each (metric_name, dimension, dimension_value) combo with enough data
    the method switches from "fixed" to "percentile".  Returns updated rows.
    """
    since = _tuning_since()
    updated = 0

    rows = session.execute(
        select(
            KpiSnapshot.metric_name,
            KpiSnapshot.dimension,
            KpiSnapshot.dimension_value,
        )
        .where(KpiSnapshot.computed_at >= since)
        .distinct()
    ).all()

    for metric_name, dimension, dimension_value in rows:
        values_query = session.execute(
            select(KpiSnapshot.value)
            .where(KpiSnapshot.metric_name == metric_name)
            .where(KpiSnapshot.dimension == dimension)
            .where(
                KpiSnapshot.dimension_value == dimension_value
                if dimension_value is not None
                else KpiSnapshot.dimension_value.is_(None)
            )
            .where(KpiSnapshot.computed_at >= since)
        ).scalars().all()

        values = [float(v) for v in values_query if v is not None]

        seed = FIXED_SEED_THRESHOLDS.get(metric_name)
        higher_is_worse = seed[2] if seed else True

        if len(values) < MIN_SAMPLES_FOR_PERCENTILE:
            if seed is None:
                continue
            warn, crit = seed[0], seed[1]
            method = "fixed"
        else:
            if higher_is_worse:
                warn = _percentile(values, 75)
                crit = _percentile(values, 90)
            else:
                # Lower is worse: warn when value drops below P25, crit below P10
                warn = _percentile(values, 25)
                crit = _percentile(values, 10)
            method = "percentile"

        _upsert_threshold(
            session, metric_name, dimension, dimension_value,
            round(warn, 4), round(crit, 4), method, len(values), higher_is_worse,
        )
        updated += 1

    session.commit()
    logger.info("thresholds.tuned", updated=updated)
    return updated


def get_threshold(
    session: Session,
    metric_name: str,
    dimension: str = "global",
    dimension_value: str | None = None,
) -> MetricThreshold | None:
    """Return the active threshold for a metric+dimension combo, or None."""
    return session.execute(
        select(MetricThreshold)
        .where(MetricThreshold.metric_name == metric_name)
        .where(MetricThreshold.dimension == dimension)
        .where(
            MetricThreshold.dimension_value == dimension_value
            if dimension_value is not None
            else MetricThreshold.dimension_value.is_(None)
        )
    ).scalars().first()
