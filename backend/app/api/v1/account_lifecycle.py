"""Case-approved application security commands; never provider administration."""

import hashlib
import re
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import AwareDatetime, Field, ValidationError, field_validator
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import (
    AccessError,
    AuthContext,
    Authenticated,
    authorize,
    require_staff,
)
from app.api.v1.cancellations import Confirmed
from app.api.v1.catalog import CatalogRoute, Closed
from app.api.v1.privacy_exports import recent
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt, encrypt

router = APIRouter(tags=["account lifecycle"], route_class=CatalogRoute)
Action = Literal["suspend", "restore", "recovery_escalated"]


class Command(Confirmed):
    case_id: UUID
    expected_revision: int = Field(ge=1, le=2147483646, strict=True)


class Suspend(Command):
    reason_code: Literal["suspected_compromise", "abuse_review", "security_review"]


class Restore(Command):
    reason_code: Literal["review_cleared"]


class Recovery(Command):
    reason_code: Literal["factor_loss", "account_access_review"]


class Receipt(Closed):
    user_id: UUID
    case_id: UUID
    action: Action
    revision: int = Field(ge=2, le=2147483647, strict=True)
    event_id: UUID
    occurred_at: AwareDatetime

    @field_validator("occurred_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


class StateReceipt(Receipt):
    action: Literal["suspend", "restore"]
    state: Literal["active", "suspended"]
    fresh_sign_in_required: Literal[True]


class ReferralReceipt(Receipt):
    action: Literal["recovery_escalated"]
    status: Literal["referred"]


class LifecycleError(Exception):
    def __init__(self, status: int, code: str):
        self.status, self.code = status, code


ERRORS = {
    "NOT_FOUND": 404,
    "STALE_VERSION": 412,
    "REAUTH_REQUIRED": 403,
    "CONTENTION": 409,
    "INVALID_STATE": 409,
    "LAST_CUSTODIAN": 409,
    "IDEMPOTENCY_KEY_REUSED": 409,
}


def checked(value: dict | None) -> dict:
    if value is None:
        raise AccessError(404)
    if not isinstance(value, dict):
        raise AccessError(503)
    if "error" in value:
        code = value["error"]
        if code not in ERRORS:
            raise AccessError(503)
        raise LifecycleError(ERRORS[code], code)
    return value


def guard(context: AuthContext, request: Request) -> None:
    require_staff(context, "security_admin")
    settings = request.app.state.settings
    if not settings.account_lifecycle_enabled:
        raise AccessError(503)
    if not settings.account_lifecycle_web_origin or request.headers.getlist(
        "origin"
    ) != [settings.account_lifecycle_web_origin]:
        raise AccessError(403)
    if request.query_params:
        raise LifecycleError(422, "INVALID_QUERY")
    # AccessError must propagate through the transaction; shared wrappers catching
    # HTTPException before dependency exit are unsuitable for mutation rollback.
    try:
        recent(context)
    except HTTPException:
        raise LifecycleError(403, "REAUTH_REQUIRED") from None


def execute(
    user_id: UUID,
    body: Suspend | Restore | Recovery,
    action: Action,
    request: Request,
    context: AuthContext,
) -> StateReceipt | ReferralReceipt:
    guard(context, request)
    keys = request.headers.getlist("idempotency-key")
    if len(keys) != 1 or not re.fullmatch(r"[A-Za-z0-9._:-]{8,160}", keys[0]):
        raise LifecycleError(400, "IDEMPOTENCY_KEY_REQUIRED")
    scope = hashlib.sha256(
        f"{context.principal.user_id}:{user_id}:{action}:{keys[0]}".encode()
    ).hexdigest()
    digest = hashlib.sha256(body.model_dump_json().encode()).hexdigest()
    params = {
        "sid": context.principal.session_id,
        "amr": context.principal.authentication_time,
        "uid": user_id,
        "cid": body.case_id,
        "action": action,
        "revision": body.expected_revision,
        "reason": body.reason_code,
        "scope": scope,
        "digest": digest,
    }
    args = ":sid,:amr,:uid,:cid,:action,:revision,:reason,:scope,:digest"
    model = ReferralReceipt if action == "recovery_escalated" else StateReceipt
    settings, db = request.app.state.settings, context.session
    try:
        previous_timeout = db.execute(text("SHOW statement_timeout")).scalar_one()
        db.execute(text("SELECT set_config('statement_timeout','3000ms',true)"))
        snapshot = checked(
            db.execute(
                text(f"SELECT public.sr_lifecycle_context({args})"), params
            ).scalar_one()
        )
        old = snapshot.get("receipt")
        if old:
            raw = decrypt(
                settings,
                context.principal.user_id,
                "account-lifecycle:" + scope,
                bytes.fromhex(old["cipher"]),
                old["key_version"],
            )
            result = model.model_validate_json(raw)
        else:
            value = checked(
                db.execute(
                    text(f"SELECT public.sr_lifecycle_apply({args})"), params
                ).scalar_one()
            )
            result = model.model_validate(value)
            cipher, version = encrypt(
                settings,
                context.principal.user_id,
                "account-lifecycle:" + scope,
                result.model_dump_json(),
            )
            saved = db.execute(
                text(
                    "SELECT public.sr_lifecycle_save_receipt(:scope,:digest,:approval,:event,:cipher,CAST(:version AS smallint))"
                ),
                {
                    "scope": scope,
                    "digest": digest,
                    "approval": snapshot["approval_id"],
                    "event": result.event_id,
                    "cipher": cipher,
                    "version": version,
                },
            ).scalar_one()
            if saved is not True:
                raise AccessError(503)
        if (
            result.user_id != user_id
            or result.case_id != body.case_id
            or result.action != action
            or result.revision != body.expected_revision + 1
        ):
            raise AccessError(503)
        if isinstance(result, StateReceipt) and result.state != (
            "suspended" if action == "suspend" else "active"
        ):
            raise AccessError(503)
        # Revalidate authority even on encrypted replay, after crypto and storage.
        checked(
            db.execute(
                text(f"SELECT public.sr_lifecycle_context({args})"), params
            ).scalar_one()
        )
        guard(authorize(db, context.principal), request)
        db.execute(
            text("SELECT set_config('statement_timeout',:timeout,true)"),
            {"timeout": previous_timeout},
        )
        return result
    except (
        SQLAlchemyError,
        ProfileCryptoUnavailable,
        ValidationError,
        ValueError,
        TypeError,
        KeyError,
    ):
        raise AccessError(503) from None


@router.post(
    "/admin/users/{user_id}/suspensions",
    operation_id="API-320",
    response_model=StateReceipt,
)
def suspend(user_id: UUID, body: Suspend, request: Request, context: Authenticated):
    return execute(user_id, body, "suspend", request, context)


@router.post(
    "/admin/users/{user_id}/restorations",
    operation_id="API-321",
    response_model=StateReceipt,
)
def restore(user_id: UUID, body: Restore, request: Request, context: Authenticated):
    return execute(user_id, body, "restore", request, context)


@router.post(
    "/admin/users/{user_id}/recovery-escalations",
    operation_id="API-322",
    response_model=ReferralReceipt,
    status_code=202,
)
def recovery(user_id: UUID, body: Recovery, request: Request, context: Authenticated):
    return execute(user_id, body, "recovery_escalated", request, context)


def install(application):
    application.include_router(router, prefix="/api/v1")

    @application.exception_handler(LifecycleError)
    async def lifecycle_error(request, error):
        return JSONResponse(
            status_code=error.status,
            content={
                "error": {
                    "code": error.code,
                    "message": "Account security request could not be completed.",
                    "request_id": getattr(request.state, "request_id", None),
                    "details": {},
                }
            },
        )
