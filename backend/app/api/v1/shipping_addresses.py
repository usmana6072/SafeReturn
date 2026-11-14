"""Owner-only saved addresses; historical checkout source rows stay private."""

from uuid import UUID, uuid4

from fastapi import APIRouter, Query, Request, Response
from pydantic import Field, ValidationError
from sqlalchemy import text

from app.api.auth import (
    AccessError,
    Authenticated,
    access_error,
    require_verified_account,
)
from app.api.v1.catalog import CatalogRoute, fail
from app.api.v1.checkout import Address, Closed
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt, encrypt


class PrivateRoute(CatalogRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handle(request):
            try:
                response = await original(request)
            except AccessError as error:
                response = await access_error(request, error)
            response.headers["Cache-Control"] = "private, no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            return response

        return handle


router = APIRouter(tags=["shipping addresses"], route_class=PrivateRoute)


def install(application):
    application.include_router(router, prefix="/api/v1")

    @application.middleware("http")
    async def private_shipping_headers(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith(
            ("/api/v1/me/shipping-addresses", "/api/v1/me/checkout/quotes")
        ):
            response.headers["Cache-Control"] = "private, no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response


class CreateAddress(Address):
    is_default: bool = Field(default=False, strict=True)
    expected_book_version: int = Field(ge=0, le=2147483646, strict=True)


class UpdateAddress(Closed):
    # Complete replacement of editable fields avoids ambiguous null/omitted patches.
    address: Address
    is_default: bool = Field(strict=True)
    expected_version: int = Field(ge=1, le=2147483646, strict=True)
    expected_book_version: int = Field(ge=0, le=2147483646, strict=True)


def guard(context, request, write=False):
    require_verified_account(context)
    if write:
        expected = request.app.state.settings.shipping_address_web_origin
        if not expected or request.headers.getlist("origin") != [expected]:
            raise AccessError(403)


def book(context, expected=None):
    session, actor = context.session, context.principal.user_id
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:scope,0))"),
        {"scope": "shipping-address-book:" + str(actor)},
    )
    row = (
        session.execute(
            text(
                "SELECT version,default_address_id FROM public.shipping_address_books WHERE customer_user_id=:actor FOR UPDATE"
            ),
            {"actor": actor},
        )
        .mappings()
        .one_or_none()
    )
    current = dict(row) if row else {"version": 0, "default_address_id": None}
    if expected is not None and current["version"] != expected:
        fail(409, "VERSION_MISMATCH")
    return current


