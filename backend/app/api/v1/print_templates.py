"""Task5.1B template lifecycle. Publication requires separately enrolled QA authority."""

import base64
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import Field, field_validator, model_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api.auth import AccessError, Authenticated, authorize, require_staff
from app.api.v1.catalog import fail
from app.api.v1.privacy_exports import Confirmed
from app.core.print_render import PrintUnavailable
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt, encrypt, key
from app.core.template_auth import recent_template_auth
from app.core.template_content import Closed, Content, plain
from app.core.template_preview import isolated_preview
from app.db.print_templates import TemplateRepository
from app.db.runtime import api_transaction
from app.db.template_registry import gate
from app.services.template_evidence import publication_proof, publisher

PREVIEW_PLATFORM_SUPPORTED = sys.platform == "linux"

class TemplateRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handle(request):
            try:
                if request.method in {"POST", "PATCH"}:
                    if (
                        request.url.query
                        or len(request.headers.getlist("content-type")) != 1
                        or request.headers.get("content-encoding")
                    ):
                        fail(422, "VALIDATION_ERROR")
                    if (
                        request.headers.get("content-type", "").split(";")[0]
                        != "application/json"
                    ):
                        fail(422, "VALIDATION_ERROR")
                    size = 0
                    chunks = []
                    async for chunk in request.stream():
                        size += len(chunk)
                        if size > (164000 if request.url.path.endswith("/qa-decision") else 32768):
                            fail(413, "FILE_TOO_LARGE")
                        chunks.append(chunk)
                    request._body = b"".join(chunks)
                elif request.method == "GET":
                    async for chunk in request.stream():
                        if chunk:
                            fail(422, "VALIDATION_ERROR")
                return await original(request)
            except RequestValidationError:
                return error(request, 422, "VALIDATION_ERROR")
            except HTTPException as exc:
                return error(request, exc.status_code, exc.detail["code"])

        return handle


def error(request, status, code):
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": "Template request could not be completed.",
                "message_ur": "ٹیمپلیٹ کی درخواست مکمل نہیں ہو سکی۔",
                "request_id": getattr(request.state, "request_id", None),
                "details": {},
            }
        },
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


class ErrorBody(Closed):
    code: Literal[
        "AUTH_REQUIRED",
        "FORBIDDEN",
        "REAUTH_REQUIRED",
        "NOT_FOUND",
        "CONFLICT",
        "IDEMPOTENCY_KEY_REUSED",
        "VERSION_MISMATCH",
        "FILE_TOO_LARGE",
        "VALIDATION_ERROR",
        "RATE_LIMITED",
        "PROVIDER_UNAVAILABLE",
        "METHOD_NOT_ALLOWED",
        "PREVIEW_TIMEOUT",
        "PREVIEW_BUSY",
        "PREVIEW_WORKER_FAILED",
        "TEMPLATE_MANAGEMENT_DISABLED",
        "TEMPLATE_ASSETS_UNAVAILABLE",
        "PREVIEW_ISOLATION_UNAVAILABLE",
        "TEMPLATE_ORIGIN_MISMATCH",
    ]
    message: str
    message_ur: str
    request_id: str
    details: dict = Field(max_length=0)


class TemplateErrorEnvelope(Closed):
    error: ErrorBody


router = APIRouter(
    tags=["print template registry"],
    route_class=TemplateRoute,
    responses={
        status: {"model": TemplateErrorEnvelope}
        for status in (400, 401, 403, 404, 405, 409, 412, 413, 422, 429, 503)
    },
)


class Create(Closed):
    key: str = Field(pattern=r"^[A-Za-z0-9._-]{3,80}$")
    name: str = Field(min_length=1, max_length=100)
    purpose: Literal["lost", "ice"]

    @field_validator("name")
    @classmethod
    def text(cls, value):
        return plain(value)


class DraftEditRequest(Closed):
    content: Content
    version_note: str = Field(min_length=4, max_length=500)

    @field_validator("version_note")
    @classmethod
    def text(cls, value):
        return plain(value)


class NewRevision(DraftEditRequest):
    base_revision_id: UUID | None


class Reason(Closed):
    reason: str = Field(min_length=4, max_length=500)

    @field_validator("reason")
    @classmethod
    def text(cls, value):
        return plain(value)


class Retire(Reason, Confirmed):
    pass


class Publish(Confirmed):
    approval_id: UUID


