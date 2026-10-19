"""Read-only role-scoped order and shipment discovery (Task 5.5A)."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.api.auth import AccessError, Authenticated, require_staff
from app.api.v1.catalog import CatalogRoute, fail
from app.api.v1.owner_qr import decode_cursor, encode_cursor

router = APIRouter(tags=["fulfillment queries"], route_class=CatalogRoute)
Sort = Literal["newest", "oldest"]
ShipmentStatus = Literal[
    "preparing", "packed", "dispatched", "delivered", "exception", "returned"
]
OrderStatus = Literal["draft", "placed", "processing", "fulfilled", "cancelled"]
PaymentStatus = Literal[
    "awaiting_transfer",
    "proof_submitted",
    "under_review",
    "verified",
    "rejected",
    "refunded",
]
FulfillmentStatus = Literal[
    "unallocated", "allocated", "packed", "dispatched", "delivered", "exception"
]


class ShipmentMetadata(BaseModel):
    shipment_id: UUID
    order_id: UUID
    order_number: str
    status: ShipmentStatus
    carrier: str | None
    tracking_reference: str | None
    created_at: datetime
    packed_at: datetime | None
    dispatched_at: datetime | None
    delivered_at: datetime | None


class ShipmentSummary(ShipmentMetadata):
    pair_count: int
    fulfillment_eligible: bool
    requires_review: bool


class ShipmentPage(BaseModel):
    items: list[ShipmentSummary]
    next_cursor: str | None


class PackedPair(BaseModel):
    pair_id: UUID
    packed_qa_confirmed: bool
    packed_at: datetime | None


class PackedPairPage(BaseModel):
    items: list[PackedPair]
    next_cursor: str | None


class ShipmentDetail(ShipmentSummary):
    pairs: PackedPairPage


class OrderMetadata(BaseModel):
    order_id: UUID
    order_number: str
    order_status: OrderStatus
    payment_status: PaymentStatus
    fulfillment_status: FulfillmentStatus
    currency_code: str
    total_pkr: Decimal
    created_at: datetime
    placed_at: datetime | None


class FinanceOrder(OrderMetadata):
    projection: Literal["finance"] = "finance"


class OperationsOrder(OrderMetadata):
    projection: Literal["operations"] = "operations"
    shipment_count: int
    latest_shipment: ShipmentMetadata | None
    fulfillment_eligible: bool


class OrderPage(BaseModel):
    items: list[
        Annotated[FinanceOrder | OperationsOrder, Field(discriminator="projection")]
    ]
    next_cursor: str | None


def bounds(limit):
    if not 1 <= limit <= 100:
        fail(422, "INVALID_LIMIT")


def location(value):
    parsed = decode_cursor(value)
    if parsed is False:
        fail(422, "INVALID_CURSOR")
    return (None, None) if parsed is None else (parsed[1], parsed[0])


def date_range(start, end):
    if any(
        stamp is not None and stamp.utcoffset() is None for stamp in (start, end)
    ) or (start and end and start >= end):
        fail(422, "INVALID_DATE_RANGE")
    return (
        start.astimezone(UTC) if start else None,
        end.astimezone(UTC) if end else None,
    )


def exact(value, maximum):
    if value is not None and (
        not 1 <= len(value) <= maximum
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        fail(422, "INVALID_FILTER")


def page(data, limit, model, identity):
    items = [model.model_validate(row) for row in data[:limit]]
    last = items[-1] if items else None
    return {
        "items": items,
        "next_cursor": encode_cursor(getattr(last, identity), last.created_at)
        if len(data) > limit and last
        else None,
    }


SHIP_FIELDS = """s.id AS shipment_id,s.order_id,o.order_number,s.status,s.carrier,s.tracking_reference,
 s.created_at,s.packed_at,s.dispatched_at,s.delivered_at"""
SHIP_JSON = """'shipment_id',s.id,'order_id',s.order_id,'order_number',o.order_number,'status',s.status,'carrier',s.carrier,
 'tracking_reference',s.tracking_reference,'created_at',s.created_at,'packed_at',s.packed_at,'dispatched_at',s.dispatched_at,'delivered_at',s.delivered_at"""
ORDER_FIELDS = """o.id AS order_id,o.order_number,o.order_status,o.payment_status,o.fulfillment_status,o.currency_code,o.total_pkr,o.created_at,o.placed_at"""
SHIP_COUNTS = """(SELECT count(*) FROM public.shipment_pairs sp WHERE sp.shipment_id=s.id) AS pair_count,
 public.sr_fulfillment_eligible(o.id) AS fulfillment_eligible,
 (s.status IN ('preparing','packed','dispatched') AND NOT public.sr_fulfillment_eligible(o.id)) AS requires_review"""


@router.get("/admin/orders", operation_id="API-080", response_model=OrderPage)
def orders(
    context: Authenticated,
    limit: int = 20,
    cursor: str | None = None,
    sort: Sort = "newest",
    order_number: str | None = None,
    order_status: OrderStatus | None = None,
    payment_status: PaymentStatus | None = None,
    fulfillment_status: FulfillmentStatus | None = None,
    created_from: datetime | None = None,
    created_before: datetime | None = None,
):
    operations = (
        context.session.execute(
            text(
                "SELECT 1 FROM public.staff_roles WHERE user_id=:uid AND role='operations' AND revoked_at IS NULL"
            ),
            {"uid": context.principal.user_id},
        ).scalar_one_or_none()
        is not None
    )
    role = "operations" if operations else "finance"
    require_staff(context, role)
    bounds(limit)
    exact(order_number, 40)
    start, end = date_range(created_from, created_before)
    stamp, ident = location(cursor)
    direction, comparison = ("DESC", "<") if sort == "newest" else ("ASC", ">")
    extra = (
        """,(SELECT count(*) FROM public.shipments s WHERE s.order_id=o.id) AS shipment_count,
      (SELECT jsonb_build_object("""
        + SHIP_JSON
        + """) FROM public.shipments s WHERE s.order_id=o.id ORDER BY s.created_at DESC,s.id DESC LIMIT 1) AS latest_shipment,
      public.sr_fulfillment_eligible(o.id) AS fulfillment_eligible"""
        if operations
        else ""
    )
    # Role is a fixed server-chosen value. Recheck inside the representation SQL
    # so revocation cannot leave a cached operations projection available.
    data = (
        context.session.execute(
            text(f"""WITH selected AS (
      SELECT o.* FROM public.orders o WHERE public.sr_is_staff(ARRAY[:role])
      AND (CAST(:number AS text) IS NULL OR o.order_number=:number)
      AND (CAST(:status AS text) IS NULL OR o.order_status=:status)
      AND (CAST(:payment AS text) IS NULL OR o.payment_status=:payment)
      AND (CAST(:fulfillment AS text) IS NULL OR o.fulfillment_status=:fulfillment)
      AND (CAST(:start AS timestamptz) IS NULL OR o.created_at>=:start)
      AND (CAST(:end AS timestamptz) IS NULL OR o.created_at<:end)
      AND (CAST(:stamp AS timestamptz) IS NULL OR (o.created_at,o.id){comparison}(:stamp,:ident))
      ORDER BY o.created_at {direction},o.id {direction} LIMIT :lim)
      SELECT {ORDER_FIELDS}{extra} FROM selected o ORDER BY o.created_at {direction},o.id {direction}"""),
            {
                "role": role,
                "number": order_number,
                "status": order_status,
                "payment": payment_status,
                "fulfillment": fulfillment_status,
                "start": start,
                "end": end,
                "stamp": stamp,
                "ident": ident,
                "lim": limit + 1,
            },
        )
        .mappings()
        .all()
    )
    return page(
        data, limit, OperationsOrder if operations else FinanceOrder, "order_id"
    )


@router.get("/admin/shipments", operation_id="API-246", response_model=ShipmentPage)
def shipments(
    context: Authenticated,
    limit: int = 20,
    cursor: str | None = None,
    sort: Sort = "newest",
    order_id: UUID | None = None,
    order_number: str | None = None,
    status: ShipmentStatus | None = None,
    carrier: str | None = None,
    tracking_reference: str | None = None,
    requires_review: bool | None = None,
    created_from: datetime | None = None,
    created_before: datetime | None = None,
):
    require_staff(context, "operations")
    bounds(limit)
    exact(order_number, 40)
    exact(carrier, 80)
    exact(tracking_reference, 150)
    start, end = date_range(created_from, created_before)
    stamp, ident = location(cursor)
    direction, comparison = ("DESC", "<") if sort == "newest" else ("ASC", ">")
    data = (
        context.session.execute(
            text(f"""WITH selected AS (
      SELECT s.* FROM public.shipments s JOIN public.orders o ON o.id=s.order_id
      WHERE public.sr_is_staff(ARRAY['operations'])
      AND (CAST(:oid AS uuid) IS NULL OR s.order_id=:oid)
      AND (CAST(:number AS text) IS NULL OR o.order_number=:number)
      AND (CAST(:status AS text) IS NULL OR s.status=:status)
      AND (CAST(:carrier AS text) IS NULL OR s.carrier=:carrier)
      AND (CAST(:tracking AS text) IS NULL OR s.tracking_reference=:tracking)
      AND (CAST(:review AS boolean) IS NULL OR (s.status IN ('preparing','packed','dispatched') AND NOT public.sr_fulfillment_eligible(o.id))=:review)
      AND (CAST(:start AS timestamptz) IS NULL OR s.created_at>=:start)
      AND (CAST(:end AS timestamptz) IS NULL OR s.created_at<:end)
      AND (CAST(:stamp AS timestamptz) IS NULL OR (s.created_at,s.id){comparison}(:stamp,:ident))
      ORDER BY s.created_at {direction},s.id {direction} LIMIT :lim)
      SELECT {SHIP_FIELDS},{SHIP_COUNTS} FROM selected s JOIN public.orders o ON o.id=s.order_id
      ORDER BY s.created_at {direction},s.id {direction}"""),
            {
                "oid": order_id,
                "number": order_number,
                "status": status,
                "carrier": carrier,
                "tracking": tracking_reference,
                "review": requires_review,
                "start": start,
                "end": end,
                "stamp": stamp,
                "ident": ident,
                "lim": limit + 1,
            },
        )
        .mappings()
        .all()
    )
    return page(data, limit, ShipmentSummary, "shipment_id")


@router.get(
    "/admin/shipments/{shipment_id}",
    operation_id="API-247",
    response_model=ShipmentDetail,
)
def shipment(
    shipment_id: UUID,
    context: Authenticated,
    pair_limit: int = 20,
    pair_cursor: UUID | None = None,
):
    require_staff(context, "operations")
    bounds(pair_limit)
    row = (
        context.session.execute(
            text(f"""SELECT {SHIP_FIELDS},{SHIP_COUNTS},
      COALESCE((SELECT jsonb_agg(jsonb_build_object('pair_id',sp.pair_id,'packed_qa_confirmed',sp.packed_qa_confirmed,'packed_at',sp.packed_at) ORDER BY sp.pair_id)
        FROM (SELECT pair_id,packed_qa_confirmed,packed_at FROM public.shipment_pairs WHERE shipment_id=s.id
          AND (CAST(:after AS uuid) IS NULL OR pair_id>:after) ORDER BY pair_id LIMIT :lim) sp),'[]'::jsonb) AS packed_pairs
      FROM public.shipments s JOIN public.orders o ON o.id=s.order_id
      WHERE s.id=:id AND public.sr_is_staff(ARRAY['operations'])"""),
            {"id": shipment_id, "after": pair_cursor, "lim": pair_limit + 1},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise AccessError(404)
    result = dict(row)
    pairs = [PackedPair.model_validate(p) for p in result.pop("packed_pairs")]
    more = len(pairs) > pair_limit
    result["pairs"] = {
        "items": pairs[:pair_limit],
        "next_cursor": str(pairs[pair_limit - 1].pair_id) if more else None,
    }
    return result
