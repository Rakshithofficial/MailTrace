"""End-to-end investigation orchestration over existing MailTrace components."""

from __future__ import annotations
import traceback
import os
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.analyzers.attachments import analyze_attachments
from app.analyzers.authentication import analyze_authentication
from app.analyzers.content import analyze_content
from app.analyzers.domains import analyze_domains
from app.analyzers.headers import analyze_headers
from app.analyzers.sender import analyze_sender
from app.analyzers.types import Finding
from app.analyzers.urls import analyze_urls
from app.db.enums import AnalysisStatus, CaseStatus, Severity, Verdict
from app.db.models import AnalysisRun, Email, FindingEvidence, HeaderEvidence, InvestigationCase
from app.integrations.explanation.base import ExplanationInput
from app.integrations.explanation.hosted import HostedLLMProvider
from app.integrations.explanation.local import LocalModelProvider
from app.integrations.explanation.service import ExplanationService
from app.integrations.threat_intel.base import IndicatorLookup
from app.integrations.threat_intel.service import ThreatIntelService
from app.intake.parser import ParsedEmail, parse_email
from app.intake.storage import remove_raw_email, store_raw_email
from app.recommendations.service import RecommendationService
from app.relationships.service import RelationshipService
from app.reports.service import ReportService
from app.risk.engine import RiskEngine


class InvestigationPipelineError(RuntimeError):
    pass


class InvestigationService:
    def __init__(
        self,
        session: Session,
        *,
        threat_intel: ThreatIntelService | None = None,
        explanation: ExplanationService | None = None,
        risk_engine: RiskEngine | None = None,
        raw_root: Path | str = "data/raw_emails",
        report_root: Path | str = "data/reports",
    ) -> None:
        self.session = session
        self.threat_intel = threat_intel or ThreatIntelService()
        self.explanation = explanation or ExplanationService(_configured_explanation_providers())
        self.risk_engine = risk_engine or RiskEngine()
        self.raw_root = Path(raw_root)
        self.report_root = Path(report_root)

    def investigate(self, raw_bytes: bytes, filename: str, title: str | None = None, analyst_note: str | None = None) -> dict[str, Any]:
        parsed = parse_email(raw_bytes)
        raw_reference = store_raw_email(raw_bytes, self.raw_root)
        case: InvestigationCase | None = None
        try:
            case = self._create_case(parsed, filename, title, analyst_note, raw_reference)
            findings = self._run_local_analysis(parsed)
            self._persist_findings(case, findings)
            relationship_service = RelationshipService(self.session)
            relationship_service.index_case(case)

            indicators = [IndicatorLookup(indicator.type.value, indicator.normalized_value) for indicator in case.indicators]
            enrichment = self.threat_intel.enrich(indicators)
            relationships = relationship_service.relate_case(case)
            campaign = relationship_service.group_possible_campaign(case)

            risk = self.risk_engine.score(findings)
            case.risk_score = risk.score
            case.severity = risk.severity
            case.verdict = Verdict.BENIGN if not findings else Verdict.SUSPICIOUS

            recommendations = RecommendationService().generate(self.session, case, findings)
            explanation_input = ExplanationInput.from_risk_result(risk)
            explanation = self.explanation.explain(explanation_input)
            case.summary = explanation.summary or f"Deterministic analysis produced {len(findings)} finding(s)."
            case.status = CaseStatus.REVIEW

            analysis_result = {
                "case_id": case.id,
                "analyzer_version": "local-rules-1",
                "findings": [finding.as_dict() for finding in findings],
                "indicators": [_indicator_payload(indicator) for indicator in case.indicators],
                "relationships": [_relationship_payload(item) for item in relationships],
                "campaign": _campaign_payload(campaign),
                "infrastructure": {"status": "unavailable", "limitations": "No infrastructure enrichment was available in this run."},
                "enrichment": enrichment.as_dict(),
                "risk": risk.as_dict(),
                "explanation": explanation.as_dict(),
                "recommendations": [_recommendation_payload(item) for item in recommendations],
            }
            analysis_run = AnalysisRun(case=case, analyzer_version="local-rules-1", status=AnalysisStatus.COMPLETED, result=analysis_result)
            self.session.add(analysis_run)
            self.session.flush()
            self.session.commit()

            report = ReportService(self.session, self.report_root).build(case.id, explanation)
            report_record = ReportService(self.session, self.report_root).persist(case.id, report, "json")
            analysis_result["report"] = {"id": report_record.id, "format": report_record.format, "content_reference": report_record.content_reference}
            return _case_payload(case, analysis_result)
        except Exception as exc:
            traceback.print_exc()
            self.session.rollback()
            remove_raw_email(raw_reference)
            if case is not None:
                case.status = CaseStatus.FAILED
            if isinstance(exc, (InvestigationPipelineError, ValueError)):
                raise
            raise InvestigationPipelineError("The investigation pipeline failed safely.") from exc

    def _create_case(self, parsed: ParsedEmail, filename: str, title: str | None, analyst_note: str | None, raw_reference: str) -> InvestigationCase:
        case = InvestigationCase(
            title=(title or parsed.subject or filename)[:255],
            status=CaseStatus.ANALYZING,
            severity=Severity.LOW,
            verdict=Verdict.INCONCLUSIVE,
            analyst_note=analyst_note,
        )
        email = Email(
            case=case,
            message_id=parsed.message_id,
            subject=parsed.subject,
            sender=parsed.sender,
            recipients=parsed.recipients,
            cc=parsed.cc,
            reply_to=parsed.reply_to,
            sent_at=parsed.sent_at,
            body_text=parsed.body_text,
            body_html=parsed.body_html,
            received_headers=parsed.received_headers,
            authentication_results=parsed.authentication_results,
            urls=parsed.urls,
            attachments=parsed.attachments,
            raw_content_reference=raw_reference,
            raw_sha256=parsed.raw_sha256,
        )
        email.headers = [HeaderEvidence(email=email, header_name="Received", value=value) for value in parsed.received_headers]
        email.headers += [HeaderEvidence(email=email, header_name="Authentication-Results", value=value) for value in parsed.authentication_results]
        self.session.add(case)
        self.session.flush()
        return case

    @staticmethod
    def _run_local_analysis(parsed: ParsedEmail) -> list[Finding]:
        findings: list[Finding] = []
        for analyzer in (analyze_sender, analyze_headers, analyze_authentication, analyze_urls, analyze_domains, analyze_attachments, analyze_content):
            findings.extend(analyzer(parsed))
        return findings

    def _persist_findings(self, case: InvestigationCase, findings: Iterable[Finding]) -> None:
        from app.db.models import Finding as FindingModel
        for finding in findings:
            stored = FindingModel(
                case=case,
                category=finding.category,
                rule_id=finding.rule_id,
                title=finding.title,
                description=finding.description,
                severity=Severity(finding.severity),
                score_contribution=finding.score_contribution,
                confidence=finding.confidence,
            )
            stored.evidence = [FindingEvidence(evidence_type=item.type, value=item.value, location=item.location) for item in finding.evidence]
            self.session.add(stored)
        self.session.flush()


