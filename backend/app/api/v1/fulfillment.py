"""Owner order history and audited, serialized operations fulfillment."""

import base64
import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from fastapi.encoders import jsonable_encoder
from pydantic import Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api.auth import AccessError, Authenticated, require_order_owner, require_staff
from app.api.v1.catalog import CatalogRoute, fail
from app.api.v1.checkout import Closed
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt, encrypt

router = APIRouter(tags=["orders and fulfillment"], route_class=CatalogRoute)


def rows(session, sql, **params):
    return [
        {k: str(v) if isinstance(v, Decimal) else v for k, v in r.items()}
        for r in session.execute(text(sql), params).mappings()
    ]


def page_cursor(value):
    if value is None:
        return None, None
    try:
        if len(value) > 200:
            raise ValueError()
        stamp, ident = json.loads(
            base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        )
        stamp = datetime.fromisoformat(stamp)
        if stamp.tzinfo is None:
            raise ValueError()
        return stamp, UUID(ident)
    except (ValueError, TypeError, KeyError):
        fail(422, "INVALID_CURSOR")


def paged(items, limit):
    more = len(items) > limit
    items = items[:limit]
    cursor = None
    if more:
        last = items[-1]
        cursor = (
            base64.urlsafe_b64encode(
                json.dumps([last["created_at"].isoformat(), str(last["id"])]).encode()
            )
            .decode()
            .rstrip("=")
        )
    return {"items": items, "next_cursor": cursor}


def bounds(limit):
    if not 1 <= limit <= 100:
        fail(422, "INVALID_LIMIT")


@router.get("/me/orders", operation_id="API-061")
def list_orders(context: Authenticated, limit: int = 20, cursor: str | None = None):
    bounds(limit)
    stamp, ident = page_cursor(cursor)
    return paged(
        rows(
            context.session,
            """SELECT id,order_number,order_status,payment_status,fulfillment_status,
      currency_code,subtotal_pkr,total_pkr,created_at,placed_at FROM public.orders
      WHERE customer_user_id=:uid AND (CAST(:stamp AS timestamptz) IS NULL OR (created_at,id)<(:stamp,:ident))
      ORDER BY created_at DESC,id DESC LIMIT :limit""",
            uid=context.principal.user_id,
            stamp=stamp,
            ident=ident,
            limit=limit + 1,
        ),
        limit,
    )


def detail(session, oid):
    items = rows(
        session,
        """SELECT id,product_id,variant_id,product_name_snapshot,variant_name_snapshot,
      sku_snapshot,size_mm_snapshot,material_snapshot,quantity,unit_price_snapshot,line_total
      FROM public.order_items WHERE order_id=:id ORDER BY created_at,id""",
        id=oid,
    )
    uses = rows(
        session,
        """SELECT u.id,u.order_item_id,u.pair_unit_id,u.qr_code_id,u.use_kind,u.tag_type_snapshot,u.copies
      FROM public.order_item_qr_uses u JOIN public.order_items i ON i.id=u.order_item_id
      WHERE i.order_id=:id ORDER BY CASE u.tag_type_snapshot WHEN 'lost' THEN 0 ELSE 1 END,u.id""",
        id=oid,
    )
    units = rows(
        session,
        "SELECT id,pair_id,status,reserved_until,allocated_at FROM public.order_pair_units WHERE order_id=:id ORDER BY created_at,id",
        id=oid,
    )
    job = rows(
        session,
        "SELECT id,status,job_revision FROM public.print_jobs WHERE order_id=:id ORDER BY job_revision DESC LIMIT 1",
        id=oid,
    )
    return {
        "items": items,
        "qr_uses": uses,
        "pair_units": units,
        "pair_count": len(units),
        "print_status": job[0]["status"] if job else "not_requested",
    }


def shipping(session, settings, oid):
    found = rows(
        session,
        "SELECT * FROM public.order_shipping_snapshots WHERE order_id=:id",
        id=oid,
    )
    if not found:
        fail(409, "SHIPPING_SNAPSHOT_MISSING")
    r = found[0]
    try:
        return {
            "shipping_address_id": r["source_address_id"],
            "city": r["city"],
            "province": r["province"],
            "postal_code": r["postal_code"],
            **{
                f: decrypt(
                    settings,
                    oid,
                    "shipping_" + f,
                    r[f + "_ciphertext"],
                    r["key_version"],
                )
                for f in ("recipient_name", "phone", "address")
            },
        }
    except ProfileCryptoUnavailable:
        raise AccessError(503) from None


