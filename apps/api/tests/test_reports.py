from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.enums import AnalysisStatus, CaseStatus, RecommendationPriority, Severity, Verdict
from app.db.models import AnalysisRun, Email, Finding, FindingEvidence, InvestigationCase, Recommendation
from app.reports.service import ReportService


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def controlled_case(session):
    now = datetime(2026, 9, 23, 10, 0, tzinfo=timezone.utc)
    case = InvestigationCase(
        id="report-case",
        title="Controlled phishing sample",
        status=CaseStatus.REVIEW,
        risk_score=81,
        severity=Severity.CRITICAL,
        verdict=Verdict.SUSPICIOUS,
        created_at=now,
        updated_at=now,
    )
    email = Email(
        case=case,
        message_id="<report@example.test>",
        subject="Urgent account verification",
        sender="support@example.test",
        recipients=["analyst@example.test"],
        cc=["reviewer@example.test"],
        reply_to="reset@credential-verify.test",
        sent_at=now,
        body_text="Sensitive body content should not be copied into the report.",
        received_headers=["from mx.example.test by mail.example.test"],
        authentication_results=["mail.example.test; spf=fail"],
        urls=[{"value": "https://credential-verify.test/login", "host": "credential-verify.test"}],
        attachments=[{"filename": "invoice.pdf.exe", "content_type": "application/octet-stream", "size": 12, "sha256": "a" * 64}],
        raw_content_reference="secret/raw-email.eml",
        raw_sha256="b" * 64,
        created_at=now,
    )
    finding = Finding(
        case=case,
        category="URL",
        rule_id="URL-003",
        title="Unusual URL structure",
        description="Raw test evidence",
        severity=Severity.HIGH,
        score_contribution=10,
        confidence=0.9,
        created_at=now,
    )
    finding.evidence.append(FindingEvidence(evidence_type="url", value="https://credential-verify.test/login", location="body", evidence_metadata={"api_key": "should-not-appear"}))
    case.recommendations.append(Recommendation(action="Quarantine message", reason="Preserve and review suspicious evidence.", priority=RecommendationPriority.HIGH, evidence_reference={"finding_id": finding.id}))
    case.analysis_runs.append(AnalysisRun(analyzer_version="rules-1", status=AnalysisStatus.COMPLETED, result={"infrastructure": {"source_ips": ["198.51.100.10"], "limitations": "Approximate only"}, "risk": {"contributors": [{"rule_id": "URL-003", "contribution": 10}]}, "explanation": {"status": "fallback", "source": "deterministic_fallback", "text": "Evidence-backed fallback explanation."}}, created_at=now, completed_at=now))
    session.add(case)
    session.commit()
    return case


def test_report_contains_required_sections_without_raw_sensitive_content(tmp_path):
    session = make_session()
    controlled_case(session)
    report = ReportService(session, tmp_path).build("report-case")

    sections = report["sections"]
    required = {"case", "investigation_timestamp", "email_summary", "sender_recipient_information", "header_findings", "authentication_findings", "url_domain_findings", "attachment_information", "infrastructure_intelligence", "related_cases", "campaign_information", "risk", "contributing_evidence", "explanation", "recommended_response", "investigation_timeline"}
    assert required.issubset(sections)
    serialized = str(report)
    assert "Sensitive body content" not in serialized
    assert "secret/raw-email.eml" not in serialized
    assert "should-not-appear" not in serialized
    assert sections["email_summary"]["status"] == "available"
    assert sections["risk"]["data"]["score"] == 81
    assert sections["explanation"]["status"] == "available"


def test_report_marks_missing_sections_unavailable(tmp_path):
    session = make_session()
    now = datetime.now(timezone.utc)
    session.add(InvestigationCase(id="empty-case", title="Empty controlled case", status=CaseStatus.REVIEW, severity=Severity.LOW, verdict=Verdict.INCONCLUSIVE, created_at=now, updated_at=now))
    session.commit()

    report = ReportService(session, tmp_path).build("empty-case")

    assert report["sections"]["email_summary"]["status"] == "unavailable"
    assert report["sections"]["infrastructure_intelligence"]["status"] == "unavailable"
    assert report["sections"]["campaign_information"]["status"] == "unavailable"


def test_pdf_report_is_generated_and_has_pdf_signature(tmp_path):
    session = make_session()
    controlled_case(session)
    service = ReportService(session, tmp_path)
    report = service.build("report-case")
    pdf_path = service.write_pdf(report)

    assert pdf_path.exists()
    assert pdf_path.read_bytes().startswith(b"%PDF")
    assert pdf_path.stat().st_size > 1000
