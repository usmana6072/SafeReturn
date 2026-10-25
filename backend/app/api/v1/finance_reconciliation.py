"""Read-only stored-state signals. Neither bank reconciliation nor a payment writer."""

import base64
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request
from pydantic import Field, ValidationError
from sqlalchemy import text

from app.api.auth import AccessError, Authenticated, require_staff
from app.api.v1.catalog import Closed, fail
from app.api.v1.financial_disputes import exact_money
from app.api.v1.shipping_addresses import PrivateRoute
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt, encrypt, key

router = APIRouter(tags=["finance reconciliation"], route_class=PrivateRoute)
Reason = Literal[
    "REVIEW_PENDING",
    "ATTEMPT_ORDER_AMOUNT_MISMATCH",
    "ATTEMPT_ORDER_CURRENCY_MISMATCH",
    "VERIFIED_HISTORY_MISMATCH",
    "ORDER_SETTLEMENT_MISMATCH",
    "VERIFIED_ALLOCATION_MISMATCH",
    "DUPLICATE_VERIFIED_REFERENCE",
]
REASONS = list(Reason.__args__)
UNAVAILABLE = ["BANK_LEDGER_AMOUNT_COMPARISON", "REJECTED_REFERENCE_MATCHES"]
ZERO = UUID(int=0)


class Item(Closed):
    order_id: UUID
    attempt_id: UUID | None
    reason_code: Reason
    observed_since: datetime
    attempt_amount: str | None = Field(pattern=r"^[0-9]{1,10}\.[0-9]{2}$")
    order_amount: str = Field(pattern=r"^[0-9]{1,10}\.[0-9]{2}$")
    currency: str | None = Field(pattern=r"^[A-Z]{3}$")
    order_currency: str = Field(pattern=r"^[A-Z]{3}$")
    next_action: Literal["review_payment", "investigate_order"]


class Page(Closed):
    as_of: datetime
    items: list[Item]
    next_cursor: str | None
    unavailable_checks: list[str]


class Count(Closed):
    value: int = Field(ge=0, le=1000)
    is_exact: bool


class Counts(Closed):
    as_of: datetime
    by_reason: dict[Reason, Count]
    affected_orders: Count
    unavailable_checks: list[str]


class Position(Closed):
    as_of: datetime
    reason: Reason | None
    observed_since: datetime
    order_id: UUID
    attempt_id: UUID
    reason_code: Reason


def guard(context, request, allowed):
    require_staff(context, "finance")
    if not request.app.state.settings.finance_reconciliation_enabled:
        raise AccessError(503)
    if any(k not in allowed for k in request.query_params) or any(
        len(request.query_params.getlist(k)) != 1 for k in request.query_params
    ):
        fail(422, "INVALID_QUERY")
    # Bound wall-clock query execution as well as returned rows. Plans remain a DB gate.
    context.session.execute(text("SET LOCAL statement_timeout='3s'"))


def encode(settings, actor, position):
    try:
        cipher, version = encrypt(
            settings, actor, "finance_reconciliation_cursor", position.model_dump_json()
        )
        return str(version) + "." + base64.urlsafe_b64encode(cipher).decode()
    except ProfileCryptoUnavailable:
        raise AccessError(503) from None


def decode(settings, actor, token, reason):
    try:
        version, data = token.split(".", 1)
        payload = decrypt(
            settings,
            actor,
            "finance_reconciliation_cursor",
            base64.b64decode(data, altchars=b"-_", validate=True),
            int(version),
        )
        pos = Position.model_validate_json(payload)
        if (
            pos.reason != reason
            or pos.as_of.utcoffset() is None
            or pos.observed_since.utcoffset() is None
            or pos.observed_since > pos.as_of
            or pos.as_of > datetime.now(UTC)
        ):
            raise ValueError()
        return pos
    except (ValueError, TypeError, ValidationError, ProfileCryptoUnavailable):
        fail(422, "INVALID_CURSOR")


