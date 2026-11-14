"""Delivered purchaser entitlement, separate from legacy pair activation."""

import hashlib
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Header, Query
from fastapi.responses import JSONResponse
from pydantic import Field
from sqlalchemy import text

from app.api.auth import (
    AccessError,
    Authenticated,
    require_staff,
    require_verified_account,
)
from app.api.v1.cancellations import Confirmed
from app.api.v1.catalog import CatalogRoute, Closed, fail


class OwnerRoute(CatalogRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def bounded(request):
            if request.method in {"POST", "PATCH"}:
                payload = bytearray()
                async for chunk in request.stream():
                    payload.extend(chunk)
                    if len(payload) > 4096:
                        return JSONResponse(
                            {"error": {"code": "REQUEST_TOO_LARGE"}},
                            status_code=413,
                            headers={"Cache-Control": "no-store"},
                        )
                request._body = bytes(payload)
            return await handler(request)

        return bounded


router = APIRouter(tags=["independent QR ownership"], route_class=OwnerRoute)


class Begin(Closed):
    logical_item_id: UUID


class Confirm(Confirmed):
    intent_id: UUID


class Availability(Confirmed):
    public_status: Literal["active", "owner_disabled"]
    expected_revision: int = Field(ge=1, le=2147483646, strict=True)


def checked(value):
    if value is None:
        raise AccessError(404)
    if "error" in value:
        code = value["error"]
        if code == "RATE_LIMITED":
            raise AccessError(429)
        fail(412 if code == "VERSION_MISMATCH" else 409, code)
    return value


def hashes(body, key):
    import re

    if key is None or not re.fullmatch(r"[A-Za-z0-9._:-]{8,160}", key):
        fail(400, "IDEMPOTENCY_KEY_REQUIRED")
    return hashlib.sha256(key.encode()).hexdigest(), hashlib.sha256(
        body.model_dump_json().encode()
    ).hexdigest()


@router.get("/me/independent-qr", operation_id="independent-qr-list")
def collection(
    context: Authenticated,
    limit: int = Query(default=20, ge=1, le=100),
    after: UUID | None = None,
):
    require_verified_account(context)
    value = checked(
        context.session.execute(
            text("SELECT public.sr_standalone_owner_list(:sid,:take,:after)"),
            {"sid": context.principal.session_id, "take": limit + 1, "after": after},
        ).scalar_one()
    )
    items = value["items"]
    return {
        "items": items[:limit],
        "next_cursor": str(items[limit - 1]["logical_item_id"])
        if len(items) > limit
        else None,
        "activation_released": value["activation_released"],
    }


@router.post(
    "/me/independent-qr/activation-intents",
    operation_id="independent-qr-intent",
    status_code=201,
)
def begin(body: Begin, context: Authenticated):
    require_verified_account(context)
    return checked(
        context.session.execute(
            text("SELECT public.sr_standalone_begin(:sid,:iid)"),
            {"sid": context.principal.session_id, "iid": body.logical_item_id},
        ).scalar_one()
    )


@router.post(
    "/me/independent-qr/activations",
    operation_id="independent-qr-activate",
    status_code=201,
)
def confirm(
    body: Confirm,
    context: Authenticated,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    require_verified_account(context)
    kh, rh = hashes(body, idempotency_key)
    return checked(
        context.session.execute(
            text("SELECT public.sr_standalone_confirm(:sid,:intent,:kh,:rh)"),
            {
                "sid": context.principal.session_id,
                "intent": body.intent_id,
                "kh": kh,
                "rh": rh,
            },
        ).scalar_one()
    )


@router.get("/me/independent-qr/{qr_id}/history", operation_id="independent-qr-history")
def history(
    qr_id: UUID,
    context: Authenticated,
    limit: int = Query(default=20, ge=1, le=100),
    after_revision: int | None = Query(default=None, ge=1),
):
    require_verified_account(context)
    return checked(
        context.session.execute(
            text("SELECT public.sr_standalone_history(:sid,:qid,:take,:after)"),
            {
                "sid": context.principal.session_id,
                "qid": qr_id,
                "take": limit,
                "after": after_revision,
            },
        ).scalar_one()
    )


@router.patch(
    "/me/independent-qr/{qr_id}/availability",
    operation_id="independent-qr-availability",
)
def availability(
    qr_id: UUID,
    body: Availability,
    context: Authenticated,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    require_verified_account(context)
    kh, rh = hashes(body, idempotency_key)
    return checked(
        context.session.execute(
            text(
                "SELECT public.sr_standalone_availability(:sid,:qid,:expected,:wanted,:kh,:rh)"
            ),
            {
                "sid": context.principal.session_id,
                "qid": qr_id,
                "expected": body.expected_revision,
                "wanted": body.public_status,
                "kh": kh,
                "rh": rh,
            },
        ).scalar_one()
    )


@router.get(
    "/admin/support-cases/{case_id}/independent-qr",
    operation_id="independent-qr-support",
)
def support(case_id: UUID, context: Authenticated):
    require_staff(context, "support")
    return checked(
        context.session.execute(
            text("SELECT public.sr_standalone_support(:sid,:cid)"),
            {"sid": context.principal.session_id, "cid": case_id},
        ).scalar_one()
    )