class Bind(Confirmed):
    variant_id: UUID
    tag_type: Literal["lost", "ice"]
    revision_id: UUID | None
    expected_variant_version: int = Field(ge=1, strict=True)
    expected_binding_id: UUID | None

    @model_validator(mode="after")
    def deactivation_target(self):
        if self.revision_id is None and self.expected_binding_id is None:
            raise ValueError("Explicit current binding required")
        return self


class Preview(Closed):
    expected_revision: int = Field(ge=1, strict=True)


class TemplateView(Closed):
    template_id: UUID
    key: str
    name: str
    purpose: Literal["lost", "ice"]
    lifecycle_status: Literal["draft", "active", "retired"]
    row_version: int = Field(ge=1)
    created_at: datetime


class RevisionView(Closed):
    revision_id: UUID
    template_id: UUID
    version: int = Field(ge=1, le=100000)
    status: Literal["draft", "pending_qa", "published", "retired"]
    row_version: int = Field(ge=1)
    content: Content
    fingerprint_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    created_at: datetime
    published_at: datetime | None


class RevisionResult(Closed):
    template: TemplateView
    revision: RevisionView


class CreateReceipt(Closed):
    command_id: UUID
    result: TemplateView


class RevisionReceipt(Closed):
    command_id: UUID
    result: RevisionResult


class EditReceipt(Closed):
    command_id: UUID
    result: RevisionView


class SubmitResult(Closed):
    revision: RevisionView
    validation_status: Literal["needs_independent_physical_qa"]


class SubmitReceipt(Closed):
    command_id: UUID
    result: SubmitResult


class TemplateList(Closed):
    items: list[TemplateView] = Field(max_length=50)
    next_cursor: str | None
    as_of: datetime


class TemplateDetail(Closed):
    template: TemplateView
    revisions: list[RevisionView] = Field(max_length=50)
    next_cursor: str | None


class PublishedTemplateResult(Closed):
    revision: RevisionView
    approval_id: UUID


class PublishedTemplateReceipt(Closed):
    command_id: UUID
    result: PublishedTemplateResult


class TemplateBindingView(Closed):
    binding_id: UUID
    variant_id: UUID
    tag_type: Literal["lost", "ice"]
    revision_id: UUID
    is_active: bool
    row_version: int
    created_at: datetime


class TemplateBindingResult(Closed):
    binding: TemplateBindingView
    variant_row_version: int


class TemplateBindingReceipt(Closed):
    command_id: UUID
    result: TemplateBindingResult


class TemplateBindingsPage(Closed):
    items: list[TemplateBindingView] = Field(max_length=50)
    next_cursor: str | None
    as_of: datetime


class RetiredTemplateResult(Closed):
    revision: RevisionView
    template: TemplateView


class RetiredTemplateReceipt(Closed):
    command_id: UUID
    result: RetiredTemplateResult


def guard(context, request, *, write=False, draft=False):
    require_staff(
        context,
        *(["operations"] if write else ["operations", "security_admin", "superadmin"]),
    )
    if write:
        recent_template_auth(context)
        origins = request.headers.getlist("origin")
        if origins and (
            len(origins) != 1
            or origins[0] != request.app.state.settings.print_template_web_origin
        ):
            fail(403, "TEMPLATE_ORIGIN_MISMATCH")
    if not request.app.state.settings.print_template_management_enabled:
        fail(503, "TEMPLATE_MANAGEMENT_DISABLED")


def match(request):
    values = request.headers.getlist("if-match")
    if len(values) != 1 or not re.fullmatch(r'"[1-9][0-9]{0,17}"', values[0]):
        fail(400, "VALIDATION_ERROR")
    return int(values[0][1:-1])


