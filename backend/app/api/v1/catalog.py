"""Task 5.1 catalog. Operations is the existing delegated catalog role.

No new roles are provisioned. All reads are uncached, so publication changes are
visible on the next request. Physical approvals and Cloudinary are fail-closed.
"""

import hashlib
import json
import re
import time
from decimal import Decimal
from typing import Annotated, Literal
from urllib.parse import quote
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api.auth import AccessError, Authenticated, require_staff
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt, encrypt
from app.db.runtime import api_transaction


class CatalogRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handle(request):
            try:
                return await original(request)
            except (HTTPException, RequestValidationError) as error:
                status = error.status_code if isinstance(error, HTTPException) else 422
                code = (
                    error.detail["code"]
                    if isinstance(error, HTTPException)
                    else "VALIDATION_ERROR"
                )
                return JSONResponse(
                    status_code=status,
                    headers={"Cache-Control": "no-store"},
                    content={
                        "error": {
                            "code": code,
                            "message": "Catalog request could not be completed.",
                            "request_id": getattr(request.state, "request_id", None),
                            "details": {},
                        }
                    },
                )

        return handle


public_router = APIRouter(tags=["public catalog"], route_class=CatalogRoute)
admin_router = APIRouter(tags=["admin catalog"], route_class=CatalogRoute)


class Closed(BaseModel):
    model_config = ConfigDict(
        extra="forbid", hide_input_in_errors=True, str_strip_whitespace=True
    )

    @field_validator("*", mode="after")
    @classmethod
    def meaningful(cls, value):
        if isinstance(value, str) and not value.strip():
            raise ValueError("Must not be blank")
        return value


class CategoryRequest(Closed):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,59}$")
    name: str = Field(min_length=1, max_length=120)
    sort_order: int = Field(default=0, ge=-100000, le=100000, strict=True)
    is_active: bool = Field(default=True, strict=True)


class ProductRequest(Closed):
    category_id: UUID | None = None
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,99}$")
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    lifecycle_status: Literal["draft", "published", "archived"] = "draft"
    is_featured: bool = Field(default=False, strict=True)
    featured_sort_order: int = Field(default=0, ge=-100000, le=100000, strict=True)


class VariantRequest(Closed):
    sku: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{1,59}$")
    name: str = Field(min_length=1, max_length=160)
    size_mm: Decimal | None = Field(
        default=None, gt=0, le=99999, decimal_places=2, allow_inf_nan=False
    )
    material: str | None = Field(default=None, max_length=120)
    color: str | None = Field(default=None, max_length=80)
    unit_price: Decimal = Field(
        ge=0, le=Decimal("9999999999.99"), decimal_places=2, allow_inf_nan=False
    )
    fulfillment_method: Literal["pdf_label", "manufacturer_artwork", "manual"]
    template_key: str | None = Field(default=None, max_length=120)
    template_version: int = Field(default=1, ge=1, le=100000, strict=True)
    is_active: bool = Field(default=True, strict=True)
    sort_order: int = Field(default=0, ge=-100000, le=100000, strict=True)

    @field_validator("unit_price", mode="before")
    @classmethod
    def decimal_money(cls, value):
        if not isinstance(value, (str, Decimal)):
            raise ValueError("Money must be a decimal string")  # noqa: TRY004 - Pydantic validates ValueError, not TypeError
        return value


class ImageRequest(Closed):
    cloudinary_public_id: str = Field(pattern=r"^[A-Za-z0-9/_-]{1,240}$")
    alt_text: str = Field(min_length=1, max_length=240)
    sort_order: int = Field(default=0, ge=-100000, le=100000, strict=True)
    is_primary: bool = Field(default=False, strict=True)


def fail(status, code):
    raise HTTPException(status, detail={"code": code})


def public_catalog(request, response, sku=None):
    response.headers["Cache-Control"] = "no-store"
    database = request.app.state.database
    if database is None:
        raise AccessError(503)
    with api_transaction(database) as session:
        return (
            session.execute(
                text("SELECT public.sr_public_catalog(:sku)"), {"sku": sku}
            ).scalar_one()
            or []
        )


