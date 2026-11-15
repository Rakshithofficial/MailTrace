"""URL structure checks that never request or resolve URLs."""

from ipaddress import ip_address
from urllib.parse import urlsplit

from app.intake.parser import ParsedEmail

from .types import Evidence, Finding


def analyze_urls(email: ParsedEmail) -> list[Finding]:
    findings: list[Finding] = []
    for item in email.urls:
        value = item.get("value", "")
        parsed = urlsplit(value)
        evidence = [Evidence("url", value, item.get("location", "body"), "local_parser")]
        host = (parsed.hostname or "").lower()
        raw_ip = False
        try:
            ip_address(host)
            raw_ip = True
        except ValueError:
            pass
        if raw_ip or "@" in parsed.netloc or parsed.port not in (None, 80, 443):
            findings.append(Finding("URL-003", "URL", "Unusual URL structure", "The URL uses a raw IP, userinfo, or unusual port.", "MEDIUM", 10, 0.9, evidence))
        if host.startswith("xn--") or "%" in parsed.netloc:
            findings.append(Finding("URL-001", "URL", "Obfuscated URL host", "The URL contains encoded or punycode host material.", "MEDIUM", 15, 0.85, evidence))
        if host.startswith(("bit.ly", "tinyurl.com", "t.co", "is.gd")):
            findings.append(Finding("URL-005", "URL", "URL shortener present", "The URL uses a known shortening service.", "MEDIUM", 10, 0.9, evidence))
    return findings