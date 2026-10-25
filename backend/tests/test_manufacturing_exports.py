"""Synthetic gateway/crypto orchestration only; no PostgreSQL or provider writes."""

import base64
import importlib.util
import io
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from pydantic import SecretStr
from sqlalchemy.exc import OperationalError
from test_auth import claims, signed
from test_auth import verifier as _verifier
from test_health import ASGIClient

from app.core.config import Settings
from app.core.inventory_secrets import create_sealed_insert, manifest_checksum
from app.core.manufacturing import (
    Handoff,
    TransportConflict,
    canonical,
    identity_snapshot,
    pack,
    read_spool,
    sealed_bytes,
    sha,
    unpack,
)
from app.core.manufacturing_custody import record_handoff, source_record
from app.main import create_app
from app.workers.manufacturing_exports import run_one
from app.workers.printing import LeaseLost

verifier = _verifier
SECRET = "SYNTHETIC_ACTIVATION_SECRET_CANARY_54A"
ORIGIN = "https://manufacturing.test"
SQL_FILE = Path(__file__).parents[1] / "alembic/versions/0027_manufacturing_exports.sql"


class Result:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value

    def scalar_one_or_none(self):
        return self.value

    def one_or_none(self):
        return self.value

    def mappings(self):
        return self


class Store:
    """Serialized transactional gateway stand-in; does NOT execute production SQL."""

    def __init__(self, actor, settings, envelope):
        self.lock = threading.RLock()
        self.info = {}
        self.actor = self.worker = None
        self.executor, self.approver = actor, uuid4()
        self.roles = {
            actor: {"operations", "finance"},
            self.approver: {"security_admin"},
        }
        self.active = self.mfa = self.approval_active = self.eligible = True
        self.fail_commit = self.fail_receipt = False
        envelope, batch_id = envelope
        self.batch, self.approval = batch_id, uuid4()
        self.fingerprint = "a" * 64
        self.pairs = [
            {
                "pair_reference": "SYNTHETIC-PAIR",
                "tags": [
                    {"tag_type": "lost", "public_token": "SYNTHETIC_LOST_TOKEN_CANARY"},
                    {"tag_type": "ice", "public_token": "SYNTHETIC_ICE_TOKEN_CANARY"},
                ],
            }
        ]
        self.raw = canonical(envelope).encode()
        self.checksum = manifest_checksum(envelope)
        self.count, self.identity = identity_snapshot(self.pairs)
        self.source = pack(settings, self.batch, "source", self.raw)
        self.job = None
        self.receipts, self.grants, self.events = {}, {}, []
        self.attempt, self.lease_until, self.retry_after = 0, 0, 0
        self.lease_owner = None
        self.durable_state = "pending"
        self.statements = []
        self.commits = self.rollbacks = 0
        self.history = (
            "original batch/QR/credential history",
            deepcopy(self.pairs),
            self.checksum,
        )
        self.custody = ed25519.Ed25519PrivateKey.generate()
        self.delivery = None

    @contextmanager
    def transaction(self):
        with self.lock:
            snapshot = deepcopy(
                (
                    self.job,
                    self.receipts,
                    self.grants,
                    self.events,
                    self.attempt,
                    self.lease_owner,
                    self.lease_until,
                    self.durable_state,
                )
            )
            try:
                yield self
                if self.fail_commit:
                    raise OperationalError("COMMIT", {}, Exception(SECRET))
            except BaseException:
                (
                    self.job,
                    self.receipts,
                    self.grants,
                    self.events,
                    self.attempt,
                    self.lease_owner,
                    self.lease_until,
                    self.durable_state,
                ) = snapshot
                self.rollbacks += 1
                raise
            else:
                self.commits += 1
            finally:
                self.actor = self.worker = None

    @contextmanager
    def begin_nested(self):
        yield self  # outer request snapshot provides rollback on any exception

    def authorized(self):
        return (
            self.approval_active
            and self.executor != self.approver
            and "operations" in self.roles.get(self.executor, set())
            and "security_admin" in self.roles.get(self.approver, set())
        )

    def export(self):
        return {
            "executor": str(self.executor),
            "approver": str(self.approver),
            "approval_id": str(self.approval),
            "printer_key_fingerprint": self.fingerprint,
            "pair_count": self.count,
            "identity_sha256": self.identity,
            "pairs": deepcopy(self.pairs),
            "manifest_sha256": self.checksum,
            "source": self.source,
            "revision": self.job["revision"] if self.job else 0,
            "job": deepcopy(self.job),
        }

    def gone(self, value):
        g = self.grants.get(value.get("grant_id"))
        return not (
            g
            and self.job
            and self.job["status"] == "ready"
            and g["job_id"] == value["job_id"]
            and g["session_id"] == value["session_id"]
            and g["actor"] == self.actor
            and not g["used"]
            and not g["superseded"]
            and g["until"] > time.time()
            and g["revision"] == self.job["revision"]
        )

    def execute(self, statement, params=None):
        sql, p = str(statement), params or {}
        self.statements.append(sql)
        if "set_config('safereturn.actor_id'" in sql:
            self.actor, self.worker = p.get("actor", ""), p.get("worker")
            return Result(None)
        if "SET LOCAL ROLE" in sql or "set_config('safereturn.mfa_verified'" in sql:
            return Result(None)
        if "sr_account_session_state" in sql:
            return Result(
                SimpleNamespace(email_verified=True, mfa_active=self.mfa)
                if self.active
                else None
            )
        if "SELECT 1 FROM public.staff_roles" in sql:
            return Result(
                1 if self.roles.get(p["uid"], set()).intersection(p["roles"]) else None
            )
        if "sr_mfg_context" in sql:
            if (
                str(p["bid"]) != str(self.batch)
                or self.actor != str(self.executor)
                or not self.authorized()
            ):
                return Result(None)
            return Result(
                self.export()
                if self.eligible
                else {"error": "BATCH_RECONCILIATION_REQUIRED"}
            )
        if "sr_mfg_apply" in sql:
            if (
                p["bid"] != self.batch
                or self.actor != str(self.executor)
                or not self.authorized()
            ):
                return Result(None)
            return Result(self.apply(p["op"], json.loads(p["body"])))
        if "sr_mfg_claim" in sql:
            if (
                not self.authorized()
                or not self.eligible
                or not self.job
                or self.job["status"] != "queued"
                or self.durable_state in {"completed", "dead"}
                or self.retry_after > time.time()
                or (self.durable_state == "leased" and self.lease_until > time.time())
            ):
                return Result(None)
            if self.attempt >= 5:
                self.job.update(status="failed", revision=self.job["revision"] + 1)
                self.durable_state = "dead"
                return Result(None)
            self.attempt += 1
            self.lease_owner, self.lease_until = self.worker, time.time() + 180
            self.durable_state = "leased"
            return Result(
                {
                    "job_id": self.job["job_id"],
                    "batch_id": str(self.batch),
                    "owner": self.worker,
                    "attempt": self.attempt,
                    "revision": self.job["revision"],
                    "pair_count": self.count,
                    "identity_sha256": self.identity,
                    "pairs": deepcopy(self.pairs),
                    "manifest_sha256": self.checksum,
                    "source": self.source,
                }
            )
        if "sr_mfg_finish" in sql:
            v = json.loads(p["body"])
            if (
                not self.authorized()
                or not self.eligible
                or self.worker != self.lease_owner
                or v["owner"] != self.lease_owner
                or v["attempt"] != self.attempt
                or self.lease_until <= time.time()
                or v["pairs"] != self.pairs
                or v["manifest_sha256"] != self.checksum
            ):
                return Result(False)
            self.lease_owner, self.lease_until = None, 0
            if v["success"]:
                self.job.update(
                    status="ready",
                    revision=self.job["revision"] + 1,
                    attempt_count=self.attempt,
                )
                self.durable_state = "completed"
                self.events.append("ready")
            else:
                self.durable_state = "dead" if self.attempt >= 5 else "retry"
                self.retry_after = time.time() + 30
                if self.attempt >= 5:
                    self.job.update(status="failed", revision=self.job["revision"] + 1)
            return Result(True)
        if "sr_mfg_handoff_context" in sql:
            if (
                self.actor != str(self.approver)
                or not self.authorized()
                or self.job["status"] != "awaiting_ack"
            ):
                return Result(None)
            pub = self.custody.public_key().public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw
            )
            return Result(
                {
                    "job_id": self.job["job_id"],
                    "revision": self.job["revision"],
                    "delivery_id": self.delivery,
                    "manifest_sha256": self.checksum,
                    "printer_key_fingerprint": self.fingerprint,
                    "acknowledgement_public_key": base64.b64encode(pub).decode(),
                }
            )
        if "sr_mfg_record_handoff" in sql:
            record = json.loads(p["body"])["record"]
            self.job.update(
                status="accepted" if record["outcome"] == "accepted" else "ready",
                revision=self.job["revision"] + 1,
            )
            self.events.append(record["outcome"])
            return Result(True)
        raise AssertionError("Unexpected SQL in narrow manufacturing fixture: " + sql)

    def apply(self, op, v):
        if not self.eligible:
            return {"error": "BATCH_RECONCILIATION_REQUIRED"}
        if op == "receipt":
            return self.receipts.get(v["scope"], {})
        if op == "save_receipt":
            if self.fail_receipt:
                raise OperationalError("INSERT", {}, Exception(SECRET))
            self.receipts[v["scope"]] = v
            return {}
        if op == "enqueue":
            if self.job or v["expected_revision"] != 0:
                return {"error": "VERSION_MISMATCH"}
            self.job = {
                "job_id": v["job_id"],
                "batch_id": str(self.batch),
                "revision": 1,
                "status": "queued",
                "manifest_sha256": self.checksum,
                "attempt_count": 0,
            }
            self.events.append("queued")
            return {k: val for k, val in self.job.items() if k != "attempt_count"}
        if not self.job or v["job_id"] != self.job["job_id"]:
            return None
        if op == "grant":
            if self.job["status"] != "ready":
                return {"error": "HANDOFF_RECONCILIATION_REQUIRED"}
            if self.job["revision"] != v["expected_revision"]:
                return {"error": "VERSION_MISMATCH"}
            for g in self.grants.values():
                if g["session_id"] == v["session_id"]:
                    g["superseded"] = True
            g = {
                **v,
                "actor": self.actor,
                "used": False,
                "superseded": False,
                "revision": self.job["revision"],
                "until": time.time() + 299,
            }
            self.grants[v["grant_id"]] = g
            self.events.append("grant_issued")
            return {
                "grant_id": v["grant_id"],
                "job_id": v["job_id"],
                "revision": self.job["revision"],
                "expires_at": datetime.fromtimestamp(g["until"], UTC).isoformat(),
            }
        if op in {"grant_live", "consume"}:
            if self.gone(v):
                return {"error": "GRANT_GONE"}
            g = self.grants[v["grant_id"]]
            if op == "grant_live":
                return {"token_hash": g["token_hash"]}
            if g["token_hash"] != v["token_hash"]:
                return {"error": "GRANT_GONE"}
            g["used"] = True
            for other in self.grants.values():
                if other is not g:
                    other["superseded"] = True
            self.delivery = v["grant_id"]
            self.job.update(status="awaiting_ack", revision=self.job["revision"] + 1)
            self.events.append("download_consumed")
            return {}
        raise AssertionError(op)


