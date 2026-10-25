"""Phase 3 DTO/orchestration checks, not PostgreSQL RLS or commit evidence."""

from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.v1 import catalog


def request_body(**changes):
    return catalog.ProductRequest(
        name="Sticker",
        slug="sticker",
        price_per_copy="12.30",
        qr_type="lost",
        **changes,
    )


@pytest.fixture
def context(monkeypatch):
    ctx = SimpleNamespace(session=MagicMock())
    req = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                settings=SimpleNamespace(catalog_approved_templates=["approved@1"])
            )
        )
    )
    # Exercise production work functions; receipts/auth/transaction coverage is elsewhere.
    monkeypatch.setattr(
        catalog, "mutation", lambda ctx, req, op, payload, work: work()[0]
    )
    return ctx, req


def test_new_product_requires_explicit_type_and_cannot_mint_legacy_product(
    context, monkeypatch
):
    ctx, req = context
    inserted = []
    monkeypatch.setattr(
        catalog,
        "insert",
        lambda ctx, table, body: inserted.append(body) or {"id": uuid4(), **body},
    )
    result = catalog.create_product(request_body(), req, ctx)
    assert (
        result["commerce_model"] == "single_qr" and result["allows_new_pair"] is False
    )
    assert result["qr_type"] == "lost" and result["price_per_copy"] == Decimal("12.30")
    with pytest.raises(HTTPException) as error:
        catalog.create_product(
            catalog.ProductRequest(name="Old", slug="old", price_per_copy="1.00"),
            req,
            ctx,
        )
    assert error.value.detail["code"] == "QR_TYPE_REQUIRED" and len(inserted) == 1


def test_create_dto_requires_type_while_legacy_edit_dto_can_retain_null():
    with pytest.raises(ValidationError):
        catalog.CreateProductRequest(
            name="Sticker", slug="sticker", price_per_copy="1.00"
        )
    assert (
        catalog.ProductRequest(
            name="Legacy", slug="legacy", price_per_copy="1.00"
        ).qr_type
        is None
    )


@pytest.mark.parametrize("qr_type", ["both", "emergency", 1, True])
def test_invalid_type_is_not_coerced(qr_type):
    with pytest.raises(ValidationError):
        catalog.ProductRequest(
            name="Sticker", slug="sticker", price_per_copy="1.00", qr_type=qr_type
        )


def test_legacy_edit_cannot_silently_convert_identity_model(context, monkeypatch):
    ctx, req = context
    monkeypatch.setattr(
        catalog,
        "lock",
        lambda *args: {
            "lifecycle_status": "draft",
            "commerce_model": "legacy_pair",
            "qr_type": None,
        },
    )
    with pytest.raises(HTTPException) as error:
        catalog.edit_product(uuid4(), request_body(), req, ctx, '"1"')
    assert error.value.detail["code"] == "LEGACY_PRODUCT_TYPE"


def publication(context, monkeypatch, *, eligible=True, image=True, duplicate=False):
    ctx, req = context
    variant = {
        "id": uuid4(),
        "fulfillment_method": "pdf_label",
        "size_mm": Decimal(35),
        "currency_code": "PKR",
        "template_key": "approved",
        "template_version": 1,
    }
    variants = [variant, {**variant, "id": uuid4()}] if duplicate else [variant]
    queries = []

    def execute(sql, params=None):
        value = MagicMock()
        queries.append(str(sql))
        value.mappings.return_value.one_or_none.return_value = {
            "slug": "qr-stickers",
            "is_active": True,
        }
        value.mappings.return_value.all.return_value = variants
        value.scalar_one_or_none.return_value = 1 if image else None
        return value

    ctx.session.execute.side_effect = execute
    seen = []
    monkeypatch.setattr(
        "app.db.template_registry.catalog_eligibility",
        lambda session, vid, kind: seen.append(kind) or eligible,
    )
    product = {
        "id": uuid4(),
        "commerce_model": "single_qr",
        "qr_type": "ice",
        "lifecycle_status": "published",
        "category_id": uuid4(),
    }
    return ctx, req, product, seen, queries


