"""Promise Platform: offers, gaps, evidence, agent jobs, contracts.

Revision ID: 007
Revises: 006
Create Date: 2026-11-08

Living Offer object + Gap runtime + Contract projection for Alyze Promise Platform.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "promise_offers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("customer_ref", sa.String(128), nullable=True),
        sa.Column("customer_name", sa.String(128), nullable=True),
        sa.Column("item_code", sa.String(50), nullable=False),
        sa.Column("qty", sa.Numeric(18, 6), nullable=False),
        sa.Column("requested_date", sa.String(10), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("owner", sa.String(64), nullable=True),
        sa.Column("datenraum", sa.Text, nullable=True),
        sa.Column("kunde", sa.String(64), nullable=True),
        sa.Column("use_llm", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("price_low_eur", sa.Float, nullable=True),
        sa.Column("price_high_eur", sa.Float, nullable=True),
        sa.Column("date_early", sa.String(10), nullable=True),
        sa.Column("date_late", sa.String(10), nullable=True),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0"),
        sa.Column("confidence_threshold", sa.Float, nullable=False, server_default="0.75"),
        sa.Column("decision", sa.String(16), nullable=True),
        sa.Column("decision_note", sa.Text, nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evaluation", sa.JSON, nullable=True),
        sa.Column("portal_token", sa.String(36), nullable=False),
        sa.Column("q2p_inquiry_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_promise_offers_status", "promise_offers", ["status"])
    op.create_index("ix_promise_offers_item_code", "promise_offers", ["item_code"])
    op.create_index("ix_promise_offers_customer_ref", "promise_offers", ["customer_ref"])
    op.create_index("ix_promise_offers_portal_token", "promise_offers", ["portal_token"], unique=True)

    op.create_table(
        "promise_gaps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("offer_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("gap_type", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("detail", sa.Text, nullable=True),
        sa.Column("owner_role", sa.String(32), nullable=False, server_default="vertrieb"),
        sa.Column("source_domain", sa.String(32), nullable=True),
        sa.Column("source_agent", sa.String(32), nullable=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("resolution_note", sa.Text, nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(64), nullable=True),
        sa.Column("extra", sa.JSON, nullable=True),
    )
    op.create_index("ix_promise_gaps_offer_id", "promise_gaps", ["offer_id"])
    op.create_index("ix_promise_gaps_gap_type", "promise_gaps", ["gap_type"])
    op.create_index("ix_promise_gaps_status", "promise_gaps", ["status"])
    op.create_index("ix_promise_gaps_fingerprint", "promise_gaps", ["fingerprint"])

    op.create_table(
        "promise_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("offer_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("label", sa.String(256), nullable=False),
        sa.Column("payload", sa.JSON, nullable=True),
        sa.Column("external_ref", sa.String(256), nullable=True),
    )
    op.create_index("ix_promise_evidence_offer_id", "promise_evidence", ["offer_id"])

    op.create_table(
        "promise_agent_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("offer_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("input_payload", sa.JSON, nullable=True),
        sa.Column("result_payload", sa.JSON, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("needs_human", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_promise_agent_jobs_offer_id", "promise_agent_jobs", ["offer_id"])
    op.create_index("ix_promise_agent_jobs_kind", "promise_agent_jobs", ["kind"])

    op.create_table(
        "promise_contracts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("offer_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("body", sa.JSON, nullable=False),
        sa.Column("customer_visible", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_by", sa.String(128), nullable=True),
        sa.Column("reject_reason", sa.Text, nullable=True),
    )
    op.create_index("ix_promise_contracts_offer_id", "promise_contracts", ["offer_id"])
    op.create_index("ix_promise_contracts_status", "promise_contracts", ["status"])


def downgrade() -> None:
    op.drop_table("promise_contracts")
    op.drop_table("promise_agent_jobs")
    op.drop_table("promise_evidence")
    op.drop_table("promise_gaps")
    op.drop_table("promise_offers")
