"""API-093/336–338: batch-bound opaque transport, never physical release."""

import hmac
import json
import re
import secrets
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, Request
from fastapi.responses import Response
from pydantic import Field, ValidationError
from sqlalchemy import text

from app.api.auth import AccessError, Authenticated, require_staff
from app.api.v1.catalog import Closed, fail
from app.api.v1.privacy_exports import Confirmed, recent
from app.api.v1.shipping_addresses import PrivateRoute
from app.core.manufacturing import (
    TransportConflict,
    canonical,
    identity_snapshot,
    pack,
    sealed_bytes,
    sha,
    unpack,
)
from app.core.profile_crypto import ProfileCryptoUnavailable

router = APIRouter(tags=["controlled manufacturing exports"], route_class=PrivateRoute)
PREFIX = "/admin/qr-batches/{batch_id}/print-exports"


class ExportRequest(Confirmed):
    expected_revision: int = Field(ge=0, le=2147483646, strict=True)
    printer_key_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    production_approval_id: UUID
    reason_code: Literal["initial_transport", "same_payload_retry"]


class GrantRequest(Confirmed):
    expected_revision: int = Field(ge=1, le=2147483646, strict=True)


class Receipt(Closed):
    job_id: UUID
    batch_id: UUID
    revision: int = Field(ge=1, strict=True)
    status: Literal["queued", "ready", "awaiting_ack", "accepted", "failed"]
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class Metadata(Receipt):
    pair_count: int = Field(ge=1, le=1000, strict=True)
    tag_count: int = Field(ge=2, le=2000, strict=True)
    attempt_count: int = Field(ge=0, le=5, strict=True)
    physical_release_enabled: Literal[False] = False


class GrantReceipt(Closed):
    grant_id: UUID
    grant_token: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
    job_id: UUID
    revision: int = Field(ge=1, strict=True)
    expires_at: datetime


def guard(context, request, write=False):
    require_staff(context, "operations")
    settings = request.app.state.settings
    if not settings.manufacturing_exports_enabled:
        raise AccessError(503)
    recent(context)
    if write and (
        not settings.manufacturing_export_web_origin
        or request.headers.getlist("origin")
        != [settings.manufacturing_export_web_origin]
    ):
        raise AccessError(403)


def call(context, operation, batch_id, value):
    result = context.session.execute(
        text("SELECT public.sr_mfg_apply(:op,:bid,CAST(:body AS jsonb))"),
        {"op": operation, "bid": batch_id, "body": canonical(value)},
    ).scalar_one()
    if result is None:
        raise AccessError(404)
    if "error" in result:
        fail({"GRANT_GONE": 410}.get(result["error"], 409), result["error"])
    return result


def current(context, batch_id, session_id):
    snapshot = context.session.execute(
        text("SELECT public.sr_mfg_context(:bid,:sid)"),
        {"bid": batch_id, "sid": session_id},
    ).scalar_one()
    if snapshot is None:
        raise AccessError(404)
    if "error" in snapshot:
        fail(409, snapshot["error"])
    if (
        snapshot["executor"] != str(context.principal.user_id)
        or snapshot["approver"] == snapshot["executor"]
    ):
        raise AccessError(404)
    count, digest = identity_snapshot(snapshot["pairs"])
    if count != snapshot["pair_count"] or digest != snapshot["identity_sha256"]:
        fail(409, "BATCH_IDENTITY_CHANGED")
    return snapshot


def checked(snapshot, job_id):
    job = snapshot.get("job")
    if not job or job["job_id"] != str(job_id):
        raise AccessError(404)
    return job


def projection(snapshot, metadata=False):
    job = snapshot["job"]
    value = {key: job[key] for key in Receipt.model_fields}
    if metadata:
        value.update(
            pair_count=snapshot["pair_count"],
            tag_count=snapshot["pair_count"] * 2,
            attempt_count=job["attempt_count"],
        )
    return (Metadata if metadata else Receipt).model_validate(value)


def command(context, request, batch_id, body, operation, work, replay_check):
    guard(context, request, True)
    try:
        snapshot = current(context, batch_id, context.principal.session_id)
    except (TransportConflict, KeyError, TypeError):
        raise AccessError(503) from None
    token = request.headers.getlist("idempotency-key")
    if len(token) != 1 or not re.fullmatch(r"[A-Za-z0-9._:-]{8,160}", token[0]):
        fail(400, "IDEMPOTENCY_KEY_REQUIRED")
    scope = sha(
        f"{context.principal.user_id}:{context.principal.session_id}:{batch_id}:{operation}:{token[0]}".encode()
    )
    digest = sha(body.model_dump_json().encode())
    old = call(context, "receipt", batch_id, {"scope": scope})
    settings = request.app.state.settings
    try:
        if old:
            if old["request_hash"] != digest:
                fail(409, "IDEMPOTENCY_KEY_REUSED")
            result = json.loads(unpack(settings, batch_id, "receipt:" + scope, old))
            replay_check(snapshot, result)
            return result
        with context.session.begin_nested():
            result = work(snapshot, settings)
            call(
                context,
                "save_receipt",
                batch_id,
                {
                    "scope": scope,
                    "request_hash": digest,
                    **pack(
                        settings,
                        batch_id,
                        "receipt:" + scope,
                        canonical(result).encode(),
                    ),
                },
            )
            return result
    except (
        ProfileCryptoUnavailable,
        ValidationError,
        TransportConflict,
        ValueError,
        KeyError,
    ):
        raise AccessError(503) from None


