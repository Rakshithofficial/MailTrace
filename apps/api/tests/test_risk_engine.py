from app.analyzers.types import Evidence, Finding
from app.db.enums import CaseStatus, Severity, Verdict
from app.db.models import InvestigationCase
from app.risk.engine import RiskEngine


def finding(rule_id: str, category: str, contribution: int, title: str | None = None) -> Finding:
    return Finding(
        rule_id=rule_id,
        category=category,
        title=title or rule_id,
        description="controlled test finding",
        severity="MEDIUM",
        score_contribution=contribution,
        confidence=0.9,
        evidence=[Evidence("test", rule_id, "fixture", "unit_test")],
    )


def test_benign_email_scores_low_with_no_contributors():
    result = RiskEngine().score([])

    assert result.score == 0
    assert result.raw_score == 0
    assert result.severity is Severity.LOW
    assert result.contributors == []


def test_medium_risk_email_uses_severity_band():
    result = RiskEngine().score([
        finding("SENDER-003", "SENDER", 10),
        finding("DOMAIN-003", "DOMAIN", 20),
    ])

    assert result.score == 30
    assert result.severity is Severity.MEDIUM
    assert [item.rule_id for item in result.contributors] == ["SENDER-003", "DOMAIN-003"]


def test_high_risk_email_is_stored_on_investigation_case():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db.base import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    case = InvestigationCase(title="High-risk test", status=CaseStatus.RECEIVED, verdict=Verdict.INCONCLUSIVE)
    session.add(case)
    session.flush()

    result = RiskEngine().score_and_store(session, case, [
        finding("AUTH-001", "AUTHENTICATION", 15),
        finding("ATTACH-002", "ATTACHMENT", 15),
        finding("DOMAIN-001", "DOMAIN", 20),
    ])

    assert result.score == 50
    assert result.severity is Severity.HIGH
    assert case.risk_score == 50
    assert case.severity is Severity.HIGH


def test_multiple_simultaneous_findings_are_traceable_and_capped():
    findings = [
        finding("SENDER-003", "SENDER", 10),
        finding("DOMAIN-001", "DOMAIN", 20),
        finding("URL-003", "URL", 25),
        finding("AUTH-001", "AUTHENTICATION", 15),
        finding("ATTACH-002", "ATTACHMENT", 15),
        finding("CONTENT-001", "CONTENT", 10),
    ]
    result = RiskEngine().score(findings)

    assert result.raw_score == 95
    assert result.score == 95
    assert result.severity is Severity.CRITICAL
    assert sum(item.contribution for item in result.contributors) == result.score
    assert all(item.evidence for item in result.contributors)


def test_weights_are_configurable_and_duplicate_rules_are_counted_once():
    engine = RiskEngine(weights={"url": 2.0, "sender": 0.5})
    result = engine.score([
        finding("URL-003", "URL", 25),
        finding("URL-003", "URL", 25),
        finding("SENDER-003", "SENDER", 10),
    ])

    assert result.raw_score == 55
    assert result.score == 55
    assert [item.contribution for item in result.contributors] == [50, 5]