@pytest.fixture(scope="module")
def envelope():
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    batch_id = uuid4()
    return create_sealed_insert(
        key.public_key(),
        {
            "batch_id": str(batch_id),
            "pairs": [
                {
                    "pair_reference": "SYNTHETIC-PAIR",
                    "activation_secret": SECRET,
                    "tags": [
                        {
                            "tag_type": "lost",
                            "public_token": "SYNTHETIC_LOST_TOKEN_CANARY",
                        },
                        {
                            "tag_type": "ice",
                            "public_token": "SYNTHETIC_ICE_TOKEN_CANARY",
                        },
                    ],
                }
            ],
        },
    ), batch_id


@pytest.fixture
def env(verifier, envelope):
    provider, private, _, _ = verifier
    settings = Settings(
        manufacturing_exports_enabled=True,
        manufacturing_export_web_origin=ORIGIN,
        profile_data_keys=SecretStr(
            json.dumps({"1": base64.b64encode(b"M" * 32).decode()})
        ),
    )
    actor, sid = uuid4(), uuid4()
    db = Store(actor, settings, envelope)
    app = create_app(settings)
    app.state.database, app.state.jwt_verifier = db, provider

    def headers(uid=actor, session=sid, **overrides):
        token = claims(
            sub=str(uid),
            session_id=str(session),
            aal="aal2",
            amr=[{"method": "totp", "timestamp": int(time.time())}],
        )
        token.update(overrides)
        return {
            "Authorization": "Bearer " + signed(private, token),
            "Origin": ORIGIN,
            "Idempotency-Key": "synthetic-initial-54a",
        }

    return ASGIClient(app), db, headers, settings, app


