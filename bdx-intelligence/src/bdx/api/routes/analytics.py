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
GET /api/v1/analytics/weaknesses     - shop-floor weakness list used by the dashboard
POST /api/v1/analytics/run           - trigger an analytics cycle on demand
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy import and_, func, or_, select
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
from bdx.models.events import DomainEvent, MachineState, OrderState, SnapshotRun
from bdx.models.sap import OPEN_STATUSES, STATUS_LABELS

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


# ── Dashboard weakness list (kept from main) ─────────────────────────────────
# The router prefix is /analytics, so this path stays /api/v1/analytics/weaknesses.

_STUCK_THRESHOLD_DAYS = 3
_STUCK_COMPLETION_THRESHOLD = 0.10  # < 10 %
_PLAN_CHANGE_WINDOW_DAYS = 7
_OFFLINE_WINDOW_HOURS = 24
_COLLECTOR_ERROR_WINDOW_DAYS = 7
_RUN_TREND_LIMIT = 20


def _order_weakness_dict(o: OrderState, extra: dict | None = None) -> dict:
    d = {
        "source_key": o.source_key,
        "doc_entry": o.doc_entry,
        "doc_num": o.doc_num,
        "status": o.status,
        "status_label": STATUS_LABELS.get(o.status, o.status),
        "item_code": o.item_code,
        "planned_qty": float(o.planned_qty),
        "completed_qty": float(o.completed_qty),
        "due_date": o.due_date,
        "last_changed_at": _as_utc(o.last_changed_at).isoformat() if o.last_changed_at else None,
    }
    if extra:
        d.update(extra)
    return d


def _completion_pct(o: OrderState) -> float:
    pq = float(o.planned_qty)
    cq = float(o.completed_qty)
    return round(cq / pq * 100, 1) if pq > 0 else 0.0


