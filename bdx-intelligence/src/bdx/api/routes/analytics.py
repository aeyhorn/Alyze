"""REST endpoints for the Sprint 005 analytics engine.

GET /api/v1/analytics/kpis           - latest KPI snapshot per metric+dimension
GET /api/v1/analytics/kpis/{metric}  - all dimension rows for a single metric
GET /api/v1/analytics/trends         - time-series KPI values
GET /api/v1/analytics/anomalies      - active (unresolved) anomalies
GET /api/v1/analytics/thresholds     - current threshold configuration
GET /api/v1/analytics/quality        - measurement gates for utilization and cycle time
GET /api/v1/analytics/flow           - four-part cycle time per production order
GET /api/v1/analytics/causes         - one lateness cause per late order
GET /api/v1/analytics/bottleneck     - machine rank by utilization times queue hours
POST /api/v1/analytics/run           - trigger an analytics cycle on demand
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from bdx.analytics.quality import reliability_for_metric
from bdx.api.deps import get_pg_session, require_api_key
from bdx.models.analytics import (
    BottleneckRank,
    DetectedAnomaly,
    DetectedAnomalyDTO,
    KpiSnapshot,
    KpiSnapshotDTO,
    LatenessCause,
    MeasurementQuality,
    MetricThreshold,
    MetricThresholdDTO,
    OrderFlowSegment,
)

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    dependencies=[Depends(require_api_key)],
)


def _kpi_payload(session: Session, row: KpiSnapshot) -> dict:
    payload = KpiSnapshotDTO.model_validate(row).model_dump(mode="json")
    reliable = reliability_for_metric(session, row.metric_name)
    if reliable is not None:
        payload["reliable"] = reliable
    return payload


# ── KPI endpoints ─────────────────────────────────────────────────────────────


@router.get("/kpis", summary="Latest KPI values (all metrics, all dimensions)")
def list_kpis(
    dimension: str | None = Query(None, description="Filter by dimension: global, machine, item_group"),
    session: Session = Depends(get_pg_session),
) -> dict:
    """Return the most recent computed value for every metric+dimension combination."""
    # Subquery: newest computed_at per metric+dimension+dimension_value
    subq = (
        select(
            KpiSnapshot.metric_name,
            KpiSnapshot.dimension,
            KpiSnapshot.dimension_value,
            func.max(KpiSnapshot.computed_at).label("latest"),
        )
        .group_by(
            KpiSnapshot.metric_name,
            KpiSnapshot.dimension,
            KpiSnapshot.dimension_value,
        )
        .subquery()
    )

    q = (
        select(KpiSnapshot)
        .join(
            subq,
            (KpiSnapshot.metric_name == subq.c.metric_name)
            & (KpiSnapshot.dimension == subq.c.dimension)
            & (
                (KpiSnapshot.dimension_value == subq.c.dimension_value)
                | (
                    KpiSnapshot.dimension_value.is_(None)
                    & subq.c.dimension_value.is_(None)
                )
            )
            & (KpiSnapshot.computed_at == subq.c.latest),
        )
    )

    if dimension:
        q = q.where(KpiSnapshot.dimension == dimension)

    rows = session.execute(q.order_by(KpiSnapshot.metric_name, KpiSnapshot.dimension_value)).scalars().all()

    return {
        "count": len(rows),
        "kpis": [_kpi_payload(session, r) for r in rows],
    }


@router.get("/kpis/{metric_name}", summary="Latest KPI values for a specific metric")
def get_kpi(metric_name: str, session: Session = Depends(get_pg_session)) -> dict:
    """Return all dimension rows for the given metric_name."""
    subq = (
        select(
            KpiSnapshot.dimension,
            KpiSnapshot.dimension_value,
            func.max(KpiSnapshot.computed_at).label("latest"),
        )
        .where(KpiSnapshot.metric_name == metric_name)
        .group_by(KpiSnapshot.dimension, KpiSnapshot.dimension_value)
        .subquery()
    )
    rows = session.execute(
        select(KpiSnapshot)
        .join(
            subq,
            (KpiSnapshot.dimension == subq.c.dimension)
            & (
                (KpiSnapshot.dimension_value == subq.c.dimension_value)
                | (
                    KpiSnapshot.dimension_value.is_(None)
                    & subq.c.dimension_value.is_(None)
                )
            )
            & (KpiSnapshot.computed_at == subq.c.latest),
        )
        .where(KpiSnapshot.metric_name == metric_name)
        .order_by(KpiSnapshot.dimension_value)
    ).scalars().all()

    if not rows:
        raise HTTPException(status_code=404, detail=f"no data for metric '{metric_name}'")

    return {
        "metric_name": metric_name,
        "count": len(rows),
        "kpis": [_kpi_payload(session, r) for r in rows],
    }


# ── Trend endpoint ────────────────────────────────────────────────────────────


@router.get("/trends", summary="Time-series KPI values for a metric+dimension")
def get_trends(
    metric: str = Query(..., description="Metric name, e.g. machine_utilization_pct"),
    dimension: str = Query("global"),
    dimension_value: str | None = Query(None),
    hours: int = Query(168, ge=1, le=8760, description="Lookback window in hours (default 7d)"),
    session: Session = Depends(get_pg_session),
) -> dict:
    """Return historical KPI values for charting."""
    since = datetime.now(UTC) - timedelta(hours=hours)

    q = (
        select(KpiSnapshot)
        .where(KpiSnapshot.metric_name == metric)
        .where(KpiSnapshot.dimension == dimension)
        .where(KpiSnapshot.computed_at >= since)
    )
    if dimension_value is not None:
        q = q.where(KpiSnapshot.dimension_value == dimension_value)
    else:
        q = q.where(KpiSnapshot.dimension_value.is_(None))

    rows = session.execute(q.order_by(KpiSnapshot.computed_at)).scalars().all()

    return {
        "metric": metric,
        "dimension": dimension,
        "dimension_value": dimension_value,
        "hours": hours,
        "count": len(rows),
        "series": [
            {
                "t": r.computed_at.isoformat(),
                "v": r.value,
                "extra": r.extra,
            }
            for r in rows
        ],
    }


# ── Anomaly endpoints ─────────────────────────────────────────────────────────


@router.get("/anomalies", summary="Active (unresolved) KPI anomalies with recommendations")
def list_anomalies(
    severity: str | None = Query(None, description="Filter: warn | crit"),
    metric: str | None = Query(None),
    include_resolved: bool = Query(False, description="Also return resolved anomalies"),
    hours: int = Query(24 * 7, description="For resolved: how far back to look (hours)"),
    session: Session = Depends(get_pg_session),
) -> dict:
    """Return detected anomalies ordered by severity (crit first)."""
    q = select(DetectedAnomaly)

    if include_resolved:
        since = datetime.now(UTC) - timedelta(hours=hours)
        q = q.where(
            (DetectedAnomaly.resolved_at.is_(None))
            | (DetectedAnomaly.last_seen_at >= since)
        )
    else:
        q = q.where(DetectedAnomaly.resolved_at.is_(None))

    if severity:
        q = q.where(DetectedAnomaly.severity == severity.lower())
    if metric:
        q = q.where(DetectedAnomaly.metric_name == metric)

    q = q.order_by(DetectedAnomaly.severity, DetectedAnomaly.last_seen_at.desc())
    rows = session.execute(q).scalars().all()

    crit_count = sum(1 for r in rows if r.severity == "crit" and r.resolved_at is None)
    warn_count = sum(1 for r in rows if r.severity == "warn" and r.resolved_at is None)

    return {
        "active_crit": crit_count,
        "active_warn": warn_count,
        "count": len(rows),
        "anomalies": [DetectedAnomalyDTO.model_validate(r).model_dump(mode="json") for r in rows],
    }


# ── Threshold endpoints ───────────────────────────────────────────────────────


@router.get("/thresholds", summary="Current metric threshold configuration")
def list_thresholds(
    metric: str | None = Query(None),
    session: Session = Depends(get_pg_session),
) -> dict:
    """Return current warn/crit thresholds (auto-tuned or seed values)."""
    q = select(MetricThreshold).order_by(
        MetricThreshold.metric_name, MetricThreshold.dimension
    )
    if metric:
        q = q.where(MetricThreshold.metric_name == metric)

    rows = session.execute(q).scalars().all()
    return {
        "count": len(rows),
        "thresholds": [MetricThresholdDTO.model_validate(r).model_dump(mode="json") for r in rows],
    }


# ── Diagnosis endpoints ───────────────────────────────────────────────────────


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


@router.get("/quality", summary="Latest measurement-quality gates")
def get_quality(session: Session = Depends(get_pg_session)) -> dict:
    """Return whether utilization and cycle time may be trusted."""
    row = session.execute(
        select(MeasurementQuality).order_by(MeasurementQuality.computed_at.desc(), MeasurementQuality.id.desc())
    ).scalars().first()
    if row is None:
        return {"available": False}
    return {
        "available": True,
        "computed_at": _iso(row.computed_at),
        "link_rate": row.link_rate,
        "linked_orders": row.linked_orders,
        "machine_orders_total": row.machine_orders_total,
        "event_history_days": row.event_history_days,
        "shift_calendar_rows": row.shift_calendar_rows,
        "wip": row.wip,
        "throughput_per_hour": row.throughput_per_hour,
        "median_cycle_time_h": row.median_cycle_time_h,
        "littles_law_predicted_wip": row.littles_law_predicted_wip,
        "littles_law_deviation": row.littles_law_deviation,
        "utilization_reliable": row.utilization_reliable,
        "cycle_time_reliable": row.cycle_time_reliable,
    }


@router.get("/flow", summary="Four-part cycle time per production order")
def list_flow(
    doc_entry: int | None = Query(None),
    limit: int = Query(200, ge=1, le=5000),
    session: Session = Depends(get_pg_session),
) -> dict:
    q = select(OrderFlowSegment).order_by(OrderFlowSegment.computed_at.desc())
    if doc_entry is not None:
        q = q.where(OrderFlowSegment.doc_entry == doc_entry)
    rows = session.execute(q.limit(limit)).scalars().all()
    return {
        "count": len(rows),
        "segments": [
            {
                "doc_entry": r.doc_entry,
                "item_code": r.item_code,
                "wait_h": r.wait_h,
                "setup_h": r.setup_h,
                "run_h": r.run_h,
                "post_process_h": r.post_process_h,
                "total_h": r.total_h,
                "released_at": _iso(r.released_at),
                "first_start_at": _iso(r.first_start_at),
                "last_run_end_at": _iso(r.last_run_end_at),
                "closed_at": _iso(r.closed_at),
            }
            for r in rows
        ],
    }


@router.get("/causes", summary="One lateness cause per late production order")
def list_causes(
    cause: str | None = Query(None),
    session: Session = Depends(get_pg_session),
) -> dict:
    from bdx.analytics.causes import CAUSE_LABELS, cause_counts

    q = select(LatenessCause).order_by(LatenessCause.cause, LatenessCause.doc_entry)
    if cause:
        q = q.where(LatenessCause.cause == cause)
    rows = session.execute(q).scalars().all()
    return {
        "count": len(rows),
        "by_cause": [
            {"cause": name, "label": CAUSE_LABELS.get(name, name), "count": n}
            for name, n in cause_counts(session)
        ],
        "causes": [
            {
                "doc_entry": r.doc_entry,
                "item_code": r.item_code,
                "cause": r.cause,
                "label": CAUSE_LABELS.get(r.cause, r.cause),
                "due_date": r.due_date,
                "closed_at": _iso(r.closed_at),
                "evidence": r.evidence,
            }
            for r in rows
        ],
    }


@router.get("/bottleneck", summary="Machines ranked by utilization times waiting hours")
def list_bottlenecks(session: Session = Depends(get_pg_session)) -> dict:
    rows = session.execute(
        select(BottleneckRank).order_by(BottleneckRank.score.desc())
    ).scalars().all()
    return {
        "count": len(rows),
        "machines": [
            {
                "machine_id": r.machine_id,
                "utilization_pct": r.utilization_pct,
                "queue_hours": r.queue_hours,
                "score": r.score,
                "waiting_orders": r.waiting_orders,
                "interpretation": r.interpretation,
                "computed_at": _iso(r.computed_at),
            }
            for r in rows
        ],
    }


# ── On-demand trigger ─────────────────────────────────────────────────────────


@router.post("/run", summary="Trigger one analytics cycle on demand")
def trigger_analytics(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict:
    """Enqueue an analytics cycle in the background and return immediately."""
    from bdx.analytics.collector import run_analytics_once

    pg_factory = getattr(request.app.state, "pg_session_factory", None)
    if pg_factory is None:
        raise HTTPException(status_code=503, detail="analytics collector not available")

    background_tasks.add_task(run_analytics_once, pg_factory)
    return {"status": "queued", "message": "Analytics cycle enqueued"}
