"""Approved owner-only034/035. No staff suspension, replacement or restoration."""

import base64
import hashlib
import re
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import AwareDatetime, Field, ValidationError, model_validator
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import AccessError, Authenticated, authorize, require_verified_account
from app.api.v1.cancellations import Confirmed
from app.api.v1.catalog import CatalogRoute, Closed
from app.api.v1.privacy_exports import recent
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt, encrypt, key

router = APIRouter(tags=["owner QR lifecycle"], route_class=CatalogRoute)
PublicState = Literal[
    "unactivated", "active", "owner_disabled", "admin_suspended", "revoked"
]


class LifecycleError(Exception):
    def __init__(self, status, code):
        self.status, self.code = status, code


class Command(Confirmed):
    public_status: Literal["active", "owner_disabled"]
    expected_revision: int = Field(ge=1, le=2147483646, strict=True)
    reason: Literal["temporary", "resume"]
    public_access_acknowledged: bool = Field(strict=True)

    @model_validator(mode="after")
    def reviewed(self):
        if not self.public_access_acknowledged or self.reason != (
            "temporary" if self.public_status == "owner_disabled" else "resume"
        ):
            raise ValueError("Explicit impact review required")
        return self


class Tag(Closed):
    qr_id: UUID
    tag_type: Literal["lost", "ice"]
    public_status: PublicState


class Event(Closed):
    event_id: UUID
    event_type: Literal["activation_completed", "owner_disabled", "owner_enabled"]
    occurred_at: AwareDatetime
    tag_type: Literal["lost", "ice"] | None
    from_status: Literal["active", "owner_disabled"] | None
    to_status: Literal["active", "owner_disabled"] | None

    @model_validator(mode="after")
    def consistent(self):
        if self.occurred_at.utcoffset() != UTC.utcoffset(None):
            self.occurred_at = self.occurred_at.astimezone(UTC)
        if self.event_type == "activation_completed":
            if any(
                x is not None for x in (self.tag_type, self.from_status, self.to_status)
            ):
                raise ValueError("Invalid event")
        elif self.tag_type is None or (self.from_status, self.to_status) != (
            ("active", "owner_disabled")
            if self.event_type == "owner_disabled"
            else ("owner_disabled", "active")
        ):
            raise ValueError("Invalid transition event")
        return self


class Snapshot(Closed):
    pair_id: UUID
    pair_revision: int = Field(ge=1, le=2147483647, strict=True)
    current_tags: list[Tag] = Field(min_length=2, max_length=2)
    items: list[Event] = Field(max_length=101)

    @model_validator(mode="after")
    def exact_pair(self):
        if {t.tag_type for t in self.current_tags} != {"lost", "ice"} or len(
            {t.qr_id for t in self.current_tags}
        ) != 2:
            raise ValueError("Invalid pair")
        keys = [(e.occurred_at, e.event_id) for e in self.items]
        if len(set(keys)) != len(keys) or keys != sorted(keys, reverse=True):
            raise ValueError("Invalid history order")
        return self


class History(Snapshot):
    next_cursor: str | None


class Receipt(Closed):
    pair_id: UUID
    qr_id: UUID
    tag_type: Literal["lost", "ice"]
    public_status: Literal["active", "owner_disabled"]
    pair_revision: int = Field(ge=2, le=2147483647, strict=True)


class Position(Closed):
    pair_id: UUID
    occurred_at: AwareDatetime
    event_id: UUID


def checked(value):
    if value is None:
        raise AccessError(404)
    if not isinstance(value, dict):
        raise AccessError(503)
    if "error" in value:
        errors = {
            "REAUTH_REQUIRED": 403,
            "VERSION_MISMATCH": 412,
            "INVALID_STATE": 409,
            "IDEMPOTENCY_KEY_REUSED": 409,
        }
        if value["error"] not in errors:
            raise AccessError(503)
        raise LifecycleError(errors[value["error"]], value["error"])
    return value


