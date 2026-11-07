"""Sprint 002 – order_state, snapshot_runs, machine_state; flexible domain_events.

Revision ID: 002
Revises: 001
Create Date: 2026-11-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── domain_events: free-text event type, optional order link, machine_id ──
    # The Postgres ENUM from 001 cannot grow without ALTER TYPE; switch to VARCHAR.
    op.alter_column(
        "domain_events",
        "event_type",
        type_=sa.String(32),
        existing_nullable=False,
        postgresql_using="event_type::text",
    )
    op.execute("DROP TYPE IF EXISTS event_type_enum")
    op.alter_column("domain_events", "doc_entry", existing_type=sa.Integer, nullable=True)
    op.alter_column("domain_events", "doc_num", existing_type=sa.Integer, nullable=True)
    op.alter_column("domain_events", "item_code", existing_type=sa.String(50), nullable=True)
    op.add_column("domain_events", sa.Column("machine_id", sa.String(64), nullable=True))
    op.create_index("ix_domain_events_machine_id", "domain_events", ["machine_id"])
    op.create_index("ix_domain_events_occurred_at", "domain_events", ["occurred_at"])

    # ── order_state: current state, one row per order ─────────────────────────
    op.create_table(
        "order_state",
        sa.Column("source_key", sa.String(64), primary_key=True),
        sa.Column("doc_entry", sa.Integer, nullable=False, index=True),
        sa.Column("doc_num", sa.Integer, nullable=False, index=True),
        sa.Column("status", sa.String(1), nullable=False, index=True),
        sa.Column("item_code", sa.String(50), nullable=False, index=True),
        sa.Column("planned_qty", sa.Numeric(18, 6), nullable=False),
        sa.Column("completed_qty", sa.Numeric(18, 6), nullable=False),
        sa.Column("rejected_qty", sa.Numeric(18, 6), nullable=False),
        sa.Column("due_date", sa.String(10)),
        sa.Column("start_date", sa.String(10)),
        sa.Column("u_type", sa.String(50)),
        sa.Column("u_priority", sa.String(50)),
        sa.Column("comments", sa.Text),
        sa.Column("sap_update_date", sa.String(10)),
        sa.Column("sap_update_ts", sa.Integer),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot_run_id", sa.String(36), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_changed_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Seed order_state from the latest full snapshot batch (if any), so that the
    # first incremental run does not re-emit ORDER_CREATED for every order.
    op.execute(
        """
        INSERT INTO order_state (
            source_key, doc_entry, doc_num, status, item_code,
            planned_qty, completed_qty, rejected_qty, due_date, start_date,
            u_type, u_priority, comments, sap_update_date, sap_update_ts,
            captured_at, snapshot_run_id, fingerprint, first_seen_at, last_changed_at
        )
        SELECT DISTINCT ON (s.source_key)
            s.source_key, s.doc_entry, s.doc_num, s.status, s.item_code,
            s.planned_qty, s.completed_qty, s.rejected_qty, s.due_date, s.start_date,
            s.u_type, s.u_priority, s.comments, s.sap_update_date, s.sap_update_ts,
            s.captured_at, s.snapshot_run_id, '', s.captured_at, s.captured_at
        FROM order_snapshots s
        WHERE s.captured_at = (SELECT MAX(captured_at) FROM order_snapshots)
        ORDER BY s.source_key, s.captured_at DESC
        """
    )

    # Full per-cycle copies are no longer written; keep only the latest batch as
    # the first history entry to stop the table from carrying ~40k rows per run.
    op.execute(
        """
        DELETE FROM order_snapshots
        WHERE captured_at < (SELECT MAX(captured_at) FROM order_snapshots)
        """
    )

    # ── snapshot_runs ─────────────────────────────────────────────────────────
    op.create_table(
        "snapshot_runs",
        sa.Column("run_id", sa.String(36), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("orders_read", sa.Integer, nullable=False, server_default="0"),
        sa.Column("orders_changed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("events_created", sa.Integer, nullable=False, server_default="0"),
        sa.Column("since_date", sa.String(10)),
        sa.Column("error", sa.Text),
    )

    # ── machine_state ─────────────────────────────────────────────────────────
    op.create_table(
        "machine_state",
        sa.Column("machine_id", sa.String(64), primary_key=True),
        sa.Column("online", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("mde_enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("exec_state", sa.String(32)),
        sa.Column("state", sa.String(32)),
        sa.Column("mode", sa.String(16)),
        sa.Column("order_ref", sa.String(64)),
        sa.Column("operation", sa.String(64)),
        sa.Column("part", sa.String(64)),
        sa.Column("nc_program", sa.String(64)),
        sa.Column("pieces", sa.Integer),
        sa.Column("pieces_raw", sa.String(32)),
        sa.Column("operator", sa.String(64)),
        sa.Column("feed_override", sa.Integer),
        sa.Column("spindle_override", sa.Integer),
        sa.Column("rapid_override", sa.Integer),
        sa.Column("load_spindle", sa.Float),
        sa.Column("load_axis_1", sa.Float),
        sa.Column("load_axis_2", sa.Float),
        sa.Column("last_message", sa.Text),
        sa.Column("last_prod_end", sa.String(32)),
        sa.Column("sap_doc_entry", sa.Integer),
        sa.Column("sap_item_code", sa.String(50)),
        sa.Column("source_timestamp", sa.DateTime(timezone=True)),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_changed_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("machine_state")
    op.drop_table("snapshot_runs")
    op.drop_table("order_state")
    op.drop_index("ix_domain_events_occurred_at", table_name="domain_events")
    op.drop_index("ix_domain_events_machine_id", table_name="domain_events")
    op.drop_column("domain_events", "machine_id")
    op.alter_column("domain_events", "item_code", existing_type=sa.String(50), nullable=False)
    op.alter_column("domain_events", "doc_num", existing_type=sa.Integer, nullable=False)
    op.alter_column("domain_events", "doc_entry", existing_type=sa.Integer, nullable=False)
    # event_type stays VARCHAR on downgrade (the enum values from 001 would be lossy)
