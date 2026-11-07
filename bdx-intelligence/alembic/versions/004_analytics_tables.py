"""Sprint 005 – Analytics tables: kpi_snapshots, metric_thresholds, detected_anomalies,
shift_calendar, machine_state_history.

Revision ID: 004
Revises: 003
Create Date: 2026-11-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── kpi_snapshots: hourly computed KPI values per dimension ───────────────
    op.create_table(
        "kpi_snapshots",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("metric_name", sa.String(64), nullable=False, index=True),
        sa.Column("dimension", sa.String(32), nullable=False, index=True),
        sa.Column("dimension_value", sa.String(128), nullable=True),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("window_hours", sa.Integer, nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("extra", sa.JSON, nullable=True),
    )
    op.create_index(
        "ix_kpi_snapshots_metric_dim_time",
        "kpi_snapshots",
        ["metric_name", "dimension", "dimension_value", "computed_at"],
    )

    # ── metric_thresholds: auto-tuned warn/crit thresholds per metric ─────────
    op.create_table(
        "metric_thresholds",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("metric_name", sa.String(64), nullable=False, index=True),
        sa.Column("dimension", sa.String(32), nullable=False),
        sa.Column("dimension_value", sa.String(128), nullable=True),
        sa.Column("warn_threshold", sa.Float, nullable=False),
        sa.Column("crit_threshold", sa.Float, nullable=False),
        sa.Column("method", sa.String(16), nullable=False),  # percentile | fixed
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sample_count", sa.Integer, nullable=False, server_default="0"),
        # higher_is_worse=true means WARN when value > threshold (e.g. rejection rate)
        # higher_is_worse=false means WARN when value < threshold (e.g. OEE)
        sa.Column("higher_is_worse", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.create_index(
        "ix_metric_thresholds_metric_dim",
        "metric_thresholds",
        ["metric_name", "dimension", "dimension_value"],
        unique=True,
    )

    # ── detected_anomalies: active weaknesses with recommendations ────────────
    op.create_table(
        "detected_anomalies",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("anomaly_id", sa.String(36), nullable=False, unique=True, index=True),
        sa.Column("metric_name", sa.String(64), nullable=False, index=True),
        sa.Column("dimension", sa.String(32), nullable=False),
        sa.Column("dimension_value", sa.String(128), nullable=True, index=True),
        sa.Column("severity", sa.String(8), nullable=False),  # warn | crit
        sa.Column("current_value", sa.Float, nullable=False),
        sa.Column("threshold", sa.Float, nullable=False),
        sa.Column("recommendation", sa.Text, nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra", sa.JSON, nullable=True),
    )
    op.create_index(
        "ix_detected_anomalies_active",
        "detected_anomalies",
        ["metric_name", "dimension", "dimension_value", "resolved_at"],
    )

    # ── shift_calendar: planned working hours per machine (or all) ────────────
    op.create_table(
        "shift_calendar",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        # NULL machine_id = default for all machines
        sa.Column("machine_id", sa.String(64), nullable=True, index=True),
        # 0=Mon … 6=Sun (ISO weekday − 1)
        sa.Column("weekday", sa.Integer, nullable=False),
        sa.Column("shift_start", sa.String(5), nullable=False),   # HH:MM
        sa.Column("shift_end", sa.String(5), nullable=False),     # HH:MM
        sa.Column("valid_from", sa.String(10), nullable=False),   # YYYY-MM-DD
    )
    op.create_index(
        "ix_shift_calendar_machine_weekday",
        "shift_calendar",
        ["machine_id", "weekday", "valid_from"],
    )

    # ── machine_state_history: timestamped state durations ───────────────────
    # Populated incrementally from MACHINE_STATE_CHANGED domain events.
    op.create_table(
        "machine_state_history",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("machine_id", sa.String(64), nullable=False, index=True),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_s", sa.Float, nullable=True),
        # Link to the SAP order active during this interval (optional)
        sa.Column("sap_doc_entry", sa.Integer, nullable=True),
        sa.Column("sap_item_code", sa.String(50), nullable=True),
    )
    op.create_index(
        "ix_machine_state_history_machine_time",
        "machine_state_history",
        ["machine_id", "started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_machine_state_history_machine_time", table_name="machine_state_history")
    op.drop_table("machine_state_history")
    op.drop_index("ix_shift_calendar_machine_weekday", table_name="shift_calendar")
    op.drop_table("shift_calendar")
    op.drop_index("ix_detected_anomalies_active", table_name="detected_anomalies")
    op.drop_table("detected_anomalies")
    op.drop_index("ix_metric_thresholds_metric_dim", table_name="metric_thresholds")
    op.drop_table("metric_thresholds")
    op.drop_index("ix_kpi_snapshots_metric_dim_time", table_name="kpi_snapshots")
    op.drop_table("kpi_snapshots")
