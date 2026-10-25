"""Versioned single-identity checkout; allocation belongs to verified settlement."""

import json
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from pydantic import Field, model_validator
from sqlalchemy import text

from app.api.auth import AccessError, Authenticated
from app.api.v1.catalog import CatalogRoute, fail
from app.api.v1.checkout import Address, Closed, ConfirmRequest, DeliveryRequest, record
from app.core.profile_crypto import decrypt, encrypt
from app.db.template_registry import recheck_quote, resolve

router = APIRouter(tags=["item checkout"], route_class=CatalogRoute)


class SizeSelection(Closed):
    variant_id: UUID
    copies: int = Field(ge=1, le=100, strict=True)


class Item(Closed):
    product_id: UUID
    # Absent means merge all lines of this product into one identity. Non-null
    # keys deliberately create separate identities, never inferred from size.
    identity_group: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,80}$")
    sizes: list[SizeSelection] = Field(min_length=1, max_length=50)


class ItemQuoteRequest(DeliveryRequest):
    # Address/confirmation validation remains identical to the legacy contract.
    commerce_model: Literal["single_qr"]
    items: list[Item] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def bounded_sizes(self):
        if sum(len(item.sizes) for item in self.items) > 50:
            raise ValueError("Too many size selections")
        return self


def admission(session):
    if (
        session.execute(text("SELECT public.sr_single_checkout_enabled()")).scalar_one()
        is not True
    ):
        fail(503, "SINGLE_QR_CHECKOUT_NOT_RELEASED")


def normalize(items):
    groups = {}
    for item in items:
        key = (str(item.product_id), item.identity_group)
        sizes = groups.setdefault(key, {})
        for size in item.sizes:
            vid = str(size.variant_id)
            sizes[vid] = sizes.get(vid, 0) + size.copies
    return [
        {
            "product_id": pid,
            "identity_group": group,
            "sizes": [
                {"variant_id": vid, "copies": copies}
                for vid, copies in sorted(sizes.items())
            ],
        }
        for (pid, group), sizes in sorted(
            groups.items(), key=lambda pair: (pair[0][0], pair[0][1] or "")
        )
    ]


def snapshots(context, items, settings):
    normalized = normalize(items)
    session = context.session
    rows = session.execute(
        text("SELECT public.sr_item_checkout_catalog(:ids)"),
        {
            "ids": sorted(
                {size["variant_id"] for item in normalized for size in item["sizes"]}
            )
        },
    ).scalar_one()
    by_id = {str(row["id"]): row for row in rows}
    subtotal = Decimal("0.00")
    result = []
    for item in normalized:
        selections = []
        product = None
        quantity = sum(size["copies"] for size in item["sizes"])
        for size in item["sizes"]:
            row = by_id.get(size["variant_id"])
            if (
                row is None
                or str(row["product_id"]) != item["product_id"]
                or row["qr_type"] not in {"lost", "ice"}
            ):
                fail(422, "VARIANT_UNAVAILABLE")
            product = row
            if quantity > row["max_order_copies"]:
                fail(422, "MAX_ORDER_COPIES_EXCEEDED")
            if row.get("price_per_copy") is None:
                fail(422, "PRODUCT_PRICE_REQUIRED")
            specs = resolve(
                session,
                {
                    "variant_id": size["variant_id"],
                    "qr_uses": [{"tag_type": row["qr_type"]}],
                },
            )
            if not specs or len(specs) != 1 or specs[0]["tag_type"] != row["qr_type"]:
                fail(422, "QR_TYPE_TEMPLATE_APPROVAL_REQUIRED")
            selections.append(
                {
                    **size,
                    "name": row["name"],
                    "sku": row["sku"],
                    "size_mm": str(row["size_mm"]),
                    "material": row["material"],
                    "variant_version": row["catalog_version"],
                    "registry_specs": specs,
                }
            )
        unit = Decimal(str(product["price_per_copy"]))
        amount = unit * quantity
        subtotal += amount
        result.append(
            {
                **item,
                "sizes": selections,
                "product_name": product["product_name"],
                "product_version": product["product_version"],
                "qr_type": product["qr_type"],
                "max_order_copies": product["max_order_copies"],
                "quantity": quantity,
                "unit_price": f"{unit:.2f}",
                "line_total": f"{amount:.2f}",
            }
        )
    if subtotal + settings.checkout_shipping_pkr + settings.checkout_tax_pkr > Decimal(
        "9999999999.99"
    ):
        fail(422, "TOTAL_OUT_OF_RANGE")
    return result, subtotal


