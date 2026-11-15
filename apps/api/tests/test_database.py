from datetime import datetime, timezone

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.enums import CaseStatus, IndicatorType, Severity, Verdict
from app.db.models import Email, Indicator, InvestigationCase
from app.db.seed import seed_controlled_cases


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_schema_contains_documented_tables_and_indexes():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    database = inspect(engine)

    expected_tables = {
        "investigation_cases",
        "emails",
        "header_evidence",
        "indicators",
        "case_indicators",
        "findings",
        "finding_evidence",
        "relationships",
        "campaigns",
        "campaign_cases",
        "recommendations",
        "analysis_runs",
        "reports",
    }
    assert expected_tables.issubset(set(database.get_table_names()))
    assert {index["name"] for index in database.get_indexes("investigation_cases")} == {
        "ix_investigation_cases_status_created",
        "ix_investigation_cases_severity_created",
    }
    assert any(column["name"] == "case_id" for column in database.get_columns("emails"))


def test_case_email_and_indicator_foreign_keys_persist():
    session = make_session()
    now = datetime.now(timezone.utc)
    case = InvestigationCase(
        title="Controlled test case",
        status=CaseStatus.RECEIVED,
        severity=Severity.LOW,
        verdict=Verdict.INCONCLUSIVE,
        created_at=now,
        updated_at=now,
    )
    email = Email(
        case=case,
        sender="sender@example.test",
        recipients=["analyst@example.test"],
        raw_content_reference="quarantine/case.eml",
        raw_sha256="a" * 64,
    )
    indicator = Indicator(
        type=IndicatorType.DOMAIN,
        value="Example.TEST",
        normalized_value="example.test",
        source="fixture",
        confidence=1.0,
        first_seen=now,
        last_seen=now,
    )
    case.indicators.append(indicator)
    session.add(case)
    session.commit()

    stored = session.get(InvestigationCase, case.id)
    assert stored is not None
    assert stored.email.raw_content_reference == "quarantine/case.eml"
    assert stored.indicators[0].normalized_value == "example.test"


def test_seed_support_is_idempotent_and_uses_safe_reference():
    session = make_session()
    seed_controlled_cases(session)
    seed_controlled_cases(session)

    cases = session.query(InvestigationCase).all()
    assert len(cases) == 1
    assert cases[0].email.raw_content_reference.startswith("sample_data/")
    assert cases[0].email.raw_sha256 == "0" * 64
