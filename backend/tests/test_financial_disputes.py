"""5.3B real application policy/HTTP checks; SQL-function stand-ins are not DB proof."""

import base64
import json
import time
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime
from threading import RLock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import OperationalError
from test_auth import claims, signed
from test_auth import verifier as _verifier
from test_critical_workflow_boundaries import MemoryDatabase, Result
from test_health import ASGIClient

from app.core.config import Settings
from app.main import create_app

verifier = _verifier
ORIGIN = "https://synthetic.test"


class FinanceMemory(MemoryDatabase):
    """Persistence primitives only; application evaluate() supplies the tested plan."""

    def __init__(self, actor, original, grantor):
        super().__init__(uuid4(), uuid4())
        self.case_id, self.attempt_id, self.review_id = uuid4(), uuid4(), uuid4()
        self.roles = {"finance"}
        self.role_map = {actor: {"finance"}, original: {"finance"}}
        self.authorities = {
            actor: {
                "can_review": True,
                "can_decide": True,
                "provisioned_by": str(grantor),
                "revoked": False,
            }
        }
        self.snapshot = {
            "case": {
                "id": str(self.case_id),
                "type": "payment",
                "status": "open",
                "revision": 1,
            },
            "order": {
                "id": str(self.order),
                "revision": 1,
                "payment_status": "verified",
                "amount": "100.10",
                "currency": "PKR",
            },
            "attempt": {
                "id": str(self.attempt_id),
                "state": "verified",
                "amount": "100.10",
                "currency": "PKR",
                "verified_at": "2026-10-01T00:00:00Z",
            },
            "verified_reviewers": [str(original)],
            "review_reference": None,
            "fence_active": False,
            "has_active_hold": False,
            "shipments": [],
            "description": "PRIVATE_SUPPORT_CANARY",
            "sender_account": "PRIVATE_BANK_CANARY",
            "shipping_address": "PRIVATE_ADDRESS_CANARY",
        }
        self.receipts, self.history = {}, []
        self.fail_receipt = False
        self.lock = RLock()
        self.business_history = {
            "reviews": [
                {
                    "id": str(self.review_id),
                    "decision": "verify",
                    "bank_reference": "PRIVATE_BANK_CANARY",
                }
            ],
            "verified_at": "2026-10-01T00:00:00Z",
            "order_lines": ["Synthetic frozen purchase"],
            "address": "Synthetic frozen shipping",
            "owned_pair": "Synthetic unchanged owner",
        }

    @contextmanager
    def transaction(self):
        with self.lock:
            before = deepcopy(
                (
                    self.snapshot,
                    self.receipts,
                    self.history,
                    self.audit,
                    self.business_history,
                )
            )
            try:
                yield self
                if self.fail_commit:
                    raise OperationalError(
                        "COMMIT", {}, Exception("PRIVATE_COMMIT_CANARY")
                    )
            except BaseException:
                (
                    self.snapshot,
                    self.receipts,
                    self.history,
                    self.audit,
                    self.business_history,
                ) = before
                raise

    @contextmanager
    def begin_nested(self):
        yield self

    def execute(self, statement, params=None):
        sql, p = str(statement), params or {}
        if "FROM public.staff_roles" in sql:
            return Result(
                1
                if self.role_map.get(p["uid"], set()).intersection(p["roles"])
                else None
            )
        if "pg_advisory_xact_lock" in sql:
            return Result(None)
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
        if "sr_financial_case_context" in sql:
            authority = self.authorities.get(UUID(str(self.actor)))
            if p["cid"] != self.case_id or authority is None:
                return Result(None)
            snap = deepcopy(self.snapshot)
            snap["authority"] = deepcopy(authority)
            if p["reference"] == self.review_id:
                snap["review_reference"] = {
                    "id": str(self.review_id),
                    "decision": "verify",
                    "bank_verified": True,
                }
            return Result(snap)
        if "sr_financial_case_history" in sql:
            if self.fail_audit:
                raise OperationalError("AUDIT", {}, Exception("PRIVATE_AUDIT_CANARY"))
            self.audit.append(
                {"action": "finance.case.read", "case": str(self.case_id)}
            )
            return Result(
                deepcopy(
                    [h for h in reversed(self.history) if h["revision"] < p["before"]][
                        : p["lim"]
                    ]
                )
            )
        if "sr_financial_case_apply" in sql:
            # No security/state machine copied here: actual application plan was evaluated.
            body, plan = json.loads(p["body"]), json.loads(p["plan"])
            self.snapshot["case"]["revision"] += 1
            if plan["activate_fence"] and not self.snapshot["fence_active"]:
                self.snapshot["fence_active"] = True
                self.snapshot["order"]["revision"] += 1
            for package in self.snapshot["shipments"]:
                if package["id"] in plan["package_exception_ids"]:
                    package["status"] = "exception"
                    self.snapshot["order"]["revision"] += 1
            did = str(uuid4())
            row = {
                "decision_id": did,
                "revision": self.snapshot["case"]["revision"],
                "decision": body["decision"],
                "effective_decision": plan["effective_decision"],
                "reason_code": body["reason_code"],
                "created_at": datetime.now(UTC).isoformat(),
            }
            self.history.append(row)
            if self.fail_audit:
                raise OperationalError("AUDIT", {}, Exception("PRIVATE_AUDIT_CANARY"))
            self.audit.append({"action": "finance.case.decided", "id": did})
            active = self.snapshot["fence_active"]
            return Result(
                {
                    "decision_id": did,
                    "case_id": str(self.case_id),
                    "case_revision": self.snapshot["case"]["revision"],
                    "order_id": str(self.order),
                    "order_revision": self.snapshot["order"]["revision"],
                    "decision": body["decision"],
                    "effective_decision": plan["effective_decision"],
                    "dispute_fence": "active" if active else "none",
                    "next_action": "escalated"
                    if plan["effective_decision"] == "escalate"
                    else "await_reconciliation"
                    if active
                    else "review_recorded",
                    "refund_execution_enabled": False,
                }
            )
        if "sr_financial_order_lock_clear" in sql or "sr_financial_order_clear" in sql:
            return Result(not self.snapshot["fence_active"])
        if sql.startswith("SELECT a.*,j.order_id"):
            return Result(
                {
                    "order_id": self.order,
                    "deleted_at": None,
                    "status": "ready",
                    "retention_until": None,
                }
            )
        return super().execute(statement, params)