def _configured_explanation_providers() -> list[Any]:
    providers: list[Any] = [HostedLLMProvider()]
    if os.getenv("OLLAMA_ENABLED", "0").lower() in {"1", "true", "yes"} or os.getenv("OLLAMA_URL"):
        providers.append(LocalModelProvider())
    return providers


def _indicator_payload(indicator: Any) -> dict[str, Any]:
    return {"id": indicator.id, "type": indicator.type.value, "value": indicator.value, "normalized_value": indicator.normalized_value, "source": indicator.source, "confidence": float(indicator.confidence)}


def _relationship_payload(relationship: Any) -> dict[str, Any]:
    return {"id": relationship.id, "source_case_id": relationship.source_case_id, "target_case_id": relationship.target_case_id, "relationship_type": relationship.relationship_type, "strength": relationship.strength.value, "confidence": float(relationship.confidence), "evidence": relationship.evidence}


def _campaign_payload(campaign: Any) -> dict[str, Any] | None:
    if campaign is None:
        return None
    return {"id": campaign.id, "name": campaign.name, "wording": "possible campaign", "confidence": float(campaign.confidence), "case_ids": sorted(member.id for member in campaign.cases)}


def _recommendation_payload(recommendation: Any) -> dict[str, Any]:
    return {"id": recommendation.id, "action": recommendation.action, "reason": recommendation.reason, "priority": recommendation.priority.value, "evidence_reference": recommendation.evidence_reference}


def _case_payload(case: InvestigationCase, analysis_result: dict[str, Any]) -> dict[str, Any]:
    email = case.email
    return {
        "id": case.id,
        "title": case.title,
        "status": case.status.value,
        "risk_score": case.risk_score,
        "severity": case.severity.value,
        "verdict": case.verdict.value,
        "summary": case.summary,
        "analysis": analysis_result,
        "email": {
            "id": email.id,
            "message_id": email.message_id,
            "subject": email.subject,
            "from": email.sender,
            "to": email.recipients,
            "cc": email.cc,
            "reply_to": email.reply_to,
            "date": email.sent_at.isoformat() if email.sent_at else None,
            "received": email.received_headers,
            "authentication_results": email.authentication_results,
            "body_text": email.body_text,
            "body_html": email.body_html,
            "urls": email.urls,
            "attachments": email.attachments,
        } if email else None,
    }