def path(db):
    return f"/api/v1/admin/qr-batches/{db.batch}/print-exports"


def enqueue(env, headers=None, **overrides):
    c, db, h, _, _ = env
    body = {
        "expected_revision": 0,
        "printer_key_fingerprint": db.fingerprint,
        "production_approval_id": str(db.approval),
        "reason_code": "initial_transport",
        "confirmed": True,
    }
    body.update(overrides)
    return c.post(path(db), headers=headers if headers is not None else h(), json=body)


def ready(env):
    assert enqueue(env).status_code == 202
    assert run_one(env[1], env[3], env[1].batch)
    return env[1].job["job_id"]


def grant(env, key="synthetic-grant-54a", headers=None, **overrides):
    c, db, h, _, _ = env
    body = {"expected_revision": db.job["revision"], "confirmed": True}
    body.update(overrides)
    return c.post(
        path(db) + f"/{db.job['job_id']}/download-grants",
        headers=headers if headers is not None else {**h(), "Idempotency-Key": key},
        json=body,
    )


def consume(env, receipt, headers=None):
    c, db, h, _, _ = env
    return c.post(
        path(db) + f"/{db.job['job_id']}/download",
        headers={
            **(headers if headers is not None else h()),
            "X-Print-Grant": receipt["grant_id"] + "." + receipt["grant_token"],
        },
    )