def command(context, request, action, body, *, prepare=None, **ids):
    draft_action = action in {"create", "revision", "edit"}
    guard(context, request, write=True, draft=draft_action)
    payload = body.model_dump(mode="json") | ids
    if action != "create":
        payload["expected"] = match(request)
    keys = request.headers.getlist("idempotency-key")
    if len(keys) != 1 or not re.fullmatch(r"[A-Za-z0-9._:-]{8,160}", keys[0]):
        fail(400, "VALIDATION_ERROR")
    actor = context.principal.user_id
    operation = "template." + action
    reference = hashlib.sha256(f"{actor}:{operation}:{keys[0]}".encode()).hexdigest()
    hashed = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    session = context.session
    if action in {"publish", "bind", "retire", "manual_review_decide"} and not gate(session, exclusive=True):
        raise AccessError(503)
    if action in {"publish", "retire"}:
        publisher(context)
    params = {"actor": actor, "scope": str(actor), "op": operation, "key": keys[0]}
    receipt_query = "SELECT * FROM public.idempotency_records WHERE actor_scope=:scope AND operation=:op AND idempotency_key=:key"
    # No locks precede rendering. Replays can skip expensive preparation.
    before = session.execute(text(receipt_query), params).mappings().one_or_none()
    proof = {}
    if before is None and prepare is not None:
        proof = prepare()
    if action not in {"publish", "bind", "retire", "manual_review_decide"}:
        # Submit renders before admission; draft writes then share the lifecycle
        # gate so a retired key cannot acquire a racing new revision.
        gate(session)
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:k,0))"), {"k": reference}
    )
    old = (
        session.execute(
            text(
                "SELECT * FROM public.idempotency_records WHERE actor_scope=:scope AND operation=:op AND idempotency_key=:key FOR UPDATE"
            ),
            params,
        )
        .mappings()
        .one_or_none()
    )
    settings = request.app.state.settings
    try:
        if old:
            if old["request_hash"] != hashed:
                fail(409, "IDEMPOTENCY_KEY_REUSED")
            guard(authorize(context.session, context.principal), request, write=True, draft=draft_action)
            return json.loads(
                decrypt(
                    settings,
                    actor,
                    "template:" + reference,
                    old["response_body_ciphertext"],
                    old["response_key_version"],
                )
            )
        with session.begin_nested():
            result = TemplateRepository(context).call(action, payload | proof)
            guard(authorize(context.session, context.principal), request, write=True, draft=draft_action)
            envelope = {"command_id": str(uuid4()), "result": result}
            cipher, kv = encrypt(
                settings, actor, "template:" + reference, json.dumps(envelope)
            )
            session.execute(
                text("""INSERT INTO public.idempotency_records(actor_scope,actor_user_id,operation,idempotency_key,request_hash,state,response_status,response_body_ciphertext,response_key_version,expires_at)
                VALUES(:scope,:actor,:op,:key,:hash,'completed',:status,:cipher,:kv,now()+interval '1 day')"""),
                params
                | {
                    "hash": hashed,
                    "status": 201 if action in {"create", "revision", "bind"} else 200,
                    "cipher": cipher,
                    "kv": kv,
                },
            )
            session.execute(
                text("""INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,request_id,reason,safe_details)
                VALUES(:actor,'staff',:op,'print_template',:target,:rid,'authorized template command',jsonb_build_object('event_id',CAST(:event AS text),'outcome','success'))"""),
                {
                    "actor": actor,
                    "op": operation,
                    "target": result.get("template_id")
                    or ids.get("template_id")
                    or result.get("binding", {}).get("binding_id"),
                    "rid": getattr(request.state, "request_id", None),
                    "event": envelope["command_id"],
                },
            )
            return envelope
    except ProfileCryptoUnavailable:
        raise AccessError(503) from None
    except IntegrityError:
        fail(409, "CONFLICT")


def query(request, allowed):
    if any(
        k not in allowed or len(request.query_params.getlist(k)) != 1
        for k in request.query_params
    ):
        fail(422, "VALIDATION_ERROR")
    if (
        request.headers.get("content-length", "0") != "0"
        or "transfer-encoding" in request.headers
    ):
        fail(422, "VALIDATION_ERROR")


def cursor(request, context, scope, value=None):
    settings = request.app.state.settings
    actor = context.principal.user_id
    try:
        if value is not None:
            cipher, kv = encrypt(
                settings,
                actor,
                "template-page:" + scope,
                json.dumps(
                    {
                        "id": value,
                        "expires": int(datetime.now(UTC).timestamp()) + 900,
                    }
                ),
            )
            return base64.urlsafe_b64encode(kv.to_bytes(2, "big") + cipher).decode()
        token = request.query_params.get("cursor") or request.query_params.get(
            "revisions_cursor"
        )
        if not token:
            return None
        if len(token) > 1024:
            fail(422, "VALIDATION_ERROR")
        raw = base64.b64decode(token, altchars=b"-_", validate=True)
        if len(raw) < 34:
            fail(422, "VALIDATION_ERROR")
        key(settings, settings.profile_data_key_version)
        try:
            plaintext = decrypt(
                settings,
                actor,
                "template-page:" + scope,
                raw[2:],
                int.from_bytes(raw[:2], "big"),
            )
        except ProfileCryptoUnavailable:
            fail(422, "VALIDATION_ERROR")
        page = json.loads(plaintext)
        if page["expires"] < datetime.now(UTC).timestamp():
            fail(422, "VALIDATION_ERROR")
        return str(UUID(page["id"]))
    except ProfileCryptoUnavailable:
        raise AccessError(503) from None
    except (ValueError, TypeError, KeyError, OverflowError):
        fail(422, "VALIDATION_ERROR")


