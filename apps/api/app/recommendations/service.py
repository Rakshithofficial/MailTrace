"""Evidence-backed recommendation templates."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.analyzers.types import Finding
from app.db.enums import RecommendationPriority
from app.db.models import InvestigationCase, Recommendation


class RecommendationService:
    def generate(self, session: Session, case: InvestigationCase, findings: list[Finding]) -> list[Recommendation]:
        recommendations: list[Recommendation] = []
        seen: set[str] = set()

        def add(action: str, reason: str, priority: RecommendationPriority, rule_ids: list[str]) -> None:
            if action in seen:
                return
            seen.add(action)
            recommendations.append(
                Recommendation(
                    case=case,
                    action=action,
                    reason=reason,
                    priority=priority,
                    evidence_reference={"rule_ids": rule_ids},
                )
            )

        rule_ids = [finding.rule_id for finding in findings]
        if findings:
            add("Preserve the original message and evidence", "Retain the inert email, parsed headers, and finding evidence for analyst review.", RecommendationPriority.HIGH, rule_ids)
        if any(finding.category in {"URL", "DOMAIN", "AUTHENTICATION"} for finding in findings):
            add("Quarantine or block confirmed indicators", "Review the cited URL, domain, and authentication evidence before applying defensive controls.", RecommendationPriority.HIGH, [finding.rule_id for finding in findings if finding.category in {"URL", "DOMAIN", "AUTHENTICATION"}])
        if any(finding.category == "ATTACHMENT" for finding in findings):
            add("Do not open the attachment", "The attachment was assessed from metadata and hash only; keep it inert during review.", RecommendationPriority.HIGH, [finding.rule_id for finding in findings if finding.category == "ATTACHMENT"])
        if findings:
            add("Search for related messages", "Compare normalized indicators with stored cases to identify likely related activity.", RecommendationPriority.MEDIUM, rule_ids)

        session.add_all(recommendations)
        session.flush()
        return recommendations