def projection(row):
    # Explicit allowlist even if a repository accidentally returns additional fields.
    try:
        return Item(
            order_id=row["order_id"],
            attempt_id=row["attempt_id"],
            reason_code=row["reason_code"],
            observed_since=row["observed_since"],
            attempt_amount=exact_money(row["attempt_amount"])
            if row["attempt_amount"] is not None
            else None,
            order_amount=exact_money(row["order_amount"]),
            currency=row["currency"],
            order_currency=row["order_currency"],
            next_action="review_payment"
            if row["reason_code"] == "REVIEW_PENDING"
            else "investigate_order",
        )
    except (KeyError, TypeError, ValueError, ValidationError):
        raise AccessError(503) from None


def audit(context, action):
    context.session.execute(
        text("""INSERT INTO public.audit_events
        (actor_user_id,actor_kind,action,target_type,reason,safe_details)
        VALUES(:actor,'staff',:action,'finance_reconciliation',
               'bounded stored-state finance read','{}'::jsonb)"""),
        {"actor": context.principal.user_id, "action": action},
    )


@router.get(
    "/admin/finance/reconciliation", operation_id="API-342", response_model=Page
)
def reconciliation(
    context: Authenticated,
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    reason: Reason | None = None,
    cursor: str | None = Query(default=None, max_length=4096),
):
    guard(context, request, {"limit", "reason", "cursor"})
    settings, actor = request.app.state.settings, context.principal.user_id
    try:
        key(settings, settings.profile_data_key_version)
    except ProfileCryptoUnavailable:
        raise AccessError(503) from None
    pos = decode(settings, actor, cursor, reason) if cursor else None
    as_of = pos.as_of if pos else datetime.now(UTC)
    rows = (
        context.session.execute(
            text("""SELECT * FROM public.sr_finance_reconciliation(
        :as_of,:reason,:stamp,:oid,:aid,:code,:take)"""),
            {
                "as_of": as_of,
                "reason": reason,
                "stamp": pos.observed_since if pos else None,
                "oid": pos.order_id if pos else ZERO,
                "aid": pos.attempt_id if pos else ZERO,
                "code": pos.reason_code if pos else "",
                "take": limit + 1,
            },
        )
        .mappings()
        .all()
    )
    items = [projection(row) for row in rows[:limit]]
    token = None
    if len(rows) > limit and items:
        last = items[-1]
        token = encode(
            settings,
            actor,
            Position(
                as_of=as_of,
                reason=reason,
                observed_since=last.observed_since,
                order_id=last.order_id,
                attempt_id=last.attempt_id or ZERO,
                reason_code=last.reason_code,
            ),
        )
    audit(context, "finance.reconciliation.read")
    return Page(
        as_of=as_of, items=items, next_cursor=token, unavailable_checks=UNAVAILABLE
    )


def capped(value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise AccessError(503)
    return Count(value=min(1000, value), is_exact=value < 1000)


@router.get(
    "/admin/finance/reconciliation/counts",
    operation_id="API-343",
    response_model=Counts,
)
def counts(context: Authenticated, request: Request):
    guard(context, request, set())
    as_of = datetime.now(UTC)
    # One statement/snapshot; distinct affected orders has a separate cap because
    # many attempts from one order must not hide other affected orders.
    rows = (
        context.session.execute(
            text("""SELECT reason_code,n
        FROM public.sr_finance_reconciliation_counts(:as_of)"""),
            {"as_of": as_of},
        )
        .mappings()
        .all()
    )
    values = {row["reason_code"]: row["n"] for row in rows}
    if len(rows) != len(REASONS) + 1 or set(values) != set(REASONS) | {
        "AFFECTED_ORDERS"
    }:
        raise AccessError(503)
    result = Counts(
        as_of=as_of,
        by_reason={r: capped(values[r]) for r in REASONS},
        affected_orders=capped(values["AFFECTED_ORDERS"]),
        unavailable_checks=UNAVAILABLE,
    )
    audit(context, "finance.reconciliation.counts")
    return result


def install(application):
    application.include_router(router, prefix="/api/v1")

    @application.middleware("http")
    async def private_headers(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/v1/admin/finance/reconciliation"):
            response.headers["Cache-Control"] = "private, no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response
