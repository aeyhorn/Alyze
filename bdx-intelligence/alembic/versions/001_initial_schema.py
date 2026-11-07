"""Initial schema – order_snapshots and domain_events.

Revision ID: 001
Revises:
Create Date: 2026-11-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "order_snapshots",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("source_key", sa.String(64), nullable=False, index=True),
        sa.Column("doc_entry", sa.Integer, nullable=False, index=True),
        sa.Column("doc_num", sa.Integer, nullable=False),
        sa.Column("status", sa.String(1), nullable=False),
        sa.Column("item_code", sa.String(50), nullable=False),
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
        sa.Column("snapshot_run_id", sa.String(36), nullable=False, index=True),
    )

    op.create_table(
        "domain_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("event_id", sa.String(36), nullable=False, unique=True),
        sa.Column(
            "event_type",
            sa.Enum(
                "ORDER_CREATED",
                "ORDER_RELEASED",
                "QUANTITY_CHANGED",
                "DUE_DATE_CHANGED",
                "ORDER_CLOSED",
                name="event_type_enum",
            ),
            nullable=False,
            index=True,
        ),
        sa.Column("source_key", sa.String(64), nullable=False, index=True),
        sa.Column("doc_entry", sa.Integer, nullable=False),
        sa.Column("doc_num", sa.Integer, nullable=False),
        sa.Column("item_code", sa.String(50), nullable=False),
        sa.Column("payload", sa.JSON),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot_run_id", sa.String(36), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table("domain_events")
    op.execute("DROP TYPE IF EXISTS event_type_enum")
    op.drop_table("order_snapshots")
