"""Real HTTP, evidence service and AEAD against a scripted repository, not PG proof."""

import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from threading import RLock
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from test_critical_workflow_boundaries import Result
from test_print_templates import BASE, RID, TID, ScriptedDatabase, revision, template
from test_print_templates import env as _env
from test_print_templates import verifier as _verifier
from test_template_evidence import signed_evidence as _signed_evidence
from test_template_evidence import uid

from app.api.auth import AccessError
from app.core.profile_crypto import decrypt
from app.services.template_evidence import publication_proof
from app.template_evidence_control import run

env = _env
verifier = _verifier
signed_evidence = _signed_evidence
BINDINGS = "/api/v1/admin/print-template-bindings"
APPROVAL = uid(9001)


class RegistryDatabase(ScriptedDatabase):
    """Repository responses are explicit scripts; serialize only this Python fake."""

    def __init__(self, actor, evidence, ctx):
        super().__init__(actor)
        self.registry_available = True
        self.evidence, self.ctx = evidence, ctx
        self.approval = None
        self.lifecycle = []
        self.denial = None
        self.result = {}
        self.mutex = RLock()

    @contextmanager
    def transaction(self):
        with self.mutex:
            self.info.pop("template_registry_gate", None)
            with super().transaction():
                yield self

    @contextmanager
    def begin_nested(self):
        before = deepcopy((self.approval, self.lifecycle))
        try:
            with super().begin_nested():
                yield self
        except BaseException:
            self.approval, self.lifecycle = before
            raise

    def execute(self, statement, params=None):
        sql, p = str(statement), params or {}
        if (
            "sr_template_registry_gate" in sql
            and "AS template_registry_available" not in sql
        ):
            return Result(None)
        if "sr_template_lifecycle" not in sql:
            return super().execute(statement, params)
        action, body = p["action"], json.loads(p["payload"])
        if self.denial:
            return Result({"error": self.denial})
        if action.endswith("_check"):
            return Result({"human_id": uid(800)})
        if action.startswith("context_"):
            ctx = deepcopy(self.ctx)
            if action == "context_publish":
                ctx.update(
                    mode="publish", actor_human=uid(800), importer_human=uid(401)
                )
            return Result(ctx)
        if action == "approval_input":
            return Result(deepcopy(self.approval))
        self.lifecycle.append((action, body))
        if action == "import":
            self.approval = dict(
                body,
                approval_id=body["approval_id"],
                importer_human=uid(401),
                evidence_sha256=body["summary"]["evidence_sha256"],
            )
            return Result({"approval_id": body["approval_id"], "state": "eligible"})
        if action == "revoke":
            return Result({"revocation_id": uid(9002), "state": "withdrawn"})
        return Result(deepcopy(self.result))


@pytest.fixture
def registry(env, signed_evidence):
    client, previous, headers, settings = env
    evidence, ctx, _, _ = signed_evidence
    db = RegistryDatabase(previous.owner, evidence, ctx)
    client.application.state.database = db
    return client, db, headers, settings


def control(registry, *, operation="import", key="synthetic-import-001", **extra):
    client, db, headers, settings = registry
    wire = {
        "operation": operation,
        "authorization": headers()["Authorization"][7:],
        "idempotency_key": key,
    }
    wire.update(
        {"envelope": db.evidence.model_dump(mode="json")}
        if operation == "import"
        else {
            "withdrawal": {
                "evidence_id": str(db.evidence.payload.evidence_id),
                "key_id": None,
                "expected_authority_version": 1,
                "reason_code": "evidence_withdrawn",
                "confirmed": True,
            }
        }
    )
    wire.update(extra)
    return run(
        json.dumps(wire).encode(), settings, client.application.state.jwt_verifier, db
    )


def import_as_custodian(registry):
    db = registry[1]
    db.roles = {"security_admin"}
    return control(registry)


