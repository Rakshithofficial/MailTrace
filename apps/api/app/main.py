"""MailTrace API entry point."""

import os
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.cases import router as cases_router
from app.api.relationships import router as relationships_router
from app.api.reports import router as reports_router

app = FastAPI(title="MailTrace API", version="0.1.0")
app.add_middleware(
	CORSMiddleware,
	allow_origins=[origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if origin.strip()],
	allow_methods=["GET", "POST", "PATCH"],
	allow_headers=["*"],
)
app.include_router(cases_router, prefix="/api/v1")
app.include_router(relationships_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")


@app.get("/api/v1/health", tags=["health"])
def health() -> dict[str, str]:
	return {"status": "ok", "service": "mailtrace-api"}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
	detail = exc.detail if isinstance(exc.detail, dict) else {"code": "HTTP_ERROR", "message": str(exc.detail)}
	detail.setdefault("request_id", str(uuid4()))
	return JSONResponse(status_code=exc.status_code, content={"error": detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
	return JSONResponse(status_code=422, content={"error": {"code": "INVALID_INPUT", "message": "Request validation failed.", "details": exc.errors(), "request_id": str(uuid4())}})
