"""Offline local provider and explicit no-op fallback."""

from __future__ import annotations

from typing import Any, Mapping

from .base import IndicatorLookup, ProviderResult, ThreatIntelProvider


class LocalProvider(ThreatIntelProvider):
    source = "local"

    def __init__(self, records: Mapping[tuple[str, str], Mapping[str, Any]] | None = None) -> None:
        self.records = {key: dict(value) for key, value in (records or {}).items()}

    def lookup(self, indicator: IndicatorLookup) -> ProviderResult:
        record = self.records.get((indicator.indicator_type.upper(), indicator.normalized_value))
        return ProviderResult(
            source=self.source,
            indicator_type=indicator.indicator_type,
            normalized_value=indicator.normalized_value,
            status="available",
            result=dict(record or {"verdict": "unknown", "matches": []}),
        )


class NoOpProvider(ThreatIntelProvider):
    source = "noop"

    def lookup(self, indicator: IndicatorLookup) -> ProviderResult:
        return ProviderResult(
            source=self.source,
            indicator_type=indicator.indicator_type,
            normalized_value=indicator.normalized_value,
            status="unavailable",
            error="No threat-intelligence provider configured.",
        )
