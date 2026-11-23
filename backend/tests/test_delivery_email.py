from unittest.mock import patch

import httpx

from app.api.v1.fulfillment import ShipmentForOrder, ShipmentUpdate
from app.core.config import Settings
from app.workers.notifications import (
    DELIVERY_FROM_EMAIL,
    BrevoProvider,
    delivery_email_html,
)


def payload():
    return {
        "order_id": "00000000-0000-4000-8000-000000000001",
        "order_number": "SR-TEST",
        "delivered_at": "2026-11-21T12:30:00+00:00",
        "carrier": "Courier",
        "tracking_reference": "PK-123",
        "items": [{"product_name_snapshot": "Lost QR", "quantity": 2}],
    }


def test_received_by_is_optional_and_escaped_in_email():
    data = payload()
    assert "Received by" not in delivery_email_html(data)
    data["received_by"] = '<script>alert("x")</script>'
    html = delivery_email_html(data)
    assert "Received by" in html and "&lt;script&gt;" in html and "<script>" not in html
    for value in ("SR-TEST", "PK-123", "Lost QR", "services@safereturnqr.me"):
        assert value in html


def test_create_does_not_require_tracking_and_delivery_does_not_require_note_or_receiver():
    assert ShipmentForOrder(carrier="Courier").tracking_reference is None
    value = ShipmentUpdate(status="delivered", expected_status="dispatched")
    assert value.received_by is None
    assert value.reason == "Courier confirmed delivery"


@patch("app.workers.notifications.httpx.post")
def test_delivery_email_uses_requested_domain_sender(mock_post):
    mock_post.return_value = httpx.Response(200, json={"messageId": "delivery-1"})
    settings = Settings(
        brevo_api_key="synthetic", notification_from_email="old@example.test"
    )
    BrevoProvider(settings).send(
        to="buyer@example.test",
        subject="Delivered",
        html=delivery_email_html(payload()),
        idempotency_key="shipment-delivered:1",
        from_email=DELIVERY_FROM_EMAIL,
    )
    assert (
        mock_post.call_args.kwargs["json"]["sender"]
        == {"email": "services@safereturnqr.me", "name": "SafeReturn"}
    )