@pytest.fixture
def review_env(verifier):
    provider, private, _, _ = verifier
    actor, original, grantor, foreign = (uuid4() for _ in range(4))
    db = FinanceMemory(actor, original, grantor)
    app = create_app(
        Settings(
            financial_review_enabled=True,
            financial_review_web_origin=ORIGIN,
            profile_data_key_version=1,
            profile_data_keys=json.dumps({"1": base64.b64encode(b"f" * 32).decode()}),
        )
    )
    app.state.database, app.state.jwt_verifier = db, provider
    db.info["settings"] = app.state.settings
    client = ASGIClient(app)

    def headers(uid=actor, **overrides):
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
                    }
                ),
            ),
            "Origin": ORIGIN,
            "Idempotency-Key": str(uuid4()),
        }

    return client, db, headers, actor, original, grantor, foreign, app


def read(env, **kwargs):
    return env[0].get(
        f"/api/v1/admin/support-cases/{env[1].case_id}/financial-review"
        + kwargs.pop("query", ""),
        headers=kwargs.pop("headers", env[2]()),
        **kwargs,
    )


def decide(env, decision="confirm_dispute", **kwargs):
    db = env[1]
    reason = {
        "investigate": "review_started",
        "confirm_dispute": "settlement_disputed",
        "resolve_no_change": "no_financial_change",
        "escalate": "requires_review",
    }
    body = {
        "expected_revision": db.snapshot["case"]["revision"],
        "expected_order_revision": db.snapshot["order"]["revision"],
        "decision": decision,
        "reason_code": reason.get(decision, "requires_review"),
        "confirmed": True,
        "settlement_review_reference": str(db.review_id)
        if decision in {"confirm_dispute", "resolve_no_change"}
        else None,
    }
    headers = kwargs.pop("headers", env[2]())
    body.update(kwargs)
    return env[0].post(
        f"/api/v1/admin/support-cases/{db.case_id}/financial-decisions",
        headers=headers,
        json=body,
    )


def test_closed_safe_projection_exact_money_and_audit(review_env):
    response = read(review_env)
    assert (
        response.status_code == 200
        and response.headers["cache-control"] == "private, no-store"
    )
    assert response.headers["x-content-type-options"] == "nosniff"
    value = response.json()
    assert set(value) == {
        "case_id",
        "case_type",
        "case_status",
        "case_revision",
        "order_id",
        "order_revision",
        "attempt_id",
        "amount",
        "currency",
        "settlement_state",
        "order_payment_status",
        "dispute_fence",
        "exceptions",
        "prior_decisions",
        "next_cursor",
        "refund_execution_enabled",
    }
    assert value["amount"] == "100.10" and value["refund_execution_enabled"] is False
    assert (
        "PRIVATE_" not in response.text
        and review_env[1].audit[-1]["action"] == "finance.case.read"
    )


