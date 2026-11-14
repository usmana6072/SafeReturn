"""5.3A synthetic policy/HTTP/transaction checks; SQL semantics remain a DB gate."""

import base64
import json
import time
from contextlib import contextmanager
from copy import deepcopy
from threading import RLock
from uuid import uuid4

import pytest
from sqlalchemy.exc import OperationalError
from test_auth import claims, signed
from test_auth import verifier as _verifier
from test_critical_workflow_boundaries import MemoryDatabase, Result
from test_health import ASGIClient

from app.api.v1.cancellations import release_eligible
from app.core.config import Settings
from app.main import create_app

verifier = _verifier
ORIGIN = "https://synthetic.test"


def eligible_snapshot():
    return {
        "order_status": "placed",
        "payment_status": "awaiting_transfer",
        "fulfillment_status": "unallocated",
        "attempt_states": [],
        "production": False,
        "shipment": False,
        "units": [
            {
                "status": "reserved",
                "ownership_status": "unclaimed",
                "owner_user_id": None,
                "activated_at": None,
                "inventory_status": "qa_passed",
            }
        ],
    }


class CancellationMemory(MemoryDatabase):
    """Storage/SQL-function stand-in only, never evidence of SQL/RLS behavior."""

    def __init__(self, owner, order):
        super().__init__(owner, order)
        self.order_revision, self.request_revision = 1, 0
        self.request_id, self.status, self.initial = None, None, None
        self.pair = uuid4()
        self.snapshot = eligible_snapshot()
        self.receipts, self.attestations, self.events = {}, {}, []
        self.role_map = {}
        self.fail_receipt = False
        self.lock = RLock()
        self.business_history = {
            "shipping": "Synthetic frozen address",
            "line": "Synthetic frozen item",
            "qr_uses": ["synthetic-lost", "synthetic-ice"],
            "settlements": [],
        }

    @contextmanager
    def transaction(self):
        with self.lock:
            fields = [
                "order_revision",
                "request_revision",
                "request_id",
                "status",
                "initial",
                "snapshot",
                "receipts",
                "attestations",
                "events",
                "audit",
                "business_history",
            ]
            before = {f: deepcopy(getattr(self, f)) for f in fields}
            try:
                yield self
                if self.fail_commit:
                    raise OperationalError(
                        "COMMIT", {}, Exception("PRIVATE_COMMIT_CANARY")
                    )
            except BaseException:
                for f, v in before.items():
                    setattr(self, f, v)
                raise

    @contextmanager
    def begin_nested(self):
        yield self

    def execute(self, statement, params=None):
        sql, p = str(statement), params or {}
        if "pg_advisory_xact_lock" in sql:
            return Result(None)
        if "FROM public.staff_roles" in sql:
            return Result(
                1
                if self.role_map.get(p["uid"], set()).intersection(p["roles"])
                else None
            )
        if "FROM public.idempotency_records" in sql:
            return Result(self.receipts.get((p["actor"], p["op"], p["key"])))
        if sql.startswith("INSERT INTO public.idempotency_records"):
            if self.fail_receipt:
                raise OperationalError(
                    "INSERT", {}, Exception("PRIVATE_RECEIPT_CANARY")
                )
            self.receipts[(p["actor"], p["op"], p["key"])] = {
                "request_hash": p["hash"],
                "response_body_ciphertext": p["cipher"],
                "response_key_version": p["version"],
            }
            return Result(None)
        if "sr_cancellation_eligibility" in sql:
            return Result(deepcopy(self.snapshot))
        if "sr_cancellation_command" in sql:
            data = json.loads(p["payload"])
            action = p["action"]
            error = lambda code: Result({"error": code})
            if (
                action == "request"
                and (p["oid"] != self.order or str(self.actor) != str(self.owner))
            ) or (action == "release" and p["pid"] != self.pair):
                return error("NOT_FOUND")
            expected = data.get(
                "expected_revision", data.get("expected_order_revision")
            )
            if expected != self.order_revision:
                return error("VERSION_MISMATCH")
            if action == "request":
                if self.snapshot["order_status"] in {"draft", "fulfilled", "cancelled"}:
                    return error("CANCELLATION_UNAVAILABLE")
                if self.status in {
                    "requested",
                    "investigating",
                    "approved",
                    "escalated",
                }:
                    return Result(self.initial)
                self.request_id, self.request_revision, self.status = (
                    str(uuid4()),
                    1,
                    "requested",
                )
                self.initial = {
                    "request_id": self.request_id,
                    "order_id": str(self.order),
                    "request_status": "requested",
                    "revision": self.order_revision,
                    "next_action": "await_review",
                }
                result = self.initial
            else:
                if data["request_id"] != self.request_id:
                    return error("NOT_FOUND")
                if data["expected_request_revision"] != self.request_revision:
                    return error("VERSION_MISMATCH")
                if action == "reconcile":
                    if self.status != "investigating":
                        return error("REVIEW_REQUIRED")
                    aid = str(uuid4())
                    self.attestations[aid] = {
                        "actor": str(self.actor),
                        "revision": self.order_revision,
                        "request_revision": self.request_revision,
                        "outcome": data["outcome"],
                        "expired": False,
                        "consumed": False,
                    }
                    return Result(
                        {
                            "reconciliation_id": aid,
                            "order_revision": self.order_revision,
                            "request_revision": self.request_revision,
                            "valid_until": "2099-01-01T00:00:00Z",
                            "outcome": data["outcome"],
                        }
                    )
                target = {
                    "investigate": "investigating",
                    "approve": "approved",
                    "reject": "rejected",
                    "escalate": "escalated",
                }.get(data.get("decision"), "completed")
                if action == "release" and self.status != "approved":
                    return error("REVIEW_REQUIRED")
                if action == "decision" and not (
                    (
                        self.status in {"requested", "escalated"}
                        and target == "investigating"
                    )
                    or (
                        self.status == "investigating"
                        and target in {"approved", "rejected", "escalated"}
                    )
                ):
                    return error("INVALID_TRANSITION")
                if target in {"approved", "completed"}:
                    a = self.attestations.get(data["reconciliation_id"])
                    if (
                        not a
                        or a["actor"] == str(self.actor)
                        or a["outcome"] != "clear"
                        or a["consumed"]
                    ):
                        return error("INDEPENDENT_RECONCILIATION_REQUIRED")
                    if (
                        a["expired"]
                        or a["revision"] != self.order_revision
                        or not data.get("application_clear")
                    ):
                        target = "investigating"
                    elif action == "release":
                        self.snapshot["order_status"] = "cancelled"
                        self.snapshot["units"][0]["status"] = "cancelled"
                        self.order_revision += 2
                        a["consumed"] = True
                self.status = target
                self.request_revision += 1
                result = {
                    "request_id": self.request_id,
                    "order_id": str(self.order),
                    "request_status": self.status,
                    "revision": self.order_revision,
                    "request_revision": self.request_revision,
                    "next_action": "none" if target == "completed" else "await_review",
                }
            if self.fail_audit:
                raise OperationalError("AUDIT", {}, Exception("PRIVATE_AUDIT_CANARY"))
            self.events.append(deepcopy(result))
            return Result(result)
        return super().execute(statement, params)


