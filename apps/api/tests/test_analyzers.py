from pathlib import Path

from app.analyzers.attachments import analyze_attachments
from app.analyzers.authentication import analyze_authentication
from app.analyzers.content import analyze_content
from app.analyzers.domains import analyze_domains
from app.analyzers.headers import analyze_headers
from app.analyzers.sender import analyze_sender
from app.analyzers.urls import analyze_urls
from app.intake.parser import parse_email


ROOT = Path(__file__).parents[3]
BENIGN = parse_email((ROOT / "sample_data" / "benign" / "intake-basic.eml").read_bytes())
PHISHING = parse_email((ROOT / "sample_data" / "phishing" / "local-analysis-basic.eml").read_bytes())


def rule_ids(findings):
    return {finding.rule_id for finding in findings}


def test_sender_analyzer_detects_reply_to_and_display_name_mismatch():
    findings = analyze_sender(PHISHING)
    assert {"SENDER-002", "SENDER-003"}.issubset(rule_ids(findings))
    assert all(finding.evidence and finding.score_contribution > 0 for finding in findings)


def test_header_analyzer_accepts_complete_benign_headers():
    assert analyze_headers(BENIGN) == []


def test_header_analyzer_reports_malformed_received_header():
    malformed = PHISHING.__class__(**{**PHISHING.__dict__, "received_headers": ["unexpected routing text"]})
    findings = analyze_headers(malformed)
    assert "HEADER-002" in rule_ids(findings)


def test_authentication_analyzer_reports_explicit_failures_only():
    findings = analyze_authentication(PHISHING)
    assert {"AUTH-001", "AUTH-002", "AUTH-003"}.issubset(rule_ids(findings))
    assert analyze_authentication(BENIGN) == []


def test_url_analyzer_reports_unusual_structure_without_fetching():
    findings = analyze_urls(PHISHING)
    assert "URL-003" not in rule_ids(findings)
    assert all(finding.evidence[0].type == "url" for finding in findings)

    raw_ip = PHISHING.__class__(**{**PHISHING.__dict__, "urls": [{"value": "http://198.51.100.4:8080/login", "scheme": "http", "host": "198.51.100.4", "location": "body_text"}]})
    assert "URL-003" in rule_ids(analyze_urls(raw_ip))


def test_domain_analyzer_reports_link_sender_difference_and_brand_lookalike():
    findings = analyze_domains(PHISHING)
    assert {"DOMAIN-001", "DOMAIN-003"}.issubset(rule_ids(findings))
    assert analyze_domains(BENIGN) == []


def test_attachment_analyzer_checks_filename_metadata_only():
    findings = analyze_attachments(PHISHING)
    assert "ATTACH-001" in rule_ids(findings)
    assert all("content" not in finding.evidence[0].value for finding in findings)
    assert analyze_attachments(BENIGN) == []


def test_content_analyzer_reports_supporting_social_engineering_signals():
    findings = analyze_content(PHISHING)
    assert {"CONTENT-001", "CONTENT-002"}.issubset(rule_ids(findings))
    assert all(finding.category == "CONTENT" for finding in findings)
    assert analyze_content(BENIGN) == []