def handoff(db, outcome="not_received", **overrides):
    record = Handoff(
        format="safereturn-printer-handoff-v1",
        batch_id=db.batch,
        job_id=db.job["job_id"],
        revision=db.job["revision"],
        manifest_sha256=db.checksum,
        printer_key_fingerprint=db.fingerprint,
        delivery_id=db.delivery,
        outcome=outcome,
    ).model_dump(mode="json")
    record.update(overrides)
    signature = base64.b64encode(db.custody.sign(canonical(record).encode())).decode()
    return record, signature


def import_handoff(db, outcome="not_received"):
    record, signature = handoff(db, outcome)
    with db.transaction():
        db.actor = str(db.approver)
        record_handoff(db, record, signature)


def test_complete_opaque_transport_immutable_counts_safe_projections(env, caplog):
    caplog.set_level("INFO")
    c, db, h, settings, _ = env
    before = deepcopy(db.history)
    jid = ready(env)
    metadata = c.get(path(db) + "/" + jid, headers=h())
    assert metadata.status_code == 200
    assert set(metadata.json()) == {
        "job_id",
        "batch_id",
        "revision",
        "status",
        "manifest_sha256",
        "pair_count",
        "tag_count",
        "attempt_count",
        "physical_release_enabled",
    }
    assert metadata.json()["tag_count"] == 2 and metadata.json()["pair_count"] == 1
    assert metadata.json()["physical_release_enabled"] is False
    g = grant(env)
    assert g.status_code == 200
    response = consume(env, g.json())
    assert response.status_code == 200 and response.content == db.raw
    assert (
        response.headers["content-type"]
        == "application/vnd.safereturn.sealed-insert+json"
    )
    assert db.job["status"] == "awaiting_ack" and db.history == before
    assert consume(env, g.json()).status_code == 410
    assert grant(env, key="synthetic-second-grant").status_code == 409
    assert SECRET not in (
        response.text + metadata.text + g.text + caplog.text + repr(db.events)
    )
    assert "SYNTHETIC_LOST_TOKEN_CANARY" not in metadata.text
    assert g.json()["grant_token"] not in repr(db.receipts)
    assert all(
        unpack(settings, db.batch, "receipt:" + scope, value)
        for scope, value in db.receipts.items()
    )
    assert db.history == before


@pytest.mark.parametrize(
    "fault",
    [
        "anonymous",
        "expired",
        "revoked_session",
        "aal1",
        "provider_mfa",
        "missing_amr",
        "stale_amr",
        "future_amr",
        "wrong_origin",
        "duplicate_origin",
        "revoked_approval",
        "same_custodian",
        "wrong_executor",
        "revoked_custodian",
        "disabled",
    ],
)
def test_guards_on_all_four_routes_before_material(env, fault):
    c, db, h, settings, _ = env
    ready(env)
    hdr = h()
    expected = 403
    if fault == "anonymous":
        hdr = {}
        expected = 401
    elif fault == "expired":
        hdr = h(exp=int(time.time()) - 100)
        expected = 401
    elif fault == "revoked_session":
        db.active = False
        expected = 401
    elif fault == "aal1":
        hdr = h(aal="aal1")
    elif fault == "provider_mfa":
        db.mfa = False
    elif fault == "missing_amr":
        hdr = h(amr=[])
    elif fault == "stale_amr":
        hdr = h(amr=[{"method": "totp", "timestamp": int(time.time()) - 301}])
    elif fault == "future_amr":
        hdr = h(amr=[{"method": "totp", "timestamp": int(time.time()) + 30}])
    elif fault == "wrong_origin":
        hdr["Origin"] = "https://foreign.test"
    elif fault == "duplicate_origin":
        hdr = list(hdr.items()) + [("Origin", ORIGIN)]
    elif fault == "revoked_approval":
        db.approval_active = False
        expected = 404
    elif fault == "same_custodian":
        db.approver = db.executor
        expected = 404
    elif fault == "wrong_executor":
        db.executor = uuid4()
        expected = 404
    elif fault == "revoked_custodian":
        db.roles[db.approver] = set()
        expected = 404
    elif fault == "disabled":
        settings.manufacturing_exports_enabled = False
        expected = 503
    before = deepcopy((db.job, db.grants, db.receipts, db.events))
    responses = [
        enqueue(env, headers=hdr),
        grant(env, headers=hdr),
        c.post(path(db) + f"/{db.job['job_id']}/download", headers=hdr),
    ]
    if fault not in {"wrong_origin", "duplicate_origin"}:
        responses.append(c.get(path(db) + "/" + db.job["job_id"], headers=hdr))
    for response in responses:
        assert response.status_code == expected, response.text
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert SECRET not in response.text
    assert before == (db.job, db.grants, db.receipts, db.events)


