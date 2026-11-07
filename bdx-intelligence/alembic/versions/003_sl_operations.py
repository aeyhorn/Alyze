"""Sprint 003 – Service Layer write-back audit log.

Revision ID: 003
Revises: 002
Create Date: 2026-11-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sl_operations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("operation_id", sa.String(36), nullable=False, unique=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("operation", sa.String(32), nullable=False),
        sa.Column("mode", sa.String(8), nullable=False),
        sa.Column("company_db", sa.String(64), nullable=False),
        sa.Column("doc_entry", sa.Integer(), nullable=True),
        sa.Column("doc_num", sa.Integer(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("operator", sa.String(64), nullable=True),
    )
    op.create_index("ix_sl_operations_operation_id", "sl_operations", ["operation_id"], unique=True)
    op.create_index("ix_sl_operations_occurred_at", "sl_operations", ["occurred_at"])
    op.create_index("ix_sl_operations_operation", "sl_operations", ["operation"])
    op.create_index("ix_sl_operations_doc_entry", "sl_operations", ["doc_entry"])


def downgrade() -> None:
    op.drop_index("ix_sl_operations_doc_entry", table_name="sl_operations")
    op.drop_index("ix_sl_operations_operation", table_name="sl_operations")
    op.drop_index("ix_sl_operations_occurred_at", table_name="sl_operations")
    op.drop_index("ix_sl_operations_operation_id", table_name="sl_operations")
    op.drop_table("sl_operations")
