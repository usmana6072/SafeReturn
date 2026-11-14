"""Approved Task 2.3C metadata reads; no provider administration or profile access."""

import base64
import json
import re
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Request
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
from app.api.v1.catalog import CatalogRoute, Closed, fail
from app.api.v1.dashboard import Count

router = APIRouter(tags=["staff user directory"], route_class=CatalogRoute)
Access = Literal["banned", "not_banned"]


def install(application):
    application.include_router(router, prefix="/api/v1")

    @application.middleware("http")
    async def directory_headers(request, call_next):
        # Leave AccessError propagation intact until the dependency rolls back.
        response = await call_next(request)
        if request.url.path == "/api/v1/admin/users" or request.url.path.startswith(
            "/api/v1/admin/users/"
        ):
            response.headers["Cache-Control"] = "private, no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response


class Filters(Closed):
    user_id: UUID | None = None
    email_verified: bool | None = Field(default=None, strict=True)
    provider_access: Access | None = None


class User(Closed):
    user_id: UUID
    registered_at: AwareDatetime
    email_verified: bool = Field(strict=True)
    provider_access: Access

    @field_validator("registered_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


class Observed(Closed):
    as_of: AwareDatetime

    @field_validator("as_of")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


class Page(Observed):
    items: list[User] = Field(max_length=100)
    next_cursor: str | None


class Suspension(Closed):
    status: Literal["unavailable"] = "unavailable"
    reason_code: Literal["NOT_IMPLEMENTED"] = "NOT_IMPLEMENTED"


class StateUnavailable(Closed):
    status: Literal["unavailable"] = "unavailable"
    reason_code: Literal["STATE_UNAVAILABLE"] = "STATE_UNAVAILABLE"


class ApplicationState(Observed):
    status: Literal["ready"] = "ready"
    state: Literal["active", "suspended"]
    revision: int = Field(ge=1, le=2147483647, strict=True)
    commands_available: bool = Field(strict=True)


class Detail(Observed):
    user: User
    application_suspension: Suspension | StateUnavailable | ApplicationState = Field(
        default_factory=Suspension
    )


class Total(Observed):
    definition: Literal["retained_nonanonymous_auth_registrations_v1"]
    filters: Filters
    count: Count


def guard(context: AuthContext, request: Request, allowed: set[str]) -> None:
    require_staff(context, "security_admin")
    if not request.app.state.settings.staff_directory_enabled:
        raise AccessError(503)
    if any(
        k not in allowed or len(request.query_params.getlist(k)) != 1
        for k in request.query_params
    ):
        fail(422, "INVALID_QUERY")


def filters(request: Request) -> Filters:
    values = dict(request.query_params)
    try:
        verified = values.get("email_verified")
        if verified not in (None, "true", "false"):
            raise ValueError()
        if values.get("provider_access") not in (None, "banned", "not_banned"):
            raise ValueError()
        return Filters(
            user_id=values.get("user_id"),
            email_verified=None if verified is None else verified == "true",
            provider_access=values.get("provider_access"),
        )
    except (ValueError, ValidationError):
        fail(422, "INVALID_QUERY")


def encode_cursor(user: User, selected: Filters) -> str:
    data = {
        "v": 1,
        "at": user.registered_at.astimezone(UTC).isoformat(),
        "id": str(user.user_id),
        "filters": selected.model_dump(mode="json"),
    }
    return (
        base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":")).encode())
        .decode()
        .rstrip("=")
    )


def decode_cursor(
    value: str | None, selected: Filters
) -> tuple[datetime | None, UUID | None]:
    if value is None:
        return None, None
    try:
        if len(value) > 1024 or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ValueError()
        raw = json.loads(
            base64.b64decode(
                value + "=" * (-len(value) % 4), altchars=b"-_", validate=True
            )
        )
        if (
            set(raw) != {"v", "at", "id", "filters"}
            or type(raw["v"]) is not int
            or raw["v"] != 1
            or raw["filters"] != selected.model_dump(mode="json")
        ):
            raise ValueError()
        user = User(
            user_id=raw["id"],
            registered_at=raw["at"],
            email_verified=False,
            provider_access="not_banned",
        )
        if encode_cursor(user, selected) != value:
            raise ValueError()
        return user.registered_at, user.user_id
    except (ValueError, TypeError, KeyError, ValidationError):
        fail(422, "INVALID_CURSOR")


