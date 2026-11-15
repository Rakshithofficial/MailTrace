"""Seed controlled, inert records for local development and tests."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .enums import CaseStatus, IndicatorType, Severity, Verdict
from .models import Email, Indicator, InvestigationCase


SAMPLE_CASE_ID = "11111111-1111-1111-1111-111111111111"
SAMPLE_EMAIL_ID = "22222222-2222-2222-2222-222222222222"
SAMPLE_INDICATOR_ID = "33333333-3333-3333-3333-333333333333"


def seed_controlled_cases(session: Session) -> None:
    """Insert one safe synthetic case and indicator when the database is empty."""
    if session.get(InvestigationCase, SAMPLE_CASE_ID) is not None:
        return

    now = datetime.now(timezone.utc)
    case = InvestigationCase(
        id=SAMPLE_CASE_ID,
        title="Synthetic invoice review",
        status=CaseStatus.REVIEW,
        risk_score=0,
        severity=Severity.LOW,
        verdict=Verdict.INCONCLUSIVE,
        summary="Controlled fixture for database development only.",
        created_at=now,
        updated_at=now,
    )
    email = Email(
        id=SAMPLE_EMAIL_ID,
        case=case,
        message_id="<synthetic-001@example.test>",
        subject="Synthetic invoice review",
        sender="billing@example.test",
        recipients=["analyst@example.test"],
        raw_content_reference="sample_data/benign/synthetic-001.eml",
        raw_sha256="0" * 64,
        created_at=now,
    )
    indicator = Indicator(
        id=SAMPLE_INDICATOR_ID,
        type=IndicatorType.DOMAIN,
        value="example.test",
        normalized_value="example.test",
        source="seed_fixture",
        confidence=1.0,
        first_seen=now,
        last_seen=now,
    )
    case.indicators.append(indicator)
    session.add(case)
    session.commit()