@pytest.fixture
def cancellation(verifier):
    provider, private, _, _ = verifier
    owner, order, finance, ops, foreign = (uuid4() for _ in range(5))
    db = CancellationMemory(owner, order)
    db.role_map = {finance: {"finance"}, ops: {"operations"}}
    app = create_app(
        Settings(
            cancellation_enabled=True,
            cancellation_web_origin=ORIGIN,
            profile_data_key_version=1,
            profile_data_keys=json.dumps({"1": base64.b64encode(b"c" * 32).decode()}),
        )
    )
    app.state.database, app.state.jwt_verifier = db, provider
    client = ASGIClient(app)

    def headers(uid=owner, **overrides):
        return {
            "Authorization": "Bearer "
            + signed(
                private,
                claims(
                    **{
                        "sub": str(uid),
                        "aal": "aal2",
                        "amr": [
                            {"method": "password", "timestamp": int(time.time()) - 1}
                        ],
                        **overrides,
                    },
                ),
            ),
            "Origin": ORIGIN,
            "Idempotency-Key": str(uuid4()),
        }

    return client, db, headers, finance, ops, foreign, app


def request_review(env, **kwargs):
    client, db, headers, *_ = env
    return client.post(
        f"/api/v1/me/orders/{db.order}/cancel",
        headers=kwargs.pop("headers", headers()),
        json={
            "expected_revision": db.order_revision,
            "reason_code": "no_longer_needed",
            "confirmed": True,
            **kwargs,
        },
    )