def test_controlled_import_real_signature_encryption_replay_and_publish(registry):
    client, db, headers, settings = registry
    imported = import_as_custodian(registry)
    assert control(registry) == imported
    assert len(db.lifecycle) == len(db.audit) == len(db.receipts) == 1
    approval = db.approval
    raw = bytes.fromhex(approval["ciphertext"])
    assert raw.startswith(b"SRD1") and b"physical_scan" not in raw
    assert json.loads(
        decrypt(
            settings,
            UUID(approval["approval_id"]),
            "template-qa:v1",
            raw,
            approval["key_version"],
        )
    ) == db.evidence.model_dump(mode="json")
    db.roles = {"operations", "finance"}
    published = revision() | {
        "status": "published",
        "row_version": 3,
        "fingerprint_sha256": db.ctx["revision"]["fingerprint_sha256"],
        "published_at": "2026-10-21T00:00:00Z",
    }
    db.result = {"revision": published, "approval_id": approval["approval_id"]}
    url = f"{BASE}/{TID}/revisions/{RID}/publish"
    body = {"approval_id": approval["approval_id"], "confirmed": True}
    response = client.post(url, json=body, headers=headers() | {"If-Match": '"2"'})
    assert response.status_code == 200, response.text
    assert (
        db.lifecycle[-1][1]["verified_evidence_sha256"] == approval["evidence_sha256"]
    )
    assert (
        client.post(url, json=body, headers=headers() | {"If-Match": '"2"'}).json()
        == response.json()
    )
    assert [a for a, _ in db.lifecycle].count("publish") == 1
    assert response.headers["cache-control"] == "private, no-store"


@pytest.mark.parametrize(
    "roles",
    [{"operations"}, {"superadmin"}, {"finance"}, {"operations", "finance"}, set()],
)
def test_import_never_inherits_security_admin(registry, roles):
    registry[1].roles = roles
    with pytest.raises(AccessError) as exc:
        control(registry)
    assert exc.value.status == 403 and registry[1].approval is None


@pytest.mark.parametrize("failure", ["signature", "receipt", "archive", "authority"])
def test_import_rolls_back_and_fails_closed(registry, failure):
    _, db, _, _ = registry
    db.roles = {"security_admin"}
    if failure == "signature":
        db.evidence.attestations[0].signature = "A" * 86
    elif failure == "receipt":
        db.fail_receipt = True
    elif failure == "archive":
        db.ctx["archive"] = {}
    else:
        db.denial = "PROVIDER_UNAVAILABLE"
    with pytest.raises((HTTPException, AccessError, IntegrityError)):
        control(registry)
    assert db.approval is None and not db.receipts and not db.audit


def test_controlled_revocation_requires_version_and_is_idempotent(registry):
    _, db, _, _ = registry
    db.roles = {"security_admin"}
    first = control(registry, operation="revoke")
    assert control(registry, operation="revoke") == first
    assert len(db.lifecycle) == 1 and db.lifecycle[0][0] == "revoke"
    db.denial = "VERSION_MISMATCH"
    with pytest.raises(HTTPException) as exc:
        control(registry, operation="revoke", key="synthetic-revoke-002")
    assert exc.value.status_code == 412


@pytest.mark.parametrize(
    "extra",
    [
        {"file_path": "private.pem"},
        {"role": "designer"},
        {"envelope": {"payload": {"url": "https://evil.test"}}},
        {"withdrawal": {}},
    ],
)
def test_control_transport_has_no_url_file_role_or_extra_channel(registry, extra):
    registry[1].roles = {"security_admin"}
    with pytest.raises(ValueError):
        control(registry, **extra)
    assert not registry[1].audit


def binding(*, active=True):
    return {
        "binding_id": uid(9010),
        "variant_id": uid(9011),
        "tag_type": "lost",
        "revision_id": str(RID),
        "is_active": active,
        "row_version": 1 if active else 2,
        "created_at": "2026-10-21T00:00:00Z",
    }


@pytest.mark.parametrize("deactivate", [False, True])
def test_binding_command_real_guards_closed_dto_encrypted_replay(registry, deactivate):
    client, db, headers, _ = registry
    db.result = {"binding": binding(active=not deactivate), "variant_row_version": 2}
    body = {
        "variant_id": uid(9011),
        "tag_type": "lost",
        "revision_id": None if deactivate else str(RID),
        "expected_variant_version": 1,
        "expected_binding_id": uid(9010) if deactivate else None,
        "confirmed": True,
    }
    first = client.post(BINDINGS, json=body, headers=headers())
    assert first.status_code == 201, first.text
    assert client.post(BINDINGS, json=body, headers=headers()).json() == first.json()
    assert len(db.lifecycle) == 1 and len(db.audit) == 1
    body["is_active"] = False
    assert client.post(BINDINGS, json=body, headers=headers()).status_code == 422
    del body["is_active"]
    db.roles = {"superadmin", "finance"}
    assert client.post(BINDINGS, json=body, headers=headers()).status_code == 403


