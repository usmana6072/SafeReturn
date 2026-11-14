"""API-325–330: reviewed, limited self-service export; never erasure."""

import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import Field, field_validator
from sqlalchemy import text

from app.api.auth import (
    AccessError,
    Authenticated,
    require_staff,
    require_verified_account,
)
from app.api.v1.catalog import CatalogRoute, Closed, fail
from app.api.v1.fulfillment import bounds, page_cursor
from app.api.v1.support_cases import command
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt, key
from app.integrations.privacy_export_storage import MAX_CIPHERTEXT_BYTES

router = APIRouter(tags=["limited privacy exports"], route_class=CatalogRoute)


class Confirmed(Closed):
    confirmed: Literal[True]

    @field_validator("confirmed", mode="before")
    @classmethod
    def explicit(cls, value):
        if value is not True:
            raise ValueError("Explicit confirmation required")
        return value


class ExportRequest(Confirmed):
    scope: Literal["basic_v1"]
    case_id: UUID | None = None


class Revision(Confirmed):
    expected_revision: int = Field(ge=1, le=2147483647, strict=True)


class Decision(Revision):
    case_id: UUID
    decision: Literal["approve", "reject", "escalate"]
    scope_version: Literal["basic_v1"]
    reason_code: Literal[
        "scope_reviewed",
        "scope_not_supported",
        "identity_review_failed",
        "requires_review",
    ]


def recent(context):
    require_verified_account(context)
    stamp = context.principal.authentication_time
    if stamp is None or not 0 <= datetime.now(UTC).timestamp() - stamp <= 300:
        fail(403, "REAUTH_REQUIRED")


def result(value):
    if value is None:
        raise AccessError(404)
    if "error" in value:
        fail(
            {
                "NOT_FOUND": 404,
                "STALE_CASE": 412,
                "GRANT_GONE": 410,
                "INVALID_REQUEST": 422,
            }.get(value["error"], 409),
            value["error"],
        )
    return value


def origin(request):
    expected = request.app.state.settings.privacy_export_web_origin
    value = request.headers.get("origin")
    if not expected or value != expected or len(request.headers.getlist("origin")) != 1:
        raise AccessError(403)
    return value


@router.post("/me/privacy/exports", operation_id="API-325", status_code=202)
def create(body: ExportRequest, request: Request, context: Authenticated):
    recent(context)
    return command(
        context,
        request,
        "privacy.export.request",
        body,
        lambda _: context.session.execute(
            text("SELECT public.sr_export_request(:rid,:cid,:mid)"),
            {"rid": uuid4(), "cid": body.case_id, "mid": uuid4()},
        ).scalar_one(),
        202,
    )


@router.get("/me/privacy/exports/{request_id}", operation_id="API-326")
def status(request_id: UUID, context: Authenticated, response: Response):
    require_verified_account(context)
    response.headers["Cache-Control"] = "private, no-store"
    return result(
        context.session.execute(
            text("SELECT public.sr_export_read(:id)"), {"id": request_id}
        ).scalar_one()
    )


@router.get("/admin/privacy/exports", operation_id="API-330")
def listing(
    context: Authenticated,
    response: Response,
    limit: int = 20,
    cursor: str | None = None,
):
    require_staff(context, "security_admin")
    response.headers["Cache-Control"] = "private, no-store"
    bounds(limit)
    stamp, ident = page_cursor(cursor)
    rows = list(
        context.session.execute(
            text("SELECT public.sr_export_list(:lim,:stamp,:id)"),
            {"lim": limit + 1, "stamp": stamp, "id": ident},
        ).scalars()
    )
    import base64
    import json

    items = rows[:limit]
    next_cursor = None
    if len(rows) > limit:
        last = items[-1]
        next_cursor = (
            base64.urlsafe_b64encode(
                json.dumps([last["created_at"], last["request_id"]]).encode()
            )
            .decode()
            .rstrip("=")
        )
    return {"items": items, "next_cursor": next_cursor}


