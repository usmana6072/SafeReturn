"""Opaque manufacturing transport. This module never decrypts printer inserts."""

import base64
import hashlib
import json
from collections.abc import Iterable
from typing import Any, Literal
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import Field

from app.api.v1.catalog import Closed
from app.core.config import Settings
from app.core.profile_crypto import decrypt, encrypt

MAX_BYTES = 2_000_000
MAX_PAIRS = 1000
LEASE_SECONDS = 180
MAX_ATTEMPTS = 5


class TransportConflict(ValueError):
    """Fixed category only; never include provider text or production material."""


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def unb64(value: str) -> bytes:
    if not isinstance(value, str) or len(value) > MAX_BYTES * 2:
        raise TransportConflict("invalid_encoding")
    try:
        return base64.b64decode(
            value + "=" * (-len(value) % 4), altchars=b"-_", validate=True
        )
    except (ValueError, UnicodeError):
        raise TransportConflict("invalid_encoding") from None


def sealed_bytes(data: bytes, checksum: str) -> bytes:
    if (
        not isinstance(data, bytes)
        or not 1 <= len(data) <= MAX_BYTES
        or sha(data) != checksum
    ):
        raise TransportConflict("sealed_integrity")
    try:
        envelope = json.loads(data)
        if set(envelope) != {"format", "wrapped_key", "nonce", "ciphertext"}:
            raise ValueError()
        if envelope["format"] != "safereturn-sealed-insert-v1":
            raise ValueError()
        if len(unb64(envelope["wrapped_key"])) < 384:
            raise ValueError()
        if (
            len(unb64(envelope["nonce"])) != 12
            or len(unb64(envelope["ciphertext"])) < 16
        ):
            raise ValueError()
        if canonical(envelope).encode() != data:
            raise ValueError()
    except (ValueError, TypeError, KeyError):
        raise TransportConflict("sealed_integrity") from None
    return data


def identity_snapshot(pairs: list[dict[str, Any]]) -> tuple[int, str]:
    """Checks original metadata, not plaintext inside the opaque envelope."""
    if not isinstance(pairs, list) or not 1 <= len(pairs) <= MAX_PAIRS:
        raise TransportConflict("pair_count")
    refs, tokens, normalized = set(), set(), []
    for pair in pairs:
        if not isinstance(pair, dict) or not isinstance(
            pair.get("pair_reference"), str
        ):
            raise TransportConflict("pair_manifest")
        ref, tags = pair["pair_reference"], pair.get("tags")
        if ref in refs or not isinstance(tags, list) or len(tags) != 2:
            raise TransportConflict("two_tags")
        refs.add(ref)
        if not all(isinstance(t, dict) for t in tags) or {
            t.get("tag_type") for t in tags
        } != {"lost", "ice"}:
            raise TransportConflict("two_tags")
        clean = []
        for tag in tags:
            token = tag.get("public_token")
            if (
                not isinstance(token, str)
                or not 20 <= len(token) <= 100
                or token in tokens
            ):
                raise TransportConflict("identity_manifest")
            tokens.add(token)
            clean.append({"tag_type": tag["tag_type"], "public_token": token})
        normalized.append(
            {"pair_reference": ref, "tags": sorted(clean, key=lambda t: t["tag_type"])}
        )
    return len(pairs), sha(
        canonical(sorted(normalized, key=lambda p: p["pair_reference"])).encode()
    )


def pack(settings: Settings, batch: UUID, field: str, data: bytes) -> dict[str, Any]:
    cipher, version = encrypt(
        settings, batch, "manufacturing:" + field, base64.b64encode(data).decode()
    )
    return {"cipher": base64.b64encode(cipher).decode(), "key_version": version}


def unpack(settings: Settings, batch: UUID, field: str, value: dict[str, Any]) -> bytes:
    return unb64(
        decrypt(
            settings,
            batch,
            "manufacturing:" + field,
            unb64(value["cipher"]),
            value["key_version"],
        )
    )


class Handoff(Closed):
    format: Literal["safereturn-printer-handoff-v1"]
    batch_id: UUID
    job_id: UUID
    revision: int = Field(ge=1, le=2147483646, strict=True)
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    printer_key_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    delivery_id: UUID
    outcome: Literal["accepted", "not_received"]


def verify_handoff(record: dict[str, Any], signature: str, public_key: str) -> Handoff:
    body = Handoff.model_validate(record)
    try:
        Ed25519PublicKey.from_public_bytes(unb64(public_key)).verify(
            unb64(signature), canonical(body.model_dump(mode="json")).encode()
        )
    except (InvalidSignature, ValueError):
        raise TransportConflict("handoff_signature") from None
    return body


def read_spool(reader: Iterable[bytes], checksum: str) -> bytes:
    """Bounded readback catches truncated/partial writes before ready publication."""
    data = bytearray()
    for chunk in reader:
        if not isinstance(chunk, bytes) or len(data) + len(chunk) > MAX_BYTES:
            raise TransportConflict("spool_integrity")
        data.extend(chunk)
    return sealed_bytes(bytes(data), checksum)