@pytest.mark.parametrize(
    "role", ["finance", "support", "security_admin", "superadmin", "customer"]
)
def test_wrong_role_has_no_implicit_authority(env, role):
    db = env[1]
    db.roles[db.executor] = {role}
    assert enqueue(env).status_code == 403
    assert db.job is None


@pytest.mark.parametrize(
    "change",
    [
        "printer",
        "approval",
        "revision",
        "pair",
        "count",
        "three_tags",
        "same_tag",
        "duplicate_token",
        "released",
    ],
)
def test_printer_provenance_identity_version_conflicts(env, change):
    db = env[1]
    overrides = {}
    if change == "printer":
        overrides["printer_key_fingerprint"] = "b" * 64
    elif change == "approval":
        overrides["production_approval_id"] = str(uuid4())
    elif change == "revision":
        overrides["expected_revision"] = 1
    elif change == "pair":
        db.pairs[0]["tags"][0]["public_token"] = "CHANGED_SYNTHETIC_TOKEN_CANARY"
    elif change == "count":
        db.count = 2
    elif change == "three_tags":
        db.pairs[0]["tags"].append(deepcopy(db.pairs[0]["tags"][0]))
    elif change == "same_tag":
        db.pairs[0]["tags"][0]["tag_type"] = "ice"
    elif change == "duplicate_token":
        db.pairs[0]["tags"][0]["public_token"] = db.pairs[0]["tags"][1]["public_token"]
    elif change == "released":
        db.eligible = False
    r = enqueue(env, **overrides)
    assert r.status_code in {409, 503}
    assert db.job is None and not db.receipts


def test_idempotency_versions_same_byte_retry_and_unknown_ack(env):
    _, db, h, _, _ = env
    first = enqueue(env)
    assert first.status_code == 202
    assert enqueue(env).json() == first.json()
    assert enqueue(env, reason_code="same_payload_retry").status_code == 409
    assert len(db.receipts) == 1 and db.events.count("queued") == 1
    assert (
        enqueue(
            env,
            headers={**h(), "Idempotency-Key": "different-key"},
            expected_revision=1,
            reason_code="same_payload_retry",
        ).json()
        == first.json()
    )
    assert run_one(db, env[3], db.batch)
    g = grant(env).json()
    assert grant(env).json() == g
    assert consume(env, g).status_code == 200
    assert enqueue(env).status_code == 409
    assert grant(env, expected_revision=g["revision"]).status_code == 410
    assert grant(env).status_code == 409  # same key with a changed request body
    import_handoff(db)
    assert db.job["status"] == "ready"
    retry = enqueue(
        env,
        headers={**h(), "Idempotency-Key": "reconciled-byte-retry"},
        expected_revision=db.job["revision"],
        reason_code="same_payload_retry",
    )
    assert retry.status_code == 202 and retry.json()["job_id"] == first.json()["job_id"]
    assert consume(env, grant(env, key="after-reconciliation").json()).content == db.raw
    import_handoff(db, "accepted")
    assert db.job["status"] == "accepted"
    assert grant(env, key="after-acceptance").status_code == 409
    assert enqueue(env).status_code == 409
    assert db.events.count("queued") == 1


def test_grant_supersession_expiry_wrong_session_wrong_verifier(env):
    ready(env)
    _, db, h, _, _ = env
    old = grant(env).json()
    new = grant(env, key="new-grant-supersedes").json()
    assert consume(env, old).status_code == 410
    assert grant(env).status_code == 410
    assert consume(env, new, headers=h(session=uuid4())).status_code == 410
    assert consume(env, {**new, "grant_token": "A" * 43}).status_code == 410
    db.grants[new["grant_id"]]["until"] = time.time() - 1
    assert consume(env, new).status_code == 410
    assert db.job["status"] == "ready"


@pytest.mark.parametrize("failure", ["fail_commit", "fail_receipt", "crypto"])
def test_enqueue_atomic_rollback_and_safe_errors(env, failure, caplog):
    _, db, _, settings, _ = env
    if failure == "crypto":
        settings.profile_data_keys = None
    else:
        setattr(db, failure, True)
    response = enqueue(env)
    assert response.status_code == 503
    assert db.job is None and not db.receipts and not db.events
    assert SECRET not in response.text + caplog.text


