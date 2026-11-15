"""Offline domain normalization and simple look-alike checks."""

import re
from urllib.parse import urlsplit

from app.intake.parser import ParsedEmail

from .types import Evidence, Finding

KNOWN_BRANDS = ("microsoft", "paypal", "google", "apple", "amazon", "office365")


def normalize_domain(value: str) -> str:
    return value.lower().rstrip(".").encode("idna").decode("ascii")


def _sender_domain(email: ParsedEmail) -> str:
    return normalize_domain(email.sender.rsplit("@", 1)[1]) if email.sender and "@" in email.sender else ""


def _looks_like_brand(domain: str) -> bool:
    compact = domain.replace("-", "").replace(".", "")
    confusable = compact.translate(str.maketrans({"0": "o", "1": "l", "3": "e", "5": "s", "@": "a"}))
    return any(brand in compact or brand in confusable for brand in KNOWN_BRANDS)


def analyze_domains(email: ParsedEmail) -> list[Finding]:
    findings: list[Finding] = []
    sender_domain = _sender_domain(email)
    for item in email.urls:
        host = item.get("host") or urlsplit(item.get("value", "")).hostname or ""
        if not host:
            continue
        normalized = normalize_domain(host)
        evidence = [Evidence("domain", normalized, item.get("location", "body"), "local_parser")]
        if _looks_like_brand(normalized) and not any(normalized == f"{brand}.com" for brand in KNOWN_BRANDS):
            findings.append(Finding("DOMAIN-001", "DOMAIN", "Possible look-alike domain", "The domain contains a known brand name without matching its canonical domain.", "HIGH", 20, 0.8, evidence))
        if sender_domain and normalized != sender_domain and normalized != f"www.{sender_domain}":
            findings.append(Finding("DOMAIN-003", "DOMAIN", "Link and sender domains differ", "A body URL domain differs from the sender domain.", "MEDIUM", 10, 0.75, [Evidence("domain", f"sender={sender_domain}; link={normalized}", "headers/body", "local_parser")]))
        if re.search(r"[^a-z0-9.-]", normalized):
            findings.append(Finding("DOMAIN-001", "DOMAIN", "Suspicious domain formatting", "The normalized domain contains unexpected characters.", "MEDIUM", 20, 0.8, evidence))
    return findings