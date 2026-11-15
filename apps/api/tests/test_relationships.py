from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.enums import CaseStatus, Severity, Verdict
from app.db.models import Email, InvestigationCase, Relationship
from app.db.session import get_session
from app.main import app
from app.relationships.service import RelationshipService


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def add_case(session, case_id, created_at, url, attachment_hash, sender):
    case = InvestigationCase(
        id=case_id,
        title=f"Controlled case {case_id}",
        status=CaseStatus.REVIEW,
        severity=Severity.HIGH,
        verdict=Verdict.SUSPICIOUS,
        created_at=created_at,
        updated_at=created_at,
    )
    Email(
        case=case,
        sender=sender,
        recipients=["analyst@example.test"],
        body_text=f"Unique message for {case_id}",
        urls=[{"value": url, "host": url.split("/")[2], "location": "body_text"}],
        attachments=[{"filename": "invoice.bin", "sha256": attachment_hash}],
        received_headers=[],
        authentication_results=[],
        raw_content_reference=f"sample_data/phishing/{case_id}.eml",
        raw_sha256=case_id * 64,
    )
    session.add(case)
    session.flush()
    return case


def test_three_case_chain_creates_strong_relationships_and_possible_campaign():
    session = make_session()
    start = datetime(2026, 9, 23, tzinfo=timezone.utc)
    case_a = add_case(session, "case-a", start, "https://campaign.test/a", "a" * 64, "a@sender-a.test")
    case_b = add_case(session, "case-b", start + timedelta(minutes=1), "https://campaign.test/b", "b" * 64, "b@sender-b.test")
    case_c = add_case(session, "case-c", start + timedelta(minutes=2), "https://other.test/c", "b" * 64, "c@sender-c.test")
    service = RelationshipService(session)

    service.index_case(case_a)
    service.relate_case(case_b)
    service.relate_case(case_c)
    campaign = service.group_possible_campaign(case_c)
    session.commit()

    assert campaign is not None
    assert {member.id for member in campaign.cases} == {"case-a", "case-b", "case-c"}
    relationships = list(session.scalars(select(Relationship)).all())
    types = {relationship.relationship_type for relationship in relationships}
    assert "SHARED_DOMAIN" in types or "SHARED_ATTACHMENT_HASH" in types
    assert campaign.name.startswith("Possible campaign")


def test_related_case_api_returns_chain_edges_and_campaign(monkeypatch):
    session = make_session()
    start = datetime(2026, 9, 23, tzinfo=timezone.utc)
    case_a = add_case(session, "api-a", start, "https://campaign.test/a", "a" * 64, "a@sender-a.test")
    case_b = add_case(session, "api-b", start + timedelta(minutes=1), "https://campaign.test/b", "b" * 64, "b@sender-b.test")
    case_c = add_case(session, "api-c", start + timedelta(minutes=2), "https://other.test/c", "b" * 64, "c@sender-c.test")
    service = RelationshipService(session)
    service.index_case(case_a)
    service.relate_case(case_b)
    service.relate_case(case_c)
    service.group_possible_campaign(case_c)
    session.commit()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        relationship_response = client.get("/api/v1/cases/api-c/relationships")
        campaign_response = client.get("/api/v1/cases/api-c/campaigns")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert relationship_response.status_code == 200
    assert "api-b" in {item["id"] for item in relationship_response.json()["related_cases"]}
    assert campaign_response.status_code == 200
    campaign = campaign_response.json()["campaigns"][0]
    assert campaign["wording"] == "possible campaign"
    assert set(campaign["case_ids"]) == {"api-a", "api-b", "api-c"}
