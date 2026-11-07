"""ORM models and Pydantic DTOs for the Sprint 005 analytics tables."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from bdx.db.postgres import Base

# ── ORM models ────────────────────────────────────────────────────────────────


class KpiSnapshot(Base):
    """One computed KPI value for a given metric/dimension/time window."""

    __tablename__ = "kpi_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # dimension: "global" | "machine" | "item_group" | "order"
    dimension: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # dimension_value: None for global, machine_id / item_group / doc_entry otherwise
    dimension_value: Mapped[str | None] = mapped_column(String(128), nullable=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    window_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    # optional extra context (e.g. sample_count, unit, p95 alongside median)
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class MetricThreshold(Base):
    """Auto-tuned warn/crit thresholds for a metric+dimension combination."""

    __tablename__ = "metric_thresholds"
    __table_args__ = (
        UniqueConstraint("metric_name", "dimension", "dimension_value", name="uq_metric_thresholds_dim"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dimension: Mapped[str] = mapped_column(String(32), nullable=False)
    dimension_value: Mapped[str | None] = mapped_column(String(128), nullable=True)
    warn_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    crit_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    # "percentile" = derived from historical P75/P90; "fixed" = hardcoded seed value
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # True → alert when value is HIGH (e.g. rejection rate, backlog age)
    # False → alert when value is LOW (e.g. OEE, on-time delivery rate)
    higher_is_worse: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class DetectedAnomaly(Base):
    """A detected KPI anomaly (weakness) with a human-readable recommendation."""

    __tablename__ = "detected_anomalies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    anomaly_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: str(uuid.uuid4()),
    )
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dimension: Mapped[str] = mapped_column(String(32), nullable=False)
    dimension_value: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    severity: Mapped[str] = mapped_column(String(8), nullable=False)  # "warn" | "crit"
    current_value: Mapped[float] = mapped_column(Float, nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ShiftCalendar(Base):
    """Planned working hours per machine (or global default when machine_id is NULL)."""

    __tablename__ = "shift_calendar"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # NULL = applies to all machines
    machine_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # 0=Mon … 6=Sun (Python weekday())
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    shift_start: Mapped[str] = mapped_column(String(5), nullable=False)   # "HH:MM"
    shift_end: Mapped[str] = mapped_column(String(5), nullable=False)     # "HH:MM"
    valid_from: Mapped[str] = mapped_column(String(10), nullable=False)   # "YYYY-MM-DD"


class MachineStateHistory(Base):
    """Timestamped machine-state durations derived from MACHINE_STATE_CHANGED events."""

    __tablename__ = "machine_state_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    machine_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    sap_doc_entry: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sap_item_code: Mapped[str | None] = mapped_column(String(50), nullable=True)


# ── Pydantic DTOs ─────────────────────────────────────────────────────────────


class KpiSnapshotDTO(BaseModel):
    id: int
    metric_name: str
    dimension: str
    dimension_value: str | None = None
    value: float
    window_hours: int
    computed_at: datetime
    extra: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class MetricThresholdDTO(BaseModel):
    metric_name: str
    dimension: str
    dimension_value: str | None = None
    warn_threshold: float
    crit_threshold: float
    method: str
    updated_at: datetime
    sample_count: int
    higher_is_worse: bool

    model_config = {"from_attributes": True}


class MeasurementQuality(Base):
    """One row per analytics run describing whether KPIs may be trusted."""

    __tablename__ = "measurement_quality"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    link_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    linked_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    machine_orders_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    event_history_days: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    shift_calendar_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wip: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    throughput_per_hour: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    median_cycle_time_h: Mapped[float | None] = mapped_column(Float, nullable=True)
    littles_law_predicted_wip: Mapped[float | None] = mapped_column(Float, nullable=True)
    littles_law_deviation: Mapped[float | None] = mapped_column(Float, nullable=True)
    utilization_reliable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cycle_time_reliable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class OrderFlowSegment(Base):
    """Four-part cycle time of one production order."""

    __tablename__ = "order_flow_segments"

    doc_entry: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    wait_h: Mapped[float | None] = mapped_column(Float, nullable=True)
    setup_h: Mapped[float | None] = mapped_column(Float, nullable=True)
    run_h: Mapped[float | None] = mapped_column(Float, nullable=True)
    post_process_h: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_h: Mapped[float | None] = mapped_column(Float, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LatenessCause(Base):
    """Single dominant cause for one late production order."""

    __tablename__ = "lateness_causes"

    doc_entry: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cause: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    due_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BottleneckRank(Base):
    """Machine ranked by utilization times queue of released-but-unstarted hours."""

    __tablename__ = "bottleneck_rank"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    machine_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    utilization_pct: Mapped[float] = mapped_column(Float, nullable=False)
    queue_hours: Mapped[float] = mapped_column(Float, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    waiting_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    interpretation: Mapped[str] = mapped_column(String(16), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DetectedAnomalyDTO(BaseModel):
    anomaly_id: str
    metric_name: str
    dimension: str
    dimension_value: str | None = None
    severity: str
    current_value: float
    threshold: float
    recommendation: str
    first_seen_at: datetime
    last_seen_at: datetime
    resolved_at: datetime | None = None
    extra: dict[str, Any] | None = None

    model_config = {"from_attributes": True}