@pytest.mark.parametrize(
    "failure",
    [
        "cipher_tamper",
        "checksum",
        "truncated",
        "provider_write_partial",
        "provider_lost_ack",
        "provider_read_failure",
    ],
)
def test_bounded_spool_failures_cannot_publish_ready(env, failure):
    assert enqueue(env).status_code == 202
    db = env[1]
    reader = None
    if failure == "cipher_tamper":
        db.source["cipher"] = base64.b64encode(b"SRD1" + b"X" * 80).decode()
    elif failure == "checksum":
        db.checksum = "b" * 64
    elif failure == "truncated":
        reader = lambda data: [data[:-1]]
    elif failure == "provider_write_partial":
        memory_provider = {}

        def reader(data):
            memory_provider["synthetic-staging"] = data[: len(data) // 2]
            return [memory_provider["synthetic-staging"]]
    elif failure == "provider_lost_ack":

        def reader(data):
            raise OSError(SECRET)
    elif failure == "provider_read_failure":

        def reader(data):
            yield data[:20]
            raise OSError(SECRET)

    assert run_one(db, env[3], db.batch, spool_reader=reader) is False
    assert db.job["status"] == "queued" and db.durable_state == "retry"
    assert grant(env).status_code == 409


def test_stale_lease_competing_worker_and_recovery(env):
    assert enqueue(env).status_code == 202
    db = env[1]

    def expire():
        db.lease_until = time.time() - 1

    with pytest.raises(LeaseLost):
        run_one(db, env[3], db.batch, before_finish=expire)
    assert db.job["status"] == "queued" and "ready" not in db.events
    assert run_one(db, env[3], db.batch)
    assert db.attempt == 2 and db.events.count("ready") == 1


def test_competing_workers_exactly_one_ready_and_consumers_one_winner(env):
    assert enqueue(env).status_code == 202
    db = env[1]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run_one(db, env[3], db.batch), range(2)))
    assert sorted(results) == [False, True]
    assert db.events.count("ready") == 1 and db.attempt == 1
    g = grant(env).json()
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: consume(env, g), range(2)))
    assert sorted(r.status_code for r in responses) == [200, 410]
    assert db.events.count("download_consumed") == 1


@pytest.mark.parametrize("change", ["revoke", "pair", "release", "competitor"])
def test_pre_completion_changes_fence_worker(env, change):
    assert enqueue(env).status_code == 202
    db = env[1]

    def mutate():
        if change == "revoke":
            db.approval_active = False
        elif change == "pair":
            db.pairs[0]["tags"][0]["public_token"] = "CHANGED_TOKEN_DURING_PROCESSING"
        elif change == "release":
            db.eligible = False
        elif change == "competitor":
            db.lease_owner = "another-worker"

    with pytest.raises(LeaseLost):
        run_one(db, env[3], db.batch, before_finish=mutate)
    assert "ready" not in db.events


def test_bounded_attempts_and_retry_delay(env):
    assert enqueue(env).status_code == 202
    db = env[1]
    for attempt in range(5):
        db.retry_after = 0
        assert (
            run_one(db, env[3], db.batch, spool_reader=lambda data: [data[:-1]])
            is False
        )
        assert db.attempt == attempt + 1
        assert run_one(db, env[3], db.batch) is False
    assert db.durable_state == "dead" and db.job["status"] == "failed"
    assert grant(env).status_code == 409


@pytest.mark.parametrize(
    "fault", ["signature", "printer", "checksum", "revision", "delivery", "recorder"]
)
def test_independent_signed_handoff_rejects_mismatch(env, fault):
    ready(env)
    db = env[1]
    assert consume(env, grant(env).json()).status_code == 200
    record, signature = handoff(db)
    if fault == "signature":
        signature = base64.b64encode(b"x" * 64).decode()
    elif fault == "printer":
        record["printer_key_fingerprint"] = "b" * 64
    elif fault == "checksum":
        record["manifest_sha256"] = "b" * 64
    elif fault == "revision":
        record["revision"] += 1
    elif fault == "delivery":
        record["delivery_id"] = str(uuid4())
    if fault in {"printer", "checksum", "revision", "delivery"}:
        signature = base64.b64encode(
            db.custody.sign(canonical(record).encode())
        ).decode()
    with pytest.raises(TransportConflict), db.transaction():
        db.actor = str(db.executor if fault == "recorder" else db.approver)
        record_handoff(db, record, signature)
    assert db.job["status"] == "awaiting_ack"


def test_closed_requests_canaries_and_private_validation(env):
    _, _, h, _, app = env
    assert enqueue(env, confirmed="true").status_code == 422
    result = enqueue(env, extra_secret=SECRET)
    assert result.status_code == 422 and SECRET not in result.text
    for hdr in (
        {**h(), "Idempotency-Key": "tiny"},
        {k: v for k, v in h().items() if k != "Idempotency-Key"},
    ):
        r = enqueue(env, headers=hdr)
        assert r.status_code == 400 and SECRET not in r.text
    schema = app.openapi()["paths"]
    root = "/api/v1/admin/qr-batches/{batch_id}/print-exports"
    for suffix, method, ident in [
        ("", "post", "API-093"),
        ("/{job_id}", "get", "API-336"),
        ("/{job_id}/download", "post", "API-337"),
        ("/{job_id}/download-grants", "post", "API-338"),
    ]:
        assert schema[root + suffix][method]["operationId"] == ident
    assert not any("handoff" in p or "manufacturing-approval" in p for p in schema)


