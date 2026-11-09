"""Sprint 005 diagnosis layer: measurement quality, flow segments, lateness causes, bottleneck rank.

Revision ID: 006
Revises: 005
Create Date: 2026-11-07

Follows the analytics tables (005) after the Quote-to-Promise migration (004).
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "measurement_quality",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("link_rate", sa.Float, nullable=True),
        sa.Column("linked_orders", sa.Integer, nullable=False, server_default="0"),
        sa.Column("machine_orders_total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("event_history_days", sa.Float, nullable=False, server_default="0"),
        sa.Column("shift_calendar_rows", sa.Integer, nullable=False, server_default="0"),
        sa.Column("wip", sa.Float, nullable=False, server_default="0"),
        sa.Column("throughput_per_hour", sa.Float, nullable=False, server_default="0"),
        sa.Column("median_cycle_time_h", sa.Float, nullable=True),
        sa.Column("littles_law_predicted_wip", sa.Float, nullable=True),
        sa.Column("littles_law_deviation", sa.Float, nullable=True),
        sa.Column("utilization_reliable", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("cycle_time_reliable", sa.Boolean, nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "order_flow_segments",
        sa.Column("doc_entry", sa.Integer, primary_key=True),
        sa.Column("item_code", sa.String(50), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("wait_h", sa.Float, nullable=True),
        sa.Column("setup_h", sa.Float, nullable=True),
        sa.Column("run_h", sa.Float, nullable=True),
        sa.Column("post_process_h", sa.Float, nullable=True),
        sa.Column("total_h", sa.Float, nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_order_flow_segments_closed_at", "order_flow_segments", ["closed_at"])

    op.create_table(
        "lateness_causes",
        sa.Column("doc_entry", sa.Integer, primary_key=True),
        sa.Column("item_code", sa.String(50), nullable=True),
        sa.Column("cause", sa.String(32), nullable=False, index=True),
        sa.Column("due_date", sa.String(10), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence", sa.JSON, nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "bottleneck_rank",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("machine_id", sa.String(64), nullable=False, index=True),
        sa.Column("utilization_pct", sa.Float, nullable=False),
        sa.Column("queue_hours", sa.Float, nullable=False),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("waiting_orders", sa.Integer, nullable=False, server_default="0"),
        sa.Column("interpretation", sa.String(16), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("bottleneck_rank")
    op.drop_table("lateness_causes")
    op.drop_index("ix_order_flow_segments_closed_at", table_name="order_flow_segments")
    op.drop_table("order_flow_segments")
    op.drop_table("measurement_quality")