def _as_utc(dt: datetime) -> datetime:
    """Normalise naive SQLite datetimes and aware PostgreSQL datetimes to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


@router.get("/weaknesses", summary="Aggregated process-weakness indicators")
def get_weaknesses(session: Session = Depends(get_pg_session)) -> dict:
    """Return all process-weakness signals in a single call.

    Covers overdue orders, stuck released orders, recent plan changes,
    idle machines, machine-offline events, and collector errors.
    """
    now = datetime.now(UTC)
    today_str = date.today().isoformat()

    overdue_rows = (
        session.execute(
            select(OrderState)
            .where(
                and_(
                    OrderState.status.in_(OPEN_STATUSES),
                    OrderState.due_date.isnot(None),
                    OrderState.due_date < today_str,
                )
            )
            .order_by(OrderState.due_date.asc())
            .limit(200)
        )
        .scalars()
        .all()
    )

    overdue_orders: list[dict] = []
    for o in overdue_rows:
        try:
            days_overdue: int | None = (date.today() - date.fromisoformat(o.due_date)).days
        except (TypeError, ValueError):
            days_overdue = None
        overdue_orders.append(
            _order_weakness_dict(
                o, {"days_overdue": days_overdue, "completion_pct": _completion_pct(o)}
            )
        )

    stuck_cutoff = now - timedelta(days=_STUCK_THRESHOLD_DAYS)
    candidate_rows = (
        session.execute(
            select(OrderState)
            .where(
                and_(
                    OrderState.status == "R",
                    OrderState.last_changed_at < stuck_cutoff,
                )
            )
            .order_by(OrderState.last_changed_at.asc())
            .limit(500)
        )
        .scalars()
        .all()
    )

    stuck_orders: list[dict] = []
    for o in candidate_rows:
        pct_raw = float(o.completed_qty) / float(o.planned_qty) if float(o.planned_qty) > 0 else 0.0
        if pct_raw < _STUCK_COMPLETION_THRESHOLD:
            days_stuck = (now - _as_utc(o.last_changed_at)).days
            stuck_orders.append(
                _order_weakness_dict(
                    o, {"completion_pct": round(pct_raw * 100, 1), "days_stuck": days_stuck}
                )
            )
    stuck_orders = stuck_orders[:200]

    plan_since = now - timedelta(days=_PLAN_CHANGE_WINDOW_DAYS)
    plan_events = (
        session.execute(
            select(DomainEvent)
            .where(
                and_(
                    DomainEvent.event_type.in_(["QUANTITY_CHANGED", "DUE_DATE_CHANGED"]),
                    DomainEvent.occurred_at >= plan_since,
                )
            )
            .order_by(DomainEvent.occurred_at.desc())
            .limit(500)
        )
        .scalars()
        .all()
    )

    latest_plan_event: dict[int, DomainEvent] = {}
    for ev in plan_events:
        if ev.doc_entry is not None and ev.doc_entry not in latest_plan_event:
            latest_plan_event[ev.doc_entry] = ev

    order_map: dict[int, OrderState] = {}
    if latest_plan_event:
        for o in session.execute(
            select(OrderState).where(OrderState.doc_entry.in_(list(latest_plan_event)))
        ).scalars():
            order_map[o.doc_entry] = o

    plan_changes: list[dict] = []
    for doc_entry, ev in latest_plan_event.items():
        o = order_map.get(doc_entry)
        if o is None:
            continue
        plan_changes.append(
            {
                **_order_weakness_dict(o, {"completion_pct": _completion_pct(o)}),
                "latest_change_type": ev.event_type,
                "latest_change_at": ev.occurred_at.isoformat(),
                "latest_change_payload": ev.payload,
            }
        )

    idle_rows = (
        session.execute(
            select(MachineState)
            .where(
                and_(
                    MachineState.online.is_(True),
                    or_(
                        MachineState.state.is_(None),
                        MachineState.state != "running",
                    ),
                )
            )
            .order_by(MachineState.machine_id)
        )
        .scalars()
        .all()
    )

    idle_machines: list[dict] = [
        {
            "machine_id": m.machine_id,
            "state": m.state,
            "exec_state": m.exec_state,
            "order_ref": m.order_ref,
            "last_seen_at": m.last_seen_at.isoformat() if m.last_seen_at else None,
            "last_changed_at": m.last_changed_at.isoformat() if m.last_changed_at else None,
        }
        for m in idle_rows
    ]

    offline_since = now - timedelta(hours=_OFFLINE_WINDOW_HOURS)
    offline_events = (
        session.execute(
            select(DomainEvent)
            .where(
                and_(
                    DomainEvent.event_type == "MACHINE_OFFLINE",
                    DomainEvent.occurred_at >= offline_since,
                )
            )
            .order_by(DomainEvent.occurred_at.desc())
            .limit(200)
        )
        .scalars()
        .all()
    )

    machine_offlines_24h: dict[str, list[dict]] = {}
    for ev in offline_events:
        mid = ev.machine_id or "unknown"
        machine_offlines_24h.setdefault(mid, []).append(
            {
                "occurred_at": ev.occurred_at.isoformat(),
                "payload": ev.payload,
            }
        )

    err_since = now - timedelta(days=_COLLECTOR_ERROR_WINDOW_DAYS)
    error_runs = (
        session.execute(
            select(SnapshotRun)
            .where(
                and_(
                    SnapshotRun.error.isnot(None),
                    SnapshotRun.started_at >= err_since,
                )
            )
            .order_by(SnapshotRun.started_at.desc())
            .limit(50)
        )
        .scalars()
        .all()
    )

    collector_errors_7d: list[dict] = [
        {
            "run_id": r.run_id,
            "started_at": r.started_at.isoformat(),
            "mode": r.mode,
            "error": r.error,
        }
        for r in error_runs
    ]

    recent_runs = (
        session.execute(
            select(SnapshotRun).order_by(SnapshotRun.started_at.desc()).limit(_RUN_TREND_LIMIT)
        )
        .scalars()
        .all()
    )

    run_trend: list[dict] = [
        {
            "run_id": r.run_id,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "mode": r.mode,
            "duration_seconds": (
                (_as_utc(r.finished_at) - _as_utc(r.started_at)).total_seconds()
                if r.finished_at and r.started_at
                else None
            ),
            "orders_read": r.orders_read,
            "orders_changed": r.orders_changed,
            "events_created": r.events_created,
            "has_error": r.error is not None,
        }
        for r in recent_runs
    ]

    return {
        "generated_at": now.isoformat(),
        "summary": {
            "overdue_orders": len(overdue_orders),
            "stuck_orders": len(stuck_orders),
            "plan_changes_7d": len(plan_changes),
            "idle_machines": len(idle_machines),
            "machine_offlines_24h": sum(len(v) for v in machine_offlines_24h.values()),
            "machines_with_offlines_24h": len(machine_offlines_24h),
            "collector_errors_7d": len(collector_errors_7d),
        },
        "overdue_orders": overdue_orders,
        "stuck_orders": stuck_orders,
        "plan_changes": plan_changes,
        "idle_machines": idle_machines,
        "machine_offlines_24h": machine_offlines_24h,
        "collector_errors_7d": collector_errors_7d,
        "run_trend": run_trend,
    }
