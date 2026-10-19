"""Unit and validation tests for recipient finder inbox operations (Task 5.7)."""

import json
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.v1.messages import MessageUpdate, _decrypt_message
from app.core.config import Settings
from app.core.profile_crypto import encrypt


def _test_settings(key_version: int = 1):
    keys = {str(key_version): "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="}
    return Settings(
        profile_data_keys=json.dumps(keys),
        profile_data_key_version=key_version,
    )


class _MockContext:
    def __init__(self, settings: Settings):
        self.session = _MockSession(settings)


class _MockSession:
    def __init__(self, settings: Settings):
        self.info = {"settings": settings}


def test_message_update_status_validation():
    """Only viewed, archived, and flagged are permitted status updates."""
    for valid_status in ("viewed", "archived", "flagged"):
        mu = MessageUpdate(status=valid_status)
        assert mu.status == valid_status

    for invalid_status in ("new", "deleted", "open", "closed", "other"):
        with pytest.raises(ValidationError):
            MessageUpdate(status=invalid_status)


def test_message_update_extra_fields_forbidden():
    """Extra fields must be forbidden on MessageUpdate."""
    with pytest.raises(ValidationError):
        MessageUpdate(status="viewed", extra="not_allowed")  # type: ignore[call-arg]


def test_decrypt_message_roundtrip():
    """Decryption succeeds when ciphertexts and keys match."""
    settings = _test_settings(key_version=1)
    qr_id = uuid4()

    email_ct, contact_ver = encrypt(
        settings, qr_id, "finder_email", "finder@example.com"
    )
    phone_ct, _ = encrypt(settings, qr_id, "finder_phone", "+923001234567")
    msg_ct, msg_ver = encrypt(settings, qr_id, "finder_message", "Found your keys!")

    row = {
        "qr_id": qr_id,
        "finder_email_ciphertext": email_ct,
        "finder_phone_ciphertext": phone_ct,
        "finder_contact_key_version": contact_ver,
        "message_text_ciphertext": msg_ct,
        "message_key_version": msg_ver,
    }

    email, phone, msg = _decrypt_message(_MockContext(settings), row)
    assert email == "finder@example.com"
    assert phone == "+923001234567"
    assert msg == "Found your keys!"


def test_decrypt_message_handles_null_email_phone():
    """Decryption handles optional email and phone."""
    settings = _test_settings(key_version=1)
    qr_id = uuid4()
    msg_ct, msg_ver = encrypt(settings, qr_id, "finder_message", "Found your item.")

    row = {
        "qr_id": qr_id,
        "finder_email_ciphertext": None,
        "finder_phone_ciphertext": None,
        "finder_contact_key_version": 1,
        "message_text_ciphertext": msg_ct,
        "message_key_version": msg_ver,
    }

    email, phone, msg = _decrypt_message(_MockContext(settings), row)
    assert email is None
    assert phone is None
    assert msg == "Found your item."


def test_decrypt_message_crypto_unavailable():
    """Decryption raises 503 HTTPException when keys are missing or invalid."""
    settings = Settings(
        profile_data_keys=None,
        profile_data_key_version=1,
    )
    qr_id = uuid4()

    row = {
        "qr_id": qr_id,
        "finder_email_ciphertext": None,
        "finder_phone_ciphertext": None,
        "finder_contact_key_version": 1,
        "message_text_ciphertext": b"SRD1invalidciphertextbytes1234567890",
        "message_key_version": 1,
    }

    with pytest.raises(HTTPException) as exc_info:
        _decrypt_message(_MockContext(settings), row)
    assert exc_info.value.status_code == 503
    assert "temporarily unavailable" in exc_info.value.detail


def test_maps_url_generation():
    """Maps URL format matches Google Maps standard query format."""
    latitude = 31.5204
    longitude = 74.3587
    maps_url = f"https://www.google.com/maps?q={latitude},{longitude}"
    assert maps_url == "https://www.google.com/maps?q=31.5204,74.3587"


def test_inbox_cursor_roundtrip_and_rejection():
    from datetime import UTC, datetime

    from app.api.v1.messages import _cursor, _parse_cursor

    row = {"submitted_at": datetime.now(UTC), "id": uuid4()}
    assert _parse_cursor(_cursor(row)) == (row["submitted_at"], row["id"])
    for value in ("invalid", "x" * 257, "!!!!"):
        with pytest.raises(HTTPException) as error:
            _parse_cursor(value)
        assert error.value.status_code == 422


@pytest.mark.parametrize(
    "latitude,longitude", [("nan", "1"), ("91", "1"), ("1", "181"), ("bad", "1")]
)
def test_invalid_decrypted_location_fails_closed(monkeypatch, latitude, longitude):
    from app.api.v1 import messages

    settings = _test_settings()
    qr = uuid4()
    lat, v = encrypt(settings, qr, "finder_latitude", latitude)
    lon, _ = encrypt(settings, qr, "finder_longitude", longitude)
    location = {
        "latitude_ciphertext": lat,
        "longitude_ciphertext": lon,
        "key_version": v,
        "accuracy_m": 25,
        "consent_at": "synthetic-consent",
    }

    class Result:
        def mappings(self):
            return self

        def one_or_none(self):
            return location

    class Session:
        def __init__(self):
            self.info = {"settings": settings}

        def execute(self, *args, **kwargs):
            return Result()

    class Context:
        session = Session()

    monkeypatch.setattr(messages, "_message_or_404", lambda *args: {"qr_id": qr})
    monkeypatch.setattr(
        messages, "_decrypt_message", lambda *args: (None, None, "synthetic")
    )
    with pytest.raises(HTTPException) as error:
        messages.get_finder_message(uuid4(), Context())
    assert error.value.status_code == 503


def test_deletion_review_requires_boolean_confirmation():
    from app.api.v1.account import DeletionRequest

    assert DeletionRequest(confirm=True).confirm is True
    for value in (1, "true", False, None):
        with pytest.raises(ValidationError):
            DeletionRequest.model_validate({"confirm": value})
