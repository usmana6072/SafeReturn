import base64
import json
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

from pydantic import SecretStr

from app.core.config import Settings
from app.core.profile_crypto import encrypt
from app.workers.notifications import (
    ClaimedNotification,
    finder_email_html,
    process_one,
)


def sample():
    settings = Settings(
        profile_data_keys=SecretStr(
            json.dumps({"1": base64.b64encode(b"x" * 32).decode()})
        )
    )
    qr, mid = uuid4(), uuid4()
    row = {
        "qr_id": qr,
        "finder_name": '<img src=x onerror="bad()">',
        "preferred_contact": "phone",
        "submitted_at": datetime(2026, 11, 19, tzinfo=UTC),
        "finder_contact_key_version": 1,
        "message_key_version": 1,
        "location_key_version": 1,
        "accuracy_m": 12,
    }
    for field, value in {
        "finder_email": "finder@example.test",
        "finder_phone": "+923001234567",
        "message_text": "Found your bag.\n<script>bad()</script>",
        "latitude": "31.5",
        "longitude": "74.3",
    }.items():
        aad = {
            "message_text": "finder_message",
            "latitude": "finder_latitude",
            "longitude": "finder_longitude",
        }.get(field, field)
        row[field + "_ciphertext"] = encrypt(settings, qr, aad, value)[0]
    now = datetime.now(UTC)
    claimed = ClaimedNotification(
        uuid4(),
        mid,
        encrypt(settings, mid, "owner_email", "owner@example.test")[0],
        1,
        "finder-message:" + str(mid),
        1,
        now,
        now + timedelta(seconds=60),
    )
    return settings, row, claimed


def test_structured_finder_email_escapes_input_and_contains_contact_and_location():
    settings, row, claimed = sample()
    html = finder_email_html(settings, claimed, row)
    for value in [
        "finder@example.test",
        "+923001234567",
        "phone",
        "Found your bag.",
        "2026-11-19 00:00 UTC",
        "https://www.google.com/maps?q=31.5,74.3",
        f"/inbox/{claimed.aggregate_id}",
    ]:
        assert value in html
    assert "<script>" not in html and "<img" not in html
    assert "&lt;script&gt;" in html
    assert finder_email_html(settings, claimed, row) == html


def test_email_omits_location_when_not_shared():
    settings, row, claimed = sample()
    row.update(latitude_ciphertext=None, longitude_ciphertext=None)
    assert "google.com/maps" not in finder_email_html(settings, claimed, row)


def test_worker_sends_details_only_after_claim_transaction_commits():
    settings, row, claimed = sample()
    session, provider = MagicMock(), MagicMock()
    session.execute.return_value.mappings.return_value.one_or_none.return_value = row
    provider.send.return_value = "accepted-id"
    inside = False

    @contextmanager
    def transaction(*args):
        nonlocal inside
        inside = True
        yield session
        inside = False

    def send(**kwargs):
        assert not inside
        assert kwargs["to"] == "owner@example.test"
        assert "finder@example.test" in kwargs["html"]
        return "accepted-id"

    provider.send.side_effect = send
    with (
        patch("app.workers.notifications.worker_transaction", transaction),
        patch("app.workers.notifications._claim_one", return_value=claimed),
        patch("app.workers.notifications._prepare_recipient", return_value=claimed),
        patch("app.workers.notifications._finish") as finish,
    ):
        assert process_one(MagicMock(), settings, provider)
        finish.assert_called_once()
        assert finish.call_args.kwargs["status"] == "sent"


def test_worker_does_not_send_if_lease_projection_is_unavailable():
    settings, _row, claimed = sample()
    session, provider = MagicMock(), MagicMock()
    session.execute.return_value.mappings.return_value.one_or_none.return_value = None

    @contextmanager
    def transaction(*args):
        yield session

    with (
        patch("app.workers.notifications.worker_transaction", transaction),
        patch("app.workers.notifications._claim_one", return_value=claimed),
        patch("app.workers.notifications._prepare_recipient", return_value=claimed),
        patch("app.workers.notifications._finish") as finish,
    ):
        assert process_one(MagicMock(), settings, provider)
        provider.send.assert_not_called()
        assert finish.call_args.kwargs["error"].code == "finder_message_unavailable"
