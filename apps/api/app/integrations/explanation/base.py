"""Contracts for bounded, structured case explanations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any, Callable, Mapping

from app.risk.engine import RiskResult


@dataclass(frozen=True)
class ExplanationInput:
    risk_score: int
    severity: str
    findings: list[dict[str, Any]]

    @classmethod
    def from_risk_result(cls, result: RiskResult) -> "ExplanationInput":
        return cls(
            risk_score=result.score,
            severity=result.severity.value,
            findings=[
                {
                    "rule_id": contributor.rule_id,
                    "title": contributor.title,
                    "category": contributor.category,
                    "contribution": contributor.contribution,
                    "evidence": contributor.evidence,
                }
                for contributor in result.contributors
            ],
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExplanationResult:
    source: str
    status: str
    summary: str
    explanation: str
    recommendations: list[str]
    risk_score: int
    severity: str
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


HttpRequester = Callable[[str, Mapping[str, str], bytes, float], tuple[int, bytes]]


class ExplanationProvider(ABC):
    source: str

    @abstractmethod
    def explain(self, case: ExplanationInput) -> ExplanationResult:
        raise NotImplementedError