def staff(env, uid, action, *, key=None, **body):
    client, db, headers, *_ = env
    path = f"/api/v1/admin/orders/{db.order}/cancellation-" + (
        "reconciliations" if action == "reconcile" else "decisions"
    )
    if action == "release":
        path = f"/api/v1/admin/tag-pairs/{db.pair}/release-allocation"
    h = headers(uid)
    if key:
        h["Idempotency-Key"] = key
    return client.post(
        path,
        headers=h,
        json={
            "request_id": db.request_id,
            "expected_order_revision": db.order_revision,
            "expected_request_revision": db.request_revision,
            "confirmed": True,
            **body,
        },
    )


def investigate(env):
    assert request_review(env).status_code == 202
    assert (
        staff(
            env,
            env[4],
            "decision",
            decision="investigate",
            reason_code="review_started",
        ).status_code
        == 200
    )


def approve(env):
    investigate(env)
    rec = staff(
        env, env[3], "reconcile", outcome="clear", reason_code="no_settlement_pending"
    )
    assert rec.status_code == 200
    aid = rec.json()["reconciliation_id"]
    assert (
        staff(
            env,
            env[4],
            "decision",
            decision="approve",
            reason_code="eligible_unpaid",
            reconciliation_id=aid,
        ).json()["request_status"]
        == "approved"
    )
    return aid


def test_request_review_only_dedupe_and_encrypted_receipt(cancellation):
    client, db, headers, *_ = cancellation
    before = deepcopy((db.snapshot, db.business_history))
    h = headers()
    first = request_review(cancellation, headers=h)
    assert (
        first.status_code == 202
        and first.headers["cache-control"] == "private, no-store"
    )
    assert set(first.json()) == {
        "request_id",
        "order_id",
        "request_status",
        "revision",
        "next_action",
    }
    assert request_review(cancellation, headers=h).json() == first.json()
    assert request_review(cancellation).json() == first.json() and len(db.events) == 1
    assert (db.snapshot, db.business_history) == before
    assert all(
        b"request_status" not in r["response_body_ciphertext"]
        for r in db.receipts.values()
    )
    assert (
        request_review(cancellation, headers=h, reason_code="other").status_code == 409
    )
    assert client.application.state.settings.cancellation_enabled


def test_owner_idor_revisions_and_safe_inputs(cancellation):
    _, db, headers, _, _, foreign, _ = cancellation
    assert request_review(cancellation, headers=headers(foreign)).status_code == 404
    assert request_review(cancellation, expected_revision=99).status_code == 409
    r = request_review(
        cancellation, expected_revision=True, private_address="PRIVATE_CANARY"
    )
    assert r.status_code == 422 and "PRIVATE_CANARY" not in r.text
    assert db.events == []


@pytest.mark.parametrize(
    "mode", ["anonymous", "expired", "revoked", "origin", "unverified"]
)
def test_authentication_origin_denial(cancellation, mode):
    _, db, headers, *_ = cancellation
    h = headers()
    if mode == "anonymous":
        h = {}
    if mode == "expired":
        h = headers(exp=1)
    if mode == "revoked":
        db.active = False
    if mode == "origin":
        h["Origin"] = "https://foreign.test"
    if mode == "unverified":
        # Real session authorization stand-in reports unverified account.
        original = db.execute
        from types import SimpleNamespace

        db.execute = lambda sql, p=None: (
            Result(SimpleNamespace(email_verified=False, mfa_active=True))
            if "sr_account_session_state" in str(sql)
            else original(sql, p)
        )
    r = request_review(cancellation, headers=h)
    assert r.status_code == (
        401 if mode in {"anonymous", "expired", "revoked"} else 403
    )
    assert r.headers["cache-control"] == "private, no-store" and not db.events


