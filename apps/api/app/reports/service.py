"""Evidence-preserving JSON and PDF investigation reports."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import AnalysisRun, Campaign, InvestigationCase, Relationship, Report
from app.integrations.explanation.base import ExplanationResult

SECRET_PATTERN = re.compile(r"(?i)(api[_-]?key|authorization|bearer|token|password|secret)\s*[:=]\s*[^\s,;]+")


class ReportUnavailableError(ValueError):
    pass


def _safe(value: Any, limit: int = 800) -> str:
    if value is None or value == "":
        return "Unavailable"
    text = SECRET_PATTERN.sub(r"\1: [REDACTED]", str(value))
    return text[:limit] + ("..." if len(text) > limit else "")


def _section(data: Any, *, note: str | None = None) -> dict[str, Any]:
    if data is None or data == [] or data == {}:
        return {"status": "unavailable", "data": None, "note": note or "No data was stored for this section."}
    return {"status": "available", "data": data}


class ReportService:
    def __init__(self, session: Session, output_root: Path | str = "data/reports") -> None:
        self.session = session
        self.output_root = Path(output_root)

    def build(self, case_id: str, explanation: ExplanationResult | None = None) -> dict[str, Any]:
        case = self.session.get(InvestigationCase, case_id)
        if case is None:
            raise ReportUnavailableError("The requested case does not exist.")
        generated_at = datetime.now(timezone.utc)
        email = case.email
        latest_analysis = self.session.scalar(
            select(AnalysisRun)
            .where(AnalysisRun.case_id == case.id)
            .order_by(AnalysisRun.created_at.desc())
        )
        analysis_result = latest_analysis.result if latest_analysis else {}
        relationships = list(self.session.scalars(select(Relationship).where(or_(Relationship.source_case_id == case.id, Relationship.target_case_id == case.id))))
        campaigns = [campaign for campaign in self.session.scalars(select(Campaign)).all() if any(member.id == case.id for member in campaign.cases)]

        findings = [self._finding(item) for item in case.findings]
        explanation_data = explanation.as_dict() if explanation else analysis_result.get("explanation")
        if explanation_data:
            explanation_data = {
                "source": explanation_data.get("source", "stored_analysis"),
                "status": explanation_data.get("status", "available"),
                "summary": _safe(explanation_data.get("summary") or explanation_data.get("text")),
                "explanation": _safe(explanation_data.get("explanation") or explanation_data.get("text")),
                "recommendations": [_safe(item, 300) for item in explanation_data.get("recommendations", [])],
            }
        timeline = self._timeline(case, latest_analysis, generated_at)
        return {
            "report_version": "1.0",
            "generated_at": generated_at.isoformat(),
            "case_id": case.id,
            "sections": {
                "case": _section({"id": case.id, "title": _safe(case.title), "status": case.status.value, "verdict": case.verdict.value}),
                "investigation_timestamp": _section(generated_at.isoformat()),
                "email_summary": _section(self._email_summary(email)),
                "sender_recipient_information": _section(self._sender_recipients(email)),
                "header_findings": _section([item for item in findings if item["category"] == "HEADER"]),
                "authentication_findings": _section([item for item in findings if item["category"] == "AUTHENTICATION"]),
                "url_domain_findings": _section([item for item in findings if item["category"] in {"URL", "DOMAIN"}]),
                "attachment_information": _section(self._attachments(email)),
                "infrastructure_intelligence": _section(analysis_result.get("infrastructure"), note="No local or optional infrastructure context was stored."),
                "related_cases": _section([self._relationship(item) for item in relationships]),
                "campaign_information": _section([self._campaign(item) for item in campaigns]),
                "risk": _section({"score": case.risk_score, "severity": case.severity.value, "contributors": analysis_result.get("risk", {}).get("contributors", [])}),
                "contributing_evidence": _section([evidence for item in findings for evidence in item["evidence"]]),
                "explanation": _section(explanation_data, note="No explanation was stored; use the deterministic fallback provider."),
                "recommended_response": _section([{"action": _safe(item.action), "reason": _safe(item.reason), "priority": item.priority.value, "evidence_reference": item.evidence_reference} for item in case.recommendations]),
                "investigation_timeline": _section(timeline),
            },
        }

    def write_json(self, report: dict[str, Any]) -> Path:
        path = self.output_root / f"{report['case_id']}.json"
        self.output_root.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return path

    def write_pdf(self, report: dict[str, Any]) -> Path:
        path = self.output_root / f"{report['case_id']}.pdf"
        self.output_root.mkdir(parents=True, exist_ok=True)
        document = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=16 * mm, leftMargin=16 * mm, topMargin=15 * mm, bottomMargin=15 * mm)
        styles = getSampleStyleSheet()
        styles["Title"].fontName = "Helvetica-Bold"
        styles["Title"].textColor = colors.HexColor("#17323b")
        story: list[Any] = [Paragraph("MailTrace Investigation Report", styles["Title"]), Spacer(1, 5 * mm)]
        story.append(Paragraph(f"Case ID: {_safe(report['case_id'])}", styles["Normal"]))
        story.append(Paragraph(f"Generated: {_safe(report['generated_at'])}", styles["Normal"]))
        story.append(Spacer(1, 5 * mm))
        for name, section in report["sections"].items():
            story.append(Paragraph(name.replace("_", " ").title(), styles["Heading2"]))
            if section["status"] == "unavailable":
                story.append(Paragraph(f"Unavailable: {_safe(section['note'])}", styles["Normal"]))
            else:
                story.extend(_pdf_value(section["data"], styles))
            story.append(Spacer(1, 3 * mm))
        document.build(story)
        return path

    def persist(self, case_id: str, report: dict[str, Any], format: str) -> Report:
        if format not in {"json", "pdf"}:
            raise ReportUnavailableError("Report format must be json or pdf.")
        path = self.write_json(report) if format == "json" else self.write_pdf(report)
        record = Report(case_id=case_id, format=format, content_reference=str(path), generated_at=datetime.fromisoformat(report["generated_at"]))
        self.session.add(record)
        self.session.commit()
        return record

    @staticmethod
    def _finding(finding: Any) -> dict[str, Any]:
        return {
            "id": finding.id,
            "category": finding.category,
            "rule_id": finding.rule_id,
            "title": _safe(finding.title),
            "description": _safe(finding.description),
            "severity": finding.severity.value,
            "score_contribution": finding.score_contribution,
            "evidence": [{"id": item.id, "type": item.evidence_type, "location": _safe(item.location), "reference": _safe(item.value)} for item in finding.evidence],
        }

    @staticmethod
    def _email_summary(email: Any) -> dict[str, Any] | None:
        if email is None:
            return None
        return {"message_id": _safe(email.message_id), "subject": _safe(email.subject), "date": email.sent_at.isoformat() if email.sent_at else "Unavailable", "url_count": len(email.urls), "attachment_count": len(email.attachments), "raw_content": "Protected reference omitted from report"}

    @staticmethod
    def _sender_recipients(email: Any) -> dict[str, Any] | None:
        if email is None:
            return None
        return {"from": _safe(email.sender), "to": [_safe(item, 320) for item in email.recipients], "cc": [_safe(item, 320) for item in email.cc], "reply_to": _safe(email.reply_to)}

    @staticmethod
    def _attachments(email: Any) -> list[dict[str, Any]] | None:
        if email is None or not email.attachments:
            return None
        return [{"filename": _safe(item.get("filename")), "content_type": _safe(item.get("content_type")), "size": item.get("size"), "sha256": _safe(item.get("sha256"))} for item in email.attachments]

    @staticmethod
    def _relationship(item: Relationship) -> dict[str, Any]:
        return {"source_case_id": item.source_case_id, "target_case_id": item.target_case_id, "type": item.relationship_type, "strength": item.strength.value, "confidence": float(item.confidence), "evidence": item.evidence}

    @staticmethod
    def _campaign(item: Campaign) -> dict[str, Any]:
        return {"id": item.id, "name": _safe(item.name), "wording": "possible campaign", "confidence": float(item.confidence), "case_ids": sorted(member.id for member in item.cases)}

    @staticmethod
    def _timeline(case: InvestigationCase, analysis: Any, generated_at: datetime) -> list[dict[str, str]]:
        events = [{"timestamp": case.created_at.isoformat(), "event": "Investigation case created"}]
        if case.email:
            events.append({"timestamp": case.email.created_at.isoformat(), "event": "Email intake record stored"})
        if analysis:
            events.append({"timestamp": analysis.created_at.isoformat(), "event": f"Analysis run {analysis.status.value}"})
            if analysis.completed_at:
                events.append({"timestamp": analysis.completed_at.isoformat(), "event": "Analysis completed"})
        events.append({"timestamp": generated_at.isoformat(), "event": "Investigation report generated"})
        return sorted(events, key=lambda item: item["timestamp"])


def _pdf_value(value: Any, styles: Any) -> list[Any]:
    if isinstance(value, dict):
        rows = [[str(key).replace("_", " ").title(), _safe(item, 600)] for key, item in value.items()]
        table = Table(rows, colWidths=[45 * mm, 125 * mm])
        table.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e7eff0")), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#b7c8cb")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8)]))
        return [table]
    if isinstance(value, list):
        return [Paragraph(f"- {_safe(item, 700)}", styles["Normal"]) for item in value] or [Paragraph("None recorded.", styles["Normal"])]
    return [Paragraph(_safe(value), styles["Normal"])]
