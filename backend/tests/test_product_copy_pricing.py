"""v1.4 pricing boundaries with synthetic sessions; no database/provider I/O."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.v1.catalog import ProductRequest
from app.api.v1.checkout import CartLine, catalog_lines


@pytest.mark.parametrize(
    "price", [None, True, 1.5, "-0.01", "0.001", "NaN", "Infinity", "10000000000.00"]
)
def test_product_rejects_invalid_price(price):
    with pytest.raises(ValidationError):
        ProductRequest(name="Sticker", slug="sticker", price_per_copy=price)


def test_price_required_and_exact_decimal():
    with pytest.raises(ValidationError):
        ProductRequest(name="Sticker", slug="sticker")
    assert ProductRequest(
        name="Sticker", slug="sticker", price_per_copy="12.30"
    ).price_per_copy == Decimal("12.30")


@pytest.mark.parametrize("limit", [0, 101, True, "5", 1.5])
def test_strict_combined_copy_limit(limit):
    with pytest.raises(ValidationError):
        ProductRequest(
            name="Sticker",
            slug="sticker",
            price_per_copy="1.00",
            max_order_copies=limit,
        )


def pricing(monkeypatch, quantities=(2, 3), limit=5, price="12.30"):
    import app.db.template_registry as registry

    monkeypatch.setattr(registry, "resolve", lambda *args: None)
    monkeypatch.setattr(registry, "attach_quote_specs", lambda *args: None)
    rows = []
    lines = []
    for n, (tag, qty) in enumerate(zip(("lost", "ice"), quantities, strict=True), 1):
        rows.append(
            {
                "id": str(UUID(int=n)),
                "product_id": str(UUID(int=10)),
                "sku": f"SIZE-{n}",
                "product_name": "Sticker",
                "name": f"Size {n}",
                "size_mm": str(30 + n),
                "material": "Vinyl",
                "fulfillment_method": "pdf_label",
                "template_key": "approved",
                "template_version": 1,
                "unit_price": "999.99",
                "price_per_copy": price,
                "max_order_copies": limit,
                "product_version": 1,
                "catalog_version": 1,
                "allows_new_pair": True,
            }
        )
        lines.append(
            CartLine(
                variant_id=UUID(int=n),
                quantity=qty,
                qr_uses=[
                    {
                        "mode": "new_pair",
                        "tag_type": tag,
                        "copies": qty,
                        "client_pair_group": "one",
                    }
                ],
            )
        )
    session = MagicMock()
    session.execute.return_value.scalar_one.return_value = rows
    context = SimpleNamespace(session=session)
    settings = SimpleNamespace(
        catalog_approved_templates=["approved@1"],
        checkout_shipping_pkr=Decimal(0),
        checkout_tax_pkr=Decimal(0),
    )
    return catalog_lines(context, lines, settings)


def test_sizes_share_product_price_and_snapshot_exact_totals(monkeypatch):
    snapshots, subtotal, _ = pricing(monkeypatch)
    assert subtotal == Decimal("61.50")
    assert [r["unit_price"] for r in snapshots] == ["12.30", "12.30"]
    assert [r["line_total"] for r in snapshots] == ["24.60", "36.90"]
    assert sum(r["quantity"] for r in snapshots) == 5


def test_combined_limit_cannot_be_bypassed_with_size_lines(monkeypatch):
    with pytest.raises(HTTPException) as error:
        pricing(monkeypatch, quantities=(3, 3))
    assert error.value.detail["code"] == "MAX_ORDER_COPIES_EXCEEDED"


def test_legacy_product_requires_explicit_admin_price(monkeypatch):
    with pytest.raises(HTTPException) as error:
        pricing(monkeypatch, price=None)
    assert error.value.detail["code"] == "PRODUCT_PRICE_REQUIRED"


def test_zero_price_uses_exact_arithmetic(monkeypatch):
    assert pricing(monkeypatch, price="0.00")[1] == Decimal("0.00")


@pytest.mark.parametrize(
    "field",
    [
        "price_per_copy",
        "unit_price",
        "unit_price_snapshot",
        "line_total",
        "subtotal_pkr",
    ],
)
def test_customer_price_overrides_rejected(field):
    with pytest.raises(ValidationError):
        CartLine(
            variant_id=UUID(int=1),
            quantity=1,
            qr_uses=[
                {
                    "mode": "new_pair",
                    "tag_type": "lost",
                    "copies": 1,
                    "client_pair_group": "one",
                }
            ],
            **{field: "0.01"},
        )