def read(
    context: AuthContext,
    mode: str,
    selected: Filters,
    limit: int = 20,
    stamp: datetime | None = None,
    ident: UUID | None = None,
) -> Any:
    # Any failed helper or invalid projection fails closed. No broad Auth fallback.
    try:
        with context.session.begin_nested():
            previous = context.session.execute(
                text("SHOW statement_timeout")
            ).scalar_one()
            context.session.execute(
                text("SELECT set_config('statement_timeout','3000ms',true)")
            )
            value = context.session.execute(
                text(
                    "SELECT public.sr_staff_directory(:sid,:mode,:uid,:verified,:access,:lim,:stamp,:ident)"
                ),
                {
                    "sid": context.principal.session_id,
                    "mode": mode,
                    "uid": selected.user_id,
                    "verified": selected.email_verified,
                    "access": selected.provider_access,
                    "lim": limit,
                    "stamp": stamp,
                    "ident": ident,
                },
            ).scalar_one()
            context.session.execute(
                text("SELECT set_config('statement_timeout',:timeout,true)"),
                {"timeout": previous},
            )
            if value is None:
                raise AccessError(403)
            return value
    except SQLAlchemyError:
        raise AccessError(503) from None


def finish(context: AuthContext) -> None:
    require_staff(authorize(context.session, context.principal), "security_admin")


def application_state(
    context: AuthContext, user_id: UUID, request: Request
) -> ApplicationState | StateUnavailable:
    try:
        with context.session.begin_nested():
            previous = context.session.execute(
                text("SHOW statement_timeout")
            ).scalar_one()
            context.session.execute(
                text("SELECT set_config('statement_timeout',:timeout,true)"),
                {"timeout": "3000ms"},
            )
            value = context.session.execute(
                text("SELECT public.sr_staff_account_state(:sid,:uid)"),
                {"sid": context.principal.session_id, "uid": user_id},
            ).scalar_one()
            context.session.execute(
                text("SELECT set_config('statement_timeout',:timeout,true)"),
                {"timeout": previous},
            )
            if value is None:
                finish(context)
                raise AccessError(404)
            settings = request.app.state.settings
            if set(value) != {"status", "state", "revision", "as_of"}:
                raise ValueError()
            return ApplicationState.model_validate(
                {
                    **value,
                    "commands_available": bool(
                        settings.account_lifecycle_enabled
                        and settings.account_lifecycle_web_origin
                    ),
                }
            )
    except (SQLAlchemyError, ValidationError, TypeError, ValueError):
        return StateUnavailable()


@router.get("/admin/users", operation_id="API-346", response_model=Page)
def users(request: Request, context: Authenticated) -> Page:
    guard(
        context,
        request,
        {"user_id", "email_verified", "provider_access", "limit", "cursor"},
    )
    selected = filters(request)
    limit_text = request.query_params.get("limit", "20")
    if (
        not re.fullmatch(r"[1-9][0-9]{0,2}", limit_text)
        or not 1 <= int(limit_text) <= 100
    ):
        fail(422, "INVALID_LIMIT")
    limit = int(limit_text)
    stamp, ident = decode_cursor(request.query_params.get("cursor"), selected)
    raw = read(context, "list", selected, limit, stamp, ident)
    try:
        if (
            set(raw) != {"as_of", "items"}
            or not isinstance(raw["items"], list)
            or len(raw["items"]) > limit + 1
        ):
            raise ValueError()
        rows = [User.model_validate(row) for row in raw["items"]]
        result = Page(
            as_of=raw["as_of"],
            items=rows[:limit],
            next_cursor=encode_cursor(rows[limit - 1], selected)
            if len(rows) > limit
            else None,
        )
    except (ValueError, TypeError, ValidationError):
        raise AccessError(503) from None
    finish(context)
    return result


@router.get("/admin/users/count", operation_id="API-348", response_model=Total)
def total(request: Request, context: Authenticated) -> Total:
    guard(context, request, {"user_id", "email_verified", "provider_access"})
    selected = filters(request)
    try:
        result = Total.model_validate(read(context, "count", selected))
        if result.filters != selected:
            raise ValueError()
    except (ValueError, TypeError, ValidationError):
        raise AccessError(503) from None
    finish(context)
    return result


@router.get("/admin/users/{user_id}", operation_id="API-347", response_model=Detail)
def detail(user_id: UUID, request: Request, context: Authenticated) -> Detail:
    guard(context, request, {"include"})
    include = request.query_params.get("include")
    if include not in (None, "account_security"):
        fail(422, "INVALID_QUERY")
    raw = read(context, "detail", Filters(user_id=user_id))
    try:
        if (
            set(raw) != {"as_of", "items"}
            or not isinstance(raw["items"], list)
            or len(raw["items"]) > 1
        ):
            raise ValueError()
        if not raw["items"]:
            finish(context)
            raise AccessError(404)
        result = Detail(as_of=raw["as_of"], user=User.model_validate(raw["items"][0]))
        if result.user.user_id != user_id:
            raise ValueError()
    except (ValueError, TypeError, ValidationError):
        raise AccessError(503) from None
    if include == "account_security":
        result.application_suspension = application_state(context, user_id, request)
    finish(context)
    return result
