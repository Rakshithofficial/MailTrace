"""Relational deterministic relationship and possible-campaign logic."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from itertools import combinations
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import IndicatorType, RelationshipStrength
from app.db.models import Campaign, CampaignCase, CaseIndicator, Email, Indicator, InvestigationCase, Relationship


@dataclass(frozen=True)
class IndicatorSpec:
    indicator_type: IndicatorType
    normalized_value: str
    value: str
    source: str


STRONG_SOURCES = {"sender_domain", "email_domain", "email_url", "received_ip", "attachment_hash"}


def _domain(address: str | None) -> str | None:
    if not address or "@" not in address:
        return None
    return address.rsplit("@", 1)[1].lower().rstrip(".")


def _normalize_url(value: str) -> str:
    parsed = urlsplit(value)
    return urlunsplit((parsed.scheme.lower(), (parsed.hostname or "").lower(), parsed.path or "/", parsed.query, ""))


def _url_pattern(value: str) -> str:
    parsed = urlsplit(value)
    path = re.sub(r"\d+", "{n}", parsed.path or "/")
    return f"{parsed.scheme.lower()}://{(parsed.hostname or '').lower()}{path}"


def _received_ips(email: Email) -> set[str]:
    values: set[str] = set()
    for header in email.received_headers:
        values.update(re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", header))
    return values


def _content_tokens(email: Email) -> set[str]:
    text = (email.body_text or email.body_html or "").lower()
    return set(re.findall(r"[a-z0-9]{4,}", text))


def _specs(email: Email) -> list[IndicatorSpec]:
    specs: list[IndicatorSpec] = []
    sender_domain = _domain(email.sender)
    if sender_domain:
        specs.append(IndicatorSpec(IndicatorType.DOMAIN, sender_domain, sender_domain, "sender_domain"))
        specs.append(IndicatorSpec(IndicatorType.EMAIL, email.sender.lower(), email.sender, "sender_infrastructure"))
    for item in email.urls:
        url = _normalize_url(str(item.get("value", "")))
        host = str(item.get("host") or urlsplit(url).hostname or "").lower().rstrip(".")
        if host:
            specs.append(IndicatorSpec(IndicatorType.DOMAIN, host, host, "email_domain"))
        if url:
            specs.append(IndicatorSpec(IndicatorType.URL, url, url, "email_url"))
            specs.append(IndicatorSpec(IndicatorType.URL, _url_pattern(url), _url_pattern(url), "url_pattern"))
    for ip in _received_ips(email):
        specs.append(IndicatorSpec(IndicatorType.IP, ip, ip, "received_ip"))
    for attachment in email.attachments:
        digest = str(attachment.get("sha256", "")).lower()
        if digest:
            specs.append(IndicatorSpec(IndicatorType.HASH, digest, digest, "attachment_hash"))
    tokens = _content_tokens(email)
    if tokens:
        signature = hashlib.sha256(" ".join(sorted(tokens)).encode("utf-8")).hexdigest()
        specs.append(IndicatorSpec(IndicatorType.HASH, f"content:{signature}", f"content:{signature}", "content_signature"))
    return specs


class RelationshipService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def index_case(self, case: InvestigationCase) -> dict[tuple[IndicatorType, str, str], Indicator]:
        if case.email is None:
            return {}
        indexed: dict[tuple[IndicatorType, str, str], Indicator] = {}
        for spec in _specs(case.email):
            key = (spec.indicator_type, spec.normalized_value, spec.source)
            indicator = self.session.scalar(
                select(Indicator).where(
                    Indicator.type == spec.indicator_type,
                    Indicator.normalized_value == spec.normalized_value,
                )
            )
            if indicator is None:
                indicator = Indicator(
                    type=spec.indicator_type,
                    value=spec.value,
                    normalized_value=spec.normalized_value,
                    source=spec.source,
                    confidence=1.0,
                )
                self.session.add(indicator)
                self.session.flush()
            if indicator not in case.indicators:
                case.indicators.append(indicator)
                self.session.flush()
            indexed[key] = indicator
        return indexed

    def relate_case(self, current_case: InvestigationCase) -> list[Relationship]:
        current_indicators = self.index_case(current_case)
        self.session.flush()
        cases = list(self.session.scalars(select(InvestigationCase).order_by(InvestigationCase.created_at, InvestigationCase.id)))
        try:
            current_position = next(index for index, case in enumerate(cases) if case.id == current_case.id)
        except StopIteration:
            return []
        relationships: list[Relationship] = []
        for previous_case in cases[:current_position]:
            previous_indicators = self.index_case(previous_case)
            shared_keys = set(current_indicators).intersection(previous_indicators)
            for key in shared_keys:
                _, normalized_value, source = key
                relationship = self._add_relationship(
                    previous_case,
                    current_case,
                    previous_indicators[key],
                    current_indicators[key],
                    source,
                    {"shared_normalized_value": normalized_value},
                )
                if relationship:
                    relationships.append(relationship)
            self._add_content_similarity(previous_case, current_case, previous_indicators, current_indicators, relationships)
        self.session.flush()
        return relationships

    def _add_content_similarity(self, previous: InvestigationCase, current: InvestigationCase, previous_indicators: dict, current_indicators: dict, relationships: list[Relationship]) -> None:
        if previous.email is None or current.email is None:
            return
        left = _content_tokens(previous.email)
        right = _content_tokens(current.email)
        if not left or not right:
            return
        similarity = len(left & right) / len(left | right)
        if similarity < 0.6:
            return
        left_key = next((key for key in previous_indicators if key[2] == "content_signature"), None)
        right_key = next((key for key in current_indicators if key[2] == "content_signature"), None)
        if left_key and right_key:
            relationship = self._add_relationship(
                previous,
                current,
                previous_indicators[left_key],
                current_indicators[right_key],
                "content_similarity",
                {"token_jaccard": round(similarity, 3)},
            )
            if relationship:
                relationships.append(relationship)

    def _add_relationship(self, source_case: InvestigationCase, target_case: InvestigationCase, source_indicator: Indicator, target_indicator: Indicator, source: str, evidence: dict[str, Any]) -> Relationship | None:
        existing = self.session.scalar(
            select(Relationship).where(
                Relationship.source_case_id == source_case.id,
                Relationship.target_case_id == target_case.id,
                Relationship.source_indicator_id == source_indicator.id,
                Relationship.target_indicator_id == target_indicator.id,
                Relationship.relationship_type == _relationship_type(source),
            )
        )
        if existing:
            return None
        strong = source in STRONG_SOURCES
        relationship = Relationship(
            source_indicator_id=source_indicator.id,
            target_indicator_id=target_indicator.id,
            source_case_id=source_case.id,
            target_case_id=target_case.id,
            relationship_type=_relationship_type(source),
            confidence=0.95 if strong else 0.7,
            strength=RelationshipStrength.STRONG if strong else RelationshipStrength.MEDIUM,
            evidence={"source": source, **evidence},
        )
        self.session.add(relationship)
        return relationship

    def group_possible_campaign(self, case: InvestigationCase) -> Campaign | None:
        relationships = list(self.session.scalars(select(Relationship).where(Relationship.strength == RelationshipStrength.STRONG)))
        graph: dict[str, set[str]] = {}
        for relationship in relationships:
            if relationship.source_case_id and relationship.target_case_id:
                graph.setdefault(relationship.source_case_id, set()).add(relationship.target_case_id)
                graph.setdefault(relationship.target_case_id, set()).add(relationship.source_case_id)
        if case.id not in graph:
            return None
        component = {case.id}
        pending = [case.id]
        while pending:
            current = pending.pop()
            for neighbor in graph.get(current, set()):
                if neighbor not in component:
                    component.add(neighbor)
                    pending.append(neighbor)
        if len(component) < 2:
            return None
        for campaign in self.session.scalars(select(Campaign)).all():
            if {member.id for member in campaign.cases} == component:
                return campaign
        members = list(self.session.scalars(select(InvestigationCase).where(InvestigationCase.id.in_(component))))
        campaign = Campaign(
            name="Possible campaign: shared indicators",
            confidence=0.95,
            first_seen=min(member.created_at for member in members),
            last_seen=max(member.created_at for member in members),
            cases=members,
        )
        self.session.add(campaign)
        self.session.flush()
        return campaign


def _relationship_type(source: str) -> str:
    return {
        "email_domain": "SHARED_DOMAIN",
        "sender_domain": "SHARED_DOMAIN",
        "email_url": "SHARED_URL",
        "received_ip": "SHARED_IP",
        "attachment_hash": "SHARED_ATTACHMENT_HASH",
        "sender_infrastructure": "SHARED_SENDER_INFRASTRUCTURE",
        "url_pattern": "SIMILAR_URL_PATTERN",
        "content_similarity": "SIMILAR_CONTENT",
        "content_signature": "SIMILAR_CONTENT",
    }[source]
