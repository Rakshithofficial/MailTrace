"""Create the MailTrace database foundation.

Revision ID: 0001_database_foundation
Revises:
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_database_foundation"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def uuid_column() -> sa.Column:
    return sa.Column(sa.String(36), nullable=False)


def upgrade() -> None:
    op.create_table(
        "investigation_cases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="RECEIVED"),
        sa.Column("risk_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("severity", sa.String(20), nullable=False, server_default="LOW"),
        sa.Column("verdict", sa.String(20), nullable=False, server_default="INCONCLUSIVE"),
        sa.Column("summary", sa.Text()),
        sa.Column("analyst_note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("risk_score >= 0 AND risk_score <= 100", name="ck_cases_risk_score"),
        sa.CheckConstraint("status IN ('RECEIVED','PARSING','ANALYZING','REVIEW','CLOSED','FAILED')", name="ck_cases_status"),
        sa.CheckConstraint("severity IN ('LOW','MEDIUM','HIGH','CRITICAL')", name="ck_cases_severity"),
        sa.CheckConstraint("verdict IN ('BENIGN','SUSPICIOUS','MALICIOUS','INCONCLUSIVE')", name="ck_cases_verdict"),
    )
    op.create_index("ix_investigation_cases_status_created", "investigation_cases", ["status", "created_at"])
    op.create_index("ix_investigation_cases_severity_created", "investigation_cases", ["severity", "created_at"])

    op.create_table(
        "indicators",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("normalized_value", sa.Text(), nullable=False),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("type IN ('IP','DOMAIN','URL','HASH','EMAIL','ASN')", name="ck_indicators_type"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_indicators_confidence"),
        sa.UniqueConstraint("type", "normalized_value", name="uq_indicators_type_normalized"),
    )

    op.create_table(
        "campaigns",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("first_seen", sa.DateTime(timezone=True)),
        sa.Column("last_seen", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_campaigns_confidence"),
    )

    op.create_table(
        "emails",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("investigation_cases.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("message_id", sa.String(998)),
        sa.Column("subject", sa.Text()),
        sa.Column("sender", sa.String(320)),
        sa.Column("recipients", sa.JSON(), nullable=False),
        sa.Column("reply_to", sa.String(320)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("raw_content_reference", sa.String(1024), nullable=False),
        sa.Column("raw_sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_emails_message_id", "emails", ["message_id"])

    op.create_table(
        "findings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("investigation_cases.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("rule_id", sa.String(100), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("score_contribution", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("severity IN ('LOW','MEDIUM','HIGH','CRITICAL')", name="ck_findings_severity"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_findings_confidence"),
    )
    op.create_index("ix_findings_case_severity", "findings", ["case_id", "severity"])

    op.create_table(
        "case_indicators",
        sa.Column("case_id", sa.String(36), sa.ForeignKey("investigation_cases.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("indicator_id", sa.String(36), sa.ForeignKey("indicators.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("location", sa.String(255)),
        sa.Column("evidence_reference", sa.Text()),
    )
    op.create_index("ix_case_indicators_indicator_case", "case_indicators", ["indicator_id", "case_id"])

    op.create_table(
        "header_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email_id", sa.String(36), sa.ForeignKey("emails.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("header_name", sa.String(255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("parsed_value", sa.JSON()),
        sa.Column("finding_id", sa.String(36), sa.ForeignKey("findings.id", ondelete="SET NULL")),
    )

    op.create_table(
        "finding_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("finding_id", sa.String(36), sa.ForeignKey("findings.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("evidence_type", sa.String(100), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("location", sa.String(255)),
        sa.Column("metadata", sa.JSON()),
    )
    op.create_index("ix_finding_evidence_finding_id", "finding_evidence", ["finding_id"])

    op.create_table(
        "relationships",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_indicator_id", sa.String(36), sa.ForeignKey("indicators.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("target_indicator_id", sa.String(36), sa.ForeignKey("indicators.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("relationship_type", sa.String(100), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("strength", sa.String(20), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_relationships_confidence"),
        sa.CheckConstraint("strength IN ('STRONG','MEDIUM','WEAK')", name="ck_relationships_strength"),
    )
    op.create_index("ix_relationships_source_indicator", "relationships", ["source_indicator_id"])
    op.create_index("ix_relationships_target_indicator", "relationships", ["target_indicator_id"])

    op.create_table(
        "campaign_cases",
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("investigation_cases.id", ondelete="RESTRICT"), primary_key=True),
    )
    op.create_index("ix_campaign_cases_case_id", "campaign_cases", ["case_id"])

    op.create_table(
        "recommendations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("investigation_cases.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("action", sa.String(255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("evidence_reference", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("priority IN ('LOW','MEDIUM','HIGH')", name="ck_recommendations_priority"),
    )

    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("investigation_cases.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("analyzer_version", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('STARTED','COMPLETED','FAILED')", name="ck_analysis_runs_status"),
    )
    op.create_index("ix_analysis_runs_case_created", "analysis_runs", ["case_id", "created_at"])

    op.create_table(
        "reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("investigation_cases.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("format", sa.String(20), nullable=False),
        sa.Column("content_reference", sa.String(1024), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_index("ix_analysis_runs_case_created", table_name="analysis_runs")
    op.drop_table("analysis_runs")
    op.drop_table("recommendations")
    op.drop_index("ix_campaign_cases_case_id", table_name="campaign_cases")
    op.drop_table("campaign_cases")
    op.drop_index("ix_relationships_target_indicator", table_name="relationships")
    op.drop_index("ix_relationships_source_indicator", table_name="relationships")
    op.drop_table("relationships")
    op.drop_index("ix_finding_evidence_finding_id", table_name="finding_evidence")
    op.drop_table("finding_evidence")
    op.drop_table("header_evidence")
    op.drop_index("ix_case_indicators_indicator_case", table_name="case_indicators")
    op.drop_table("case_indicators")
    op.drop_index("ix_findings_case_severity", table_name="findings")
    op.drop_table("findings")
    op.drop_index("ix_emails_message_id", table_name="emails")
    op.drop_table("emails")
    op.drop_table("campaigns")
    op.drop_table("indicators")
    op.drop_index("ix_investigation_cases_severity_created", table_name="investigation_cases")
    op.drop_index("ix_investigation_cases_status_created", table_name="investigation_cases")
    op.drop_table("investigation_cases")