@public_router.get(
    "/public/products", operation_id="API-003", response_model=list[dict]
)
def list_products(
    request: Request,
    response: Response,
    category: str | None = None,
    limit: int = Query(default=100, ge=1, le=100),
    cursor: UUID | None = None,
):
    items = public_catalog(request, response)
    if category:
        items = [p for p in items if p["category"]["slug"] == category]
    if cursor:
        index = next(
            (i for i, p in enumerate(items) if p["product_id"] == str(cursor)), None
        )
        if index is None:
            fail(400, "INVALID_CURSOR")
        items = items[index + 1 :]
    return items[:limit]


@public_router.get(
    "/public/products/{sku}", operation_id="API-004", response_model=dict
)
def get_product(sku: str, request: Request, response: Response):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,59}", sku):
        raise AccessError(404)
    items = public_catalog(request, response, sku)
    if len(items) != 1:
        raise AccessError(404)
    return items[0]


@public_router.get("/public/catalog/featured", operation_id="API-201")
def featured(request: Request, response: Response):
    return {
        "items": [p for p in public_catalog(request, response) if p["featured"]][:100],
        "next_cursor": None,
    }


@public_router.get("/public/catalog/categories", operation_id="API-200")
def categories(request: Request, response: Response):
    items = public_catalog(request, response)
    return {"items": list({p["category"]["id"]: p["category"] for p in items}.values())}


@public_router.get(
    "/public/catalog/products/{product_id}/variants", operation_id="API-202"
)
def variants(product_id: UUID, request: Request, response: Response):
    for p in public_catalog(request, response):
        if p["product_id"] == str(product_id):
            return {"items": p["variants"], "catalog_version": p["catalog_version"]}
    raise AccessError(404)


def guard(context):
    require_staff(context, "operations", "security_admin", "superadmin")