@pytest.mark.parametrize(
    "role", ["operations", "support", "security_admin", "superadmin", "customer"]
)
def test_wrong_roles_do_not_inherit_finance(review_env, role):
    _, db, headers, _, _, _, foreign, _ = review_env
    db.role_map[foreign] = {role}
    assert read(review_env, headers=headers(foreign)).status_code == 403
    assert decide(review_env, headers=headers(foreign)).status_code == 403


@pytest.mark.parametrize("write", [False, True])
@pytest.mark.parametrize(
    "failure",
    [
        "anonymous",
        "expired",
        "revoked_session",
        "aal1",
        "no_case_authority",
        "revoked_authority",
    ],
)
def test_session_and_case_authority_denials(review_env, write, failure):
    _, db, headers, actor, _, _, foreign, _ = review_env
    h = headers()
    if failure == "anonymous":
        h = {}
    if failure == "expired":
        h = headers(exp=1)
    if failure == "revoked_session":
        db.active = False
    if failure == "aal1":
        h = headers(aal="aal1")
    if failure == "no_case_authority":
        db.role_map[foreign] = {"finance"}
        h = headers(foreign)
    if failure == "revoked_authority":
        db.authorities[actor]["revoked"] = True
    r = decide(review_env, headers=h) if write else read(review_env, headers=h)
    assert r.status_code == (
        401
        if failure in {"anonymous", "expired", "revoked_session"}
        else 403
        if failure == "aal1"
        else 404
    )
    assert (
        r.headers["cache-control"] == "private, no-store" and "PRIVATE_" not in r.text
    )


def test_cross_case_and_foreign_review_reference_concealed(review_env):
    client, db, headers, *_ = review_env
    assert (
        client.get(
            f"/api/v1/admin/support-cases/{uuid4()}/financial-review", headers=headers()
        ).status_code
        == 404
    )
    foreign_write = client.post(
        f"/api/v1/admin/support-cases/{uuid4()}/financial-decisions",
        headers=headers(),
        json={
            "expected_revision": 1,
            "expected_order_revision": 1,
            "decision": "investigate",
            "reason_code": "review_started",
            "confirmed": True,
        },
    )
    assert foreign_write.status_code == 404 and "PRIVATE_" not in foreign_write.text
    assert (
        decide(review_env, settlement_review_reference=str(uuid4())).status_code == 404
    )
    assert db.history == []


@pytest.mark.parametrize(
    "failure",
    [
        "no_decide",
        "original_verifier",
        "grant_provisioner",
        "missing_amr",
        "old_amr",
        "wrong_origin",
    ],
)
def test_recent_and_independent_decision_authority(review_env, failure):
    _, db, headers, actor, original, _, _, _ = review_env
    h = headers()
    if failure == "no_decide":
        db.authorities[actor]["can_decide"] = False
    if failure == "original_verifier":
        db.authorities[original] = deepcopy(db.authorities[actor])
        h = headers(original)
    if failure == "grant_provisioner":
        db.authorities[actor]["provisioned_by"] = str(actor)
    if failure == "missing_amr":
        h = headers(amr=[])
    if failure == "old_amr":
        h = headers(amr=[{"method": "password", "timestamp": int(time.time()) - 301}])
    if failure == "wrong_origin":
        h["Origin"] = "https://foreign.test"
    assert decide(review_env, headers=h).status_code == (
        403 if failure in {"missing_amr", "old_amr", "wrong_origin"} else 404
    )
    assert not db.history


def test_multi_role_union_does_not_bypass_original_reviewer(review_env):
    _, db, headers, actor, original, *_ = review_env
    db.role_map[actor] = {"finance", "operations"}
    assert decide(review_env, "investigate").status_code == 200
    db.authorities[original] = deepcopy(db.authorities[actor])
    db.role_map[original] = {"finance", "operations"}
    assert decide(review_env, headers=headers(original)).status_code == 404
    assert db.role_map[actor] == {"finance", "operations"}