def owned(context, address_id):
    row = (
        context.session.execute(
            text(
                "SELECT * FROM public.shipping_addresses WHERE id=:id AND customer_user_id=:actor AND is_saved FOR UPDATE"
            ),
            {"id": address_id, "actor": context.principal.user_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise AccessError(404)
    return row


def plaintext(settings, row):
    try:
        return Address(
            **{
                field: decrypt(
                    settings,
                    row["id"],
                    "saved_shipping_" + field,
                    row[field + "_ciphertext"],
                    row["key_version"],
                )
                for field in ("recipient_name", "phone", "address")
            },
            **{field: row[field] for field in ("city", "province", "postal_code")},
        )
    except (ProfileCryptoUnavailable, ValidationError):
        raise AccessError(503) from None


def projection(settings, row, current):
    return {
        "id": row["id"],
        "version": row["version"],
        "is_default": row["id"] == current["default_address_id"],
        **plaintext(settings, row).model_dump(),
    }


def resolve(context, settings, address_id, version):
    book(context)  # Same lock order as address mutations; freezes a consistent version.
    row = owned(context, address_id)
    if row["version"] != version:
        fail(409, "VERSION_MISMATCH")
    return plaintext(settings, row)


def mutable(context, row, version):
    if row["version"] != version:
        fail(409, "VERSION_MISMATCH")
    referenced = context.session.execute(
        text(
            "SELECT EXISTS(SELECT 1 FROM public.order_shipping_snapshots WHERE source_address_id=:id) OR EXISTS(SELECT 1 FROM public.shipments WHERE shipping_address_id=:id)"
        ),
        {"id": row["id"]},
    ).scalar_one()
    if referenced:
        fail(409, "CONFLICT")


def advance(context, current, default_id):
    # Increment the previous default's version when its selection changes.
    if current["default_address_id"] and current["default_address_id"] != default_id:
        context.session.execute(
            text(
                "UPDATE public.shipping_addresses SET version=version+1 WHERE id=:id AND customer_user_id=:actor AND is_saved"
            ),
            {"id": current["default_address_id"], "actor": context.principal.user_id},
        )
    version = current["version"] + 1
    context.session.execute(
        text(
            "INSERT INTO public.shipping_address_books(customer_user_id,version,default_address_id) VALUES(:actor,:version,:default) ON CONFLICT(customer_user_id) DO UPDATE SET version=EXCLUDED.version,default_address_id=EXCLUDED.default_address_id"
        ),
        {"actor": context.principal.user_id, "version": version, "default": default_id},
    )
    return {"version": version, "default_address_id": default_id}


def audit(context, request, operation, address_id):
    context.session.execute(
        text(
            "INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,request_id,reason,safe_details) VALUES(:actor,'customer',:operation,'shipping_address',:id,:rid,'customer address management','{}'::jsonb)"
        ),
        {
            "actor": context.principal.user_id,
            "operation": operation,
            "id": address_id,
            "rid": getattr(request.state, "request_id", None),
        },
    )


def cipher_params(settings, address_id, address):
    try:
        return {
            **{
                field: encrypt(
                    settings,
                    address_id,
                    "saved_shipping_" + field,
                    getattr(address, field),
                )[0]
                for field in ("recipient_name", "phone", "address")
            },
            "key_version": settings.profile_data_key_version,
            **{
                field: getattr(address, field)
                for field in ("city", "province", "postal_code")
            },
        }
    except ProfileCryptoUnavailable:
        raise AccessError(503) from None


@router.get("/me/shipping-addresses", operation_id="API-068")
def listing(context: Authenticated, request: Request):
    guard(context, request)
    current = book(context)
    rows = context.session.execute(
        text(
            "SELECT * FROM public.shipping_addresses WHERE customer_user_id=:actor AND is_saved ORDER BY created_at,id LIMIT 100"
        ),
        {"actor": context.principal.user_id},
    ).mappings()
    return {
        "book_version": current["version"],
        "items": [projection(request.app.state.settings, row, current) for row in rows],
    }


@router.post("/me/shipping-addresses", operation_id="API-067", status_code=201)
def create(body: CreateAddress, context: Authenticated, request: Request):
    guard(context, request, True)
    current = book(context, body.expected_book_version)
    count = context.session.execute(
        text(
            "SELECT count(*) FROM public.shipping_addresses WHERE customer_user_id=:actor AND is_saved"
        ),
        {"actor": context.principal.user_id},
    ).scalar_one()
    if count >= 100:
        fail(409, "CONFLICT")
    address_id = uuid4()
    params = {
        "id": address_id,
        "actor": context.principal.user_id,
        **cipher_params(request.app.state.settings, address_id, body),
    }
    context.session.execute(
        text(
            "INSERT INTO public.shipping_addresses(id,customer_user_id,is_saved,version,recipient_name_ciphertext,phone_ciphertext,address_ciphertext,city,province,postal_code,key_version) VALUES(:id,:actor,true,1,:recipient_name,:phone,:address,:city,:province,:postal_code,:key_version)"
        ),
        params,
    )
    current = advance(
        context,
        current,
        address_id if body.is_default else current["default_address_id"],
    )
    audit(context, request, "shipping_address.create", address_id)
    return {
        "book_version": current["version"],
        "item": projection(
            request.app.state.settings, owned(context, address_id), current
        ),
    }


@router.patch("/me/shipping-addresses/{address_id}", operation_id="API-069")
def update(
    address_id: UUID, body: UpdateAddress, context: Authenticated, request: Request
):
    guard(context, request, True)
    # Conceal foreign IDs even when the caller supplied a stale book version.
    current = book(context)
    row = owned(context, address_id)
    if current["version"] != body.expected_book_version:
        fail(409, "VERSION_MISMATCH")
    mutable(context, row, body.expected_version)
    params = {
        "id": address_id,
        "actor": context.principal.user_id,
        **cipher_params(request.app.state.settings, address_id, body.address),
    }
    context.session.execute(
        text(
            "UPDATE public.shipping_addresses SET recipient_name_ciphertext=:recipient_name,phone_ciphertext=:phone,address_ciphertext=:address,city=:city,province=:province,postal_code=:postal_code,key_version=:key_version,version=version+1 WHERE id=:id AND customer_user_id=:actor AND is_saved"
        ),
        params,
    )
    default_id = (
        address_id
        if body.is_default
        else (
            None
            if current["default_address_id"] == address_id
            else current["default_address_id"]
        )
    )
    # This row already received its mutation version increment.
    previous = dict(current)
    if previous["default_address_id"] == address_id:
        previous["default_address_id"] = None
    current = advance(context, previous, default_id)
    audit(context, request, "shipping_address.update", address_id)
    return {
        "book_version": current["version"],
        "item": projection(
            request.app.state.settings, owned(context, address_id), current
        ),
    }


@router.delete(
    "/me/shipping-addresses/{address_id}", operation_id="API-070", status_code=204
)
def remove(
    address_id: UUID,
    context: Authenticated,
    request: Request,
    expected_version: int = Query(ge=1, le=2147483646),
    expected_book_version: int = Query(ge=0, le=2147483646),
):
    guard(context, request, True)
    current = book(context)
    row = owned(context, address_id)
    if current["version"] != expected_book_version:
        fail(409, "VERSION_MISMATCH")
    mutable(context, row, expected_version)
    default_id = (
        None
        if current["default_address_id"] == address_id
        else current["default_address_id"]
    )
    current = advance(context, current, default_id)
    context.session.execute(
        text(
            "DELETE FROM public.shipping_addresses WHERE id=:id AND customer_user_id=:actor AND is_saved"
        ),
        {"id": address_id, "actor": context.principal.user_id},
    )
    audit(context, request, "shipping_address.delete", address_id)
    return Response(status_code=204)
