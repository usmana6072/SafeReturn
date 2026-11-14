"""Approved349/350 investigation metadata, never production or financial authority."""

import base64
import re
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import AwareDatetime, Field, ValidationError, field_validator
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import AccessError, Authenticated, authorize, require_staff
from app.api.v1.catalog import CatalogRoute, Closed, fail
from app.api.v1.fulfillment_queries import (
    FulfillmentStatus,
    OrderStatus,
    PaymentStatus,
)
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt, encrypt, key

router = APIRouter(tags=["print investigation metadata"], route_class=CatalogRoute)
State = Literal[
    "queued",
    "rendering",
    "ready",
    "downloaded",
    "qa_passed",
    "failed",
    "superseded",
    "deleted",
]
STATES = list(State.__args__)
Sort = Literal["oldest", "newest"]


class Filters(Closed):
    job_id: UUID | None = None
    order_id: UUID | None = None
    order_number: str | None = Field(default=None, min_length=1, max_length=40)
    job_status: State | None = None
    order_status: OrderStatus | None = None
    payment_status: PaymentStatus | None = None
    fulfillment_status: FulfillmentStatus | None = None
    created_from: AwareDatetime | None = None
    created_before: AwareDatetime | None = None

    @field_validator("order_number", mode="before")
    @classmethod
    def exact_number(cls, value):
        if isinstance(value, str) and (
            value != value.strip() or re.search(r"[\x00-\x1f\x7f]", value)
        ):
            raise ValueError("Invalid exact number")
        return value

    @field_validator("created_from", "created_before", mode="before")
    @classmethod
    def aware_text(cls, value):
        if isinstance(value, str) and not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})",
            value,
        ):
            raise ValueError("Expected aware ISO timestamp")
        return value

    @field_validator("created_from", "created_before")
    @classmethod
    def utc(cls, value):
        return value.astimezone(UTC) if value else value


class Item(Closed):
    job_id: UUID
    order_id: UUID
    order_number: str = Field(min_length=1, max_length=40)
    job_revision: int = Field(ge=1, strict=True)
    job_status: State
    created_at: AwareDatetime
    order_status: OrderStatus
    payment_status: PaymentStatus
    fulfillment_status: FulfillmentStatus
    attempt_count: int = Field(ge=0, strict=True)
    failure_category: Literal["PHYSICAL_QA_FAILED", "PRINT_FAILURE_RECORDED"] | None

    @field_validator("created_at")
    @classmethod
    def utc(cls, value):
        return value.astimezone(UTC)


class Page(Closed):
    as_of: AwareDatetime
    items: list[Item]
    next_cursor: str | None


class Count(Closed):
    value: int = Field(ge=0, le=1000, strict=True)
    is_exact: bool = Field(strict=True)


class Counts(Closed):
    as_of: AwareDatetime
    matching_jobs: Count
    by_job_status: dict[State, Count]
    affected_orders: Count


class Position(Closed):
    filters: str
    sort: Sort
    as_of: AwareDatetime
    at: AwareDatetime
    job_id: UUID


def selected(context, request, paging):
    require_staff(context, "operations")
    values = request.query_params
    allowed = set(Filters.model_fields) | (
        {"limit", "sort", "cursor"} if paging else set()
    )
    if any(k not in allowed or len(values.getlist(k)) != 1 for k in values):
        fail(422, "INVALID_QUERY")
    try:
        filters = Filters.model_validate(
            {k: v for k, v in values.items() if k in Filters.model_fields}
        )
        if (
            filters.created_from
            and filters.created_before
            and filters.created_from >= filters.created_before
        ):
            raise ValueError()
    except ValueError:
        fail(422, "INVALID_QUERY")
    return filters


def encode(settings, actor, position):
    cipher, version = encrypt(
        settings, actor, "print_query_cursor", position.model_dump_json()
    )
    return str(version) + "." + base64.urlsafe_b64encode(cipher).decode()


def decode(settings, actor, token, filters, sort):
    try:
        if len(token) > 4096 or not re.fullmatch(
            r"[1-9][0-9]*\.[A-Za-z0-9_-]+={0,2}", token
        ):
            raise ValueError()
        version, encoded = token.split(".", 1)
        value = decrypt(
            settings,
            actor,
            "print_query_cursor",
            base64.b64decode(encoded, altchars=b"-_", validate=True),
            int(version),
        )
        pos = Position.model_validate_json(value)
        if (
            pos.filters != filters.model_dump_json()
            or pos.sort != sort
            or pos.at > pos.as_of
            or pos.as_of > datetime.now(UTC)
        ):
            raise ValueError()
        return pos
    except (ValueError, TypeError, ValidationError, ProfileCryptoUnavailable):
        fail(422, "INVALID_CURSOR")


WHERE = """FROM public.print_jobs j JOIN public.orders o ON o.id=j.order_id
 WHERE public.sr_is_staff(ARRAY['operations']) AND j.created_at<=:as_of
 AND (CAST(:job_id AS uuid) IS NULL OR j.id=:job_id)
 AND (CAST(:order_id AS uuid) IS NULL OR j.order_id=:order_id)
 AND (CAST(:order_number AS text) IS NULL OR o.order_number=:order_number)
 AND (CAST(:job_status AS text) IS NULL OR j.status=:job_status)
 AND (CAST(:order_status AS text) IS NULL OR o.order_status=:order_status)
 AND (CAST(:payment_status AS text) IS NULL OR o.payment_status=:payment_status)
 AND (CAST(:fulfillment_status AS text) IS NULL OR o.fulfillment_status=:fulfillment_status)
 AND (CAST(:created_from AS timestamptz) IS NULL OR j.created_at>=:created_from)
 AND (CAST(:created_before AS timestamptz) IS NULL OR j.created_at<:created_before)"""
