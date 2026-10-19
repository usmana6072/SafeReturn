"""HTTP input boundaries for shipment mutations and pagination."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.v1.fulfillment import ShipmentRequest, ShipmentUpdate, page_cursor


def test_shipment_requires_exact_pair_set_and_reason_fields():
    with pytest.raises(ValidationError):
        ShipmentRequest.model_validate(
            {
                "order_id": str(uuid4()),
                "shipping_address_id": str(uuid4()),
                "carrier": "Test",
            }
        )


@pytest.mark.parametrize("value", ["bad", "W10", "bnVsbA", "e30"])
def test_malformed_cursor_is_validation_error(value):
    with pytest.raises(HTTPException) as e:
        page_cursor(value)
    assert e.value.status_code == 422


@pytest.mark.parametrize(
    "extra",
    [
        {"packing_confirmed": "true"},
        {"status": "preparing"},
        {"expected_status": "returned"},
        {"owner_user_id": str(uuid4())},
    ],
)
def test_shipment_update_rejects_unsafe_types_states_and_extra_fields(extra):
    with pytest.raises(ValidationError):
        ShipmentUpdate.model_validate(
            {
                "status": "packed",
                "expected_status": "preparing",
                "reason": "Fixture reason",
                **extra,
            }
        )
