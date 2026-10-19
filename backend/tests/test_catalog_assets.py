"""Fixed-host public asset verification: controlled provider responses only."""

import httpx
import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from app.api.auth import AccessError
from app.api.v1.catalog import VariantRequest, verified_asset
from app.core.config import Settings


def settings():
    return Settings(
        cloudinary_cloud_name="synthetic",
        cloudinary_api_key=SecretStr("fixture-key"),
        cloudinary_api_secret=SecretStr("fixture-secret"),
    )


def test_asset_verification_fails_closed():
    with pytest.raises(AccessError):
        verified_asset(Settings(), "safereturn/catalog/test")
    with pytest.raises(HTTPException):
        verified_asset(settings(), "private-order-print/test")


@pytest.mark.parametrize(
    "change",
    [
        {},
        {"type": "private"},
        {"resource_type": "raw"},
        {"format": "svg"},
        {"public_id": "other"},
        {"access_control": [{"access_type": "token"}]},
        {"bytes": 0},
        {"bytes": 5242881},
    ],
)
def test_only_controlled_public_raster_assets(monkeypatch, change):
    asset = {
        "public_id": "safereturn/catalog/test",
        "resource_type": "image",
        "type": "upload",
        "format": "png",
        "version": 123,
        "bytes": 100,
        **change,
    }

    def get(url, **kwargs):
        assert (
            url
            == "https://api.cloudinary.com/v1_1/synthetic/resources/image/upload/safereturn%2Fcatalog%2Ftest"
        )
        assert kwargs["follow_redirects"] is False and kwargs["timeout"] == 5
        return httpx.Response(200, json=asset)

    monkeypatch.setattr(httpx, "get", get)
    if change:
        with pytest.raises(HTTPException):
            verified_asset(settings(), "safereturn/catalog/test")
    else:
        assert (
            verified_asset(settings(), "safereturn/catalog/test")
            == "https://res.cloudinary.com/synthetic/image/upload/v123/safereturn/catalog/test.png"
        )


@pytest.mark.parametrize(
    "price", ["NaN", "Infinity", "-1", "0.001", "10000000000.00", 1.23, True]
)
def test_invalid_decimal_prices(price):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        VariantRequest(
            sku="valid-sku",
            name="Name",
            unit_price=price,
            fulfillment_method="pdf_label",
        )


def test_signed_upload_scopes_and_secret_separation(monkeypatch):
    import hashlib
    from uuid import uuid4

    from app.api.v1.catalog import upload_authorization

    config = settings()
    config.cloudinary_upload_preset = "bounded-public-raster"
    monkeypatch.setattr("app.api.v1.catalog.time.time", lambda: 1234567890)
    pid = uuid4()
    grant = upload_authorization(config, pid, 3)
    assert grant["public_id"].startswith(f"safereturn/catalog/{pid}/")
    assert grant["upload_params"]["overwrite"] == "false"
    params = {
        k: v
        for k, v in grant["upload_params"].items()
        if k not in {"api_key", "signature"}
    }
    expected = hashlib.sha256(
        (
            "&".join(f"{k}={v}" for k, v in sorted(params.items())) + "fixture-secret"
        ).encode()
    ).hexdigest()
    assert grant["upload_params"]["signature"] == expected
    assert "fixture-secret" not in str(grant)
    assert grant["expires_at"] == 1234571490
    with pytest.raises(AccessError):
        upload_authorization(settings(), pid, 1)