@pytest.mark.parametrize("field", ["expected_revision", "expected_order_revision"])
def test_stale_versions_and_strict_boolean_integer(review_env, field):
    assert decide(review_env, **{field: 99}).status_code == 409
    assert decide(review_env, **{field: True}).status_code == 422
    r = decide(review_env, confirmed=False, private_note="PRIVATE_INPUT_CANARY")
    assert r.status_code == 422 and "PRIVATE_INPUT_CANARY" not in r.text


def test_real_application_policy_dispute_preserves_original_settlement(review_env):
    db = review_env[1]
    before = deepcopy(db.business_history)
    response = decide(review_env)
    assert response.status_code == 200 and response.json()["dispute_fence"] == "active"
    assert response.json()["effective_decision"] == "confirm_dispute"
    assert (
        db.business_history == before and db.snapshot["attempt"]["state"] == "verified"
    )
    assert (
        db.snapshot["order"]["payment_status"] == "verified"
        and db.snapshot["case"]["status"] == "open"
    )
    resolved = decide(review_env, "resolve_no_change")
    assert resolved.status_code == 200 and resolved.json()["dispute_fence"] == "active"
    assert (
        resolved.json()["next_action"] == "await_reconciliation"
        and db.business_history == before
    )


@pytest.mark.parametrize(
    "status",
    ["preparing", "packed", "dispatched", "delivered", "returned", "exception"],
)
def test_real_application_package_exception_and_escalation_plan(review_env, status):
    db = review_env[1]
    db.snapshot["shipments"] = [
        {
            "id": str(uuid4()),
            "status": status,
            "dispatched_at": "2026-10-01T00:00:00Z" if status == "exception" else None,
            "tracking": "Synthetic unchanged tracking",
        }
    ]
    before = deepcopy(db.snapshot["shipments"])
    response = decide(review_env)
    assert response.status_code == 200
    if status in {"preparing", "packed"}:
        assert db.snapshot["shipments"][0]["status"] == "exception"
        assert db.snapshot["shipments"][0]["tracking"] == before[0]["tracking"]
    else:
        assert (
            response.json()["effective_decision"] == "escalate"
            and db.snapshot["shipments"] == before
        )


@pytest.mark.parametrize("failure", ["amount", "currency", "no_verified_timestamp"])
def test_settlement_reference_requires_real_matching_settlement(review_env, failure):
    db = review_env[1]
    if failure == "amount":
        db.snapshot["attempt"]["amount"] = "100.11"
    if failure == "currency":
        db.snapshot["attempt"]["currency"] = "USD"
    if failure == "no_verified_timestamp":
        db.snapshot["attempt"]["verified_at"] = None
    assert decide(review_env).status_code == 409 and not db.history


def test_idempotence_replay_rechecks_current_authority(review_env):
    db, headers, actor = review_env[1], review_env[2], review_env[3]
    h = headers()
    first = decide(review_env, headers=h)
    replay = decide(
        review_env, headers=h, expected_revision=1, expected_order_revision=1
    )
    assert (
        first.status_code == 200
        and replay.json() == first.json()
        and len(db.history) == 1
    )
    assert decide(review_env, "escalate", headers=h).status_code == 409
    db.authorities[actor]["revoked"] = True
    assert (
        decide(
            review_env, headers=h, expected_revision=1, expected_order_revision=1
        ).status_code
        == 404
    )
    assert all(
        b"effective_decision" not in row["response_body_ciphertext"]
        for row in db.receipts.values()
    )


@pytest.mark.parametrize("failure", ["fail_audit", "fail_receipt", "fail_commit"])
def test_atomic_fence_package_history_receipt_rollback(review_env, failure):
    db = review_env[1]
    db.snapshot["shipments"] = [
        {"id": str(uuid4()), "status": "packed", "dispatched_at": None}
    ]
    before = deepcopy(
        (db.snapshot, db.business_history, db.history, db.audit, db.receipts)
    )
    setattr(db, failure, True)
    response = decide(review_env)
    assert response.status_code == 503 and "PRIVATE_" not in response.text
    assert (
        db.snapshot,
        db.business_history,
        db.history,
        db.audit,
        db.receipts,
    ) == before


def test_closed_case_and_disabled_refund_restoration(review_env):
    for action in ("refund", "clear_fence", "restore", "verify_payment"):
        assert decide(review_env, action).status_code == 422
    review_env[1].snapshot["case"]["status"] = "closed"
    assert decide(review_env).status_code == 409
    review_env[-1].state.settings.financial_review_enabled = False
    assert read(review_env).status_code == 503 and decide(review_env).status_code == 503