@pytest.mark.parametrize("role", ["finance", "support", "security_admin", "superadmin"])
def test_no_implicit_operations_or_recent_auth_bypass(cancellation, role):
    client, db, headers, _finance, ops, foreign, _ = cancellation
    request_review(cancellation)
    db.role_map[foreign] = {role}
    assert (
        staff(
            cancellation,
            foreign,
            "decision",
            decision="investigate",
            reason_code="review_started",
        ).status_code
        == 403
    )
    body = {
        "request_id": db.request_id,
        "expected_order_revision": 1,
        "expected_request_revision": 1,
        "confirmed": True,
        "reconciliation_id": str(uuid4()),
    }
    h = headers(ops, amr=[])
    assert (
        client.post(
            f"/api/v1/admin/tag-pairs/{db.pair}/release-allocation",
            headers=h,
            json=body,
        ).status_code
        == 403
    )
    assert (
        staff(
            cancellation,
            ops,
            "reconcile",
            outcome="clear",
            reason_code="no_settlement_pending",
        ).status_code
        == 403
    )


@pytest.mark.parametrize(
    "change",
    [
        {"order_status": "cancelled"},
        {"payment_status": "verified"},
        {"payment_status": "refunded"},
        {"payment_status": "under_review"},
        {"fulfillment_status": "allocated"},
        {"fulfillment_status": "packed"},
        {"fulfillment_status": "dispatched"},
        {"attempt_states": ["initiated"]},
        {"attempt_states": ["submitted"]},
        {"attempt_states": ["under_review"]},
        {"attempt_states": ["disputed"]},
        {"attempt_states": ["verified"]},
        {"attempt_states": ["ambiguous"]},
        {"production": True},
        {"shipment": True},
        {"units": []},
        {"units": [{"status": "allocated"}]},
        {
            "units": [
                {
                    "status": "reserved",
                    "ownership_status": "active",
                    "owner_user_id": "synthetic-owner",
                    "activated_at": "synthetic-time",
                    "inventory_status": "qa_passed",
                }
            ]
        },
    ],
)
def test_real_application_release_policy_and_clear_attestation_cutoffs(
    cancellation, change
):
    investigate(cancellation)
    db = cancellation[1]
    db.snapshot.update(deepcopy(change))
    assert not release_eligible(db.snapshot)
    assert (
        staff(
            cancellation,
            cancellation[3],
            "reconcile",
            outcome="clear",
            reason_code="no_settlement_pending",
        ).status_code
        == 409
    )
    assert not db.attestations and db.status == "investigating"


def test_application_policy_allows_only_reconciled_unpaid_stock():
    assert release_eligible(eligible_snapshot())
    for states in (["rejected"], ["expired"], ["rejected", "expired"]):
        assert release_eligible({**eligible_snapshot(), "attempt_states": states})
    for value in (None, {}, {"units": []}):
        assert not release_eligible(value)


def test_multi_role_actor_cannot_attest_and_execute_own_release(cancellation):
    _, db, _, finance, _, _, _ = cancellation
    investigate(cancellation)
    db.role_map[finance] = {"operations", "finance"}
    rec = staff(
        cancellation,
        finance,
        "reconcile",
        outcome="clear",
        reason_code="no_settlement_pending",
    ).json()
    r = staff(
        cancellation,
        finance,
        "decision",
        decision="approve",
        reason_code="eligible_unpaid",
        reconciliation_id=rec["reconciliation_id"],
    )
    assert r.status_code == 409 and db.snapshot["units"][0]["status"] == "reserved"
    assert db.role_map[finance] == {"operations", "finance"}


def test_synthetic_release_replay_and_frozen_history(cancellation):
    before = deepcopy(cancellation[1].business_history)
    aid = approve(cancellation)
    key = str(uuid4())
    r = staff(cancellation, cancellation[4], "release", key=key, reconciliation_id=aid)
    assert r.status_code == 200 and r.json()["request_status"] == "completed"
    # Replay exact original request values after core/request versions advanced.
    replay = staff(
        cancellation,
        cancellation[4],
        "release",
        key=key,
        reconciliation_id=aid,
        expected_order_revision=1,
        expected_request_revision=3,
    )
    assert replay.json() == r.json()
    db = cancellation[1]
    assert (
        db.snapshot["units"][0]["status"] == "cancelled"
        and db.attestations[aid]["consumed"]
    )
    assert db.business_history == before


