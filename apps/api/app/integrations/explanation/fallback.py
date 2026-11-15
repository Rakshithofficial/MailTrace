"""Deterministic explanation used when no model is available or trusted."""

from .base import ExplanationInput, ExplanationProvider, ExplanationResult


class FallbackExplanationProvider(ExplanationProvider):
    source = "deterministic_fallback"

    def explain(self, case: ExplanationInput) -> ExplanationResult:
        if not case.findings:
            summary = f"The investigation has a {case.severity} risk score of {case.risk_score}, with no recorded findings."
            explanation = "No deterministic security findings were supplied. This is not proof that the message is benign; preserve the message and review it if context changes."
            recommendations = ["Retain the original message and parsed evidence for review."]
        else:
            titles = ", ".join(str(item.get("title", "unnamed finding")) for item in case.findings[:5])
            summary = f"The investigation has a {case.severity} risk score of {case.risk_score}, driven by: {titles}."
            explanation = "This explanation summarizes findings already produced by local rules. The risk score and evidence come from the application, not from a language model."
            recommendations = [
                "Review each cited finding and preserve its evidence.",
                "Quarantine or block suspicious indicators according to analyst policy.",
                "Search for related messages when shared indicators are present.",
            ]
        return ExplanationResult(
            source=self.source,
            status="fallback",
            summary=summary,
            explanation=explanation,
            recommendations=recommendations,
            risk_score=case.risk_score,
            severity=case.severity,
        )
