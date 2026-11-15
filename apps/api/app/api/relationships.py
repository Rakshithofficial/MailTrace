"""Read-only API for related cases and possible campaigns."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import Campaign, InvestigationCase, Relationship
from app.db.session import get_session

router = APIRouter(prefix="/cases", tags=["relationships"])


def _case_or_404(session: Session, case_id: str) -> InvestigationCase:
    case = session.get(InvestigationCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "The requested case does not exist."})
    return case


@router.get("/{case_id}/relationships")
def get_case_relationships(case_id: str, session: Session = Depends(get_session)) -> dict:
    _case_or_404(session, case_id)
    relationships = list(session.scalars(select(Relationship).where(or_(Relationship.source_case_id == case_id, Relationship.target_case_id == case_id))))
    related_ids = sorted({
        relationship.target_case_id if relationship.source_case_id == case_id else relationship.source_case_id
        for relationship in relationships
        if relationship.source_case_id and relationship.target_case_id
    })
    return {
        "case_id": case_id,
        "related_cases": [{"id": related_id, "relationship_count": sum(related_id in {item.source_case_id, item.target_case_id} for item in relationships)} for related_id in related_ids],
        "relationships": [_relationship_payload(item) for item in relationships],
    }


@router.get("/{case_id}/campaigns")
def get_case_campaigns(case_id: str, session: Session = Depends(get_session)) -> dict:
    case = _case_or_404(session, case_id)
    campaigns = [campaign for campaign in session.scalars(select(Campaign)).all() if any(member.id == case.id for member in campaign.cases)]
    return {
        "case_id": case_id,
        "campaigns": [_campaign_payload(campaign) for campaign in campaigns],
    }


def _relationship_payload(relationship: Relationship) -> dict:
    return {
        "id": relationship.id,
        "source_case_id": relationship.source_case_id,
        "target_case_id": relationship.target_case_id,
        "source_indicator_id": relationship.source_indicator_id,
        "target_indicator_id": relationship.target_indicator_id,
        "relationship_type": relationship.relationship_type,
        "strength": relationship.strength.value,
        "confidence": float(relationship.confidence),
        "evidence": relationship.evidence,
    }


def _campaign_payload(campaign: Campaign) -> dict:
    return {
        "id": campaign.id,
        "name": campaign.name,
        "confidence": float(campaign.confidence),
        "wording": "possible campaign",
        "case_ids": sorted(member.id for member in campaign.cases),
        "first_seen": campaign.first_seen.isoformat() if campaign.first_seen else None,
        "last_seen": campaign.last_seen.isoformat() if campaign.last_seen else None,
    }