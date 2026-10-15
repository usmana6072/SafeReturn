"""Cryptographic primitives for paired-inventory generation."""

import base64
import hashlib
import hmac
import json
import secrets
import uuid
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import SecretStr


class InventoryCryptoUnavailable(ValueError):
    pass


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def verifier_key(value: SecretStr | None) -> bytes:
    if value is None:
        raise InventoryCryptoUnavailable("Activation verifier key is unavailable")
    try:
        encoded = value.get_secret_value().encode("ascii")
        key = base64.b64decode(
            encoded + b"=" * (-len(encoded) % 4), altchars=b"-_", validate=True
        )
    except (UnicodeEncodeError, ValueError):
        raise InventoryCryptoUnavailable("Activation verifier key is invalid") from None
    if len(key) != 32:
        raise InventoryCryptoUnavailable("Activation verifier key is invalid")
    return key


def activation_verifier(key: bytes, version: int, pair_id: uuid.UUID, secret: str) -> bytes:
    message = b"SafeReturn:activation:v1\0" + version.to_bytes(2, "big") + pair_id.bytes + secret.encode("ascii")
    return hmac.digest(key, message, "sha256")


def load_recipient_public_key(
    public_key_pem: SecretStr | rsa.RSAPublicKey | None,
) -> rsa.RSAPublicKey:
    if public_key_pem is None:
        raise InventoryCryptoUnavailable("Print recipient key is unavailable")
    if isinstance(public_key_pem, rsa.RSAPublicKey):
        public_key = public_key_pem
    else:
        try:
            public_key = serialization.load_pem_public_key(
                public_key_pem.get_secret_value().encode("ascii")
            )
        except (ValueError, TypeError, UnicodeEncodeError):
            raise InventoryCryptoUnavailable("Print recipient key is invalid") from None
    if not isinstance(public_key, rsa.RSAPublicKey) or public_key.key_size < 3072:
        raise InventoryCryptoUnavailable("Print recipient key is invalid")
    return public_key


def create_sealed_insert(
    public_key_pem: SecretStr | rsa.RSAPublicKey | None, manifest: dict[str, Any]
) -> dict[str, str]:
    public_key = load_recipient_public_key(public_key_pem)

    content_key = secrets.token_bytes(32)
    nonce = secrets.token_bytes(12)
    batch_id = uuid.UUID(manifest["batch_id"])
    aad = b"SafeReturn:sealed-insert:v1\0" + batch_id.bytes
    plaintext = json.dumps(manifest, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    ciphertext = AESGCM(content_key).encrypt(nonce, plaintext, aad)
    wrapped_key = public_key.encrypt(
        content_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=b"SafeReturn:sealed-insert:v1",
        ),
    )
    return {
        "format": "safereturn-sealed-insert-v1",
        "wrapped_key": _b64url(wrapped_key),
        "nonce": _b64url(nonce),
        "ciphertext": _b64url(ciphertext),
    }


def manifest_checksum(sealed_insert: dict[str, str]) -> str:
    canonical = json.dumps(sealed_insert, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def new_public_token() -> str:
    return secrets.token_urlsafe(32)


def new_activation_secret() -> str:
    return secrets.token_urlsafe(24)
