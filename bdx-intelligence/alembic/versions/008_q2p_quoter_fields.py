"""Q2P – link inquiries to bdx-quoter datenraum.

Revision ID: 008
Revises: 007
Create Date: 2026-11-08

Renumbered from the #39 migration that incorrectly reused revision ``005``
(already taken by analytics tables). Linear chain:
004 → 005 analytics → 006 diagnosis → 007 promise → 008 quoter fields.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("q2p_inquiries", sa.Column("datenraum", sa.Text(), nullable=True))
    op.add_column("q2p_inquiries", sa.Column("kunde", sa.String(64), nullable=True))
    op.add_column(
        "q2p_inquiries",
        sa.Column("use_llm", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("q2p_inquiries", "use_llm")
    op.drop_column("q2p_inquiries", "kunde")
    op.drop_column("q2p_inquiries", "datenraum")
