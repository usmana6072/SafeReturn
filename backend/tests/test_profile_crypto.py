"""Real AEAD binding/rotation/tamper tests; no real credentials or user data."""

import base64
import json
import time
import uuid

import pytest
from pydantic import SecretStr
from test_auth import claims, signed
from test_auth import verifier as _verifier

from app.core.config import Settings
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt, encrypt

verifier = _verifier


def configuration(version=1):
    return Settings(
        profile_data_keys=SecretStr(
            json.dumps(
                {
                    str(i): base64.urlsafe_b64encode(bytes([i]) * 32).decode()
                    for i in (1, 2)
                }
            )
        ),
        profile_data_key_version=version,
    )


def test_random_nonce_authenticated_scopes_and_key_rotation():
    qr, cid = uuid.uuid4(), uuid.uuid4()
    settings = configuration()
    first, version = encrypt(settings, qr, "ice_phone", "+923001234567", cid)
    second, _ = encrypt(settings, qr, "ice_phone", "+923001234567", cid)
    assert first != second and b"923001234567" not in first
    assert (
        decrypt(configuration(2), qr, "ice_phone", first, version, cid)
        == "+923001234567"
    )
    for other_qr, field, contact in (
        (uuid.uuid4(), "ice_phone", cid),
        (qr, "whatsapp_phone", cid),
        (qr, "ice_phone", uuid.uuid4()),
    ):
        with pytest.raises(ProfileCryptoUnavailable):
            decrypt(settings, other_qr, field, first, version, contact)
    with pytest.raises(ProfileCryptoUnavailable):
        decrypt(
            settings, qr, "ice_phone", first[:-1] + bytes([first[-1] ^ 1]), version, cid
        )
    with pytest.raises(ProfileCryptoUnavailable):
        decrypt(settings, qr, "ice_phone", first, 2, cid)


@pytest.mark.parametrize("keys", [None, "{}", "not-json", '{"1":"abc"}'])
def test_missing_or_invalid_keys_fail_closed(keys):
    settings = Settings(profile_data_keys=SecretStr(keys) if keys is not None else None)
    with pytest.raises(ProfileCryptoUnavailable):
        encrypt(settings, uuid.uuid4(), "medical_notes", "private notes")


@pytest.mark.parametrize(
    "amr,expected",
    [
        ("fresh", True),
        ("old", True),
        ("future", False),
        ("malformed", False),
        ("refresh", False),
    ],
)
def test_fresh_authentication_uses_signed_amr_not_refreshed_iat(
    verifier,
    amr,
    expected,
):
    provider, private, _, _ = verifier
    now = int(time.time())
    entries = {
        "fresh": [{"method": "password", "timestamp": now - 1}],
        "old": [{"method": "password", "timestamp": now - 3600}],
        "future": [{"method": "password", "timestamp": now + 100}],
        "malformed": [{"method": "password", "timestamp": True}],
        "refresh": [{"method": "token_refresh", "timestamp": now - 1}],
    }
    principal = provider.verify(signed(private, claims(amr=entries[amr])))
    assert (principal.authentication_time is not None) is expected
    if expected:
        assert principal.authentication_time == entries[amr][0]["timestamp"]