def public_items(items):
    return [
        {
            k: (
                [
                    {sk: sv for sk, sv in size.items() if sk != "registry_specs"}
                    for size in value
                ]
                if k == "sizes"
                else value
            )
            for k, value in item.items()
        }
        for item in items
    ]


@router.post(
    "/me/checkout/item-quotes", status_code=201, operation_id="item-checkout-quote"
)
def create_quote(body: ItemQuoteRequest, context: Authenticated, request: Request):
    if body.shipping_address_id is not None:
        from app.api.v1.shipping_addresses import guard

        guard(context, request, True)

    def work(settings):
        admission(context.session)
        instructions = context.session.execute(
            text("SELECT public.sr_checkout_payment_instructions()")
        ).scalar_one()
        if not instructions:
            fail(503, "PAYMENT_INSTRUCTIONS_UNAVAILABLE")
        address = body.address
        if body.shipping_address_id is not None:
            from app.api.v1.shipping_addresses import resolve as saved_address

            address = saved_address(
                context,
                settings,
                body.shipping_address_id,
                body.shipping_address_version,
            )
        items, subtotal = snapshots(context, body.items, settings)
        total = subtotal + settings.checkout_shipping_pkr + settings.checkout_tax_pkr
        qid = uuid4()
        cipher, version = encrypt(
            settings, qid, "checkout_address", address.model_dump_json()
        )
        payload = {
            "commerce_model": "single_qr",
            "items": items,
            "payment_instructions": instructions,
        }
        expires = context.session.execute(
            text("""INSERT INTO public.checkout_quotes
            (id,customer_user_id,commerce_model,payload,address_ciphertext,address_key_version,subtotal_pkr,shipping_pkr,tax_pkr,total_pkr,expires_at)
            VALUES(:id,:actor,'single_qr',CAST(:payload AS jsonb),:cipher,:version,:subtotal,:shipping,:tax,:total,clock_timestamp()+interval '15 minutes') RETURNING expires_at"""),
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
        return {
            "quote_id": qid,
            "commerce_model": "single_qr",
            "expires_at": expires,
            "currency_code": "PKR",
            "subtotal_pkr": f"{subtotal:.2f}",
            "shipping_pkr": f"{settings.checkout_shipping_pkr:.2f}",
            "tax_pkr": f"{settings.checkout_tax_pkr:.2f}",
            "total_pkr": f"{total:.2f}",
            "discount_pkr": "0.00",
            "items": public_items(items),
            "identity_count": len(items),
            "allocation_policy": "after_verified_payment",
            "stock_reserved": False,
            "payment_instructions": instructions,
            "shipping_confirmation": {
                "city": address.city,
                "phone_masked": "••••" + address.phone[-4:],
            },
        }, qid

    return record(
        context, request, "checkout.item_quote", body.model_dump(mode="json"), work
    )


def revalidate(context, payload, settings):
    items = [
        Item.model_validate(
            {
                "product_id": item["product_id"],
                "identity_group": item["identity_group"],
                "sizes": [
                    {"variant_id": size["variant_id"], "copies": size["copies"]}
                    for size in item["sizes"]
                ],
            }
        )
        for item in payload["items"]
    ]
    current, _ = snapshots(context, items, settings)
    # A catalog edit invalidates this quote, including price/cap/type or binding.
    if current != payload["items"]:
        fail(409, "QUOTE_STALE")
    for item in payload["items"]:
        recheck_quote(
            context.session,
            [
                {
                    "variant_id": size["variant_id"],
                    "qr_uses": [{"tag_type": item["qr_type"]}],
                    "registry_specs": size["registry_specs"],
                }
                for size in item["sizes"]
            ],
        )


@router.post(
    "/me/checkout/item-quotes/{quote_id}/confirm",
    status_code=201,
    operation_id="item-checkout-confirm",
)
def confirm_quote(
    quote_id: UUID, body: ConfirmRequest, context: Authenticated, request: Request
):
    def work(settings):
        session, actor = context.session, context.principal.user_id
        admission(session)
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
        if (
            row["commerce_model"] != "single_qr"
            or row["status"] != "open"
            or row["expires_at"] <= now
        ):
            fail(409, "QUOTE_UNAVAILABLE")
        if (
            Decimal(body.accept_total) != row["total_pkr"]
            or body.accept_currency != row["currency_code"]
        ):
            fail(409, "QUOTE_TOTAL_MISMATCH")
        payload = row["payload"]
        revalidate(context, payload, settings)
        address = Address.model_validate_json(
            decrypt(
                settings,
                quote_id,
                "checkout_address",
                row["address_ciphertext"],
                row["address_key_version"],
            )
        )
        oid, aid = uuid4(), uuid4()
        number = f"SR-{now:%Y%m%d}-{oid.hex[:12].upper()}"
        instructions = session.execute(
            text("SELECT public.sr_checkout_payment_instructions()")
        ).scalar_one()
        if instructions != payload["payment_instructions"]:
            fail(409, "QUOTE_STALE")
        session.execute(
            text("""INSERT INTO public.orders(id,order_number,customer_user_id,commerce_model,payment_instructions_snapshot,subtotal_pkr,shipping_pkr,tax_pkr,total_pkr)
            VALUES(:id,:number,:actor,'single_qr',CAST(:instructions AS jsonb),:subtotal,:shipping,:tax,:total)"""),
            {
                "id": oid,
                "number": number,
                "actor": actor,
                "instructions": json.dumps(instructions),
                "subtotal": row["subtotal_pkr"],
                "shipping": row["shipping_pkr"],
                "tax": row["tax_pkr"],
                "total": row["total_pkr"],
            },
        )
        fields = {
            field: encrypt(settings, oid, "shipping_" + field, getattr(address, field))[
                0
            ]
            for field in ("recipient_name", "phone", "address")
        }
        params = {
            "id": aid,
            "oid": oid,
            "actor": actor,
            **fields,
            "city": address.city,
            "province": address.province,
            "postal": address.postal_code,
            "version": settings.profile_data_key_version,
        }
        session.execute(
            text("""INSERT INTO public.shipping_addresses(id,customer_user_id,recipient_name_ciphertext,phone_ciphertext,address_ciphertext,city,province,postal_code,key_version)
            VALUES(:id,:actor,:recipient_name,:phone,:address,:city,:province,:postal,:version)"""),
            params,
        )
        session.execute(
            text("""INSERT INTO public.order_shipping_snapshots(order_id,source_address_id,recipient_name_ciphertext,phone_ciphertext,address_ciphertext,city,province,postal_code,key_version)
            VALUES(:oid,:id,:recipient_name,:phone,:address,:city,:province,:postal,:version)"""),
            params,
        )
        for item in payload["items"]:
            iid = uuid4()
            session.execute(
                text("""INSERT INTO public.order_logical_items
                (id,order_id,product_id,identity_group,product_name_snapshot,qr_type_snapshot,quantity,unit_price_snapshot,line_total,max_copies_snapshot,product_version_snapshot)
                VALUES(:id,:oid,:pid,:group,:name,:kind,:qty,:price,:total,:cap,:version)"""),
                {
                    "id": iid,
                    "oid": oid,
                    "pid": item["product_id"],
                    "group": item["identity_group"],
                    "name": item["product_name"],
                    "kind": item["qr_type"],
                    "qty": item["quantity"],
                    "price": item["unit_price"],
                    "total": item["line_total"],
                    "cap": item["max_order_copies"],
                    "version": item["product_version"],
                },
            )
            for size in item["sizes"]:
                session.execute(
                    text("""INSERT INTO public.order_item_sizes
                    (logical_item_id,variant_id,variant_name_snapshot,sku_snapshot,size_mm_snapshot,material_snapshot,copies,variant_version_snapshot,print_spec_snapshot)
                    VALUES(:iid,:vid,:name,:sku,:mm,:material,:copies,:version,CAST(:spec AS jsonb))"""),
                    {
                        "iid": iid,
                        "vid": size["variant_id"],
                        "name": size["name"],
                        "sku": size["sku"],
                        "mm": size["size_mm"],
                        "material": size["material"],
                        "copies": size["copies"],
                        "version": size["variant_version"],
                        "spec": json.dumps(size["registry_specs"][0]),
                    },
                )
        session.execute(
            text(
                "UPDATE public.orders SET order_status='placed',placed_at=clock_timestamp() WHERE id=:id"
            ),
            {"id": oid},
        )
        session.execute(
            text(
                "UPDATE public.checkout_quotes SET status='confirmed',order_id=:oid WHERE id=:id"
            ),
            {"id": quote_id, "oid": oid},
        )
        session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        session.execute(text("SET CONSTRAINTS ALL DEFERRED"))
        return {
            "order_id": oid,
            "order_reference": number,
            "commerce_model": "single_qr",
            "order_status": "placed",
            "payment_status": "awaiting_transfer",
            "allocation_state": "awaiting_verified_payment",
            "identity_count": len(payload["items"]),
            "total_pkr": f"{row['total_pkr']:.2f}",
            "currency_code": "PKR",
        }, oid

    return record(
        context,
        request,
        "checkout.item_confirm",
        {"quote_id": str(quote_id), **body.model_dump()},
        work,
    )