@router.get("/me/orders/{order_id}", operation_id="API-062")
def get_order(order_id: UUID, context: Authenticated, request: Request):
    require_order_owner(context, order_id)
    order = rows(
        context.session,
        """SELECT id,order_number,order_status,payment_status,fulfillment_status,currency_code,
      subtotal_pkr,shipping_pkr,tax_pkr,discount_pkr,total_pkr,created_at,placed_at FROM public.orders WHERE id=:id""",
        id=order_id,
    )[0]
    return {
        **order,
        **detail(context.session, order_id),
        "shipping_snapshot": shipping(
            context.session, request.app.state.settings, order_id
        ),
    }


@router.get("/me/orders/{order_id}/shipments", operation_id="API-066")
def list_shipments(order_id: UUID, context: Authenticated):
    require_order_owner(context, order_id)
    return {
        "items": rows(
            context.session,
            "SELECT id,carrier,tracking_reference,status,packed_at,dispatched_at,delivered_at FROM public.shipments WHERE order_id=:id ORDER BY created_at DESC,id DESC",
            id=order_id,
        )
    }


# The newest revision and QA observation must match the retained current artifact.
ELIGIBLE = "public.sr_fulfillment_eligible(o.id)"


@router.get("/admin/orders/ready-to-ship", operation_id="API-232")
def ready_to_ship(
    context: Authenticated,
    limit: int = 20,
    cursor: str | None = None,
    status: Literal[
        "allocated", "packed", "dispatched", "delivered", "exception", "returned"
    ]
    | None = None,
):
    require_staff(context, "operations")
    bounds(limit)
    stamp, ident = page_cursor(cursor)
    outbound = status is None or status in {"allocated", "packed"}
    condition = (
        ELIGIBLE
        + """ AND o.fulfillment_status IN ('allocated','packed')
      AND NOT EXISTS(SELECT 1 FROM public.shipments sh WHERE sh.order_id=o.id AND sh.status IN ('dispatched','delivered','exception','returned'))"""
        if outbound
        else "EXISTS(SELECT 1 FROM public.shipments sh WHERE sh.order_id=o.id AND (sh.status=CAST(:status AS text) OR (CAST(:status AS text)='exception' AND sh.status IN('preparing','packed','dispatched') AND NOT public.sr_fulfillment_eligible(o.id))))"
    )
    data = rows(
        context.session,
        """SELECT o.id,o.order_number,o.fulfillment_status,o.created_at,o.placed_at,s.source_address_id AS shipping_address_id,s.city
      FROM public.orders o JOIN public.order_shipping_snapshots s ON s.order_id=o.id WHERE """
        + condition
        + """
      AND (NOT :outbound OR CAST(:status AS text) IS NULL OR o.fulfillment_status=CAST(:status AS text))
      AND (CAST(:stamp AS timestamptz) IS NULL OR (o.created_at,o.id)<(:stamp,:ident))
      ORDER BY o.created_at DESC,o.id DESC LIMIT :limit""",
        outbound=outbound,
        status=status,
        stamp=stamp,
        ident=ident,
        limit=limit + 1,
    )
    result = paged(data, limit)
    for item in result["items"]:
        item.update(detail(context.session, item["id"]))
        item["workflow_stage"] = (
            "ready_to_ship"
            if item["fulfillment_status"] == "packed" and outbound
            else "packing_pending"
            if outbound
            else "shipment_history"
        )
        item["shipments"] = rows(
            context.session,
            "SELECT id,status,carrier,tracking_reference FROM public.shipments WHERE order_id=:id ORDER BY created_at,id",
            id=item["id"],
        )
    return result


class ShipmentRequest(Closed):
    order_id: UUID
    shipping_address_id: UUID
    pair_ids: list[UUID] = Field(min_length=1, max_length=100)
    carrier: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=4, max_length=500)


class ShipmentUpdate(Closed):
    status: Literal["packed", "dispatched", "delivered", "exception", "returned"]
    expected_status: Literal[
        "preparing", "packed", "dispatched", "exception", "delivered"
    ]
    tracking_reference: str | None = Field(default=None, min_length=1, max_length=150)
    packing_confirmed: bool = Field(default=False, strict=True)
    reason: str = Field(min_length=4, max_length=500)


