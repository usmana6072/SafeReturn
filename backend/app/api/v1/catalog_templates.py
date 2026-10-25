"""API-339: configured catalog references only, never renderer/physical approval."""

import re
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.auth import AccessError, Authenticated
from app.api.v1.catalog import guard

PATH = "/api/v1/admin/catalog/approved-templates"
router = APIRouter(tags=["catalog template discovery"])


class TemplateChoice(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    template_key: str = Field(pattern=r"^[A-Za-z0-9._-]{3,80}$")
    template_version: int = Field(ge=1, le=100000)


class TemplateChoices(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    as_of: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$")
    items: list[TemplateChoice] = Field(max_length=100)


class ErrorContent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    code: Literal[
        "AUTH_REQUIRED",
        "FORBIDDEN",
        "VALIDATION_ERROR",
        "PROVIDER_UNAVAILABLE",
        "METHOD_NOT_ALLOWED",
    ]
    message: str
    message_ur: str
    request_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    details: dict = Field(max_length=0)


class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    error: ErrorContent


def safe_error(request, status, code):
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": "Catalog template choices are unavailable or the request is invalid.",
                "message_ur": "کیٹلاگ ٹیمپلیٹس دستیاب نہیں یا درخواست درست نہیں۔",
                "request_id": getattr(request.state, "request_id", None),
                "details": {},
            }
        },
    )


@router.get(
    "/admin/catalog/approved-templates",
    operation_id="API-339",
    response_model=TemplateChoices,
    responses={
        status: {"model": ErrorEnvelope} for status in (401, 403, 405, 422, 503)
    },
)
async def choices(request: Request, context: Authenticated):
    guard(context)
    if request.url.query:
        return safe_error(request, 422, "VALIDATION_ERROR")
    async for chunk in request.stream():
        if chunk:
            return safe_error(request, 422, "VALIDATION_ERROR")
    raw = getattr(request.app.state.settings, "catalog_approved_templates", None)
    if type(raw) is not list or len(raw) > 100:
        raise AccessError(503)
    pairs = set()
    for entry in raw:
        if not isinstance(entry, str) or not 5 <= len(entry) <= 87:
            raise AccessError(503)
        match = re.fullmatch(
            r"([A-Za-z0-9._-]{3,80})@([1-9][0-9]{0,5})", entry, re.ASCII
        )
        if match is None or int(match[2]) > 100000:
            raise AccessError(503)
        key, version = match[1], int(match[2])
        if f"{key}@{version}" != entry:
            raise AccessError(503)
        pairs.add((key, version))
    return TemplateChoices(
        as_of=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        items=[
            TemplateChoice(template_key=k, template_version=v) for k, v in sorted(pairs)
        ],
    )


def install(application):
    application.include_router(router, prefix="/api/v1")

    @application.middleware("http")
    async def discovery_headers(request, call_next):
        response = await call_next(request)
        if request.url.path == PATH:
            if response.status_code == 405:
                response = safe_error(request, 405, "METHOD_NOT_ALLOWED")
                response.headers["Allow"] = "GET"
            response.headers["X-Template-Binding-Policy"] = "manual-print-v1"
            response.headers["Cache-Control"] = "private, no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            request_id = getattr(request.state, "request_id", None)
            if request_id:
                response.headers["X-Request-ID"] = request_id
        return response
