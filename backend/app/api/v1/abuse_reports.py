"""API014: bounded, private, blind allegation intake; no moderation side effects."""

import re
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import Field
from sqlalchemy.exc import SQLAlchemyError

from app.core.abuse_intake import Closed, Receipt, Report, Unavailable, unique_json
from app.core.profile_crypto import ProfileCryptoUnavailable
from app.core.turnstile import ChallengeRequired, ChallengeUnavailable
from app.services.abuse_intake import preflight, submit

PATH = "/api/v1/public/abuse-reports"
HEADERS = {
    "Cache-Control": "private, no-store",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Robots-Tag": "noindex, nofollow",
    "Pragma": "no-cache",
}


class ChallengeDetails(Closed):
    challenge: Literal["turnstile"]


class EmptyDetails(Closed):
    pass


class AbuseError(Closed):
    code: Literal[
        "VALIDATION_ERROR",
        "UNSUPPORTED_MEDIA_TYPE",
        "FILE_TOO_LARGE",
        "RATE_LIMITED",
        "CHALLENGE_REQUIRED",
        "IDEMPOTENCY_KEY_REUSED",
        "PROVIDER_UNAVAILABLE",
        "METHOD_NOT_ALLOWED",
    ]
    message: str
    message_ur: str
    request_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    details: EmptyDetails | ChallengeDetails


class AbuseErrorEnvelope(Closed):
    error: AbuseError


def failure(request, status, code):
    return JSONResponse(
        status_code=status,
        headers=HEADERS,
        content={
            "error": {
                "code": code,
                "message": "The report request could not be completed. No response time is promised.",
                "message_ur": "رپورٹ کی درخواست مکمل نہیں ہو سکی۔ جواب کا وقت مقرر نہیں ہے۔",
                "request_id": getattr(request.state, "request_id", ""),
                "details": {"challenge": "turnstile"}
                if code == "CHALLENGE_REQUIRED"
                else {},
            }
        },
    )


class AbuseRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def bounded(request):
            try:
                if (
                    len(request.headers.getlist("content-type")) != 1
                    or request.headers.get("content-type", "").split(";")[0]
                    != "application/json"
                ):
                    return failure(request, 415, "UNSUPPORTED_MEDIA_TYPE")
                if request.headers.getlist("content-encoding") or request.url.query:
                    return failure(request, 400, "VALIDATION_ERROR")
                value = bytearray()
                async for chunk in request.stream():
                    if len(value) + len(chunk) > 8192:
                        return failure(request, 413, "FILE_TOO_LARGE")
                    value.extend(chunk)
                request._body = bytes(value)
                # The peer budget commits even for later malformed DTO/challenge.
                admission = preflight(request)
                if not admission["allowed"]:
                    return failure(request, 429, "RATE_LIMITED")
                try:
                    unique_json(request._body)
                except (ValueError, RecursionError):
                    return failure(request, 400, "VALIDATION_ERROR")
                retries = request.headers.getlist("idempotency-key")
                if len(retries) != 1 or not re.fullmatch(
                    r"[A-Za-z0-9_-]{16,100}", retries[0]
                ):
                    return failure(request, 400, "VALIDATION_ERROR")
                request.state.abuse_admission = admission
                return await handler(request)
            except RequestValidationError:
                return failure(request, 400, "VALIDATION_ERROR")
            except ChallengeRequired:
                return failure(request, 429, "CHALLENGE_REQUIRED")
            except (
                Unavailable,
                ProfileCryptoUnavailable,
                ChallengeUnavailable,
                SQLAlchemyError,
            ):
                return failure(request, 503, "PROVIDER_UNAVAILABLE")
            except HTTPException:
                return failure(request, 400, "VALIDATION_ERROR")

        return bounded


router = APIRouter(tags=["public abuse intake"], route_class=AbuseRoute)


@router.post(
    "/public/abuse-reports",
    operation_id="API-014",
    status_code=202,
    response_model=Receipt,
    responses={
        "4XX": {"model": AbuseErrorEnvelope},
        **{
            code: {"model": AbuseErrorEnvelope}
            for code in (400, 405, 409, 413, 415, 429, 503)
        },
    },
)
def report(body: Report, request: Request):
    error = submit(
        request, body, request.headers["idempotency-key"], request.state.abuse_admission
    )
    if error:
        return failure(
            request,
            409 if error == "IDEMPOTENCY_KEY_REUSED" else 429,
            error
            if error in {"IDEMPOTENCY_KEY_REUSED", "RATE_LIMITED"}
            else "RATE_LIMITED",
        )
    return {"status": "accepted"}


def install(application):
    application.include_router(router, prefix="/api/v1")

    @application.middleware("http")
    async def privacy(request, call_next):
        response = await call_next(request)
        if request.url.path == PATH:
            if response.status_code == 405:
                allowed = response.headers.get("Allow")
                response = failure(request, 405, "METHOD_NOT_ALLOWED")
                if allowed:
                    response.headers["Allow"] = allowed
            response.headers.update(HEADERS)
        return response
