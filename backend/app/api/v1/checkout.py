"""Task 5.2: immutable server quotes, private address snapshots and one-pair checkout."""

import hashlib
import json
import re
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api.auth import AccessError, Authenticated, require_verified_account
from app.api.v1.catalog import CatalogRoute, fail
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt, encrypt

router = APIRouter(tags=["checkout"], route_class=CatalogRoute)


class Closed(BaseModel):
    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, hide_input_in_errors=True
    )


class Address(Closed):
    recipient_name: str = Field(min_length=1, max_length=160)
    phone: str = Field(pattern=r"^\+[1-9][0-9]{7,14}$")
    address: str = Field(min_length=1, max_length=500)
    city: str = Field(min_length=1, max_length=100)
    province: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)


class QRUse(Closed):
    mode: Literal["new_pair", "existing_owned"]
    tag_type: Literal["lost", "ice"]
    copies: int = Field(ge=1, le=100, strict=True)
    existing_qr_id: UUID | None = None
    client_pair_group: str | None = Field(default=None, min_length=1, max_length=80)

    @model_validator(mode="after")
    def binding(self):
        if self.mode == "new_pair" and (
            self.existing_qr_id is not None or not self.client_pair_group
        ):
            raise ValueError("Invalid new-pair binding")
        if self.mode == "existing_owned" and (
            self.existing_qr_id is None or self.client_pair_group is not None
        ):
            raise ValueError("Invalid existing binding")
        return self


class CartLine(Closed):
    variant_id: UUID
    quantity: int = Field(ge=1, le=100, strict=True)
    qr_uses: list[QRUse] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def copies_match(self):
        if sum(u.copies for u in self.qr_uses) != self.quantity:
            raise ValueError("Copy counts must match quantity")
        return self


class DeliveryRequest(Closed):
    address: Address | None = None
    shipping_address_id: UUID | None = None
    shipping_address_version: int | None = Field(
        default=None, ge=1, le=2147483646, strict=True
    )
    contact_phone_confirmation: bool = Field(strict=True)

    @model_validator(mode="after")
    def address_source(self):
        if self.address is not None:
            if (
                self.shipping_address_id is not None
                or self.shipping_address_version is not None
            ):
                raise ValueError("Choose one address source")
        elif self.shipping_address_id is None or self.shipping_address_version is None:
            raise ValueError("Saved address and version required")
        return self

    @field_validator("contact_phone_confirmation")
    @classmethod
    def confirmed(cls, value):
        if not value:
            raise ValueError("Confirm shipping contact")
        return value


class QuoteRequest(DeliveryRequest):
    lines: list[CartLine] = Field(min_length=1, max_length=50)


class ConfirmRequest(Closed):
    accept_total: str = Field(pattern=r"^[0-9]{1,10}\.[0-9]{2}$")
    accept_currency: Literal["PKR"]


def configured(request):
    s = request.app.state.settings
    if (
        not s.checkout_enabled
        or s.checkout_shipping_pkr is None
        or s.checkout_tax_pkr is None
    ):
        raise AccessError(503)
    return s