@router.post(PREFIX, operation_id="API-093", status_code=202, response_model=Receipt)
def enqueue(
    batch_id: UUID, body: ExportRequest, request: Request, context: Authenticated
):
    def authority(snapshot):
        if (
            str(body.production_approval_id) != snapshot["approval_id"]
            or body.printer_key_fingerprint != snapshot["printer_key_fingerprint"]
        ):
            fail(409, "PRODUCTION_AUTHORITY_CHANGED")

    def replay(snapshot, result):
        authority(snapshot)
        job = checked(snapshot, result["job_id"])
        if job["status"] not in {"queued", "ready"}:
            fail(409, "HANDOFF_RECONCILIATION_REQUIRED")

    def work(snapshot, settings):
        authority(snapshot)
        if snapshot["revision"] != body.expected_revision:
            fail(409, "VERSION_MISMATCH")
        if snapshot.get("job"):
            if body.reason_code == "same_payload_retry" and snapshot["job"][
                "status"
            ] in {"queued", "ready"}:
                return projection(snapshot).model_dump(mode="json")
            fail(409, "EXISTING_EXPORT_RECONCILE")
        if body.reason_code != "initial_transport":
            fail(409, "INITIAL_TRANSPORT_REQUIRED")
        payload = sealed_bytes(
            unpack(settings, batch_id, "source", snapshot["source"]),
            snapshot["manifest_sha256"],
        )
        result = call(
            context,
            "enqueue",
            batch_id,
            {
                "job_id": str(uuid4()),
                "expected_revision": body.expected_revision,
                "source_sha256": sha(payload),
            },
        )
        return Receipt.model_validate(result).model_dump(mode="json")

    return command(context, request, batch_id, body, "enqueue", work, replay)


@router.get(PREFIX + "/{job_id}", operation_id="API-336", response_model=Metadata)
def status(batch_id: UUID, job_id: UUID, request: Request, context: Authenticated):
    guard(context, request)
    try:
        snapshot = current(context, batch_id, context.principal.session_id)
        checked(snapshot, job_id)
        return projection(snapshot, True)
    except (TransportConflict, ValidationError, KeyError):
        raise AccessError(503) from None


@router.post(
    PREFIX + "/{job_id}/download-grants",
    operation_id="API-338",
    response_model=GrantReceipt,
)
def issue(
    batch_id: UUID,
    job_id: UUID,
    body: GrantRequest,
    request: Request,
    context: Authenticated,
):
    def replay(snapshot, result):
        checked(snapshot, job_id)
        call(
            context,
            "grant_live",
            batch_id,
            {
                "grant_id": result["grant_id"],
                "session_id": str(context.principal.session_id),
                "job_id": str(job_id),
            },
        )

    def work(snapshot, _):
        job = checked(snapshot, job_id)
        if job["revision"] != body.expected_revision:
            fail(409, "VERSION_MISMATCH")
        secret, gid = secrets.token_urlsafe(32), uuid4()
        result = call(
            context,
            "grant",
            batch_id,
            {
                "grant_id": str(gid),
                "token_hash": sha(secret.encode()),
                "session_id": str(context.principal.session_id),
                "job_id": str(job_id),
                "expected_revision": body.expected_revision,
            },
        )
        return GrantReceipt.model_validate(
            {**result, "grant_token": secret}
        ).model_dump(mode="json")

    return command(
        context, request, batch_id, body, "grant:" + str(job_id), work, replay
    )


@router.post(
    PREFIX + "/{job_id}/download", operation_id="API-337", response_class=Response
)
def download(
    batch_id: UUID,
    job_id: UUID,
    request: Request,
    context: Authenticated,
    grant: str | None = Header(default=None, alias="X-Print-Grant"),
):
    guard(context, request, True)
    try:
        snapshot = current(context, batch_id, context.principal.session_id)
        checked(snapshot, job_id)
        if (
            len(request.headers.getlist("x-print-grant")) != 1
            or grant is None
            or not re.fullmatch(r"[0-9a-f-]{36}\.[A-Za-z0-9_-]{43}", grant)
        ):
            fail(410, "GRANT_GONE")
        gid, token = grant.split(".")
        try:
            grant_id = str(UUID(gid))
        except ValueError:
            fail(410, "GRANT_GONE")
        args = {
            "grant_id": grant_id,
            "session_id": str(context.principal.session_id),
            "job_id": str(job_id),
        }
        valid = call(context, "grant_live", batch_id, args)
        if not hmac.compare_digest(valid["token_hash"], sha(token.encode())):
            fail(410, "GRANT_GONE")
        payload = sealed_bytes(
            unpack(request.app.state.settings, batch_id, "source", snapshot["source"]),
            snapshot["manifest_sha256"],
        )
        call(context, "consume", batch_id, {**args, "token_hash": sha(token.encode())})
        return Response(
            payload,
            media_type="application/vnd.safereturn.sealed-insert+json",
            headers={
                "Content-Disposition": 'attachment; filename="sealed-insert.json"',
                "Cache-Control": "private, no-store",
                "Pragma": "no-cache",
                "Referrer-Policy": "no-referrer",
            },
        )
    except (
        ProfileCryptoUnavailable,
        TransportConflict,
        ValidationError,
        ValueError,
        KeyError,
    ):
        raise AccessError(503) from None


def install(application):
    application.include_router(router, prefix="/api/v1")

    @application.middleware("http")
    async def private_headers(request, call_next):
        response = await call_next(request)
        if "/qr-batches/" in request.url.path and "/print-exports" in request.url.path:
            response.headers["Cache-Control"] = "private, no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "no-referrer"
        return response