@router.get(
    "/admin/print-templates", operation_id="API-300", response_model=TemplateList
)
def listing(request: Request, context: Authenticated):
    guard(context, request)
    query(request, {"purpose", "status", "limit", "cursor"})
    p = dict(request.query_params)
    if p.get("purpose", "lost") not in {"lost", "ice"} or p.get(
        "status", "draft"
    ) not in {"draft", "active", "retired"}:
        fail(422, "VALIDATION_ERROR")
    if (
        not re.fullmatch(r"[1-9][0-9]?", p.get("limit", "20"))
        or int(p.get("limit", 20)) > 50
    ):
        fail(422, "VALIDATION_ERROR")
    scope = "list:" + json.dumps(
        {k: v for k, v in p.items() if k != "cursor"}, sort_keys=True
    )
    p["after"] = cursor(request, context, scope)
    value = TemplateRepository(context).call("list", p)
    if value["next_cursor"]:
        value["next_cursor"] = cursor(request, context, scope, value["next_cursor"])
    return value


@router.post(
    "/admin/print-templates",
    operation_id="API-301",
    status_code=201,
    response_model=CreateReceipt,
)
def create(body: Create, request: Request, context: Authenticated):
    return command(context, request, "create", body)


@router.get(
    "/admin/print-templates/{template_id}",
    operation_id="API-302",
    response_model=TemplateDetail,
)
def detail(
    template_id: UUID, request: Request, response: Response, context: Authenticated
):
    guard(context, request)
    query(request, {"revisions_limit", "revisions_cursor"})
    limit = request.query_params.get("revisions_limit", "20")
    if not re.fullmatch(r"[1-9][0-9]?", limit) or int(limit) > 50:
        fail(422, "VALIDATION_ERROR")
    scope = "revisions:" + str(template_id) + ":" + limit
    value = TemplateRepository(context).call(
        "detail",
        {
            "template_id": str(template_id),
            "limit": int(limit),
            "after": cursor(request, context, scope),
        },
    )
    if value["next_cursor"]:
        value["next_cursor"] = cursor(request, context, scope, value["next_cursor"])
    response.headers["ETag"] = f'"{value["template"]["row_version"]}"'
    return value


@router.post(
    "/admin/print-templates/{template_id}/revisions",
    operation_id="API-303",
    status_code=201,
    response_model=RevisionReceipt,
)
def revision(
    template_id: UUID, body: NewRevision, request: Request, context: Authenticated
):
    return command(context, request, "revision", body, template_id=str(template_id))


@router.patch(
    "/admin/print-templates/{template_id}/revisions/{revision_id}",
    operation_id="API-304",
    response_model=EditReceipt,
)
def edit(
    template_id: UUID,
    revision_id: UUID,
    body: DraftEditRequest,
    request: Request,
    context: Authenticated,
):
    return command(
        context,
        request,
        "edit",
        body,
        template_id=str(template_id),
        revision_id=str(revision_id),
    )


@router.post(
    "/admin/print-templates/{template_id}/revisions/{revision_id}/preview",
    operation_id="API-305",
    response_class=Response,
    responses={
        200: {
            "description": "Private synthetic PDF; not physical QA approval",
            "content": {
                "application/pdf": {"schema": {"type": "string", "format": "binary"}}
            },
        }
    },
)
def preview(
    template_id: UUID,
    revision_id: UUID,
    body: Preview,
    request: Request,
    context: Authenticated,
):
    data, fingerprint, _ = proof(
        context, request, template_id, revision_id, body.expected_revision
    )
    return Response(
        data,
        media_type="application/pdf",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": 'inline; filename="synthetic-template-preview.pdf"',
            "X-Template-Fingerprint": fingerprint,
        },
    )


