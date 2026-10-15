"""Task 3.1 API generation checks against an isolated real PostgreSQL schema."""

import base64
import hashlib
import hmac
import json
import uuid

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import SecretStr
from sqlalchemy import text

pytest_plugins = ["test_auth_guards"]

from app.core.config import Settings


@pytest.fixture
def inventory_context(guarded):
    pg, wf, _, _, headers, client = guarded
    private = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    public = private.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    secret_key = bytes(range(32))
    settings = Settings(
        activation_verifier_key=SecretStr(base64.urlsafe_b64encode(secret_key).decode().rstrip("=")),
        activation_verifier_key_version=3,
        print_recipient_public_key=SecretStr(public),
    )
    client.application.state.settings = settings
    return pg, wf, headers, client, private, secret_key


def batch_request(label=None):
    return {
        "pair_count": 3,
        "batch_label": label or ("T31-" + uuid.uuid4().hex[:12]),
        "logo_template_key": "safe-return-primary",
        "qr_ecc": "Q",
        "print_material": "Waterproof vinyl",
        "intended_environment": "indoor",
        "lost_symbol_size_mm": 30,
        "ice_symbol_size_mm": 35,
    }


def open_insert(private, envelope, batch_id):
    decode = lambda value: base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    content_key = private.decrypt(
        decode(envelope["wrapped_key"]),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=b"SafeReturn:sealed-insert:v1",
        ),
    )
    aad = b"SafeReturn:sealed-insert:v1\0" + uuid.UUID(batch_id).bytes
    return json.loads(AESGCM(content_key).decrypt(
        decode(envelope["nonce"]), decode(envelope["ciphertext"]), aad
    ))


