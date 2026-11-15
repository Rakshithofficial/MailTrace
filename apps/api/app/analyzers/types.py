"""Stable analyzer output structures."""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Evidence:
    type: str
    value: str
    location: str
    source: str
    limitations: str = ""


@dataclass(frozen=True)
class Finding:
    rule_id: str
    category: str
    title: str
    description: str
    severity: str
    score_contribution: int
    confidence: float
    evidence: list[Evidence] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)