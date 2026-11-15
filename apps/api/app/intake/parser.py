"""Safe, offline RFC 5322/MIME parsing for controlled email intake."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from email import policy
from email.message import Message
from email.parser import BytesParser
from email.utils import getaddresses, parseaddr, parsedate_to_datetime
from typing import Any
from urllib.parse import urlparse

URL_PATTERN = re.compile(r"(?i)\b(?:https?://|ftp://)[^\s<>\"']+")
AUTHENTICATION_HEADERS = {"authentication-results", "received-spf", "arc-authentication-results"}


class EmailParseError(ValueError):
    """Raised when an uploaded message cannot be safely parsed."""


@dataclass(frozen=True)
class ParsedEmail:
    message_id: str | None
    subject: str | None
    sender: str | None
    sender_display_name: str | None
    recipients: list[str]
    cc: list[str]
    reply_to: str | None
    sent_at: Any
    body_text: str | None
    body_html: str | None
    received_headers: list[str]
    authentication_results: list[str]
    urls: list[dict[str, str]]
    attachments: list[dict[str, Any]]
    raw_sha256: str


def _addresses(header_value: str | None) -> list[str]:
    if not header_value:
        return []
    return [address for _, address in getaddresses([header_value]) if address]


def _single_address(header_value: str | None) -> str | None:
    addresses = _addresses(header_value)
    return addresses[0] if addresses else None


def _display_name(header_value: str | None) -> str | None:
    display_name, _ = parseaddr(header_value or "")
    return display_name or None


def _safe_text(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        raw_payload = part.get_payload()
        return raw_payload if isinstance(raw_payload, str) else ""
    charset = part.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def _extract_urls(*bodies: str | None) -> list[dict[str, str]]:
    extracted: list[dict[str, str]] = []
    seen: set[str] = set()
    for location, body in (("body_text", bodies[0]), ("body_html", bodies[1])):
        for match in URL_PATTERN.finditer(body or ""):
            value = match.group(0).rstrip(".,;:!?)]}")
            if value in seen:
                continue
            seen.add(value)
            parsed = urlparse(value)
            extracted.append({"value": value, "scheme": parsed.scheme, "host": parsed.hostname or "", "location": location})
    return extracted


def parse_email(raw_bytes: bytes) -> ParsedEmail:
    if not raw_bytes:
        raise EmailParseError("The uploaded email is empty.")

    try:
        message = BytesParser(policy=policy.default).parsebytes(raw_bytes)
    except (ValueError, TypeError) as exc:
        raise EmailParseError("The uploaded file is not a readable RFC 5322 message.") from exc

    text_parts: list[str] = []
    html_parts: list[str] = []
    attachments: list[dict[str, Any]] = []
    received_headers = [str(value) for value in message.get_all("Received", [])]
    authentication_results = [
        str(value)
        for header_name, value in message.raw_items()
        if header_name.lower() in AUTHENTICATION_HEADERS
    ]

    for part in message.walk():
        if part.is_multipart():
            continue
        filename = part.get_filename()
        payload = part.get_payload(decode=True)
        if filename or part.get_content_disposition() == "attachment":
            attachment_bytes = payload or b""
            attachments.append(
                {
                    "filename": filename or "unnamed",
                    "content_type": part.get_content_type(),
                    "content_disposition": part.get_content_disposition(),
                    "size": len(attachment_bytes),
                    "sha256": hashlib.sha256(attachment_bytes).hexdigest(),
                }
            )
            continue
        if part.get_content_type() == "text/plain":
            text_parts.append(_safe_text(part))
        elif part.get_content_type() == "text/html":
            html_parts.append(_safe_text(part))

    sent_at = None
    date_header = message.get("Date")
    if date_header:
        try:
            sent_at = parsedate_to_datetime(date_header)
        except (TypeError, ValueError, IndexError):
            sent_at = None

    body_text = "\n".join(text_parts) or None
    body_html = "\n".join(html_parts) or None
    return ParsedEmail(
        message_id=message.get("Message-ID"),
        subject=message.get("Subject"),
        sender=_single_address(message.get("From")),
        sender_display_name=_display_name(message.get("From")),
        recipients=_addresses(message.get("To")),
        cc=_addresses(message.get("Cc")),
        reply_to=_single_address(message.get("Reply-To")),
        sent_at=sent_at,
        body_text=body_text,
        body_html=body_html,
        received_headers=received_headers,
        authentication_results=authentication_results,
        urls=_extract_urls(body_text, body_html),
        attachments=attachments,
        raw_sha256=hashlib.sha256(raw_bytes).hexdigest(),
    )