def record(context, request, operation, payload, work):
    require_verified_account(context)
    s = configured(request)
    session = context.session
    from app.db.template_registry import gate
    gate(session)
    actor = context.principal.user_id
    key = request.headers.get("idempotency-key", "")
    if not re.fullmatch(r"[A-Za-z0-9._:-]{8,160}", key):
        fail(400, "IDEMPOTENCY_KEY_REQUIRED")
    canonical = json.dumps(
        jsonable_encoder(payload), sort_keys=True, separators=(",", ":")
    )
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    reference = hashlib.sha256(f"{actor}:{operation}:{key}".encode()).hexdigest()
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
        {"key": reference},
    )
    params = {"scope": str(actor), "actor": actor, "op": operation, "key": key}
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
    try:
        if old:
            if old["request_hash"] != digest:
                fail(409, "IDEMPOTENCY_KEY_REUSED")
            return json.loads(
                decrypt(
                    s,
                    actor,
                    "checkout:" + reference,
                    old["response_body_ciphertext"],
                    old["response_key_version"],
                )
            )
        with session.begin_nested():
            result, target = work(s)
            result = jsonable_encoder(result, custom_encoder={Decimal: str})
            cipher, version = encrypt(
                s, actor, "checkout:" + reference, json.dumps(result)
            )
            session.execute(
                text("""INSERT INTO public.idempotency_records(actor_scope,actor_user_id,operation,idempotency_key,request_hash,state,response_status,response_body_ciphertext,response_key_version,expires_at)
   VALUES(:scope,:actor,:op,:key,:hash,'completed',201,:cipher,:version,now()+interval '1 day')"""),
                {**params, "hash": digest, "cipher": cipher, "version": version},
            )
            session.execute(
                text("""INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,request_id,reason,safe_details)
   VALUES(:actor,'customer',:op,'checkout',:target,:rid,'customer checkout',jsonb_build_object('event_id',CAST(:reference AS text),'outcome','success'))"""),
                {
                    "actor": actor,
                    "op": operation,
                    "target": target,
                    "rid": getattr(request.state, "request_id", None),
                    "reference": reference,
                },
            )
            return result
    except ProfileCryptoUnavailable:
        raise AccessError(503) from None
    except IntegrityError:
        fail(409, "CHECKOUT_CONFLICT")


def catalog_lines(context, lines, settings):
    session = context.session
    groups = {}
    snapshots = []
    total = Decimal("0.00")
    product_copies = {}
    rows = session.execute(
        text("SELECT public.sr_checkout_catalog(:ids)"),
        {"ids": [l.variant_id for l in lines]},
    ).scalar_one()
    by_id = {row["id"]: row for row in rows}
    for line in sorted(lines, key=lambda l: str(l.variant_id)):
        row = by_id.get(str(line.variant_id))
        if row is None:
            fail(422, "VARIANT_UNAVAILABLE")
        from app.db.template_registry import resolve
        registry_specs=resolve(session,{"variant_id":str(line.variant_id),"qr_uses":[u.model_dump(mode="json") for u in line.qr_uses]})
        if (
            f"{row['template_key']}@{row['template_version']}"
            not in settings.catalog_approved_templates
        ) and registry_specs is None:
            fail(422, "PHYSICAL_CATALOG_APPROVAL_REQUIRED")
        for use in line.qr_uses:
            if use.mode == "existing_owned":
                # Implemented authorization remains behind the approved future-reuse flag.
                if (
                    not settings.checkout_existing_qr_reuse_enabled
                    or not row["allows_existing_qr"]
                ):
                    fail(422, "EXISTING_QR_REUSE_DISABLED")
                owned = session.execute(
                    text("""SELECT q.id FROM public.qr_codes q JOIN public.tag_pairs p ON p.id=q.pair_id
     WHERE q.id=:id AND q.is_current AND q.tag_type=:tag AND q.public_status='active'
     AND p.owner_user_id=:actor AND p.ownership_status='active'"""),
                    {
                        "id": use.existing_qr_id,
                        "tag": use.tag_type,
                        "actor": context.principal.user_id,
                    },
                ).scalar_one_or_none()
                if owned is None:
                    raise AccessError(404)
            else:
                if not row["allows_new_pair"]:
                    fail(422, "NEW_PAIR_DISABLED")
                groups.setdefault(use.client_pair_group, set()).add(use.tag_type)
        # Every size of a product uses the authoritative product price. Never
        # accept a client price or fall back to a legacy variant price.
        if row.get("price_per_copy") is None:
            fail(422, "PRODUCT_PRICE_REQUIRED")
        product_id = str(row["product_id"])
        product_copies[product_id] = product_copies.get(product_id, 0) + line.quantity
        if product_copies[product_id] > row["max_order_copies"]:
            fail(422, "MAX_ORDER_COPIES_EXCEEDED")
        amount = Decimal(str(row["price_per_copy"])) * line.quantity
        total += amount
        snapshots.append(
            {
                "variant_id": str(row["id"]),
                "product_id": str(row["product_id"]),
                "sku": row["sku"],
                "product_name": row["product_name"],
                "variant_name": row["name"],
                "size_mm": str(row["size_mm"]),
                "material": row["material"],
                "fulfillment_method": row["fulfillment_method"],
                "template_key": row["template_key"],
                "template_version": row["template_version"],
                "unit_price": f"{Decimal(str(row['price_per_copy'])):.2f}",
                "currency_code": "PKR",
                "quantity": line.quantity,
                "line_total": f"{amount:.2f}",
                "product_version": row["product_version"],
                "variant_version": row["catalog_version"],
                "qr_uses": [u.model_dump(mode="json") for u in line.qr_uses],
            }
        )
    if any(tags != {"lost", "ice"} for tags in groups.values()):
        fail(422, "BOTH_TAG_TYPES_REQUIRED")
    if len(groups) > 1:
        fail(422, "MULTIPLE_NEW_PAIRS_DISABLED")
    if total + settings.checkout_shipping_pkr + settings.checkout_tax_pkr > Decimal(
        "9999999999.99"
    ):
        fail(422, "TOTAL_OUT_OF_RANGE")
    from app.db.template_registry import attach_quote_specs
    attach_quote_specs(session,snapshots)
    return snapshots, total, len(groups)


