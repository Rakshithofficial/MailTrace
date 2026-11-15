"""Small, explainable weighted risk engine with no model or network dependency."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.analyzers.types import Finding
from app.db.enums import Severity
from app.db.models import InvestigationCase

DEFAULT_WEIGHTS: dict[str, float] = {
    "SENDER": 1.0,
    "HEADER": 1.0,
    "AUTHENTICATION": 1.0,
    "URL": 1.0,
    "DOMAIN": 1.0,
    "ATTACHMENT": 1.0,
    "CONTENT": 1.0,
    "THREAT_INTELLIGENCE": 1.0,
}

SEVERITY_BANDS: tuple[tuple[int, int, Severity], ...] = (
    (0, 24, Severity.LOW),
    (25, 49, Severity.MEDIUM),
    (50, 74, Severity.HIGH),
    (75, 100, Severity.CRITICAL),
)


@dataclass(frozen=True)
class RiskContributor:
    rule_id: str
    category: str
    title: str
    contribution: int
    evidence: list[dict[str, Any]]


@dataclass(frozen=True)
class RiskResult:
    raw_score: int
    score: int
    severity: Severity
    contributors: list[RiskContributor]

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["severity"] = self.severity.value
        return result


class RiskEngine:
    """Calculate a bounded score from deterministic analyzer findings."""

    def __init__(self, weights: Mapping[str, float] | None = None) -> None:
        configured = dict(DEFAULT_WEIGHTS)
        if weights:
            configured.update({key.upper(): float(value) for key, value in weights.items()})
        if any(value < 0 for value in configured.values()):
            raise ValueError("Risk weights cannot be negative.")
        self.weights = configured

    def score(self, findings: list[Finding]) -> RiskResult:
        contributors: list[RiskContributor] = []
        seen: set[tuple[str, str]] = set()
        raw_score = 0
        for finding in findings:
            identity = (finding.rule_id, finding.category.upper())
            if identity in seen:
                continue
            seen.add(identity)
            multiplier = self.weights.get(finding.category.upper(), 1.0)
            contribution = max(0, round(finding.score_contribution * multiplier))
            if contribution == 0:
                continue
            raw_score += contribution
            contributors.append(
                RiskContributor(
                    rule_id=finding.rule_id,
                    category=finding.category,
                    title=finding.title,
                    contribution=contribution,
                    evidence=[asdict(item) for item in finding.evidence],
                )
            )

        score = min(100, raw_score)
        severity = next(band for lower, upper, band in SEVERITY_BANDS if lower <= score <= upper)
        return RiskResult(raw_score, score, severity, contributors)

    def score_and_store(
        self,
        session: Session,
        case: InvestigationCase,
        findings: list[Finding],
    ) -> RiskResult:
        result = self.score(findings)
        case.risk_score = result.score
        case.severity = result.severity
        session.add(case)
        session.flush()
        return result
