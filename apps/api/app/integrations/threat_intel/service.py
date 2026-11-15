"""Graceful orchestration of optional threat-intelligence providers."""

from __future__ import annotations

from collections.abc import Iterable

from .base import EnrichmentResult, IndicatorLookup, ProviderResult, ThreatIntelProvider, normalize_status
from .local import LocalProvider
from .urlscan import UrlscanProvider
from .virustotal import VirusTotalProvider


class ThreatIntelService:
    def __init__(self, providers: Iterable[ThreatIntelProvider] | None = None) -> None:
        self.providers = list(providers) if providers is not None else [
            LocalProvider(),
            VirusTotalProvider(),
            UrlscanProvider(),
        ]

    def enrich(self, indicators: Iterable[IndicatorLookup]) -> EnrichmentResult:
        results: list[ProviderResult] = []
        for indicator in indicators:
            for provider in self.providers:
                try:
                    results.append(provider.lookup(indicator))
                except Exception as exc:  # provider failures never break local analysis
                    results.append(
                        ProviderResult(
                            source=getattr(provider, "source", provider.__class__.__name__.lower()),
                            indicator_type=indicator.indicator_type,
                            normalized_value=indicator.normalized_value,
                            status="unavailable",
                            error=f"Provider failure: {type(exc).__name__}",
                        )
                    )
        return EnrichmentResult(normalize_status(results), results)