def proof(context, request, template_id, revision_id, expected, *, draft=True):
    guard(context, request, write=True, draft=draft)
    if match(request) != expected:
        fail(412, "VERSION_MISMATCH")
    keys = request.headers.getlist("idempotency-key")
    if len(keys) != 1 or not re.fullmatch(r"[A-Za-z0-9._:-]{8,160}", keys[0]):
        fail(400, "VALIDATION_ERROR")
    root = request.app.state.settings.print_template_asset_root
    if not root:
        fail(503, "TEMPLATE_ASSETS_UNAVAILABLE")
    if not PREVIEW_PLATFORM_SUPPORTED:
        fail(503, "PREVIEW_ISOLATION_UNAVAILABLE")
    payload = {
        "template_id": str(template_id),
        "revision_id": str(revision_id),
        "expected": expected,
    }
    spec = TemplateRepository(context).call("preview_input", payload)
    c = Content.model_validate(spec["content"])
    fingerprint = c.fingerprint(
        spec["key"], spec["version"], spec["purpose"], spec["assets"]
    )
    key_hash = hashlib.sha256((request.url.path + ":" + keys[0]).encode()).hexdigest()
    body_hash = hashlib.sha256(
        json.dumps(payload | {"fingerprint": fingerprint}, sort_keys=True).encode()
    ).hexdigest()
    # Separate committed admission counts failures too; no lock spans PDF processing.
    with api_transaction(
        request.app.state.database, context.principal.user_id
    ) as session:
        admitted_context = authorize(session, context.principal)
        guard(admitted_context, request, write=True, draft=draft)
        admission = session.execute(
            text("SELECT public.sr_template_preview_admit(:sid,:amr,:k,:h)"),
            {
                "sid": context.principal.session_id,
                "amr": context.principal.authentication_time,
                "k": key_hash,
                "h": body_hash,
            },
        ).scalar_one()
        if admission == "RATE_LIMITED":
            raise AccessError(429)
        if admission != "ok":
            if admission == "FORBIDDEN":
                raise AccessError(403)
            fail(409, "IDEMPOTENCY_KEY_REUSED")
    try:
        data = isolated_preview(spec, root)
    except PrintUnavailable as exc:
        code = {"preview_timeout": "PREVIEW_TIMEOUT", "preview_busy": "PREVIEW_BUSY", "asset_unavailable": "TEMPLATE_ASSETS_UNAVAILABLE", "unsafe_asset": "TEMPLATE_ASSETS_UNAVAILABLE", "asset_registry_unavailable": "TEMPLATE_ASSETS_UNAVAILABLE", "preview_failed": "PREVIEW_WORKER_FAILED"}.get(str(exc), "PREVIEW_WORKER_FAILED")
        fail(503, code)
    except (OSError, ValueError, KeyError):
        raise AccessError(503) from None
    current_context = authorize(context.session, context.principal)
    guard(current_context, request, write=True, draft=draft)
    current = TemplateRepository(current_context).call("preview_input", payload)
    if current != spec:
        fail(409, "CONFLICT")
    return data, fingerprint, spec


@router.post(
    "/admin/print-templates/{template_id}/revisions/{revision_id}/submit-qa",
    operation_id="API-306",
    response_model=SubmitReceipt,
)
def submit(
    template_id: UUID,
    revision_id: UUID,
    body: Reason,
    request: Request,
    context: Authenticated,
):
    def prepare():
        _, fingerprint, spec = proof(
            context, request, template_id, revision_id, match(request), draft=False
        )
        return {
            "proof_content": spec["content"],
            "proof_font": spec["assets"]["font"]["sha256"],
            "proof_logo": spec["assets"]["logo"]["sha256"],
            "proof_fingerprint": fingerprint,
        }

    return command(
        context,
        request,
        "submit",
        body,
        prepare=prepare,
        template_id=str(template_id),
        revision_id=str(revision_id),
    )


@router.post(
    "/admin/print-templates/{template_id}/revisions/{revision_id}/publish",
    operation_id="API-307",
    response_model=PublishedTemplateReceipt,
)
def publish(
    template_id: UUID,
    revision_id: UUID,
    body: Publish,
    request: Request,
    context: Authenticated,
):
    return command(
        context,
        request,
        "publish",
        body,
        template_id=str(template_id),
        revision_id=str(revision_id),
        prepare=lambda: publication_proof(
            context,
            request.app.state.settings,
            template_id,
            revision_id,
            body.approval_id,
        ),
    )


@router.post(
    "/admin/print-template-bindings",
    operation_id="API-308",
    status_code=201,
    response_model=TemplateBindingReceipt,
)
def bind(body: Bind, request: Request, context: Authenticated):
    return command(context, request, "bind", body)


