"""Checkout input contracts: no database or provider calls."""

import pytest
from pydantic import ValidationError

from app.api.v1.checkout import Address, CartLine, ConfirmRequest, QRUse


@pytest.mark.parametrize("copies", [0, 101, True, 1.5, "3"])
def test_counts_are_bounded_strict_integers(copies):
    with pytest.raises(ValidationError):
        QRUse(mode="new_pair", tag_type="lost", copies=copies, client_pair_group="one")


@pytest.mark.parametrize(
    "total", [1.23, "NaN", "Infinity", "-1.00", "1.001", "10000000000.00"]
)
def test_confirmation_requires_exact_money_string(total):
    with pytest.raises(ValidationError):
        ConfirmRequest(accept_total=total, accept_currency="PKR")


def test_private_address_validation_and_extra_fields():
    with pytest.raises(ValidationError):
        Address(
            recipient_name="Name",
            phone="+۹۲۳۰۰۱۲۳۴۵۶۷",
            address="Street",
            city="Lahore",
        )
    with pytest.raises(ValidationError):
        Address(
            recipient_name="Name", phone="+923001234567", address="   ", city="Lahore"
        )
    with pytest.raises(ValidationError):
        ConfirmRequest(
            accept_total="1.00", accept_currency="PKR", owner_user_id="forged"
        )


def test_modes_and_quantity_must_match():
    with pytest.raises(ValidationError):
        QRUse(mode="new_pair", tag_type="ice", copies=1)
    with pytest.raises(ValidationError):
        QRUse(
            mode="existing_owned", tag_type="ice", copies=1, client_pair_group="forged"
        )
    with pytest.raises(ValidationError):
        CartLine(
            variant_id="00000000-0000-4000-8000-000000000001",
            quantity=3,
            qr_uses=[
                {
                    "mode": "new_pair",
                    "tag_type": "lost",
                    "copies": 2,
                    "client_pair_group": "one",
                }
            ],
        )


@pytest.mark.parametrize("verified,expected", [(True, 409), (False, 403)])
def test_legacy_order_request_cannot_run_an_independent_writer(verified, expected):
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    from test_health import ASGIClient

    from app.api.auth import get_auth_context
    from app.core.config import Settings
    from app.main import create_app

    app = create_app(Settings())
    session = MagicMock()
    app.dependency_overrides[get_auth_context] = lambda: SimpleNamespace(
        email_verified=verified, session=session
    )
    r = ASGIClient(app).post(
        "/api/v1/me/orders",
        json={"total_pkr": "0.01", "owner_user_id": "FORGED-PRIVATE-INPUT"},
    )
    assert r.status_code == expected
    assert "FORGED-PRIVATE-INPUT" not in r.text
    if verified:
        assert r.json()["error"]["code"] == "QUOTE_REQUIRED"
    session.execute.assert_not_called()


def test_legacy_order_requires_authentication():
    from test_health import ASGIClient

    from app.core.config import Settings
    from app.main import create_app

    assert (
        ASGIClient(create_app(Settings()))
        .post("/api/v1/me/orders", json={})
        .status_code
        == 401
    )
