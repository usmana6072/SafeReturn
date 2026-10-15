"""Versioned profile AEAD; keys are server-only and independent of activation."""

import base64
import json
import secrets
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class ProfileCryptoUnavailable(ValueError):
    pass


def key(settings, version):
    try:
        keys = json.loads(settings.profile_data_keys.get_secret_value())
        encoded = keys[str(version)].encode("ascii")
        value = base64.b64decode(
            encoded + b"=" * (-len(encoded) % 4), altchars=b"-_", validate=True
        )
        if len(value) != 32:
            raise ValueError()
        return value
    except (AttributeError, KeyError, TypeError, ValueError, UnicodeError):
        raise ProfileCryptoUnavailable() from None


def aad(qr_id: UUID, field: str, version: int, contact_id: UUID | None = None):
    return f"SafeReturn:profile:v1:{qr_id}:{field}:{contact_id or ''}:{version}".encode(
        "ascii"
    )


def encrypt(settings, qr_id, field, value, contact_id=None):
    version = settings.profile_data_key_version
    nonce = secrets.token_bytes(12)
    payload = AESGCM(key(settings, version)).encrypt(
        nonce, value.encode(), aad(qr_id, field, version, contact_id)
    )
    return b"SRD1" + nonce + payload, version


def decrypt(settings, qr_id, field, value, version, contact_id=None):
    try:
        value = bytes(value)
        if not value.startswith(b"SRD1") or len(value) < 32:
            raise ValueError()
        return (
            AESGCM(key(settings, version))
            .decrypt(value[4:16], value[16:], aad(qr_id, field, version, contact_id))
            .decode()
        )
    except (InvalidTag, ValueError, TypeError, UnicodeError):
        raise ProfileCryptoUnavailable() from None
