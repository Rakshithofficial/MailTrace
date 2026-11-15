"""Provider contracts and normalized, non-finding enrichment results."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class IndicatorLookup:
    indicator_type: str
    normalized_value: str


@dataclass(frozen=True)
class ProviderResult:
    source: str
    indicator_type: str
    normalized_value: str
    status: str
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EnrichmentResult:
    status: str
    providers: list[ProviderResult]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "providers": [provider.as_dict() for provider in self.providers],
        }


HttpRequester = Callable[[str, Mapping[str, str], float], tuple[int, bytes]]


class ThreatIntelProvider(ABC):
    """Read-only normalized-indicator lookup contract."""

    source: str

    @abstractmethod
    def lookup(self, indicator: IndicatorLookup) -> ProviderResult:
        raise NotImplementedError


def normalize_status(provider_results: list[ProviderResult]) -> str:
    if any(result.status == "available" for result in provider_results):
        return "available"
    if provider_results and all(result.status == "unavailable" for result in provider_results):
        return "unavailable"
    return "partial"
