from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import AnalysisRun, Finding, InvestigationCase, Report
from app.integrations.explanation.fallback import FallbackExplanationProvider
from app.integrations.explanation.service import ExplanationService
from app.integrations.threat_intel.local import NoOpProvider
from app.integrations.threat_intel.service import ThreatIntelService
from app.services.investigation import InvestigationService


def test_controlled_eml_runs_complete_offline_pipeline(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    service = InvestigationService(
        session,
        threat_intel=ThreatIntelService([NoOpProvider()]),
        explanation=ExplanationService([], FallbackExplanationProvider()),
        raw_root=tmp_path / "raw",
        report_root=tmp_path / "reports",
    )
    fixture = Path(__file__).parents[3] / "sample_data" / "phishing" / "local-analysis-basic.eml"

    result = service.investigate(fixture.read_bytes(), "campaign-a.eml")
    related_result = service.investigate(fixture.read_bytes(), "campaign-b.eml")

    assert result["status"] == "REVIEW"
    assert result["analysis"]["findings"]
    assert result["analysis"]["risk"]["score"] > 0
    assert result["analysis"]["enrichment"]["status"] == "unavailable"
    assert result["analysis"]["explanation"]["status"] == "fallback"
    assert result["analysis"]["recommendations"]
    assert result["analysis"]["report"]["format"] == "json"
    assert related_result["analysis"]["relationships"]
    assert related_result["analysis"]["campaign"] is not None
    assert session.scalar(select(AnalysisRun).where(AnalysisRun.case_id == result["id"])) is not None
    assert session.scalar(select(Finding).where(Finding.case_id == result["id"])) is not None
    assert session.scalar(select(Report).where(Report.case_id == result["id"])) is not None