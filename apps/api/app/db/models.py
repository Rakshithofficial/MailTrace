"""Persistence models only; analysis and API behavior belong elsewhere."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import (
    Base,
    TimestampMixin,
    UpdatedTimestampMixin,
    UUIDPrimaryKeyMixin,
    UUIDString,
    utc_now,
)
from .enums import (
    AnalysisStatus,
    CaseStatus,
    IndicatorType,
    RecommendationPriority,
    RelationshipStrength,
    Severity,
    Verdict,
)
from sqlalchemy import Enum as SAEnum


def enum_column(enum_type: type, *, nullable: bool = False) -> Any:
    return SAEnum(
        enum_type,
        name=f"{enum_type.__name__.lower()}_enum",
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        nullable=nullable,
    )


class InvestigationCase(Base, UUIDPrimaryKeyMixin, TimestampMixin, UpdatedTimestampMixin):
    __tablename__ = "investigation_cases"
    __table_args__ = (
        Index("ix_investigation_cases_status_created", "status", "created_at"),
        Index("ix_investigation_cases_severity_created", "severity", "created_at"),
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[CaseStatus] = mapped_column(enum_column(CaseStatus), default=CaseStatus.RECEIVED)
    risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    severity: Mapped[Severity] = mapped_column(enum_column(Severity), default=Severity.LOW)
    verdict: Mapped[Verdict] = mapped_column(enum_column(Verdict), default=Verdict.INCONCLUSIVE)
    summary: Mapped[str | None] = mapped_column(Text)
    analyst_note: Mapped[str | None] = mapped_column(Text)

    email: Mapped["Email | None"] = relationship(back_populates="case", uselist=False)
    findings: Mapped[list["Finding"]] = relationship(back_populates="case")
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="case")
    indicators: Mapped[list["Indicator"]] = relationship(secondary="case_indicators", back_populates="cases")
    campaigns: Mapped[list["Campaign"]] = relationship(secondary="campaign_cases", back_populates="cases")
    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(back_populates="case")
    reports: Mapped[list["Report"]] = relationship(back_populates="case")


class Email(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "emails"
    __table_args__ = (Index("ix_emails_message_id", "message_id"),)

    case_id: Mapped[str] = mapped_column(
        UUIDString(), ForeignKey("investigation_cases.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    message_id: Mapped[str | None] = mapped_column(String(998))
    subject: Mapped[str | None] = mapped_column(Text)
    sender: Mapped[str | None] = mapped_column(String(320))
    recipients: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    cc: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    reply_to: Mapped[str | None] = mapped_column(String(320))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    body_text: Mapped[str | None] = mapped_column(Text)
    body_html: Mapped[str | None] = mapped_column(Text)
    received_headers: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    authentication_results: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    urls: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    attachments: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    raw_content_reference: Mapped[str] = mapped_column(String(1024), nullable=False)
    raw_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    case: Mapped[InvestigationCase] = relationship(back_populates="email")
    headers: Mapped[list["HeaderEvidence"]] = relationship(back_populates="email")


class HeaderEvidence(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "header_evidence"

    email_id: Mapped[str] = mapped_column(
        UUIDString(), ForeignKey("emails.id", ondelete="RESTRICT"), nullable=False
    )
    header_name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_value: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    finding_id: Mapped[str | None] = mapped_column(
        UUIDString(), ForeignKey("findings.id", ondelete="SET NULL")
    )

    email: Mapped[Email] = relationship(back_populates="headers")
    finding: Mapped["Finding | None"] = relationship(back_populates="header_evidence")


class Indicator(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "indicators"
    __table_args__ = (
        UniqueConstraint("type", "normalized_value", name="uq_indicators_type_normalized"),
    )

    type: Mapped[IndicatorType] = mapped_column(enum_column(IndicatorType), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_value: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    cases: Mapped[list[InvestigationCase]] = relationship(secondary="case_indicators", back_populates="indicators")
    source_relationships: Mapped[list["Relationship"]] = relationship(
        foreign_keys="Relationship.source_indicator_id", back_populates="source_indicator"
    )
    target_relationships: Mapped[list["Relationship"]] = relationship(
        foreign_keys="Relationship.target_indicator_id", back_populates="target_indicator"
    )


class CaseIndicator(Base):
    __tablename__ = "case_indicators"
    case_id: Mapped[str] = mapped_column(
        UUIDString(), ForeignKey("investigation_cases.id", ondelete="RESTRICT"), primary_key=True
    )
    indicator_id: Mapped[str] = mapped_column(
        UUIDString(), ForeignKey("indicators.id", ondelete="RESTRICT"), primary_key=True
    )
    location: Mapped[str | None] = mapped_column(String(255))
    evidence_reference: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (Index("ix_case_indicators_indicator_case", "indicator_id", "case_id"),)


class Finding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "findings"
    __table_args__ = (Index("ix_findings_case_severity", "case_id", "severity"),)

    case_id: Mapped[str] = mapped_column(
        UUIDString(), ForeignKey("investigation_cases.id", ondelete="RESTRICT"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[Severity] = mapped_column(enum_column(Severity), nullable=False)
    score_contribution: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)

    case: Mapped[InvestigationCase] = relationship(back_populates="findings")
    evidence: Mapped[list["FindingEvidence"]] = relationship(back_populates="finding")
    header_evidence: Mapped[list[HeaderEvidence]] = relationship(back_populates="finding")


class FindingEvidence(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "finding_evidence"

    finding_id: Mapped[str] = mapped_column(
        UUIDString(), ForeignKey("findings.id", ondelete="RESTRICT"), nullable=False
    )
    evidence_type: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))
    evidence_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON)

    finding: Mapped[Finding] = relationship(back_populates="evidence")


class Relationship(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "relationships"
    __table_args__ = (
        Index("ix_relationships_source_indicator", "source_indicator_id"),
        Index("ix_relationships_target_indicator", "target_indicator_id"),
    )

    source_indicator_id: Mapped[str] = mapped_column(
        UUIDString(), ForeignKey("indicators.id", ondelete="RESTRICT"), nullable=False
    )
    target_indicator_id: Mapped[str] = mapped_column(
        UUIDString(), ForeignKey("indicators.id", ondelete="RESTRICT"), nullable=False
    )
    source_case_id: Mapped[str | None] = mapped_column(
        UUIDString(), ForeignKey("investigation_cases.id", ondelete="RESTRICT")
    )
    target_case_id: Mapped[str | None] = mapped_column(
        UUIDString(), ForeignKey("investigation_cases.id", ondelete="RESTRICT")
    )
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    strength: Mapped[RelationshipStrength] = mapped_column(enum_column(RelationshipStrength), nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    source_indicator: Mapped[Indicator] = relationship(
        foreign_keys=[source_indicator_id], back_populates="source_relationships"
    )
    target_indicator: Mapped[Indicator] = relationship(
        foreign_keys=[target_indicator_id], back_populates="target_relationships"
    )


class Campaign(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "campaigns"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    cases: Mapped[list[InvestigationCase]] = relationship(secondary="campaign_cases", back_populates="campaigns")


class CampaignCase(Base):
    __tablename__ = "campaign_cases"
    campaign_id: Mapped[str] = mapped_column(
        UUIDString(), ForeignKey("campaigns.id", ondelete="RESTRICT"), primary_key=True
    )
    case_id: Mapped[str] = mapped_column(
        UUIDString(), ForeignKey("investigation_cases.id", ondelete="RESTRICT"), primary_key=True
    )


class Recommendation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "recommendations"

    case_id: Mapped[str] = mapped_column(
        UUIDString(), ForeignKey("investigation_cases.id", ondelete="RESTRICT"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[RecommendationPriority] = mapped_column(enum_column(RecommendationPriority), nullable=False)
    evidence_reference: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    case: Mapped[InvestigationCase] = relationship(back_populates="recommendations")


class AnalysisRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "analysis_runs"
    __table_args__ = (Index("ix_analysis_runs_case_created", "case_id", "created_at"),)

    case_id: Mapped[str] = mapped_column(
        UUIDString(), ForeignKey("investigation_cases.id", ondelete="RESTRICT"), nullable=False
    )
    analyzer_version: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[AnalysisStatus] = mapped_column(enum_column(AnalysisStatus), nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    case: Mapped[InvestigationCase] = relationship(back_populates="analysis_runs")


class Report(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "reports"

    case_id: Mapped[str] = mapped_column(
        UUIDString(), ForeignKey("investigation_cases.id", ondelete="RESTRICT"), nullable=False
    )
    format: Mapped[str] = mapped_column(String(20), nullable=False)
    content_reference: Mapped[str] = mapped_column(String(1024), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    case: Mapped[InvestigationCase] = relationship(back_populates="reports")