def guard(context, request, write=False):
    require_verified_account(context)
    settings = request.app.state.settings
    if not settings.qr_lifecycle_enabled:
        raise AccessError(503)
    if write:
        if request.query_params:
            raise LifecycleError(422, "INVALID_QUERY")
        if not settings.qr_lifecycle_web_origin or request.headers.getlist(
            "origin"
        ) != [settings.qr_lifecycle_web_origin]:
            raise AccessError(403)
        try:
            recent(context)
        except HTTPException:
            raise LifecycleError(403, "REAUTH_REQUIRED") from None


def cursor(settings, actor, pos):
    cipher, version = encrypt(
        settings, actor, "qr_lifecycle_history", pos.model_dump_json()
    )
    return str(version) + "." + base64.urlsafe_b64encode(cipher).decode()


def position(settings, actor, pid, token):
    try:
        if len(token) > 4096 or not re.fullmatch(
            r"[1-9]\d*\.[A-Za-z0-9_-]+={0,2}", token
        ):
            raise ValueError()
        version, raw = token.split(".", 1)
        value = decrypt(
            settings,
            actor,
            "qr_lifecycle_history",
            base64.b64decode(raw, altchars=b"-_", validate=True),
            int(version),
        )
        pos = Position.model_validate_json(value)
        if pos.pair_id != pid or pos.occurred_at > datetime.now(UTC):
            raise ValueError()
        return pos
    except (ValueError, TypeError, ProfileCryptoUnavailable):
        raise LifecycleError(422, "INVALID_CURSOR") from None


@router.get(
    "/me/tag-pairs/{pair_id}/activation-history",
    operation_id="API-034",
    response_model=History,
)
def history(pair_id: UUID, context: Authenticated, request: Request):
    guard(context, request)
    params = request.query_params
    if any(k not in {"limit", "cursor"} or len(params.getlist(k)) != 1 for k in params):
        raise LifecycleError(422, "INVALID_QUERY")
    raw_limit = params.get("limit", "20")
    if not re.fullmatch(r"[1-9]\d{0,2}", raw_limit) or not 1 <= int(raw_limit) <= 100:
        raise LifecycleError(422, "INVALID_QUERY")
    settings, actor, db = (
        request.app.state.settings,
        context.principal.user_id,
        context.session,
    )
    try:
        key(settings, settings.profile_data_key_version)
    except ProfileCryptoUnavailable:
        raise AccessError(503) from None
    pos = (
        position(settings, actor, pair_id, params["cursor"])
        if "cursor" in params
        else None
    )
    limit = int(raw_limit)
    try:
        db.execute(text("SET LOCAL statement_timeout='3s'"))
        args = {
            "sid": context.principal.session_id,
            "pid": pair_id,
            "take": limit + 1,
            "stamp": pos.occurred_at if pos else None,
            "eid": pos.event_id if pos else None,
        }
        snap = Snapshot.model_validate(
            checked(
                db.execute(
                    text(
                        "SELECT public.sr_qr_lifecycle_history(:sid,:pid,:take,:stamp,:eid)"
                    ),
                    args,
                ).scalar_one()
            )
        )
        if snap.pair_id != pair_id or len(snap.items) > limit + 1:
            raise AccessError(503)
        items = snap.items[:limit]
        next_cursor = (
            cursor(
                settings,
                actor,
                Position(
                    pair_id=pair_id,
                    occurred_at=items[-1].occurred_at,
                    event_id=items[-1].event_id,
                ),
            )
            if len(snap.items) > limit
            else None
        )
        guard(authorize(db, context.principal), request)
        # Recheck ownership after projection/crypto. A shared parent lock in the
        # helper holds cooperative lifecycle changes through transaction end.
        final_snapshot = Snapshot.model_validate(
            checked(
                db.execute(
                    text(
                        "SELECT public.sr_qr_lifecycle_history(:sid,:pid,1,NULL,NULL)"
                    ),
                    {"sid": args["sid"], "pid": pair_id},
                ).scalar_one()
            )
        )
        if (
            final_snapshot.pair_id != pair_id
            or final_snapshot.pair_revision != snap.pair_revision
            or final_snapshot.current_tags != snap.current_tags
        ):
            raise AccessError(503)
        return History(
            **snap.model_dump(exclude={"items"}), items=items, next_cursor=next_cursor
        )
    except (SQLAlchemyError, ProfileCryptoUnavailable, ValueError, TypeError, KeyError):
        raise AccessError(503) from None


