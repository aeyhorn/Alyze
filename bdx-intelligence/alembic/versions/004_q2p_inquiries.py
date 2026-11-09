"""Sprint Q2P – inquiry cases for Quote-to-Promise cockpit.

Revision ID: 004
Revises: 003
Create Date: 2026-11-08
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "q2p_inquiries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("customer_ref", sa.String(128), nullable=True),
        sa.Column("item_code", sa.String(50), nullable=False),
        sa.Column("qty", sa.Numeric(18, 6), nullable=False),
        sa.Column("requested_date", sa.String(10), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("owner", sa.String(64), nullable=True),
        sa.Column("decision", sa.String(16), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("promise_snapshot", sa.JSON(), nullable=True),
        sa.Column("open_questions", sa.JSON(), nullable=True),
    )
    op.create_index("ix_q2p_inquiries_status", "q2p_inquiries", ["status"])
    op.create_index("ix_q2p_inquiries_item_code", "q2p_inquiries", ["item_code"])
    op.create_index("ix_q2p_inquiries_created_at", "q2p_inquiries", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_q2p_inquiries_created_at", table_name="q2p_inquiries")
    op.drop_index("ix_q2p_inquiries_item_code", table_name="q2p_inquiries")
    op.drop_index("ix_q2p_inquiries_status", table_name="q2p_inquiries")
    op.drop_table("q2p_inquiries")
