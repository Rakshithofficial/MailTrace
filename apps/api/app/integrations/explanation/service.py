"""Provider orchestration with deterministic fallback."""

from __future__ import annotations

from collections.abc import Iterable

from .base import ExplanationInput, ExplanationProvider, ExplanationResult
from .fallback import FallbackExplanationProvider
from .hosted import HostedLLMProvider
from .local import LocalModelProvider


class ExplanationService:
    def __init__(
        self,
        providers: Iterable[ExplanationProvider] | None = None,
        fallback: ExplanationProvider | None = None,
    ) -> None:
        self.providers = list(providers) if providers is not None else [HostedLLMProvider(), LocalModelProvider()]
        self.fallback = fallback or FallbackExplanationProvider()

    def explain(self, case: ExplanationInput) -> ExplanationResult:
        for provider in self.providers:
            try:
                result = provider.explain(case)
            except Exception:
                continue
            if result.status == "available":
                return _preserve_authoritative_fields(result, case)
        return self.fallback.explain(case)


def _preserve_authoritative_fields(result: ExplanationResult, case: ExplanationInput) -> ExplanationResult:
    return ExplanationResult(
        source=result.source,
        status=result.status,
        summary=result.summary,
        explanation=result.explanation,
        recommendations=result.recommendations,
        risk_score=case.risk_score,
        severity=case.severity,
        error=result.error,
    )