def lock(context, table, identifier, match):
    row = (
        context.session.execute(
            text(f"SELECT * FROM public.{table} WHERE id=:id FOR UPDATE"),
            {"id": identifier},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise AccessError(404)
    if match != f'"{row["catalog_version"]}"':
        fail(412, "VERSION_MISMATCH")
    return dict(row)


def mutation(context, request, operation, body, work):
    guard(context)
    key = request.headers.get("idempotency-key", "")
    if not re.fullmatch(r"[A-Za-z0-9._:-]{8,160}", key):
        fail(400, "IDEMPOTENCY_KEY_REQUIRED")
    scope = str(context.principal.user_id)
    digest = hashlib.sha256(
        json.dumps(
            jsonable_encoder(body), sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    reference = hashlib.sha256(f"{scope}:{operation}:{key}".encode()).hexdigest()
    session = context.session
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
        {"key": reference},
    )
    params = {
        "actor": context.principal.user_id,
        "scope": scope,
        "op": operation,
        "key": key,
    }
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
    settings = request.app.state.settings
    if old:
        if old["request_hash"] != digest:
            fail(409, "IDEMPOTENCY_KEY_REUSED")
        try:
            return json.loads(
                decrypt(
                    settings,
                    context.principal.user_id,
                    "catalog:" + reference,
                    old["response_body_ciphertext"],
                    old["response_key_version"],
                )
            )
        except (ProfileCryptoUnavailable, ValueError):
            raise AccessError(503) from None
    try:
        with session.begin_nested():
            result, previous = work()
            result = jsonable_encoder(result, custom_encoder={Decimal: str})
            ciphertext, version = encrypt(
                settings,
                context.principal.user_id,
                "catalog:" + reference,
                json.dumps(result),
            )
            session.execute(
                text("""INSERT INTO public.idempotency_records(actor_scope,actor_user_id,operation,idempotency_key,request_hash,state,response_status,response_body_ciphertext,response_key_version,expires_at)
              VALUES(:scope,:actor,:op,:key,:hash,'completed',200,:cipher,:version,now()+interval '1 day')"""),
                {**params, "hash": digest, "cipher": ciphertext, "version": version},
            )
            session.execute(
                text("""INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,request_id,reason,safe_details)
            VALUES(:actor,'staff',:op,'catalog',:target,:request_id,'catalog management',CAST(:details AS jsonb))"""),
                {
                    "actor": context.principal.user_id,
                    "op": operation,
                    "target": result["id"],
                    "request_id": getattr(request.state, "request_id", None),
                    "details": json.dumps(
                        {
                            "event_id": reference,
                            "version": result.get("catalog_version"),
                            "from_status": (previous or {}).get("lifecycle_status"),
                            "to_status": result.get("lifecycle_status"),
                            "outcome": "success",
                        }
                    ),
                },
            )
            return result
    except IntegrityError:
        fail(409, "CATALOG_CONFLICT")
    except ProfileCryptoUnavailable:
        raise AccessError(503) from None


def insert(context, table, values):
    columns = ",".join(values)
    bindings = ",".join(":" + k for k in values)
    return dict(
        context.session.execute(
            text(
                f"INSERT INTO public.{table}({columns}) VALUES({bindings}) RETURNING *"
            ),
            values,
        )
        .mappings()
        .one()
    )


def update(context, table, identifier, values):
    setters = ",".join(f"{k}=:{k}" for k in values)
    return dict(
        context.session.execute(
            text(
                f"UPDATE public.{table} SET {setters},catalog_version=catalog_version+1 WHERE id=:identifier RETURNING *"
            ),
            {**values, "identifier": identifier},
        )
        .mappings()
        .one()
    )


def publishable(context, request, product):
    if product["lifecycle_status"] != "published":
        return
    session = context.session
    category = (
        session.execute(
            text(
                "SELECT slug,is_active FROM public.product_categories WHERE id=:id FOR SHARE"
            ),
            {"id": product["category_id"]},
        )
        .mappings()
        .one_or_none()
    )
    if not category or category["slug"] != "qr-stickers" or not category["is_active"]:
        fail(422, "FUTURE_PRODUCT_DISABLED")
    variants = (
        session.execute(
            text(
                "SELECT * FROM public.product_variants WHERE product_id=:id AND is_active"
            ),
            {"id": product["id"]},
        )
        .mappings()
        .all()
    )
    approved = request.app.state.settings.catalog_approved_templates
    if not variants or any(
        v["fulfillment_method"] != "pdf_label"
        or v["size_mm"] is None
        or v["size_mm"] < 30
        or v["currency_code"] != "PKR"
        or f"{v['template_key']}@{v['template_version']}" not in approved
        for v in variants
    ):
        fail(422, "PHYSICAL_CATALOG_APPROVAL_REQUIRED")
    if not session.execute(
        text(
            "SELECT 1 FROM public.product_images WHERE product_id=:id AND verified_public_url IS NOT NULL LIMIT 1"
        ),
        {"id": product["id"]},
    ).scalar_one_or_none():
        fail(422, "VERIFIED_PUBLIC_IMAGE_REQUIRED")


def upload_authorization(settings, product_id, version):
    if (
        not settings.cloudinary_cloud_name
        or not settings.cloudinary_api_key
        or not settings.cloudinary_api_secret
        or not settings.cloudinary_upload_preset
    ):
        raise AccessError(503)
    public_id = f"{settings.cloudinary_public_folder}{product_id}/{uuid4().hex}"
    params = {
        "timestamp": str(int(time.time())),
        "public_id": public_id,
        "overwrite": "false",
        "allowed_formats": "png,jpg,jpeg,webp,avif",
        "type": "upload",
        "upload_preset": settings.cloudinary_upload_preset,
    }
    canonical = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    signature = hashlib.sha256(
        (canonical + settings.cloudinary_api_secret.get_secret_value()).encode()
    ).hexdigest()
    return {
        "id": str(product_id),
        "catalog_version": version,
        "public_id": public_id,
        "upload_url": f"https://api.cloudinary.com/v1_1/{settings.cloudinary_cloud_name}/image/upload",
        "upload_params": {
            **params,
            "signature": signature,
            "api_key": settings.cloudinary_api_key.get_secret_value(),
        },
        "expires_at": int(params["timestamp"]) + 3600,
    }


def verified_asset(settings, public_id):
    if (
        not settings.cloudinary_cloud_name
        or not settings.cloudinary_api_key
        or not settings.cloudinary_api_secret
    ):
        raise AccessError(503)
    if not public_id.startswith(settings.cloudinary_public_folder) or "//" in public_id:
        fail(422, "PUBLIC_ASSET_FOLDER_REQUIRED")
    try:
        r = httpx.get(
            f"https://api.cloudinary.com/v1_1/{settings.cloudinary_cloud_name}/resources/image/upload/{quote(public_id, safe='')}",
            auth=(
                settings.cloudinary_api_key.get_secret_value(),
                settings.cloudinary_api_secret.get_secret_value(),
            ),
            timeout=5,
            follow_redirects=False,
        )
        if r.status_code != 200:
            raise AccessError(503)
        asset = r.json()
        if (
            asset.get("public_id") != public_id
            or asset.get("resource_type") != "image"
            or asset.get("type") != "upload"
            or asset.get("format") not in {"png", "jpg", "jpeg", "webp", "avif"}
            or not isinstance(asset.get("bytes"), int)
            or not 0 < asset["bytes"] <= 5 * 1024 * 1024
            or asset.get("access_control")
            or asset.get("access_mode", "public") != "public"
            or not asset.get("version")
        ):
            fail(422, "INVALID_PUBLIC_ASSET")
        return f"https://res.cloudinary.com/{settings.cloudinary_cloud_name}/image/upload/v{int(asset['version'])}/{public_id}.{asset['format']}"
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise AccessError(503) from None


@admin_router.get("/admin/products", operation_id="API-220")
def admin_products(
    context: Authenticated,
    limit: int = Query(100, ge=1, le=100),
    cursor: UUID | None = None,
):
    guard(context)
    rows = (
        context.session.execute(
            text(
                "SELECT * FROM public.products WHERE (CAST(:cursor AS uuid) IS NULL OR id>:cursor) ORDER BY id LIMIT :limit"
            ),
            {"cursor": cursor, "limit": limit + 1},
        )
        .mappings()
        .all()
    )
    items = []
    for row in rows[:limit]:
        item = dict(row)
        for key, table in (
            ("variants", "product_variants"),
            ("images", "product_images"),
        ):
            item[key] = [
                dict(r)
                for r in context.session.execute(
                    text(
                        f"SELECT * FROM public.{table} WHERE product_id=:id ORDER BY id"
                    ),
                    {"id": row["id"]},
                ).mappings()
            ]
        items.append(jsonable_encoder(item, custom_encoder={Decimal: str}))
    return {
        "items": items,
        "next_cursor": str(rows[limit - 1]["id"]) if len(rows) > limit else None,
    }


@admin_router.get("/admin/catalog/categories", operation_id="API-227")
def admin_categories(context: Authenticated):
    guard(context)
    return {
        "items": [
            dict(r)
            for r in context.session.execute(
                text(
                    "SELECT * FROM public.product_categories ORDER BY sort_order,id LIMIT 100"
                )
            ).mappings()
        ]
    }


@admin_router.post("/admin/catalog/categories", operation_id="API-228", status_code=201)
def create_category(body: CategoryRequest, request: Request, context: Authenticated):
    return mutation(
        context,
        request,
        "catalog.category.create",
        body.model_dump(),
        lambda: (insert(context, "product_categories", body.model_dump()), None),
    )


@admin_router.patch("/admin/catalog/categories/{category_id}", operation_id="API-229")
def edit_category(
    category_id: UUID,
    body: CategoryRequest,
    request: Request,
    context: Authenticated,
    if_match: Annotated[str | None, Header()] = None,
):
    def work():
        old = lock(context, "product_categories", category_id, if_match)
        return update(
            context, "product_categories", category_id, body.model_dump()
        ), jsonable_encoder(old)

    return mutation(
        context,
        request,
        "catalog.category.edit",
        {**body.model_dump(), "id": category_id, "version": if_match},
        work,
    )


@admin_router.post("/admin/products", operation_id="API-221", status_code=201)
def create_product(body: ProductRequest, request: Request, context: Authenticated):
    def work():
        if body.lifecycle_status != "draft":
            fail(422, "CREATE_AS_DRAFT")
        return insert(context, "products", body.model_dump()), None

    return mutation(context, request, "catalog.product.create", body.model_dump(), work)


@admin_router.patch("/admin/products/{product_id}", operation_id="API-222")
def edit_product(
    product_id: UUID,
    body: ProductRequest,
    request: Request,
    context: Authenticated,
    if_match: Annotated[str | None, Header()] = None,
):
    def work():
        old = lock(context, "products", product_id, if_match)
        if (
            old["lifecycle_status"] == "archived"
            and body.lifecycle_status != "archived"
        ):
            fail(422, "ARCHIVED_PRODUCT")
        row = update(context, "products", product_id, body.model_dump())
        publishable(context, request, row)
        return row, jsonable_encoder(old)

    return mutation(
        context,
        request,
        "catalog.product.edit",
        {**body.model_dump(), "id": product_id, "version": if_match},
        work,
    )


@admin_router.post(
    "/admin/products/{product_id}/variants", operation_id="API-223", status_code=201
)
def create_variant(
    product_id: UUID,
    body: VariantRequest,
    request: Request,
    context: Authenticated,
    if_match: Annotated[str | None, Header()] = None,
):
    def work():
        parent = lock(context, "products", product_id, if_match)
        row = insert(
            context, "product_variants", {**body.model_dump(), "product_id": product_id}
        )
        update(context, "products", product_id, {"name": parent["name"]})
        publishable(context, request, parent)
        return row, None

    return mutation(
        context,
        request,
        "catalog.variant.create",
        {**body.model_dump(), "id": product_id, "version": if_match},
        work,
    )


@admin_router.patch("/admin/product-variants/{variant_id}", operation_id="API-224")
def edit_variant(
    variant_id: UUID,
    body: VariantRequest,
    request: Request,
    context: Authenticated,
    if_match: Annotated[str | None, Header()] = None,
):
    def work():
        pid = context.session.execute(
            text("SELECT product_id FROM public.product_variants WHERE id=:id"),
            {"id": variant_id},
        ).scalar_one_or_none()
        if pid is None:
            raise AccessError(404)
        parent = dict(
            context.session.execute(
                text("SELECT * FROM public.products WHERE id=:id FOR UPDATE"),
                {"id": pid},
            )
            .mappings()
            .one()
        )
        old = lock(context, "product_variants", variant_id, if_match)
        row = update(context, "product_variants", variant_id, body.model_dump())
        update(context, "products", pid, {"name": parent["name"]})
        publishable(context, request, parent)
        return row, jsonable_encoder(old)

    return mutation(
        context,
        request,
        "catalog.variant.edit",
        {**body.model_dump(), "id": variant_id, "version": if_match},
        work,
    )


@admin_router.post(
    "/admin/products/{product_id}/images", operation_id="API-225", status_code=201
)
def create_image(
    product_id: UUID,
    body: ImageRequest,
    request: Request,
    context: Authenticated,
    if_match: Annotated[str | None, Header()] = None,
    authorize_upload: bool = False,
):
    def work():
        if authorize_upload:
            parent = lock(context, "products", product_id, if_match)
            return upload_authorization(
                request.app.state.settings, product_id, parent["catalog_version"]
            ), None
        # Replay is resolved first; provider HTTP holds no catalog row locks.
        url = verified_asset(request.app.state.settings, body.cloudinary_public_id)
        parent = lock(context, "products", product_id, if_match)
        if body.is_primary:
            context.session.execute(
                text(
                    "UPDATE public.product_images SET is_primary=false WHERE product_id=:id"
                ),
                {"id": product_id},
            )
        row = insert(
            context,
            "product_images",
            {**body.model_dump(), "product_id": product_id, "verified_public_url": url},
        )
        update(context, "products", product_id, {"name": parent["name"]})
        return row, None

    return mutation(
        context,
        request,
        "catalog.image.authorize" if authorize_upload else "catalog.image.create",
        {**body.model_dump(), "id": product_id, "version": if_match},
        work,
    )


@admin_router.delete(
    "/admin/products/{product_id}/images/{image_id}", operation_id="API-226"
)
def unlink_image(
    product_id: UUID,
    image_id: UUID,
    request: Request,
    context: Authenticated,
    if_match: Annotated[str | None, Header()] = None,
):
    def work():
        parent = lock(context, "products", product_id, if_match)
        row = (
            context.session.execute(
                text(
                    "DELETE FROM public.product_images WHERE id=:id AND product_id=:pid RETURNING *"
                ),
                {"id": image_id, "pid": product_id},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise AccessError(404)
        update(context, "products", product_id, {"name": parent["name"]})
        publishable(context, request, parent)
        return dict(row), dict(row)

    return mutation(
        context,
        request,
        "catalog.image.unlink",
        {"id": image_id, "product": product_id, "version": if_match},
        work,
    )