def test_common_guard_blocks_real_print_artifact_and_fulfillment_before_work(
    review_env,
):
    from app.api.v1 import fulfillment, printing

    db = review_env[1]
    assert decide(review_env).status_code == 200
    for operation in (
        lambda: printing.occurrences(db, db.order),
        lambda: printing.artifact(db, uuid4(), check_binding=False),
        lambda: fulfillment.eligible(db, db.order),
    ):
        with pytest.raises(HTTPException) as raised:
            operation()
        assert raised.value.detail["code"] == "FINANCIAL_REVIEW_REQUIRED"


def test_bounded_case_cursor_and_revision_binding(review_env):
    for _ in range(3):
        assert decide(review_env, "investigate").status_code == 200
    response = read(review_env, query="?limit=1")
    assert response.status_code == 200 and len(response.json()["prior_decisions"]) == 1
    cursor = response.json()["next_cursor"]
    assert cursor and "PRIVATE_" not in cursor
    page = read(review_env, query="?limit=1&cursor=" + cursor)
    assert (
        page.status_code == 200
        and page.json()["prior_decisions"][0]["revision"]
        < response.json()["prior_decisions"][0]["revision"]
    )
    assert read(review_env, query="?limit=101").status_code == 422
    assert read(review_env, query="?cursor=PRIVATE_CURSOR_CANARY").status_code == 422
    assert decide(review_env, "investigate").status_code == 200
    assert read(review_env, query="?cursor=" + cursor).status_code == 409


def test_money_never_coerces_float_or_echoes_reference(review_env):
    db = review_env[1]
    db.snapshot["attempt"]["amount"] = 100.1
    response = read(review_env)
    assert response.status_code == 503 and "PRIVATE_" not in response.text
    response = decide(review_env, settlement_review_reference="PRIVATE_BANK_REFERENCE")
    assert response.status_code == 422 and "PRIVATE_BANK_REFERENCE" not in response.text


def test_cursor_cannot_be_reused_for_another_authorized_case(review_env):
    from app.api.v1.financial_disputes import page_token, parse_token

    token = page_token(review_env[-1].state.settings, review_env[1].case_id, 1, 2)
    with pytest.raises(HTTPException) as raised:
        parse_token(review_env[-1].state.settings, uuid4(), 1, token)
    assert raised.value.detail["code"] == "INVALID_CURSOR"