def test_opaque_crypto_integrity_boundaries_and_no_plaintext_recovery(env):
    db, s = env[1], env[3]
    assert sealed_bytes(db.raw, db.checksum) == db.raw
    assert unpack(s, db.batch, "source", db.source) == db.raw
    with pytest.raises(ValueError):
        unpack(s, uuid4(), "source", db.source)
    for value in (b"", b"X" * 2_000_001, db.raw[:-1]):
        with pytest.raises(TransportConflict):
            read_spool([value], db.checksum)
    assert SECRET.encode() not in db.raw
    assert not hasattr(db, "printer_private_key")


def test_source_enrollment_frozen_request_proof_and_exact_metadata(env):
    db, settings = env[1], env[3]
    model = {
        "pair_count": 1,
        "printer_key_fingerprint": db.fingerprint,
        "verifier_key_version": 1,
    }
    value = source_record(
        settings, db.batch, "synthetic-generation", model, db.pairs, db.raw
    )
    assert value["generation_request"] == canonical(model)
    assert value["identity_sha256"] == db.identity
    assert unpack(settings, db.batch, "source", value) == db.raw
    assert db.history[1] == db.pairs
    with pytest.raises(TransportConflict):
        source_record(
            settings,
            db.batch,
            "synthetic-generation",
            {**model, "pair_count": 2},
            db.pairs,
            db.raw,
        )