@pytest.mark.parametrize("cause", ["expiry", "settlement", "production", "allocation"])
def test_synthetic_changed_attestation_reopens_without_release(cancellation, cause):
    aid = approve(cancellation)
    db = cancellation[1]
    if cause == "expiry":
        db.attestations[aid]["expired"] = True
    else:
        db.order_revision += 1
        if cause == "settlement":
            db.snapshot["attempt_states"] = ["under_review"]
        if cause == "production":
            db.snapshot["production"] = True
        if cause == "allocation":
            db.snapshot["units"][0]["status"] = "allocated"
    r = staff(cancellation, cancellation[4], "release", reconciliation_id=aid)
    assert r.status_code == 200 and r.json()["request_status"] == "investigating"
    assert (
        db.snapshot["order_status"] == "placed" and not db.attestations[aid]["consumed"]
    )


@pytest.mark.parametrize("failure", ["fail_audit", "fail_receipt", "fail_commit"])
def test_request_transaction_rollback_before_response(cancellation, failure):
    db = cancellation[1]
    before = deepcopy((db.snapshot, db.business_history))
    setattr(db, failure, True)
    r = request_review(cancellation)
    assert r.status_code == 503 and "PRIVATE_" not in r.text
    assert db.events == [] and db.receipts == {} and db.request_id is None
    assert (db.snapshot, db.business_history) == before


def test_closed_gate_and_canonical_ids(cancellation):
    app = cancellation[-1]
    paths = app.openapi()["paths"]
    assert (
        paths["/api/v1/me/orders/{order_id}/cancel"]["post"]["operationId"] == "API-065"
    )
    assert (
        paths["/api/v1/admin/tag-pairs/{pair_id}/release-allocation"]["post"][
            "operationId"
        ]
        == "API-087"
    )
    assert (
        paths["/api/v1/admin/orders/{order_id}/cancellation-reconciliations"]["post"][
            "operationId"
        ]
        == "API-340"
    )
    app.state.settings.cancellation_enabled = False
    assert request_review(cancellation).status_code == 503


@pytest.mark.parametrize("action", ["reconcile", "decision", "release"])
def test_all_staff_commands_deny_anonymous_expired_and_foreign_origin(
    cancellation, action
):
    client, db, headers, finance, ops, *_ = cancellation
    request_review(cancellation)
    path = f"/api/v1/admin/orders/{db.order}/cancellation-" + (
        "reconciliations" if action == "reconcile" else "decisions"
    )
    body = {
        "request_id": db.request_id,
        "expected_order_revision": 1,
        "expected_request_revision": 1,
        "confirmed": True,
    }
    if action == "reconcile":
        body.update(outcome="clear", reason_code="no_settlement_pending")
    elif action == "decision":
        body.update(decision="investigate", reason_code="review_started")
    else:
        path = f"/api/v1/admin/tag-pairs/{db.pair}/release-allocation"
        body["reconciliation_id"] = str(uuid4())
    uid = finance if action == "reconcile" else ops
    for h in ({}, headers(uid, exp=1)):
        response = client.post(path, headers=h, json=body)
        assert (
            response.status_code == 401
            and response.headers["cache-control"] == "private, no-store"
        )
    assert (
        client.post(
            path, headers={**headers(uid), "Origin": "https://foreign.test"}, json=body
        ).status_code
        == 403
    )


@pytest.mark.parametrize("failure", ["fail_receipt", "fail_commit"])
def test_release_rollback_restores_attestation_and_stock(cancellation, failure):
    aid = approve(cancellation)
    db = cancellation[1]
    before = deepcopy((db.snapshot, db.attestations, db.events, db.business_history))
    setattr(db, failure, True)
    response = staff(cancellation, cancellation[4], "release", reconciliation_id=aid)
    assert response.status_code == 503
    assert (db.snapshot, db.attestations, db.events, db.business_history) == before
    assert db.status == "approved"