def command(context, request, operation, payload, work):
    # Recheck roles/MFA before even replaying an old receipt.
    require_staff(context, "operations")
    key = request.headers.get("Idempotency-Key", "")
    import re

    if not re.fullmatch(r"[A-Za-z0-9._:-]{8,160}", key):
        fail(400, "IDEMPOTENCY_KEY_REQUIRED")
    s = context.session
    actor = context.principal.user_id
    digest = hashlib.sha256(
        json.dumps(
            jsonable_encoder(payload), sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    ref = hashlib.sha256(f"{actor}:{operation}:{key}".encode()).hexdigest()
    s.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:ref,0))"), {"ref": ref}
    )
    old = rows(
        s,
        "SELECT * FROM public.idempotency_records WHERE actor_scope=:scope AND operation=:op AND idempotency_key=:key FOR UPDATE",
        scope=str(actor),
        op=operation,
        key=key,
    )
    settings = request.app.state.settings
    try:
        if old:
            if old[0]["request_hash"] != digest:
                fail(409, "IDEMPOTENCY_KEY_REUSED")
            return json.loads(
                decrypt(
                    settings,
                    actor,
                    "fulfillment:" + ref,
                    old[0]["response_body_ciphertext"],
                    old[0]["response_key_version"],
                )
            )
        with s.begin_nested():
            result, target = work(s, settings)
            result = jsonable_encoder(result, custom_encoder={Decimal: str})
            cipher, version = encrypt(
                settings, actor, "fulfillment:" + ref, json.dumps(result)
            )
            s.execute(
                text("""INSERT INTO public.idempotency_records(actor_scope,actor_user_id,operation,idempotency_key,request_hash,state,response_status,response_body_ciphertext,response_key_version,expires_at)
              VALUES(:scope,:actor,:op,:key,:hash,'completed',:status,:cipher,:version,now()+interval '1 day')"""),
                {
                    "scope": str(actor),
                    "actor": actor,
                    "op": operation,
                    "key": key,
                    "hash": digest,
                    "status": 201 if operation == "shipment.create" else 200,
                    "cipher": cipher,
                    "version": version,
                },
            )
            s.execute(
                text("""INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,request_id,reason,safe_details)
              VALUES(:actor,'staff',:op,'shipment',:target,:rid,:reason,jsonb_build_object('event_id',CAST(:ref AS text),'outcome','success','from_status',CAST(:before AS text),'to_status',CAST(:after AS text)))"""),
                {
                    "actor": actor,
                    "op": operation.partition(":")[0],
                    "target": target,
                    "rid": getattr(request.state, "request_id", None),
                    "reason": payload["reason"],
                    "before": payload.get("expected_status", "not_created"),
                    "after": result["status"],
                    "ref": ref,
                },
            )
            return result
    except ProfileCryptoUnavailable:
        raise AccessError(503) from None
    except IntegrityError:
        fail(409, "SHIPMENT_CONFLICT")


def lock_order(s, oid):
    # Same parent lock as finance, print enqueue/review, and all shipment commands.
    found = rows(
        s,
        "SELECT id,fulfillment_status FROM public.orders WHERE id=:id FOR UPDATE",
        id=oid,
    )
    if not found:
        raise AccessError(404)
    return found[0]


def eligible(s, oid):
    s.execute(
        text(
            "SELECT p.id FROM public.tag_pairs p JOIN public.order_pair_units u ON u.pair_id=p.id WHERE u.order_id=:id ORDER BY p.id FOR UPDATE OF p"
        ),
        {"id": oid},
    )
    if not rows(
        s, "SELECT o.id FROM public.orders o WHERE o.id=:id AND " + ELIGIBLE, id=oid
    ):
        fail(409, "ORDER_NOT_READY_TO_SHIP")


@router.post("/admin/shipments", operation_id="API-095", status_code=201)
def create_shipment(body: ShipmentRequest, context: Authenticated, request: Request):
    def work(s, settings):
        order = lock_order(s, body.order_id)
        if order["fulfillment_status"] != "allocated":
            fail(409, "SHIPMENT_CONFLICT")
        eligible(s, body.order_id)
        snap = shipping(s, settings, body.order_id)
        if str(snap["shipping_address_id"]) != str(body.shipping_address_id):
            fail(409, "SHIPPING_SNAPSHOT_MISMATCH")
        pairs = [
            r["pair_id"]
            for r in rows(
                s,
                "SELECT pair_id FROM public.order_pair_units WHERE order_id=:id AND status='allocated'",
                id=body.order_id,
            )
        ]
        if len(body.pair_ids) != len(set(body.pair_ids)) or set(pairs) != set(
            body.pair_ids
        ):
            fail(409, "SHIPMENT_PAIR_MISMATCH")
        if rows(
            s, "SELECT id FROM public.shipments WHERE order_id=:id", id=body.order_id
        ):
            fail(409, "SHIPMENT_EXISTS")
        sid = uuid4()
        s.execute(
            text(
                "INSERT INTO public.shipments(id,order_id,shipping_address_id,status,carrier) VALUES(:id,:oid,:address,'preparing',:carrier)"
            ),
            {
                "id": sid,
                "oid": body.order_id,
                "address": body.shipping_address_id,
                "carrier": body.carrier,
            },
        )
        for pid in pairs:
            s.execute(
                text(
                    "INSERT INTO public.shipment_pairs(shipment_id,pair_id) VALUES(:id,:pair)"
                ),
                {"id": sid, "pair": pid},
            )
        return {
            "shipment_id": sid,
            "order_id": body.order_id,
            "status": "preparing",
            "shipping_snapshot": snap,
        }, sid

    return command(context, request, "shipment.create", body.model_dump(), work)