@pytest.mark.parametrize(
    "error,status",
    [("VERSION_MISMATCH", 412), ("CONFLICT", 409), ("PROVIDER_UNAVAILABLE", 503)],
)
def test_binding_repository_rejection_is_safe(registry, error, status):
    client, db, headers, _ = registry
    db.denial = error
    body = {
        "variant_id": uid(9011),
        "tag_type": "lost",
        "revision_id": None,
        "expected_variant_version": 1,
        "expected_binding_id": uid(9010),
        "confirmed": True,
    }
    response = client.post(BINDINGS, json=body, headers=headers())
    assert response.status_code == status and not db.receipts and not db.audit


def test_binding_missing_deactivation_target_and_false_confirmation(registry):
    client, _, headers, _ = registry
    body = {
        "variant_id": uid(9011),
        "tag_type": "lost",
        "revision_id": None,
        "expected_variant_version": 1,
        "expected_binding_id": None,
        "confirmed": True,
    }
    assert client.post(BINDINGS, json=body, headers=headers()).status_code == 422
    body.update(revision_id=str(RID), confirmed=False)
    assert client.post(BINDINGS, json=body, headers=headers()).status_code == 422


def test_retirement_and_bounded_binding_metadata(registry):
    client, db, headers, _ = registry
    db.result = {
        "template": template() | {"lifecycle_status": "retired", "row_version": 2},
        "revision": revision()
        | {
            "status": "retired",
            "row_version": 4,
            "fingerprint_sha256": "a" * 64,
            "published_at": "2026-10-21T00:00:00Z",
        },
    }
    response = client.post(
        f"{BASE}/{TID}/revisions/{RID}/retire",
        json={"confirmed": True, "reason": "Synthetic retirement"},
        headers=headers(),
    )
    assert response.status_code == 200, response.text
    db.result = {
        "items": [binding()],
        "next_cursor": None,
        "as_of": "2026-10-21T00:00:00Z",
    }
    db.roles = {"security_admin"}
    assert (
        client.get(BINDINGS + "?active=false&limit=1", headers=headers()).status_code
        == 200
    )
    for suffix in (
        "?limit=51",
        "?active=maybe",
        "?role=operations",
        "?limit=1&limit=2",
    ):
        assert client.get(BINDINGS + suffix, headers=headers()).status_code == 422


@pytest.mark.parametrize("action", ["bind", "publish"])
def test_simultaneous_command_replay_serialized_in_memory_only(registry, action):
    client, db, headers, _ = registry
    db.result = {"binding": binding(), "variant_row_version": 2}
    body = {
        "variant_id": uid(9011),
        "tag_type": "lost",
        "revision_id": str(RID),
        "expected_variant_version": 1,
        "expected_binding_id": None,
        "confirmed": True,
    }
    url = BINDINGS
    if action == "publish":
        import_as_custodian(registry)
        db.roles = {"operations"}
        db.result = {
            "revision": revision()
            | {
                "status": "published",
                "row_version": 3,
                "fingerprint_sha256": "a" * 64,
                "published_at": "2026-10-21T00:00:00Z",
            },
            "approval_id": db.approval["approval_id"],
        }
        body = {"approval_id": db.approval["approval_id"], "confirmed": True}
        url = f"{BASE}/{TID}/revisions/{RID}/publish"
    before = len(db.lifecycle)

    def invoke(_):
        return client.post(url, json=body, headers=headers())

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(invoke, range(2)))
    assert all(r.status_code == (201 if action == "bind" else 200) for r in responses)
    assert (
        responses[0].json() == responses[1].json() and len(db.lifecycle) == before + 1
    )


def test_encrypted_approval_cannot_be_redirected_to_another_revision(registry):
    client, db, headers, settings = registry
    import_as_custodian(registry)
    db.roles = {"operations"}
    principal = client.application.state.jwt_verifier.verify(
        headers()["Authorization"][7:]
    )
    from app.api.auth import authorize

    with db.transaction():
        context = authorize(db, principal)
        with pytest.raises(HTTPException) as exc:
            publication_proof(
                context, settings, TID, UUID(int=9999), db.approval["approval_id"]
            )
        assert exc.value.status_code == 409
