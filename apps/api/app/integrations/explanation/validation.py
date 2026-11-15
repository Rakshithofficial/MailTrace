"""Strict validation for model-produced explanation objects."""

from __future__ import annotations

from typing import Any

from .base import ExplanationInput, ExplanationResult

MAX_TEXT_LENGTH = 4000
MAX_RECOMMENDATIONS = 8


class ExplanationValidationError(ValueError):
    pass


def validate_model_output(payload: Any, case: ExplanationInput, source: str) -> ExplanationResult:
    if not isinstance(payload, dict):
        raise ExplanationValidationError("Model output must be a JSON object.")
    required = {"summary", "explanation", "recommendations"}
    if set(payload) != required:
        raise ExplanationValidationError("Model output must contain only summary, explanation, and recommendations.")
    summary = payload.get("summary")
    explanation = payload.get("explanation")
    recommendations = payload.get("recommendations")
    if not isinstance(summary, str) or not summary.strip() or len(summary) > MAX_TEXT_LENGTH:
        raise ExplanationValidationError("summary must be a non-empty bounded string.")
    if not isinstance(explanation, str) or not explanation.strip() or len(explanation) > MAX_TEXT_LENGTH:
        raise ExplanationValidationError("explanation must be a non-empty bounded string.")
    if not isinstance(recommendations, list) or not 1 <= len(recommendations) <= MAX_RECOMMENDATIONS:
        raise ExplanationValidationError("recommendations must contain between one and eight items.")
    if any(not isinstance(item, str) or not item.strip() or len(item) > 500 for item in recommendations):
        raise ExplanationValidationError("Each recommendation must be a bounded string.")
    return ExplanationResult(
        source=source,
        status="available",
        summary=summary.strip(),
        explanation=explanation.strip(),
        recommendations=[item.strip() for item in recommendations],
        risk_score=case.risk_score,
        severity=case.severity,
    )
