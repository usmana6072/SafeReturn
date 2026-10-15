import base64
import json
import uuid

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import SecretStr

from app.core.inventory_secrets import (
    InventoryCryptoUnavailable,
    activation_verifier,
    create_sealed_insert,
    new_activation_secret,
    new_public_token,
    verifier_key,
)


def test_activation_verifiers_are_pair_bound_and_do_not_equal_secret():
    key = bytes(range(32))
    pair_a, pair_b = uuid.uuid4(), uuid.uuid4()
    secret = new_activation_secret()
    verifier = activation_verifier(key, 1, pair_a, secret)

    assert len(secret) >= 32
    assert len(verifier) == 32
    assert verifier != secret.encode()
    assert verifier != activation_verifier(key, 1, pair_b, secret)
    assert verifier != activation_verifier(key, 2, pair_a, secret)


def test_public_tokens_are_long_and_distinct_from_activation_secrets():
    tokens = {new_public_token() for _ in range(32)}
    secrets = {new_activation_secret() for _ in range(32)}
    assert len(tokens) == len(secrets) == 32
    assert all(len(token) >= 40 for token in tokens)
    assert not tokens.intersection(secrets)


def test_verifier_key_requires_exact_base64url_encoded_256_bits():
    encoded = base64.urlsafe_b64encode(bytes(range(32))).decode().rstrip("=")
    assert verifier_key(SecretStr(encoded)) == bytes(range(32))
    for invalid in (None, SecretStr("short"), SecretStr("*" * 44)):
        with pytest.raises(InventoryCryptoUnavailable):
            verifier_key(invalid)


def test_sealed_insert_is_private_authenticated_and_printer_decryptable():
    private = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    public_pem = private.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    pair_id = uuid.uuid4()
    secret = new_activation_secret()
    manifest = {"batch_id": str(pair_id), "pairs": [{"activation_secret": secret}]}
    sealed = create_sealed_insert(SecretStr(public_pem), manifest)
    assert secret not in json.dumps(sealed)
    unwrap_key = private.decrypt(
        base64.urlsafe_b64decode(sealed["wrapped_key"] + "=="),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=b"SafeReturn:sealed-insert:v1",
        ),
    )
    aad = b"SafeReturn:sealed-insert:v1\0" + pair_id.bytes
    plaintext = AESGCM(unwrap_key).decrypt(
        base64.urlsafe_b64decode(sealed["nonce"] + "=="),
        base64.urlsafe_b64decode(sealed["ciphertext"] + "=="),
        aad,
    )
    assert json.loads(plaintext) == manifest
    tampered = bytearray(base64.urlsafe_b64decode(sealed["ciphertext"] + "=="))
    tampered[-1] ^= 1
    with pytest.raises(InvalidTag):
        AESGCM(unwrap_key).decrypt(
            base64.urlsafe_b64decode(sealed["nonce"] + "=="), bytes(tampered), aad
        )


def test_sealed_insert_rejects_untrusted_or_weak_recipient_keys():
    with pytest.raises(InventoryCryptoUnavailable):
        create_sealed_insert(None, {"batch_id": str(uuid.uuid4())})
    with pytest.raises(InventoryCryptoUnavailable):
        create_sealed_insert(SecretStr("not-a-public-key"), {"batch_id": str(uuid.uuid4())})
