"""Investigation report generation and retrieval endpoints."""

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Report
from app.db.session import get_session
from app.reports.service import ReportService, ReportUnavailableError

router = APIRouter(prefix="/cases", tags=["reports"])


@router.post("/{case_id}/report")
def create_report(
    case_id: str,
    format: Literal["json", "pdf"] = "pdf",
    session: Session = Depends(get_session),
) -> dict:
    try:
        record = ReportService(session).persist(case_id, ReportService(session).build(case_id), format)
    except ReportUnavailableError as exc:
        raise HTTPException(status_code=404, detail={"code": "REPORT_UNAVAILABLE", "message": str(exc)}) from exc
    return {"id": record.id, "case_id": record.case_id, "format": record.format, "generated_at": record.generated_at.isoformat(), "content_reference": record.content_reference}


@router.get("/{case_id}/report/{report_id}")
def download_report(case_id: str, report_id: str, session: Session = Depends(get_session)) -> FileResponse:
    record = session.scalar(select(Report).where(Report.id == report_id, Report.case_id == case_id))
    if record is None:
        raise HTTPException(status_code=404, detail={"code": "REPORT_NOT_FOUND", "message": "The requested report does not exist."})
    path = Path(record.content_reference)
    if not path.is_file():
        raise HTTPException(status_code=404, detail={"code": "REPORT_FILE_NOT_FOUND", "message": "The report file is unavailable."})
    media_type = "application/pdf" if record.format == "pdf" else "application/json"
    return FileResponse(path, media_type=media_type, filename=path.name)