@router.patch(
    "/me/qr/{qr_id}/public-status", operation_id="API-035", response_model=Receipt
)
def change_status(qr_id: UUID, body: Command, context: Authenticated, request: Request):
    guard(context, request, True)
    keys = request.headers.getlist("idempotency-key")
    if len(keys) != 1 or not re.fullmatch(r"[A-Za-z0-9._:-]{8,160}", keys[0]):
        raise LifecycleError(400, "IDEMPOTENCY_KEY_REQUIRED")
    actor, db, settings = (
        context.principal.user_id,
        context.session,
        request.app.state.settings,
    )
    scope = hashlib.sha256(
        f"{actor}:qr.public_status:{qr_id}:{keys[0]}".encode()
    ).hexdigest()
    digest = hashlib.sha256(body.model_dump_json().encode()).hexdigest()
    params = {
        "sid": context.principal.session_id,
        "amr": context.principal.authentication_time,
        "qid": qr_id,
        "expected": body.expected_revision,
        "wanted": body.public_status,
        "why": body.reason,
        "scope": scope,
        "digest": digest,
    }
    sql = text(
        "SELECT public.sr_qr_lifecycle_command(:sid,:amr,:qid,:expected,:wanted,:why,:scope,:digest)"
    )
    try:
        db.execute(text("SET LOCAL statement_timeout='3s'"))
        value = checked(db.execute(sql, params).scalar_one())
        if "receipt" in value:
            if set(value) != {"receipt"}:
                raise AccessError(503)
            record = ClosedReceipt.model_validate(value["receipt"])
            result = Receipt.model_validate_json(
                decrypt(
                    settings,
                    actor,
                    "qr-lifecycle:" + scope,
                    bytes.fromhex(record.cipher),
                    record.key_version,
                )
            )
        else:
            result = Receipt.model_validate(value)
            cipher, version = encrypt(
                settings, actor, "qr-lifecycle:" + scope, result.model_dump_json()
            )
            if (
                db.execute(
                    text(
                        "SELECT public.sr_qr_lifecycle_save(:sid,:amr,:qid,:scope,:digest,:cipher,CAST(:version AS smallint))"
                    ),
                    {
                        "sid": params["sid"],
                        "amr": params["amr"],
                        "qid": qr_id,
                        "scope": scope,
                        "digest": digest,
                        "cipher": cipher,
                        "version": version,
                    },
                ).scalar_one()
                is not True
            ):
                raise AccessError(503)
        if (
            result.qr_id != qr_id
            or result.public_status != body.public_status
            or result.pair_revision != body.expected_revision + 1
        ):
            raise AccessError(503)
        # Replay helper cannot mutate again: original encrypted receipt now exists.
        final = checked(db.execute(sql, params).scalar_one())
        if set(final) != {"receipt"}:
            raise AccessError(503)
        ClosedReceipt.model_validate(final["receipt"])
        guard(authorize(db, context.principal), request, True)
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


class ClosedReceipt(Closed):
    cipher: str = Field(pattern=r"^[0-9a-f]+$", max_length=8192)
    key_version: int = Field(ge=1, le=32767, strict=True)


def install(application):
    application.include_router(router, prefix="/api/v1")

    @application.exception_handler(LifecycleError)
    async def lifecycle_error(request, error):
        return JSONResponse({"error": {"code": error.code}}, status_code=error.status)

    @application.middleware("http")
    async def privacy(request, call_next):
        response = await call_next(request)
        if request.url.path.endswith(("/activation-history", "/public-status")):
            response.headers.update(
                {
                    "Cache-Control": "private, no-store",
                    "X-Content-Type-Options": "nosniff",
                    "Referrer-Policy": "no-referrer",
                }
            )
        return response