@router.post("/me/checkout/quotes", operation_id="API-203", status_code=201)
def create_quote(body: QuoteRequest, context: Authenticated, request: Request):
    if body.shipping_address_id is not None:
        from app.api.v1.shipping_addresses import guard

        guard(context, request, True)

    def work(settings):
        address = body.address
        if body.shipping_address_id is not None:
            from app.api.v1.shipping_addresses import resolve

            address = resolve(
                context,
                settings,
                body.shipping_address_id,
                body.shipping_address_version,
            )
        lines, subtotal, pairs = catalog_lines(context, body.lines, settings)
        if (
            pairs
            and context.session.execute(
                text("SELECT public.sr_checkout_capacity()")
            ).scalar_one()
            < pairs
        ):
            fail(409, "INSUFFICIENT_PAIR_STOCK")
        total = subtotal + settings.checkout_shipping_pkr + settings.checkout_tax_pkr
        qid = uuid4()
        cipher, version = encrypt(
            settings, qid, "checkout_address", address.model_dump_json()
        )
        payload = {
            "lines": lines,
            "new_pair_count": pairs,
            "reservation_minutes": settings.checkout_reservation_minutes,
        }
        expires = context.session.execute(
            text("""INSERT INTO public.checkout_quotes(id,customer_user_id,payload,address_ciphertext,address_key_version,subtotal_pkr,shipping_pkr,tax_pkr,total_pkr,expires_at)
   VALUES(:id,:actor,CAST(:payload AS jsonb),:cipher,:version,:subtotal,:shipping,:tax,:total,clock_timestamp()+interval '15 minutes') RETURNING expires_at"""),
            {
                "id": qid,
                "actor": context.principal.user_id,
                "payload": json.dumps(payload),
                "cipher": cipher,
                "version": version,
                "subtotal": subtotal,
                "shipping": settings.checkout_shipping_pkr,
                "tax": settings.checkout_tax_pkr,
                "total": total,
            },
        ).scalar_one()
        public_lines = [
            {
                k: v
                for k, v in line.items()
                if k not in {"template_key", "template_version", "registry_specs"}
            }
            for line in lines
        ]
        return {
            "quote_id": qid,
            "expires_at": expires,
            "currency_code": "PKR",
            "subtotal_pkr": f"{subtotal:.2f}",
            "shipping_pkr": f"{settings.checkout_shipping_pkr:.2f}",
            "tax_pkr": f"{settings.checkout_tax_pkr:.2f}",
            "discount_pkr": "0.00",
            "total_pkr": f"{total:.2f}",
            "lines": public_lines,
            "new_pair_count": pairs,
            "shipping_confirmation": {
                "city": address.city,
                "phone_masked": "••••" + address.phone[-4:],
            },
            "reservation_policy": {
                "minutes": settings.checkout_reservation_minutes,
                "starts_at": "confirmation",
                "payment_review": "reconciliation_hold",
            },
        }, qid

    return record(
        context, request, "checkout.quote", body.model_dump(mode="json"), work
    )


