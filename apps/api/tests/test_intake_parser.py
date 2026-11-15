from email.message import EmailMessage
from hashlib import sha256
from pathlib import Path

from app.intake.parser import parse_email


def sample_eml() -> bytes:
    message = EmailMessage()
    message["From"] = "Billing Desk <billing@example.test>"
    message["To"] = "analyst@example.test"
    message["Cc"] = "reviewer@example.test"
    message["Reply-To"] = "reply@example.test"
    message["Subject"] = "Controlled invoice"
    message["Date"] = "Tue, 23 Sep 2026 10:00:00 +0000"
    message["Message-ID"] = "<controlled-001@example.test>"
    message["Received"] = "from mx.example.test (198.51.100.10) by mail.example.test"
    message["Authentication-Results"] = "mail.example.test; spf=pass"
    message.set_content("Review https://example.test/invoice.\n")
    message.add_alternative("<p>Review <a href='https://example.test/invoice'>invoice</a>.</p>", subtype="html")
    message.add_attachment(b"synthetic attachment", maintype="application", subtype="octet-stream", filename="invoice.txt")
    return message.as_bytes()


def test_repository_fixture_is_parseable():
    fixture = Path(__file__).parents[3] / "sample_data" / "benign" / "intake-basic.eml"
    parsed = parse_email(fixture.read_bytes())
    assert parsed.message_id == "<intake-basic@example.test>"
    assert parsed.attachments[0]["filename"] == "notice.txt"


def test_parse_extracts_headers_bodies_urls_and_attachment_metadata():
    raw = sample_eml()
    parsed = parse_email(raw)

    assert parsed.sender == "billing@example.test"
    assert parsed.recipients == ["analyst@example.test"]
    assert parsed.cc == ["reviewer@example.test"]
    assert parsed.reply_to == "reply@example.test"
    assert parsed.subject == "Controlled invoice"
    assert parsed.message_id == "<controlled-001@example.test>"
    assert parsed.sent_at.isoformat() == "2026-09-23T10:00:00+00:00"
    assert parsed.received_headers == ["from mx.example.test (198.51.100.10) by mail.example.test"]
    assert parsed.authentication_results == ["mail.example.test; spf=pass"]
    assert "https://example.test/invoice" in [item["value"] for item in parsed.urls]
    assert parsed.body_text and "Review" in parsed.body_text
    assert parsed.body_html and "example.test/invoice" in parsed.body_html
    assert parsed.attachments[0]["filename"] == "invoice.txt"
    assert parsed.attachments[0]["size"] == len(b"synthetic attachment")
    assert parsed.attachments[0]["sha256"] == sha256(b"synthetic attachment").hexdigest()


def test_parse_does_not_fetch_urls_or_store_attachment_bytes():
    parsed = parse_email(sample_eml())
    assert all("content" not in attachment for attachment in parsed.attachments)
    assert all(item["scheme"] in {"http", "https"} for item in parsed.urls)