def test_stale_executor_cannot_use_old_core_revision(cancellation):
    aid = approve(cancellation)
    db = cancellation[1]
    db.order_revision += 1
    response = staff(
        cancellation,
        cancellation[4],
        "release",
        reconciliation_id=aid,
        expected_order_revision=1,
    )
    assert response.status_code == 409 and not db.attestations[aid]["consumed"]
    assert db.snapshot["units"][0]["status"] == "reserved"


def test_parallel_request_deduplication(cancellation):
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: request_review(cancellation), range(2)))
    assert all(r.status_code == 202 for r in responses)
    assert (
        responses[0].json() == responses[1].json() and len(cancellation[1].events) == 1
    )


def test_synthetic_release_against_settlement_race(cancellation):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    aid = approve(cancellation)
    db = cancellation[1]
    barrier = Barrier(2)

    def settle():
        barrier.wait()
        with db.transaction():
            if db.snapshot["order_status"] != "placed":
                return "reconciliation"
            db.order_revision += 1
            db.snapshot["payment_status"] = "verified"
            db.snapshot["units"][0]["status"] = "allocated"
            return "settled"

    def execute():
        barrier.wait()
        return staff(
            cancellation,
            cancellation[4],
            "release",
            reconciliation_id=aid,
            expected_order_revision=1,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        settlement = pool.submit(settle)
        release_result = pool.submit(execute)
        outcome = settlement.result()
        response = release_result.result()
    assert (
        outcome == "reconciliation"
        and response.status_code == 200
        and db.snapshot["order_status"] == "cancelled"
    ) or (
        outcome == "settled"
        and response.status_code == 409
        and db.snapshot["units"][0]["status"] == "allocated"
    )


def test_expired_reservation_without_review_never_releases(cancellation):
    db = cancellation[1]
    assert request_review(cancellation).status_code == 202
    db.snapshot["units"][0]["reserved_until"] = "2000-01-01T00:00:00Z"
    response = staff(
        cancellation, cancellation[4], "release", reconciliation_id=str(uuid4())
    )
    assert (
        response.status_code == 409 and db.snapshot["units"][0]["status"] == "reserved"
    )


def test_existing_finance_writer_denies_late_settlement_after_cancel(
    cancellation, monkeypatch
):
    from app.api.v1 import payments

    aid = approve(cancellation)
    assert (
        staff(
            cancellation, cancellation[4], "release", reconciliation_id=aid
        ).status_code
        == 200
    )
    db = cancellation[1]
    monkeypatch.setattr(
        payments,
        "lock_attempt",
        lambda *_: (
            {
                "id": db.order,
                "payment_status": "under_review",
                "order_status": "cancelled",
            },
            {"state": "under_review"},
        ),
    )
    response = cancellation[0].post(
        f"/api/v1/admin/payment-attempts/{uuid4()}/reviews",
        headers=cancellation[2](cancellation[3]),
        json={
            "decision": "verify",
            "bank_verified": True,
            "bank_match_reference": "synthetic-only",
            "settled_amount": "10.00",
            "settled_currency": "PKR",
            "reason": "Synthetic late transfer",
        },
    )
    assert (
        response.status_code == 409
        and response.json()["error"]["code"] == "ORDER_RECONCILIATION_REQUIRED"
    )
    assert db.snapshot["units"][0]["status"] == "cancelled"


def test_offline_migration_capture_not_sql_execution(monkeypatch):
    import importlib.util
    from pathlib import Path

    from sqlalchemy.dialects import postgresql
    from sqlalchemy.schema import CreateTable

    from app.db.commerce import Order

    file = Path(__file__).parents[1] / "alembic/versions/0024_order_cancellations.py"
    spec = importlib.util.spec_from_file_location("cancellation_migration", file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    captured = []
    monkeypatch.setattr(module.op, "execute", captured.append)
    module.upgrade()
    assert module.down_revision == "0023_saved_shipping_addresses" and captured[
        1
    ] == file.with_suffix(".sql").read_text(encoding="utf-8")
    assert "revision" in str(
        CreateTable(Order.__table__).compile(dialect=postgresql.dialect())
    )
    with pytest.raises(RuntimeError):
        module.downgrade()
