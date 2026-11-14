"""Read-only catalog metadata orchestration; no database or release writes."""
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import Response

from app.api.v1 import catalog


@pytest.mark.parametrize("released,instructions,expected", [
    (False, False, ["SINGLE_QR_CHECKOUT_NOT_RELEASED", "PAYMENT_INSTRUCTIONS_UNAVAILABLE"]),
    (False, True, ["SINGLE_QR_CHECKOUT_NOT_RELEASED"]),
    (True, False, ["PAYMENT_INSTRUCTIONS_UNAVAILABLE"]),
    (True, True, []),
])
@pytest.mark.parametrize("available", [True, False])
def test_catalog_reports_gates_without_enabling_ineligible_products(monkeypatch, released, instructions, expected, available):
    session = MagicMock()
    products = [{"commerce_model": "single_qr", "checkout_available": available},
                {"commerce_model": "legacy_pair", "checkout_available": True}]
    session.execute.return_value.scalar_one.return_value = products
    session.execute.return_value.mappings.return_value.one.return_value = {
        "released": released, "instructions": instructions,
    }

    @contextmanager
    def transaction(database):
        yield session

    monkeypatch.setattr(catalog, "api_transaction", transaction)
    settings = SimpleNamespace(checkout_enabled=True, checkout_shipping_pkr=0, checkout_tax_pkr=0)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(database=object(), settings=settings)))
    response = Response()
    result = catalog.public_catalog(request, response)
    assert result[0]["checkout_available"] is (available and released and instructions)
    assert result[0]["checkout_unavailable_reasons"] == (expected or ([] if available else ["PRODUCT_UNAVAILABLE"]))
    assert result[1] == {"commerce_model": "legacy_pair", "checkout_available": True}
    assert response.headers["Cache-Control"] == "no-store"
    assert "bank_name" not in str(result)
    assert session.execute.call_count == 2
    assert all(str(call.args[0]).strip().startswith("SELECT") for call in session.execute.call_args_list)
