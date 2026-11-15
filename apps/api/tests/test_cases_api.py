from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_session
from main import app


engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine, expire_on_commit=False)


def override_session():
    session = Session()
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_session] = override_session
client = TestClient(app)


def test_create_case_from_eml_persists_parsed_content(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    eml = b"""From: sender@example.test\nTo: analyst@example.test\nCc: reviewer@example.test\nReply-To: reply@example.test\nSubject: API fixture\nDate: Tue, 23 Sep 2026 10:00:00 +0000\nMessage-ID: <api-001@example.test>\nReceived: from 198.51.100.20 by mx.example.test\nAuthentication-Results: mx.example.test; dkim=pass\nContent-Type: text/plain; charset=utf-8\n\nVisit https://example.test/path.\n"""

    response = client.post(
        "/api/v1/cases",
        files={"file": ("fixture.eml", eml, "message/rfc822")},
        data={"title": "API fixture"},
    )

    assert response.status_code == 201
    result = response.json()
    assert result["status"] == "REVIEW"
    assert result["analysis"]["risk"]["score"] == 0
    assert result["email"]["from"] == "sender@example.test"
    assert result["email"]["cc"] == ["reviewer@example.test"]
    assert result["email"]["urls"][0]["value"] == "https://example.test/path"
    assert list(Path("data/raw_emails").glob("*.eml"))


def test_create_case_rejects_non_eml_without_storing():
    response = client.post(
        "/api/v1/cases",
        files={"file": ("fixture.txt", b"not an email", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE"