@router.get(
    "/admin/print-template-bindings",
    operation_id="API-309",
    response_model=TemplateBindingsPage,
)
def bindings(request: Request, context: Authenticated):
    guard(context, request)
    query(request, {"variant_id", "tag_type", "active", "limit", "cursor"})
    p = dict(request.query_params)
    limit = p.get("limit", "20")
    if (
        not re.fullmatch(r"[1-9][0-9]?", limit)
        or int(limit) > 50
        or p.get("tag_type", "lost") not in {"lost", "ice"}
        or p.get("active", "true") not in {"true", "false"}
    ):
        fail(422, "VALIDATION_ERROR")
    try:
        if "variant_id" in p:
            p["variant_id"] = str(UUID(p["variant_id"]))
    except ValueError:
        fail(422, "VALIDATION_ERROR")
    scope = "bindings:" + json.dumps(
        {k: v for k, v in p.items() if k != "cursor"}, sort_keys=True
    )
    p["after"] = cursor(request, context, scope)
    result = TemplateRepository(context).call("bindings", p)
    if len(result["items"]) > int(limit):
        result["items"] = result["items"][: int(limit)]
        result["next_cursor"] = cursor(
            request, context, scope, result["items"][-1]["binding_id"]
        )
    return result


@router.post(
    "/admin/print-templates/{template_id}/revisions/{revision_id}/retire",
    operation_id="API-310",
    response_model=RetiredTemplateReceipt,
)
def retire(
    template_id: UUID,
    revision_id: UUID,
    body: Retire,
    request: Request,
    context: Authenticated,
):
    return command(
        context,
        request,
        "retire",
        body,
        template_id=str(template_id),
        revision_id=str(revision_id),
    )


def install(application):
    application.include_router(router, prefix="/api/v1")

    @application.middleware("http")
    async def headers(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith(
            ("/api/v1/admin/print-templates", "/api/v1/admin/print-template-bindings")
        ):
            if response.status_code == 405:
                allowed = response.headers.get("Allow")
                response = error(request, 405, "METHOD_NOT_ALLOWED")
                if allowed:
                    response.headers["Allow"] = allowed
            response.headers["Cache-Control"] = "private, no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response

class QAReviewView(Closed):
    review_id: UUID
    revision_id: UUID
    revision_row_version: int = Field(ge=1)
    review_version: int = Field(ge=1)
    decision: Literal["approved", "rejected"]
    review_note: str = Field(min_length=4, max_length=500)
    reviewer_user_id: UUID
    reviewer_human_id: UUID | None
    evidence_kind: Literal["signed_evidence", "manual_print"]
    preview_fingerprint: str | None
    approval_id: UUID | None
    decided_at: datetime


class QAStateView(Closed):
    revision_id: UUID
    revision_row_version: int = Field(ge=1)
    review_version: int = Field(ge=0)
    status: Literal["pending", "approved", "rejected"]
    can_review: bool
    history: list[QAReviewView] = Field(max_length=20)


class QADecisionReceipt(Closed):
    command_id: UUID
    result: QAStateView


class QADecision(Confirmed):
    decision: Literal["approved", "rejected"]
    expected_review_version: int = Field(ge=0, strict=True)
    preview_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    reason: str = Field(default="Staff recorded a manual print review", min_length=4, max_length=500)

    @field_validator("reason")
    @classmethod
    def text(cls, value):
        return plain(value)


def review_available(context):
    if not context.session.execute(text("SELECT EXISTS(SELECT 1 FROM pg_attribute WHERE attrelid=to_regclass('public.template_qa_reviews') AND attname='evidence_kind' AND NOT attisdropped) AS template_qa_reviews_available")).scalar_one():
        fail(503, "PROVIDER_UNAVAILABLE")


@router.get("/admin/print-templates/{template_id}/revisions/{revision_id}/qa", operation_id="API-311", response_model=QAStateView)
def qa_status(template_id: UUID, revision_id: UUID, request: Request, context: Authenticated):
    from app.db.template_registry import RegistryRepository
    guard(context, request)
    recent_template_auth(context)
    query(request, set())
    review_available(context)
    return RegistryRepository(context).call("manual_review_status", {"template_id": str(template_id), "revision_id": str(revision_id)})


@router.post("/admin/print-templates/{template_id}/revisions/{revision_id}/qa-decision", operation_id="API-312", response_model=QADecisionReceipt)
def qa_decision(template_id: UUID, revision_id: UUID, body: QADecision, request: Request, context: Authenticated):
    guard(context, request, write=True)
    if request.headers.getlist("origin") != [request.app.state.settings.print_template_web_origin]:
        fail(403, "TEMPLATE_ORIGIN_MISMATCH")
    review_available(context)
    return command(context, request, "manual_review_decide", body, template_id=str(template_id), revision_id=str(revision_id))