def test_offline_migration_upgrade_downgrade_capture_only(env):
    file = SQL_FILE.with_suffix(".py")
    spec = importlib.util.spec_from_file_location("mfg_migration", file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = Path(__file__).parents[2] / "output/task54a"
    output.mkdir(parents=True, exist_ok=True)
    for name in ("upgrade", "downgrade"):
        buf = io.StringIO()
        context = MigrationContext.configure(
            dialect_name="postgresql", opts={"as_sql": True, "output_buffer": buf}
        )
        with Operations.context(context):
            getattr(module, name)()
        rendered = buf.getvalue()
        (output / (name + ".sql")).write_text(rendered, encoding="utf-8")
        assert "manufacturing" in rendered and "CASCADE" not in rendered
    assert module.down_revision == "0026_finance_reconciliation"
    sql = SQL_FILE.read_text()
    assert "FOR UPDATE SKIP LOCKED" in sql
    assert (
        "lease_until>clock_timestamp()" in sql
        and "attempt_count=(body->>'attempt')::integer" in sql
    )
    assert (
        "GRANT EXECUTE ON FUNCTION public.sr_mfg_claim(uuid),public.sr_mfg_finish(uuid,jsonb) TO safereturn_worker"
        in sql
    )
    assert "GRANT EXECUTE ON FUNCTION public.sr_mfg_provision" not in sql
    assert "FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker" in sql
    assert "q.public_status<>'unactivated'" in sql


@pytest.mark.parametrize("mode", ["disabled", "enabled", "enrollment_failure"])
def test_generation_source_enrollment_is_atomic_and_preserves_api090(env, mode):
    c, db, h, settings, _ = env
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    settings.print_recipient_public_key = SecretStr(
        key.public_key()
        .public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        .decode()
    )
    settings.activation_verifier_key = SecretStr(base64.b64encode(b"V" * 32).decode())
    settings.manufacturing_exports_enabled = mode != "disabled"
    generated = {}
    original = db.execute

    def execute(statement, params=None):
        sql, p = str(statement), params or {}
        if "pg_advisory_xact_lock" in sql:
            return Result(None)
        if "FROM public.idempotency_records" in sql:
            return Result(None)
        if "SELECT 1 FROM public.qr_batches" in sql:
            return Result(None)
        if "INSERT INTO public.idempotency_records" in sql:
            generated["request_hash"] = p["request_hash"]
        elif "UPDATE public.idempotency_records" in sql:
            generated["sealed"] = p["body"]
        elif "INSERT INTO public.qr_batches" in sql:
            generated["batch"] = p["id"]
        elif "INSERT INTO public.tag_pairs" in sql:
            generated["pairs"] = p
        elif "INSERT INTO public.qr_codes" in sql:
            generated["tags"] = p
        elif "INSERT INTO public.pair_activation_credentials" in sql:
            generated["verifiers"] = p
        elif "INSERT INTO public.audit_events" in sql:
            generated["audit"] = p
        elif "sr_mfg_register" in sql:
            v = json.loads(p["body"])
            assert v["pair_count"] == 2 and len(v["pairs"]) == 2
            assert all(
                {t["tag_type"] for t in pair["tags"]} == {"lost", "ice"}
                for pair in v["pairs"]
            )
            assert len(generated["tags"]) == 4 and len(generated["verifiers"]) == 2
            assert unpack(settings, p["bid"], "source", v) == generated["sealed"]
            assert sha(v["generation_request"].encode()) == generated["request_hash"]
            generated["enrollment"] = v
            return Result(mode != "enrollment_failure")
        else:
            return original(statement, params)
        return Result(None)

    db.execute = execute
    response = c.post(
        "/api/v1/admin/qr-batches",
        headers=h(),
        json={
            "pair_count": 2,
            "batch_label": "SYNTHETIC-54A-GENERATION",
            "logo_template_key": "safe-return-primary",
            "qr_ecc": "Q",
            "print_material": "synthetic-vinyl",
            "intended_environment": "outdoor",
            "lost_symbol_size_mm": 35,
            "ice_symbol_size_mm": 35,
        },
    )
    if mode == "enrollment_failure":
        assert response.status_code == 503
        assert db.job is None and db.rollbacks == 1 and db.commits == 0
    else:
        assert response.status_code == 201
        assert (
            response.json()["generated_pair_count"] == 2
            and response.json()["generated_qr_count"] == 4
        )
        assert (
            canonical(response.json()["sealed_insert"]).encode() == generated["sealed"]
        )
        assert ("enrollment" in generated) == (mode == "enabled")
        assert db.commits == 1 and db.rollbacks == 0
    assert SECRET not in response.text


@pytest.mark.parametrize("stage", ["grant", "consume", "worker"])
def test_mutation_commit_failure_preserves_unconsumed_state(env, stage):
    ready(env) if stage != "worker" else enqueue(env)
    db = env[1]
    g = grant(env).json() if stage == "consume" else None
    before = deepcopy((db.job, db.grants, db.events, db.receipts))
    db.fail_commit = True
    if stage == "worker":
        with pytest.raises(OperationalError):
            run_one(db, env[3], db.batch)
    else:
        response = (
            grant(env, key="failing-grant") if stage == "grant" else consume(env, g)
        )
        assert response.status_code == 503
    assert (db.job, db.grants, db.events, db.receipts) == before


def test_cross_batch_cross_job_and_worker_disabled_denials(env):
    ready(env)
    c, db, h, settings, _ = env
    assert c.get(path(db) + "/" + str(uuid4()), headers=h()).status_code == 404
    assert (
        c.get(
            f"/api/v1/admin/qr-batches/{uuid4()}/print-exports/{db.job['job_id']}",
            headers=h(),
        ).status_code
        == 404
    )
    settings.manufacturing_exports_enabled = False
    with pytest.raises(TransportConflict):
        run_one(db, settings, db.batch)


def test_malformed_grants_never_expose_material(env):
    ready(env)
    c, db, h, _, _ = env
    route = path(db) + f"/{db.job['job_id']}/download"
    for value in (
        None,
        "-" * 36 + "." + "A" * 43,
        "not-a-grant",
        str(uuid4()) + "." + "A" * 43,
    ):
        headers = h()
        if value is not None:
            headers["X-Print-Grant"] = value
        response = c.post(route, headers=headers)
        assert response.status_code == 410 and SECRET not in response.text
    g = grant(env).json()
    headers = (
        list(h().items())
        + [("X-Print-Grant", g["grant_id"] + "." + g["grant_token"])] * 2
    )
    assert c.post(route, headers=headers).status_code == 410
    assert db.job["status"] == "ready"


def test_pair_manifest_bounds_and_malformed_tags():
    pairs = [
        {
            "pair_reference": f"SYNTHETIC-{i}",
            "tags": [
                {"tag_type": kind, "public_token": f"SYNTHETIC-54A-{kind}-{i:08d}"}
                for kind in ("lost", "ice")
            ],
        }
        for i in range(1000)
    ]
    assert identity_snapshot(pairs)[0] == 1000
    for invalid in (
        [],
        pairs + [pairs[0]],
        [{"pair_reference": "bad", "tags": [None, {}]}],
    ):
        with pytest.raises(TransportConflict):
            identity_snapshot(invalid)


def test_receipt_tamper_and_authority_checked_before_replay(env):
    ready(env)
    db = env[1]
    assert grant(env).status_code == 200
    scope = next(reversed(db.receipts))
    db.receipts[scope]["cipher"] = base64.b64encode(b"SRD1" + b"x" * 64).decode()
    assert grant(env).status_code == 503
    db.approval_active = False
    assert grant(env).status_code == 404