@pytest.mark.parametrize("work_kind", ["dispatch", "reprint"])
def test_financial_decision_against_actual_common_work_guard_race(
    review_env, work_kind
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from app.api.v1.financial_disputes import require_order_clear

    db = review_env[1]
    barrier = Barrier(2)

    def work():
        barrier.wait()
        try:
            with db.transaction():
                require_order_clear(db, db.order)
                db.snapshot["order"]["revision"] += 1
                db.snapshot["synthetic_work"] = work_kind
                if work_kind == "dispatch":
                    db.snapshot["shipments"] = [
                        {
                            "id": str(uuid4()),
                            "status": "dispatched",
                            "dispatched_at": datetime.now(UTC).isoformat(),
                        }
                    ]
                return "started"
        except HTTPException:
            return "fenced"

    def dispute():
        barrier.wait()
        return decide(review_env, expected_order_revision=1)

    with ThreadPoolExecutor(max_workers=2) as pool:
        pending_work, pending_dispute = pool.submit(work), pool.submit(dispute)
        outcome, response = pending_work.result(), pending_dispute.result()
    assert (
        outcome == "fenced"
        and response.status_code == 200
        and db.snapshot["fence_active"]
    ) or (
        outcome == "started"
        and response.status_code == 409
        and not db.snapshot["fence_active"]
    )


def test_actual_payment_review_writer_cannot_verify_while_fenced(
    review_env, monkeypatch
):
    from app.api.v1 import payments

    assert decide(review_env).status_code == 200
    db = review_env[1]
    monkeypatch.setattr(
        payments,
        "lock_attempt",
        lambda *_: (
            {
                "id": db.order,
                "payment_status": "under_review",
                "order_status": "placed",
            },
            {"state": "under_review"},
        ),
    )
    response = review_env[0].post(
        f"/api/v1/admin/payment-attempts/{db.attempt_id}/reviews",
        headers=review_env[2](),
        json={"decision": "verify", "reason": "Synthetic review only"},
    )
    assert (
        response.status_code == 409
        and response.json()["error"]["code"] == "FINANCIAL_REVIEW_REQUIRED"
    )


def test_real_worker_recheck_stops_before_render_upload_and_records_safe_failure(
    review_env, monkeypatch
):
    from types import SimpleNamespace

    from app.workers import printing

    db = review_env[1]
    db.snapshot["fence_active"] = True
    settings = review_env[-1].state.settings
    settings.print_enabled = True
    lease = {
        "id": uuid4(),
        "order_id": db.order,
        "job_kind": "print.render",
        "lease_owner": "synthetic-worker",
        "print_job_id": uuid4(),
        "attempt_count": 1,
    }
    monkeypatch.setattr(printing, "claim", lambda *_: lease)
    admissions = []

    def fence(*_, admit=True):
        admissions.append(admit)

    monkeypatch.setattr(printing, "fence", fence)

    @contextmanager
    def transaction(*_):
        with db.transaction():
            yield db

    monkeypatch.setattr(printing, "worker_transaction", transaction)
    monkeypatch.setattr(
        printing,
        "render_pdf",
        lambda *_: pytest.fail("Financial fence reached rendering"),
    )
    calls = []
    original = db.execute

    def execute(sql, p=None):
        if str(sql).startswith(
            ("UPDATE public.print_jobs", "UPDATE public.durable_jobs")
        ):
            calls.append((str(sql), deepcopy(p)))
            return Result(None)
        return original(sql, p)

    db.execute = execute
    store = SimpleNamespace(
        upload=lambda *_: pytest.fail("Financial fence reached upload")
    )
    assert printing.run_one(db, settings, store) is False
    assert True in admissions and admissions[-1] is False
    assert calls and all(
        item[1].get("code") == "financial_review_required" for item in calls
    )


def test_worker_claim_financial_race_is_safely_retryable(review_env, monkeypatch):
    from types import SimpleNamespace

    from app.workers import printing

    settings = review_env[-1].state.settings
    settings.print_enabled = True

    class DriverError(Exception):
        diag = SimpleNamespace(constraint_name="financial_review_fence")

    def claim(*_):
        raise OperationalError("UPDATE", {}, DriverError("PRIVATE_DRIVER_CANARY"))

    monkeypatch.setattr(printing, "claim", claim)
    assert printing.run_one(review_env[1], settings) is False


def test_mixed_dispatched_package_preserves_all_package_history(review_env):
    db = review_env[1]
    db.snapshot["shipments"] = [
        {"id": str(uuid4()), "status": "packed", "dispatched_at": None},
        {
            "id": str(uuid4()),
            "status": "dispatched",
            "dispatched_at": "2026-10-01T00:00:00Z",
        },
    ]
    before = deepcopy(db.snapshot["shipments"])
    assert decide(review_env).json()["effective_decision"] == "escalate"
    assert db.snapshot["shipments"] == before


def test_offline_migration_capture_and_canonical_routes(review_env, monkeypatch):
    import importlib.util
    from pathlib import Path

    file = Path(__file__).parents[1] / "alembic/versions/0025_financial_disputes.py"
    spec = importlib.util.spec_from_file_location("financial_migration", file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls = []
    monkeypatch.setattr(module.op, "execute", calls.append)
    module.upgrade()
    assert module.down_revision == "0024_order_cancellations"
    assert calls == [
        "SET LOCAL lock_timeout='5s'",
        file.with_suffix(".sql").read_text(encoding="utf-8"),
    ]
    with pytest.raises(RuntimeError):
        module.downgrade()
    paths = review_env[-1].openapi()["paths"]
    assert (
        paths["/api/v1/admin/support-cases/{case_id}/financial-review"]["get"][
            "operationId"
        ]
        == "API-324"
    )
    assert (
        paths["/api/v1/admin/support-cases/{case_id}/financial-decisions"]["post"][
            "operationId"
        ]
        == "API-323"
    )
    assert not any("/refund" in path or "/unfreeze" in path for path in paths)


def test_initial_artifact_probe_is_read_only_then_final_check_fences(review_env):
    from app.api.v1.printing import artifact

    db = review_env[1]
    queries = []
    original = db.execute

    def execute(sql, p=None):
        queries.append(str(sql))
        return original(sql, p)

    db.execute = execute
    artifact(db, uuid4(), check_binding=False)
    assert any("sr_financial_order_clear" in sql for sql in queries)
    assert not any("sr_financial_order_lock_clear" in sql for sql in queries)
    db.snapshot["fence_active"] = True
    with pytest.raises(HTTPException):
        artifact(db, uuid4())
    assert any("sr_financial_order_lock_clear" in sql for sql in queries)
