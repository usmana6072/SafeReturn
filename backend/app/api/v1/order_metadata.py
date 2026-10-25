"""Independent staff order metadata. Orders-only SQL; no fulfillment service."""

import base64
import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal, DecimalException
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import text

from app.api.auth import AccessError, Authenticated, authorize, require_staff
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt, encrypt, key

PATH = "/api/v1/admin/order-metadata"
NAMESPACE = "admin-order-metadata:v1:roles-operations-finance"
ORDERS = ("draft", "placed", "processing", "fulfilled", "cancelled")
PAYMENTS = (
    "awaiting_transfer",
    "proof_submitted",
    "under_review",
    "verified",
    "rejected",
    "refunded",
)
HEADERS = {
    "Cache-Control": "private, no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}


def invalid(code="VALIDATION_ERROR"):
    raise HTTPException(422, detail={"code": code})


def stamp(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})", value
    ):
        raise ValueError()
    result = datetime.fromisoformat(value)
    if result.utcoffset() is None:
        raise ValueError()
    return result.astimezone(UTC)


def utc(value):
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError()
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)


class Item(Closed):
    order_id: str = Field(pattern=r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
    order_number: str = Field(min_length=1, max_length=40)
    order_status: Literal["draft", "placed", "processing", "fulfilled", "cancelled"]
    payment_status: Literal[
        "awaiting_transfer",
        "proof_submitted",
        "under_review",
        "verified",
        "rejected",
        "refunded",
    ]
    currency_code: str = Field(pattern=r"^[A-Z]{3}$")
    total_amount: str = Field(pattern=r"^(0|[1-9][0-9]{0,9})\.[0-9]{2}$")
    created_at: str
    placed_at: str | None


class Page(Closed):
    items: list[Item] = Field(max_length=100)
    next_cursor: str | None = Field(max_length=2048)
    as_of: str


class MetadataRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handle(request):
            try:
                return await original(request)
            except HTTPException as exc:
                return JSONResponse(
                    {
                        "error": {
                            "code": exc.detail["code"],
                            "message": "Invalid metadata request.",
                            "message_ur": "درخواست درست نہیں۔",
                            "request_id": getattr(request.state, "request_id", None),
                            "details": {},
                        }
                    },
                    status_code=exc.status_code,
                    headers=HEADERS,
                )

        return handle


router = APIRouter(route_class=MetadataRoute)


QUERY_SCHEMAS = {
    "order_number": {"type": "string", "minLength": 1, "maxLength": 40},
    "order_status": {"type": "string", "enum": list(ORDERS)},
    "payment_status": {"type": "string", "enum": list(PAYMENTS)},
    "created_from": {"type": "string", "format": "date-time"},
    "created_before": {"type": "string", "format": "date-time"},
    "sort": {"type": "string", "enum": ["newest", "oldest"], "default": "newest"},
    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
    "cursor": {"type": "string", "maxLength": 2048},
}


@router.get(
    "/admin/order-metadata",
    operation_id="admin_order_metadata_list",
    response_model=Page,
    openapi_extra={
        "parameters": [
            {"name": name, "in": "query", "required": False, "schema": schema}
            for name, schema in QUERY_SCHEMAS.items()
        ]
    },
)
async def order_metadata(request: Request, context: Authenticated):
    require_staff(context, "operations", "finance")
    q = request.query_params
    fields = {
        "order_number",
        "order_status",
        "payment_status",
        "created_from",
        "created_before",
        "sort",
        "limit",
        "cursor",
    }
    if len(str(request.url).encode()) > 8192 or any(
        k not in fields or len(q.getlist(k)) != 1 for k in q
    ):
        invalid()
    async for chunk in request.stream():
        if chunk:
            invalid()
    if request.headers.get("content-encoding"):
        invalid()
    try:
        number = q.get("order_number")
        if number is not None and (
            not 1 <= len(number) <= 40
            or any(ord(c) < 32 or ord(c) == 127 for c in number)
        ):
            raise ValueError()
        status, payment = q.get("order_status"), q.get("payment_status")
        if (
            status is not None
            and status not in ORDERS
            or payment is not None
            and payment not in PAYMENTS
        ):
            raise ValueError()
        direction = q.get("sort", "newest")
        if direction not in ("newest", "oldest"):
            raise ValueError()
        rawlimit = q.get("limit", "20")
        if (
            not re.fullmatch(r"[1-9][0-9]{0,2}", rawlimit)
            or not 1 <= int(rawlimit) <= 100
        ):
            raise ValueError()
        limit = int(rawlimit)
        start = stamp(q["created_from"]) if "created_from" in q else None
        end = stamp(q["created_before"]) if "created_before" in q else None
        if start and end and start >= end:
            raise ValueError()
    except ValueError:
        invalid("INVALID_FILTER")
    settings = request.app.state.settings
    actor = context.principal.user_id
    try:
        key(settings, settings.profile_data_key_version)
    except ProfileCryptoUnavailable:
        raise AccessError(503) from None
    filters = {
        "order_number": number,
        "order_status": status,
        "payment_status": payment,
        "created_from": utc(start) if start else None,
        "created_before": utc(end) if end else None,
        "sort": direction,
        "limit": limit,
    }
    digest = hashlib.sha256(
        json.dumps(filters, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    now = datetime.now(UTC)
    as_of = now
    expiry = now + timedelta(minutes=15)
    after = None
    ident = None
    token = q.get("cursor")
    if token is not None:
        try:
            if not 1 <= len(token) <= 2048 or not re.fullmatch(
                r"[A-Za-z0-9_-]+={0,2}", token
            ):
                raise ValueError()
            raw = base64.b64decode(token, altchars=b"-_", validate=True)
            v = json.loads(
                decrypt(
                    settings, actor, NAMESPACE, raw[2:], int.from_bytes(raw[:2], "big")
                )
            )
            if (
                set(v) != {"v", "filters", "as_of", "expires", "after", "id"}
                or v["v"] != 1
                or v["filters"] != digest
            ):
                raise ValueError()
            as_of, expiry, after = (
                stamp(v["as_of"]),
                stamp(v["expires"]),
                stamp(v["after"]),
            )
            ident = UUID(v["id"])
            if (
                expiry <= now
                or as_of > now
                or after > as_of
                or expiry - as_of != timedelta(minutes=15)
            ):
                raise ValueError()
        except (
            ValueError,
            TypeError,
            KeyError,
            OverflowError,
            ProfileCryptoUnavailable,
        ):
            invalid("INVALID_CURSOR")
    order, comparison = ("DESC", "<") if direction == "newest" else ("ASC", ">")
    # Only fixed SQL fragments selected above are interpolated. All values are bound.
    rows = (
        context.session.execute(
            text(f"""SELECT o.id AS order_id,o.order_number,o.order_status,o.payment_status,
      o.currency_code,o.total_pkr AS total_amount,o.created_at,o.placed_at
      FROM public.orders o WHERE public.sr_is_staff(ARRAY['operations','finance'])
      AND o.created_at<=:as_of
      AND (CAST(:number AS text) IS NULL OR o.order_number=:number)
      AND (CAST(:status AS text) IS NULL OR o.order_status=:status)
      AND (CAST(:payment AS text) IS NULL OR o.payment_status=:payment)
      AND (CAST(:start AS timestamptz) IS NULL OR o.created_at>=:start)
      AND (CAST(:end AS timestamptz) IS NULL OR o.created_at<:end)
      AND (CAST(:after AS timestamptz) IS NULL OR (o.created_at,o.id){comparison}(:after,:ident))
      ORDER BY o.created_at {order},o.id {order} LIMIT :lim"""),
            {
                "as_of": as_of,
                "number": number,
                "status": status,
                "payment": payment,
                "start": start,
                "end": end,
                "after": after,
                "ident": ident,
                "lim": limit + 1,
            },
        )
        .mappings()
        .all()
    )
    items = []
    try:
        for row in rows[:limit]:
            amount = row["total_amount"]
            if (
                not isinstance(amount, Decimal)
                or not amount.is_finite()
                or amount < 0
                or amount > Decimal("9999999999.99")
                or amount != amount.quantize(Decimal(".01"))
            ):
                raise ValueError()
            item = Item.model_validate(
                {
                    **row,
                    "order_id": str(UUID(str(row["order_id"]))),
                    "total_amount": format(amount, ".2f"),
                    "created_at": utc(row["created_at"]),
                    "placed_at": utc(row["placed_at"])
                    if row["placed_at"] is not None
                    else None,
                }
            )
            if any(ord(c) < 32 or ord(c) == 127 for c in item.order_number):
                raise ValueError()
            items.append(item)
        if len({i.order_id for i in items}) != len(items):
            raise ValueError()
    except (ValueError, TypeError, KeyError, ValidationError, DecimalException):
        raise AccessError(503) from None
    next_cursor = None
    if len(rows) > limit and items:
        last = items[-1]
        cipher, version = encrypt(
            settings,
            actor,
            NAMESPACE,
            json.dumps(
                {
                    "v": 1,
                    "filters": digest,
                    "as_of": utc(as_of),
                    "expires": utc(expiry),
                    "after": last.created_at,
                    "id": last.order_id,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
        )
        next_cursor = base64.urlsafe_b64encode(
            version.to_bytes(2, "big") + cipher
        ).decode()
        if len(next_cursor) > 2048:
            raise AccessError(503)
    require_staff(
        authorize(context.session, context.principal), "operations", "finance"
    )
    return Page(items=items, next_cursor=next_cursor, as_of=utc(as_of))


def install(application):
    application.include_router(router, prefix="/api/v1")

    @application.middleware("http")
    async def metadata_headers(request, call_next):
        response = await call_next(request)
        if request.url.path.rstrip("/") == PATH:
            for k, v in HEADERS.items():
                response.headers[k] = v
        return response