def test_operations_generation_is_atomic_pair_complete_and_credential_safe(inventory_context):
    pg, wf, headers, client, private, secret_key = inventory_context
    payload = batch_request()
    idempotency_key = "t31-" + uuid.uuid4().hex
    response = client.post(
        "/api/v1/admin/qr-batches",
        json=payload,
        headers={**headers(wf["operations"]), "Idempotency-Key": idempotency_key},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["generated_pair_count"] == 3
    assert data["generated_qr_count"] == 6
    assert "activation_secret" not in response.text
    assert "secret_verifier" not in response.text
    manifest = open_insert(private, data["sealed_insert"], data["batch_id"])
    assert len(manifest["pairs"]) == 3
    secrets = [pair["activation_secret"] for pair in manifest["pairs"]]
    tokens = [tag["public_token"] for pair in manifest["pairs"] for tag in pair["tags"]]
    assert len(set(secrets)) == 3
    assert len(set(tokens)) == 6
    assert all({tag["tag_type"] for tag in pair["tags"]} == {"lost", "ice"} for pair in manifest["pairs"])
    assert not any(secret in tokens for secret in secrets)

    with pg.connect() as connection:
        batch = connection.execute(
            text("SELECT status,logo_template_key,print_material,ecc_level,intended_environment,print_manifest_checksum FROM qr_batches WHERE id=:id"),
            {"id": data["batch_id"]},
        ).one()
        assert batch == ("generated", "safe-return-primary", "Waterproof vinyl", "Q", "indoor", hashlib.sha256(json.dumps(data["sealed_insert"], sort_keys=True, separators=(",", ":")).encode()).hexdigest())
        audit = connection.execute(
            text("SELECT action,request_id,safe_details FROM audit_events WHERE target_id=:id"),
            {"id": data["batch_id"]},
        ).one()
        assert audit[0] == "inventory.qr_batch.generated"
        assert audit[1] == hashlib.sha256(idempotency_key.encode()).hexdigest()
        assert audit[2] == {"outcome": "success", "reason_code": "api_090"}
        stored_response = connection.execute(
            text("SELECT state,response_key_version,response_body_ciphertext FROM idempotency_records WHERE idempotency_key=:key"),
            {"key": idempotency_key},
        ).one()
        assert stored_response[0:2] == ("completed", 1)
        assert stored_response[2] == json.dumps(data["sealed_insert"], sort_keys=True, separators=(",", ":")).encode()
        rows = connection.execute(
            text("""
                SELECT p.pair_reference,p.id,c.tag_type,c.public_token,c.printed_size_mm,
                       v.secret_verifier,v.verifier_key_version
                FROM tag_pairs p JOIN qr_codes c ON c.pair_id=p.id
                JOIN pair_activation_credentials v ON v.pair_id=p.id
                WHERE p.batch_id=:id ORDER BY p.id,c.tag_type
            """),
            {"id": data["batch_id"]},
        ).all()
        assert len(rows) == 6
        verifiers = {row[5] for row in rows}
        assert len(verifiers) == 3
        secrets_by_pair = {
            pair["pair_reference"]: pair["activation_secret"]
            for pair in manifest["pairs"]
        }
        pairs = {}
        for row in rows:
            pairs.setdefault(row[0], []).append(row)
        for pair_reference, rows_for_pair in pairs.items():
            actual = rows_for_pair[0]
            expected = hmac.digest(
                secret_key,
                b"SafeReturn:activation:v1\0" + (3).to_bytes(2, "big") + actual[1].bytes + secrets_by_pair[pair_reference].encode(),
                "sha256",
            )
            assert actual[5] == expected
            assert len(rows_for_pair) == 2
            assert {row[2] for row in rows_for_pair} == {"lost", "ice"}
            assert all(row[6] == 3 for row in rows_for_pair)


def test_generation_idempotency_replays_ciphertext_and_rejects_changed_request(inventory_context):
    _, wf, headers, client, _, _ = inventory_context
    payload = batch_request()
    key = "t31-replay-" + uuid.uuid4().hex
    first = client.post("/api/v1/admin/qr-batches", json=payload, headers={**headers(wf["operations"]), "Idempotency-Key": key})
    replay = client.post("/api/v1/admin/qr-batches", json=payload, headers={**headers(wf["operations"]), "Idempotency-Key": key})
    changed = client.post("/api/v1/admin/qr-batches", json={**payload, "pair_count": 4}, headers={**headers(wf["operations"]), "Idempotency-Key": key})
    assert first.status_code == replay.status_code == 201
    assert first.json() == replay.json()
    assert changed.status_code == 409


def test_duplicate_batch_label_does_not_leave_a_processing_idempotency_row(inventory_context):
    pg, wf, headers, client, _, _ = inventory_context
    payload = batch_request()
    first_key = "t31-label-" + uuid.uuid4().hex
    second_key = "t31-label-" + uuid.uuid4().hex
    first = client.post("/api/v1/admin/qr-batches", json=payload, headers={**headers(wf["operations"]), "Idempotency-Key": first_key})
    duplicate = client.post("/api/v1/admin/qr-batches", json=payload, headers={**headers(wf["operations"]), "Idempotency-Key": second_key})
    assert first.status_code == 201
    assert duplicate.status_code == 409
    with pg.connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM idempotency_records WHERE idempotency_key=:key"),
            {"key": second_key},
        ).scalar_one() == 0


@pytest.mark.parametrize("actor,headers_extra,status", [
    ("support", {}, 403),
    ("operations", {"aal": "aal1"}, 403),
])
def test_generation_requires_operations_role_and_current_mfa(inventory_context, actor, headers_extra, status):
    _, wf, headers, client, _, _ = inventory_context
    response = client.post(
        "/api/v1/admin/qr-batches",
        json=batch_request(),
        headers={**headers(wf[actor], **headers_extra), "Idempotency-Key": "t31-deny-" + uuid.uuid4().hex},
    )
    assert response.status_code == status


def test_generation_fails_closed_without_both_credential_keys(inventory_context):
    _, wf, headers, client, _, _ = inventory_context
    client.application.state.settings = Settings()
    response = client.post(
        "/api/v1/admin/qr-batches",
        json=batch_request(),
        headers={**headers(wf["operations"]), "Idempotency-Key": "t31-key-" + uuid.uuid4().hex},
    )
    assert response.status_code == 503


def test_outdoor_batch_rejects_symbol_below_35mm(inventory_context):
    _, wf, headers, client, _, _ = inventory_context
    response = client.post(
        "/api/v1/admin/qr-batches",
        json={**batch_request(), "intended_environment": "outdoor", "lost_symbol_size_mm": 30},
        headers={**headers(wf["operations"]), "Idempotency-Key": "t31-size-" + uuid.uuid4().hex},
    )
    assert response.status_code == 422