def test_publication_requires_matching_type_approval_and_main_image(
    context, monkeypatch
):
    ctx, req, product, seen, queries = publication(context, monkeypatch)
    catalog.publishable(ctx, req, product)
    assert seen == ["ice"]
    assert any("AND is_primary" in sql for sql in queries)


@pytest.mark.parametrize(
    "eligible,image,duplicate,code",
    [
        (None, True, False, "QR_TYPE_TEMPLATE_APPROVAL_REQUIRED"),
        (False, True, False, "QR_TYPE_TEMPLATE_APPROVAL_REQUIRED"),
        (True, False, False, "VERIFIED_PUBLIC_IMAGE_REQUIRED"),
        (True, True, True, "DUPLICATE_SIZE"),
    ],
)
def test_publication_cannot_bypass_approval_with_configured_key(
    context, monkeypatch, eligible, image, duplicate, code
):
    ctx, req, product, _, _ = publication(
        context, monkeypatch, eligible=eligible, image=image, duplicate=duplicate
    )
    with pytest.raises(HTTPException) as error:
        catalog.publishable(ctx, req, product)
    assert error.value.detail["code"] == code


def test_image_metadata_cannot_rebind_storage_or_product():
    with pytest.raises(ValidationError):
        catalog.ImageMetadataRequest(
            alt_text="Photo", is_primary=True, cloudinary_public_id="forged"
        )


def test_new_catalog_isolated_from_legacy_public_and_checkout_queries():
    sql = (
        Path(__file__).parents[1] / "alembic/versions/0039_single_qr_catalog.sql"
    ).read_text(encoding="utf-8")
    assert sql.count("p.commerce_model='legacy_pair'") == 2
    assert "DEFERRABLE INITIALLY DEFERRED" in sql
    assert "qr_type IS NOT NULL" in sql
    assert "GRANT INSERT" not in sql
    assert "UPDATE public.order_items" not in sql


def test_stale_product_version_refuses_before_writing():
    ctx = SimpleNamespace(session=MagicMock())
    ctx.session.execute.return_value.mappings.return_value.one_or_none.return_value = {
        "catalog_version": 2
    }
    with pytest.raises(HTTPException) as error:
        catalog.lock(ctx, "products", uuid4(), '"1"')
    assert error.value.status_code == 412
    assert ctx.session.execute.call_count == 1


def test_image_primary_change_scoped_to_product_and_versions_parent(
    context, monkeypatch
):
    ctx, req = context
    pid, iid = uuid4(), uuid4()
    parent = {
        "id": pid,
        "name": "Sticker",
        "catalog_version": 3,
        "lifecycle_status": "draft",
    }
    monkeypatch.setattr(catalog, "lock", lambda *args: parent)
    updates = []
    monkeypatch.setattr(
        catalog,
        "update",
        lambda ctx, table, target, values: updates.append((table, target, values)),
    )
    monkeypatch.setattr(catalog, "publishable", lambda *args: None)
    old = {
        "id": iid,
        "product_id": pid,
        "alt_text": "Photo",
        "sort_order": 0,
        "is_primary": False,
    }
    statements = []

    def execute(statement, params):
        sql = str(statement)
        statements.append((sql, params))
        value = MagicMock()
        value.mappings.return_value.one_or_none.return_value = old
        value.mappings.return_value.one.return_value = {**old, "is_primary": True}
        return value

    ctx.session.execute.side_effect = execute
    result = catalog.edit_image(
        pid,
        iid,
        catalog.ImageMetadataRequest(alt_text="Photo", is_primary=True),
        req,
        ctx,
        '"3"',
    )
    assert result["is_primary"] is True
    assert updates == [("products", pid, {"name": "Sticker"})]
    assert all(args.get("pid") == pid for _, args in statements)
    assert all("product_id=:pid" in sql for sql, _ in statements)


def test_product_detail_does_not_return_demo_or_truncated_list(context, monkeypatch):
    ctx, _ = context
    monkeypatch.setattr(catalog, "guard", lambda *args: None)
    ctx.session.execute.return_value.mappings.return_value.one_or_none.return_value = (
        None
    )
    from app.api.auth import AccessError

    with pytest.raises(AccessError) as error:
        catalog.admin_product_detail(uuid4(), ctx)
    assert error.value.status == 404