TRANSITIONS = {
    "preparing": {"packed", "exception"},
    "packed": {"dispatched", "exception"},
    "dispatched": {"delivered", "exception", "returned"},
    "exception": {"returned"},
    "delivered": set(),
    "returned": set(),
}


@router.patch("/admin/shipments/{shipment_id}", operation_id="API-096")
def update_shipment(
    shipment_id: UUID, body: ShipmentUpdate, context: Authenticated, request: Request
):
    def work(s, settings):
        found = rows(
            s, "SELECT order_id FROM public.shipments WHERE id=:id", id=shipment_id
        )
        if not found:
            raise AccessError(404)
        oid = found[0]["order_id"]
        lock_order(s, oid)
        row = rows(
            s, "SELECT * FROM public.shipments WHERE id=:id FOR UPDATE", id=shipment_id
        )[0]
        if row["status"] != body.expected_status:
            fail(412, "VERSION_MISMATCH")
        if body.status not in TRANSITIONS[row["status"]]:
            fail(409, "INVALID_SHIPMENT_TRANSITION")
        if body.status in {"packed", "dispatched", "delivered"}:
            eligible(s, oid)
        if body.status == "packed":
            if not body.packing_confirmed:
                fail(422, "PACKING_CONFIRMATION_REQUIRED")
            s.execute(
                text(
                    "UPDATE public.shipment_pairs SET packed_qa_confirmed=true,packed_by=:uid,packed_at=clock_timestamp() WHERE shipment_id=:id"
                ),
                {"uid": context.principal.user_id, "id": shipment_id},
            )
        tracking = body.tracking_reference or row["tracking_reference"]
        if body.status == "dispatched" and not tracking:
            fail(422, "TRACKING_REQUIRED")
        s.execute(
            text("""UPDATE public.shipments SET status=CAST(:status AS text),tracking_reference=:tracking,
          packed_at=CASE WHEN CAST(:status AS text)='packed' THEN clock_timestamp() ELSE packed_at END,
          dispatched_at=CASE WHEN CAST(:status AS text)='dispatched' THEN clock_timestamp() ELSE dispatched_at END,
          delivered_at=CASE WHEN CAST(:status AS text)='delivered' THEN clock_timestamp() ELSE delivered_at END WHERE id=:id"""),
            {"status": body.status, "tracking": tracking, "id": shipment_id},
        )
        s.execute(
            text("UPDATE public.orders SET fulfillment_status=:status WHERE id=:id"),
            {
                "id": oid,
                "status": "exception" if body.status == "returned" else body.status,
            },
        )
        return {
            "shipment_id": shipment_id,
            "order_id": oid,
            "status": body.status,
            "tracking_reference": tracking,
        }, shipment_id

    return command(
        context, request, "shipment.update:" + str(shipment_id), body.model_dump(), work
    )


@router.get("/admin/orders/{order_id}", operation_id="API-081")
def operations_order_detail(order_id: UUID, context: Authenticated, request: Request):
    require_staff(context, "operations", "finance")
    found = rows(
        context.session,
        "SELECT id,order_number,order_status,payment_status,fulfillment_status,currency_code,total_pkr,created_at,placed_at FROM public.orders WHERE id=:id",
        id=order_id,
    )
    if not found:
        raise AccessError(404)
    result = {**found[0], **detail(context.session, order_id)}
    operations = rows(
        context.session,
        "SELECT id FROM public.staff_roles WHERE user_id=:uid AND role='operations' AND revoked_at IS NULL",
        uid=context.principal.user_id,
    )
    if operations:
        result["shipping_snapshot"] = shipping(
            context.session, request.app.state.settings, order_id
        )
        context.session.execute(
            text("""INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,reason,safe_details)
          VALUES(:uid,'staff','shipment.address.read','order',:id,'operations purchase shipping snapshot retrieval','{}'::jsonb)"""),
            {"uid": context.principal.user_id, "id": order_id},
        )
    if not operations:
        result["print_status"] = "restricted"
    return result