FIELDS = """j.id AS job_id,j.order_id,o.order_number,j.job_revision,j.status AS job_status,
 j.created_at,o.order_status,o.payment_status,o.fulfillment_status,j.attempt_count,
 CASE WHEN j.failure_code IS NULL THEN NULL WHEN j.failure_code='physical_qa_failed'
 THEN 'PHYSICAL_QA_FAILED' ELSE 'PRINT_FAILURE_RECORDED' END AS failure_category"""


def finish(context, action):
    require_staff(authorize(context.session, context.principal), "operations")
    context.session.execute(
        text("""INSERT INTO public.audit_events
      (actor_user_id,actor_kind,action,target_type,reason,safe_details)
      VALUES(:actor,'staff',:action,'print_job','bounded print metadata read','{}'::jsonb)"""),
        {"actor": context.principal.user_id, "action": action},
    )


def timed(context, sql, params):
    context.session.execute(text("SET LOCAL statement_timeout='3s'"))
    return context.session.execute(text(sql), params).mappings()


@router.get("/admin/print-jobs/counts", operation_id="API-350", response_model=Counts)
def counts(context: Authenticated, request: Request):
    filters = selected(context, request, False)
    as_of = datetime.now(UTC)
    measures = [
        "(SELECT count(*) FROM (SELECT 1 FROM selected LIMIT 1000) bounded) AS matching_jobs",
        "(SELECT count(*) FROM (SELECT DISTINCT order_id FROM selected LIMIT 1000) bounded) AS affected_orders",
    ]
    measures += [
        f"(SELECT count(*) FROM (SELECT 1 FROM selected WHERE job_status=:{state} LIMIT 1000) bounded) AS {state}"
        for state in STATES
    ]
    try:
        row = timed(
            context,
            "WITH selected AS (SELECT j.order_id,j.status AS job_status "
            + WHERE
            + ") SELECT "
            + ",".join(measures),
            {**filters.model_dump(), "as_of": as_of, **{s: s for s in STATES}},
        ).one()

        def cap(value):
            if type(value) is not int or not 0 <= value <= 1000:
                raise ValueError("Invalid bounded count")
            return Count(value=value, is_exact=value < 1000)

        result = Counts(
            as_of=as_of,
            matching_jobs=cap(row["matching_jobs"]),
            affected_orders=cap(row["affected_orders"]),
            by_job_status={s: cap(row[s]) for s in STATES},
        )
        finish(context, "print.metadata.counts")
        return result
    except (SQLAlchemyError, ValueError, ProfileCryptoUnavailable):
        raise AccessError(503) from None


@router.get("/admin/print-jobs", operation_id="API-349", response_model=Page)
def jobs(context: Authenticated, request: Request):
    filters = selected(context, request, True)
    values = request.query_params
    raw_limit, sort = values.get("limit", "20"), values.get("sort", "oldest")
    if (
        not re.fullmatch(r"[1-9][0-9]{0,2}", raw_limit)
        or not 1 <= int(raw_limit) <= 100
        or sort not in ("oldest", "newest")
    ):
        fail(422, "INVALID_QUERY")
    limit = int(raw_limit)
    settings, actor = request.app.state.settings, context.principal.user_id
    try:
        key(settings, settings.profile_data_key_version)
    except ProfileCryptoUnavailable:
        raise AccessError(503) from None
    pos = (
        decode(settings, actor, values["cursor"], filters, sort)
        if "cursor" in values
        else None
    )
    as_of = pos.as_of.astimezone(UTC) if pos else datetime.now(UTC)
    direction, comparison = ("ASC", ">") if sort == "oldest" else ("DESC", "<")
    try:
        rows = timed(
            context,
            "SELECT "
            + FIELDS
            + " "
            + WHERE
            + f" AND (CAST(:at AS timestamptz) IS NULL OR (j.created_at,j.id){comparison}(:at,:after_id)) ORDER BY j.created_at {direction},j.id {direction} LIMIT :take",
            {
                **filters.model_dump(),
                "as_of": as_of,
                "at": pos.at if pos else None,
                "after_id": pos.job_id if pos else UUID(int=0),
                "take": limit + 1,
            },
        ).all()
        items = [Item.model_validate(r) for r in rows[:limit]]
        cursor = (
            encode(
                settings,
                actor,
                Position(
                    filters=filters.model_dump_json(),
                    sort=sort,
                    as_of=as_of,
                    at=items[-1].created_at,
                    job_id=items[-1].job_id,
                ),
            )
            if len(rows) > limit
            else None
        )
        result = Page(as_of=as_of, items=items, next_cursor=cursor)
        finish(context, "print.metadata.list")
        return result
    except (SQLAlchemyError, ValueError, ProfileCryptoUnavailable):
        raise AccessError(503) from None


def install(application):
    # Register before235's dynamic /{job_id}, particularly the literal counts path.
    application.include_router(router, prefix="/api/v1")

    @application.middleware("http")
    async def privacy(request, call_next):
        response = await call_next(request)
        if request.url.path in (
            "/api/v1/admin/print-jobs",
            "/api/v1/admin/print-jobs/counts",
        ):
            response.headers.update(
                {
                    "Cache-Control": "private, no-store",
                    "X-Content-Type-Options": "nosniff",
                    "Referrer-Policy": "no-referrer",
                }
            )
        return response
