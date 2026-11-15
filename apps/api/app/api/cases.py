"""Investigation intake and completed-result endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.intake.parser import EmailParseError
from app.services.investigation import InvestigationPipelineError, InvestigationService

MAX_EML_BYTES = 10 * 1024 * 1024
router = APIRouter(prefix="/cases", tags=["cases"])


def _error(code: str, message: str, status_code: int) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_case_from_eml(
    file: Annotated[UploadFile, File(...)],
    title: Annotated[str | None, Form()] = None,
    analyst_note: Annotated[str | None, Form()] = None,
    session: Session = Depends(get_session),
) -> dict:
    if not file.filename or not file.filename.lower().endswith(".eml"):
        raise _error("UNSUPPORTED_FILE", "Only .eml files are accepted.", status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
    if file.content_type not in {None, "message/rfc822", "application/octet-stream", "text/plain"}:
        raise _error("UNSUPPORTED_FILE", "The uploaded content type is not accepted for .eml intake.", status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    raw_bytes = await file.read(MAX_EML_BYTES + 1)
    if len(raw_bytes) > MAX_EML_BYTES:
        raise _error("PAYLOAD_TOO_LARGE", "The .eml file exceeds the 10 MiB limit.", status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
    try:
        return InvestigationService(session).investigate(raw_bytes, file.filename, title, analyst_note)
    except EmailParseError as exc:
        raise _error("INVALID_INPUT", str(exc), status.HTTP_422_UNPROCESSABLE_ENTITY) from exc
    except InvestigationPipelineError as exc:
        raise _error("ANALYSIS_FAILED", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR) from exc