@router.post("/admin/privacy/exports/{request_id}/decisions", operation_id="API-327")
def decide(request_id: UUID, body: Decision, request: Request, context: Authenticated):
    require_staff(context, "security_admin")
    recent(context)
    current = result(
        context.session.execute(
            text("SELECT public.sr_export_preflight(:id,'decision')"),
            {"id": request_id},
        ).scalar_one()
    )
    if current["case_id"] != str(body.case_id):
        raise AccessError(404)
    return command(
        context,
        request,
        "privacy.export.decide:" + str(request_id),
        body,
        lambda _: context.session.execute(
            text("SELECT public.sr_export_decide(:rid,:cid,:rev,:choice,:reason)"),
            {
                "rid": request_id,
                "cid": body.case_id,
                "rev": body.expected_revision,
                "choice": body.decision,
                "reason": body.reason_code,
            },
        ).scalar_one(),
        200,
    )


@router.post("/me/privacy/exports/{request_id}/download-grants", operation_id="API-328")
def grant(request_id: UUID, body: Revision, request: Request, context: Authenticated):
    recent(context)
    web_origin = origin(request)
    result(
        context.session.execute(
            text("SELECT public.sr_export_preflight(:id,'grant')"), {"id": request_id}
        ).scalar_one()
    )

    def verifier(settings, receipt):
        # A 256-bit random nonce is transformed with a domain-separated keyring
        # PRF. Only the verifier digest persists in the grant table. An encrypted
        # receipt retains nonce/key version, never the bearer verifier itself.
        binding = f"SafeReturn:privacy-grant:v1:{request_id}:{context.principal.user_id}:{context.principal.session_id}:{web_origin}:{receipt['nonce']}"
        return (
            base64.urlsafe_b64encode(
                hmac.digest(
                    key(settings, receipt["key_version"]), binding.encode(), "sha256"
                )
            )
            .decode()
            .rstrip("=")
        )

    def work(settings):
        receipt = {
            "nonce": secrets.token_hex(32),
            "key_version": settings.profile_data_key_version,
        }
        token = verifier(settings, receipt)
        value = context.session.execute(
            text("SELECT public.sr_export_grant(:rid,:sid,:rev,:hash,:origin)"),
            {
                "rid": request_id,
                "sid": context.principal.session_id,
                "rev": body.expected_revision,
                "hash": hashlib.sha256(token.encode()).hexdigest(),
                "origin": web_origin,
            },
        ).scalar_one()
        return {**result(value), **receipt}

    # Bind replay to the originating live session and origin as well as resource.
    receipt = command(
        context,
        request,
        "privacy.grant:"
        + hashlib.sha256(
            f"{request_id}:{context.principal.session_id}:{web_origin}".encode()
        ).hexdigest(),
        body,
        work,
        200,
    )
    try:
        token = verifier(request.app.state.settings, receipt)
    except ProfileCryptoUnavailable:
        raise AccessError(503) from None
    return {"expires_in": receipt["expires_in"], "grant": token}


@router.post("/me/privacy/exports/{request_id}/download", operation_id="API-329")
def download(request_id: UUID, request: Request, context: Authenticated):
    recent(context)
    web_origin = origin(request)
    tokens = request.headers.getlist("x-privacy-grant")
    if len(tokens) != 1 or len(tokens[0]) != 43:
        fail(410, "GRANT_GONE")
    value = result(
        context.session.execute(
            text("SELECT public.sr_export_consume(:rid,:sid,:hash,:origin)"),
            {
                "rid": request_id,
                "sid": context.principal.session_id,
                "hash": hashlib.sha256(tokens[0].encode()).hexdigest(),
                "origin": web_origin,
            },
        ).scalar_one()
    )
    # Consumption commits even if storage/decryption fails. A failed transfer
    # requires a fresh authorized grant. No private bytes in idempotency receipts.
    try:
        store = getattr(request.app.state, "privacy_export_store", None)
        if store is None:
            raise ProfileCryptoUnavailable()
        cipher = store.read(value["object_key"])
        if len(cipher) > MAX_CIPHERTEXT_BYTES:
            raise ProfileCryptoUnavailable()
        data = decrypt(
            request.app.state.settings,
            request_id,
            "privacy-export:" + value["manifest_id"],
            cipher,
            value["key_version"],
        ).encode()
        if (
            len(data) > 10 * 1024 * 1024
            or hashlib.sha256(data).hexdigest() != value["checksum"]
        ):
            raise ProfileCryptoUnavailable()
    except (ProfileCryptoUnavailable, OSError, KeyError):
        return Response(
            status_code=503,
            headers={
                "Cache-Control": "private, no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )
    return StreamingResponse(
        (data[offset : offset + 65536] for offset in range(0, len(data), 65536)),
        media_type="application/json",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": 'attachment; filename="safereturn-basic-v1.json"',
        },
    )