@router.post(
    "/me/checkout/quotes/{quote_id}/confirm", operation_id="API-204", status_code=201
)
def confirm_quote(
    quote_id: UUID, body: ConfirmRequest, context: Authenticated, request: Request
):
    def work(settings):
        session = context.session
        actor = context.principal.user_id
        row = (
            session.execute(
                text(
                    "SELECT * FROM public.checkout_quotes WHERE id=:id AND customer_user_id=:actor FOR UPDATE"
                ),
                {"id": quote_id, "actor": actor},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise AccessError(404)
        now = session.execute(text("SELECT clock_timestamp()")).scalar_one()
        if row["status"] != "open" or row["expires_at"] <= now:
            fail(409, "QUOTE_UNAVAILABLE")
        if (
            Decimal(body.accept_total) != row["total_pkr"]
            or body.accept_currency != row["currency_code"]
        ):
            fail(409, "QUOTE_TOTAL_MISMATCH")
        payload = row["payload"]
        if payload.get("commerce_model", "legacy_pair") != "legacy_pair":
            fail(409, "QUOTE_UNAVAILABLE")
        from app.db.template_registry import recheck_quote
        recheck_quote(session,payload["lines"])
        if any(
            f"{line['template_key']}@{line['template_version']}"
            not in settings.catalog_approved_templates
            for line in payload["lines"]
            if "registry_specs" not in line
        ):
            fail(422, "PHYSICAL_CATALOG_APPROVAL_REQUIRED")
        # Recheck publication and physical policy; preserve the unexpired quoted prices.
        current_lines = [
            CartLine(
                variant_id=l["variant_id"], quantity=l["quantity"], qr_uses=l["qr_uses"]
            )
            for l in payload["lines"]
        ]
        catalog_lines(context, current_lines, settings)
        address = Address.model_validate_json(
            decrypt(
                settings,
                quote_id,
                "checkout_address",
                row["address_ciphertext"],
                row["address_key_version"],
            )
        )
        order = uuid4()
        number = f"SR-{now:%Y%m%d}-{order.hex[:12].upper()}"
        address_id = uuid4()
        session.execute(
            text("""INSERT INTO public.orders(id,order_number,customer_user_id,subtotal_pkr,shipping_pkr,tax_pkr,total_pkr)
   VALUES(:id,:number,:actor,:subtotal,:shipping,:tax,:total)"""),
            {
                "id": order,
                "number": number,
                "actor": actor,
                "subtotal": row["subtotal_pkr"],
                "shipping": row["shipping_pkr"],
                "tax": row["tax_pkr"],
                "total": row["total_pkr"],
            },
        )
        encrypted = {
            field: encrypt(
                settings, order, "shipping_" + field, getattr(address, field)
            )[0]
            for field in ("recipient_name", "phone", "address")
        }
        params = {
            "id": address_id,
            "actor": actor,
            "order": order,
            "name": encrypted["recipient_name"],
            "phone": encrypted["phone"],
            "address": encrypted["address"],
            "city": address.city,
            "province": address.province,
            "postal": address.postal_code,
            "version": settings.profile_data_key_version,
        }
        session.execute(
            text("""INSERT INTO public.shipping_addresses(id,customer_user_id,recipient_name_ciphertext,phone_ciphertext,address_ciphertext,city,province,postal_code,key_version)
   VALUES(:id,:actor,:name,:phone,:address,:city,:province,:postal,:version)"""),
            params,
        )
        session.execute(
            text("""INSERT INTO public.order_shipping_snapshots(order_id,source_address_id,recipient_name_ciphertext,phone_ciphertext,address_ciphertext,city,province,postal_code,key_version)
   VALUES(:order,:id,:name,:phone,:address,:city,:province,:postal,:version)"""),
            params,
        )
        reserved = None
        if payload["new_pair_count"]:
            reserved = session.execute(
                text("SELECT public.sr_checkout_reserve(:quote,:order,:unit,:minutes)"),
                {
                    "quote": quote_id,
                    "order": order,
                    "unit": uuid4(),
                    "minutes": payload["reservation_minutes"],
                },
            ).scalar_one()
            if reserved is None:
                fail(409, "INSUFFICIENT_PAIR_STOCK")
        for line in payload["lines"]:
            item = uuid4()
            session.execute(
                text("""INSERT INTO public.order_items(id,order_id,product_id,variant_id,product_name_snapshot,variant_name_snapshot,sku_snapshot,size_mm_snapshot,material_snapshot,fulfillment_method_snapshot,template_key_snapshot,template_version_snapshot,quantity,unit_price_snapshot,line_total)
    VALUES(:id,:order,:product,:variant,:product_name,:variant_name,:sku,:size,:material,:method,:template,:version,:quantity,:unit_price,:line_total)"""),
                {
                    "id": item,
                    "order": order,
                    "product": line["product_id"],
                    "variant": line["variant_id"],
                    "product_name": line["product_name"],
                    "variant_name": line["variant_name"],
                    "sku": line["sku"],
                    "size": line["size_mm"],
                    "material": line["material"],
                    "method": line["fulfillment_method"],
                    "template": line["template_key"],
                    "version": line["template_version"],
                    "quantity": line["quantity"],
                    "unit_price": line["unit_price"],
                    "line_total": line["line_total"],
                },
            )
            for use in line["qr_uses"]:
                qr = (
                    reserved[use["tag_type"]]
                    if use["mode"] == "new_pair"
                    else use["existing_qr_id"]
                )
                use_id = session.execute(
                    text("""INSERT INTO public.order_item_qr_uses(order_item_id,qr_code_id,pair_unit_id,use_kind,tag_type_snapshot,copies)
     VALUES(:item,:qr,:unit,:kind,:tag,:copies) RETURNING id"""),
                    {
                        "item": item,
                        "qr": qr,
                        "unit": reserved["unit_id"]
                        if use["mode"] == "new_pair"
                        else None,
                        "kind": use["mode"],
                        "tag": use["tag_type"],
                        "copies": use["copies"],
                    },
                ).scalar_one()
                from app.db.template_registry import freeze_use
                specs=line.get("registry_specs")
                spec=next((s for s in specs if s["tag_type"]==use["tag_type"]),None) if specs is not None else None
                if specs is not None and spec is None:
                    fail(409,"CONFLICT")
                freeze_use(session,use_id,spec)
        session.execute(
            text(
                "UPDATE public.orders SET order_status='placed',placed_at=clock_timestamp() WHERE id=:id"
            ),
            {"id": order},
        )
        session.execute(
            text(
                "UPDATE public.checkout_quotes SET status='confirmed',order_id=:order WHERE id=:id"
            ),
            {"id": quote_id, "order": order},
        )
        # Check every deferred invariant while failure can still roll back the receipt.
        session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        session.execute(text("SET CONSTRAINTS ALL DEFERRED"))
        return {
            "order_id": order,
            "order_reference": number,
            "order_status": "placed",
            "payment_status": "awaiting_transfer",
            "reservation_state": "reserved" if reserved else "not_required",
            "reserved_until": reserved["reserved_until"] if reserved else None,
            "total_pkr": f"{row['total_pkr']:.2f}",
            "currency_code": "PKR",
        }, order

    return record(
        context,
        request,
        "checkout.confirm",
        {"quote_id": str(quote_id), **body.model_dump()},
        work,
    )


@router.post("/me/orders", operation_id="API-060", status_code=409)
def legacy_order(context: Authenticated):
    """Legacy callers must upgrade; never run a competing order writer."""
    require_verified_account(context)
    fail(409, "QUOTE_REQUIRED")
