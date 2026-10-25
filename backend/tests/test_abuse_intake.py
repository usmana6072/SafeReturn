"""Real HTTP/JWT/AEAD/challenge with synthetic scripted DB; no PostgreSQL proof."""

import base64
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from threading import RLock
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy.exc import OperationalError
from test_auth import claims, signed
from test_auth import verifier as _verifier
from test_critical_workflow_boundaries import MemoryDatabase, Result
from test_health import ASGIClient

from app.core.abuse_intake import Policy, Report, canonical
from app.core.config import Settings
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt
from app.core.turnstile import challenge_binding
from app.main import create_app

verifier = _verifier
URL = "/api/v1/public/abuse-reports"
CASES = "/api/v1/admin/support-cases"
PID = UUID(int=4401)
INDEX_KEY = b"s" * 32


def fixture_policy():
    # Explicit synthetic values, not production/legal/retention approvals.
    now = datetime.now(UTC)
    rule = {"duration_seconds": 7200, "anchor": "created_at"}
    body = {
        "schema_version": 1,
        "approval_reference": "SYNTHETIC-NOT-APPROVED",
        "notice_reference": "SYNTHETIC-NOT-LIVE",
        "consent_version": "abuse-report-v1",
        "intake_enabled": True,
        "triage_enabled": True,
        "hmac_key_version": 1,
        "hmac_key_sha256": hashlib.sha256(INDEX_KEY).hexdigest(),
        "retention": {
            k: deepcopy(rule)
            for k in ("report", "case", "budget", "proof", "receipt", "audit")
        },
    }
    return {
        "policy_id": str(PID),
        "version": 1,
        "body": body,
        "sha256": hashlib.sha256(canonical(body).encode()).hexdigest(),
        "effective_at": (now - timedelta(hours=1)).isoformat(),
        "expires_at": (now + timedelta(hours=1)).isoformat(),
        "revoked": False,
    }


class Rows(Result):
    def all(self):
        return self.value


class Store(MemoryDatabase):
    """Scripted helper outcomes; Python lock/rollback are not SQL guarantees."""

    def __init__(self):
        super().__init__(uuid4(), uuid4())
        self.row = fixture_policy()
        self.attempts, self.proofs, self.reports, self.public_receipts = (
            [],
            set(),
            {},
            {},
        )
        self.case_rows, self.events, self.staff_receipts = {}, [], {}
        self.calls = []
        self.fail = None
        self.mutex = RLock()
        self.last_submit = False
        self.role_drop = False
        self.capability = True

    @contextmanager
    def begin_nested(self):
        before = deepcopy(
            (
                self.reports,
                self.public_receipts,
                self.case_rows,
                self.events,
                self.staff_receipts,
                self.audit,
            )
        )
        try:
            yield self
        except BaseException:
            (
                self.reports,
                self.public_receipts,
                self.case_rows,
                self.events,
                self.staff_receipts,
                self.audit,
            ) = before
            raise

    @contextmanager
    def transaction(self):
        with self.mutex:
            self.last_submit = False
            with self.begin_nested(), super().transaction():
                yield self
                if self.fail == "commit" and self.last_submit:
                    raise OperationalError("COMMIT", {}, Exception("PRIVATE_CANARY"))

    def scoped_case(self, cid):
        c = self.case_rows.get(str(cid))
        return (
            c
            if c
            and (
                c["assigned_staff_id"] is None
                or str(c["assigned_staff_id"]) == self.actor
            )
            else None
        )

    def execute(self, statement, params=None):
        sql, p = str(statement), params or {}
        self.calls.append(sql)
        if "AS abuse_intake_available" in sql:
            return Result(self.capability)
        if "sr_abuse_policy(" in sql:
            return Result(deepcopy(self.row))
        if "sr_abuse_intake(" in sql:
            action, a = p["action"], json.loads(p["payload"])
            if not self.row or self.row["revoked"]:
                return Result({"error": "PROVIDER_UNAVAILABLE"})
            if action in {"peer", "target"}:
                n = sum(x == (action, a["scope"]) for x in self.attempts)
                allowed = n < (20 if action == "peer" else 5)
                if allowed:
                    self.attempts.append((action, a["scope"]))
                return Result({"allowed": allowed})
            if action == "proof":
                allowed = a["proof"] not in self.proofs
                self.proofs.add(a["proof"])
                return Result({"allowed": allowed})
            assert action == "submit"
            self.last_submit = True
            k = (a["scope"], a["retry"])
            if k in self.public_receipts:
                return Result(
                    {"status": "accepted"}
                    if self.public_receipts[k] == a["body"]
                    else {"error": "IDEMPOTENCY_KEY_REUSED"}
                )
            duplicate = any(
                r["duplicate"] == a["duplicate"] for r in self.reports.values()
            )
            if not duplicate:
                self.reports[a["report_id"]] = deepcopy(a)
                self.case_rows[a["case_id"]] = {
                    "id": a["case_id"],
                    "case_type": "other",
                    "status": "open",
                    "priority": "normal",
                    "case_revision": 1,
                    "created_at": datetime.now(UTC),
                    "assigned_staff_id": None,
                    "description_format": 1,
                    "pair_id": None,
                    "order_id": None,
                    "opened_by_user_id": None,
                    "description_ciphertext": bytes.fromhex(
                        a["description_ciphertext"]
                    ),
                    "description_key_version": a["description_key_version"],
                }
                self.events.append(
                    {"event_id": a["event_id"], "actor_kind": "anonymous"}
                )
                if self.fail == "audit":
                    raise OperationalError("audit", {}, Exception("PRIVATE_CANARY"))
            self.public_receipts[k] = a["body"]
            if self.fail == "receipt":
                raise OperationalError("receipt", {}, Exception("PRIVATE_CANARY"))
            return Result({"status": "accepted"})
        if "sr_abuse_case_policy(" in sql:
            linked = any(r["case_id"] == str(p["id"]) for r in self.reports.values())
            if (
                not linked
                or not self.scoped_case(p["id"])
                or "support" not in self.roles
            ):
                return Result(None)
            return Result(
                deepcopy(self.row)
                if self.row and not self.row["revoked"]
                else {"error": "PROVIDER_UNAVAILABLE"}
            )
        if "FROM public.support_cases" in sql:
            if "SELECT 1" in sql:
                return Result(1 if self.scoped_case(p["id"]) else None)
            if "description_ciphertext" in sql:
                return Result(deepcopy(self.scoped_case(p["id"])))
            rows = [
                deepcopy(c)
                for c in self.case_rows.values()
                if self.scoped_case(c["id"])
                and (not p["id"] or str(p["id"]) == c["id"])
            ]
            if not self.row or self.row["revoked"]:
                rows = [
                    c
                    for c in rows
                    if not any(r["case_id"] == c["id"] for r in self.reports.values())
                ]
            fields = (
                "id",
                "case_type",
                "status",
                "priority",
                "case_revision",
                "created_at",
                "assigned_staff_id",
                "description_format",
            )
            return Rows([{k: c[k] for k in fields} for c in rows])
        if "sr_support_context(" in sql:
            return Result({"has_active_hold": False, "account_deletion_request": False})
        if "FROM public.support_case_events" in sql:
            return Rows([])
        if "SELECT pg_advisory_xact_lock" in sql:
            return Result(None)
        if "SELECT request_hash" in sql and "idempotency_records" in sql:
            return Result(self.staff_receipts.get((p["scope"], p["op"], p["key"])))
        if "INSERT INTO public.idempotency_records" in sql:
            self.staff_receipts[(p["scope"], p["op"], p["key"])] = {
                "request_hash": p["hash"],
                "response_body_ciphertext": p["cipher"],
                "response_key_version": p["version"],
                "receipt_live": True,
            }
            if "receipt_seconds" in p:
                assert (
                    p["receipt_seconds"]
                    == self.row["body"]["retention"]["receipt"]["duration_seconds"]
                )
            return Result(None)
        if "sr_support_change(" in sql:
            c = self.scoped_case(p["id"])
            if c is None:
                return Result({"error": "NOT_FOUND"})
            if p["expected"] != c["case_revision"]:
                return Result({"error": "STALE_CASE"})
            if p["status"] in {"resolved", "closed"} and any(
                r["case_id"] == str(p["id"]) for r in self.reports.values()
            ):
                return Result({"error": "ESCALATION_REQUIRED"})
            if p["action"] == "claim":
                c["assigned_staff_id"] = UUID(self.actor)
            else:
                c["status"] = p["status"] or c["status"]
            c["case_revision"] += 1
            if self.role_drop:
                self.roles.clear()
            return Result(
                {
                    "id": c["id"],
                    "status": c["status"],
                    "case_revision": c["case_revision"],
                }
            )
        return super().execute(statement, params)


@pytest.fixture
def intake(verifier):
    provider, private, _, _ = verifier
    db = Store()
    settings = Settings(
        _env_file=None,
        abuse_reports_enabled=True,
        abuse_report_policy_id=str(PID),
        abuse_report_hmac_key=base64.b64encode(INDEX_KEY).decode(),
        profile_data_keys=json.dumps({"1": base64.b64encode(b"e" * 32).decode()}),
        turnstile_secret_key="synthetic-secret",
        turnstile_expected_hostname="public.test",
    )
    app = create_app(settings)
    app.state.database, app.state.jwt_verifier = db, provider
    challenge = {"mode": "ok", "calls": 0, "after": None}

    def transport(req):
        challenge["calls"] += 1
        if challenge["after"]:
            challenge["after"]()
        value = json.loads(req.content)
        if challenge["mode"] == "outage":
            raise httpx.ConnectError("PRIVATE_CANARY")
        if challenge["mode"] == "reject":
            return httpx.Response(200, json={"success": False})
        token, mid = value["response"].split("|", 1)
        return httpx.Response(
            200,
            json={
                "success": True,
                "hostname": "wrong.test"
                if challenge["mode"] == "host"
                else "public.test",
                "action": "wrong" if challenge["mode"] == "action" else "abuse_report",
                "cdata": "wrong"
                if challenge["mode"] == "binding"
                else challenge_binding(
                    "abuse_report", token, mid.split(":", 1)[0] or None
                ),
                "challenge_ts": (
                    datetime.now(UTC) - timedelta(hours=1)
                    if challenge["mode"] == "stale"
                    else datetime.now(UTC)
                ).isoformat(),
            },
        )

    app.state.turnstile_transport = httpx.MockTransport(transport)
    counter = 0

    def body(**changes):
        nonlocal counter
        counter += 1
        value = {
            "qr_token": "S" * 43,
            "category": "spam",
            "message": "Synthetic complaint",
            "consent_accepted": True,
            "consent_version": "abuse-report-v1",
        } | changes
        value["turnstile_token"] = (
            f"{value['qr_token']}|{value.get('message_id') or ''}:{counter}"
        )
        return value

    def headers(user=None, **extra):
        token = signed(
            private,
            claims(
                sub=str(user or db.owner),
                aal="aal2",
                amr=[{"method": "totp", "timestamp": int(time.time())}],
            ),
        )
        return {
            "Idempotency-Key": "synthetic_retry_0001",
            "Authorization": "Bearer " + token,
        } | extra

    return ASGIClient(app), db, settings, body, headers, challenge


def send(env, **changes):
    client, _, _, body, headers, _ = env
    return client.post(URL, json=body(**changes), headers=headers())


def test_real_blind_persistence_crypto_audit_and_private_minimal_receipt(
    intake, caplog
):
    _, db, s, _, _, _ = intake
    response = send(
        intake, message="PRIVATE_REPORT_CANARY", message_id=str(UUID(int=123))
    )
    assert response.status_code == 202, response.text
    assert response.json() == {"status": "accepted"}
    r = next(iter(db.reports.values()))
    context = decrypt(
        s,
        UUID(r["report_id"]),
        "abuse_context:v1",
        bytes.fromhex(r["context_ciphertext"]),
        r["context_key_version"],
    )
    assert json.loads(context) == {
        "qr_token": "S" * 43,
        "message_id": str(UUID(int=123)),
    }
    with pytest.raises(ProfileCryptoUnavailable):
        decrypt(
            s,
            UUID(r["case_id"]),
            "abuse_context:v1",
            bytes.fromhex(r["context_ciphertext"]),
            r["context_key_version"],
        )
    assert (
        "PRIVATE_REPORT_CANARY" not in canonical(r)
        and "PRIVATE_REPORT_CANARY" not in caplog.text
    )
    assert (
        len(db.events) == len(db.case_rows) == 1
        and db.events[0]["actor_kind"] == "anonymous"
    )
    assert all(
        "qr_codes" not in sql and "finder_messages" not in sql for sql in db.calls
    )
    assert (
        response.headers["cache-control"] == "private, no-store"
        and response.headers["referrer-policy"] == "no-referrer"
    )


@pytest.mark.parametrize(
    "mutation",
    [
        {"owner_user_id": str(UUID(int=1))},
        {"contact": "test@example.test"},
        {"consent_accepted": 1},
        {"category": "suspend"},
        {"message": "<script>PRIVATE_CANARY</script>"},
        {"message": "\x00"},
        {"qr_token": "https://evil.test"},
        {"message_id": "bad"},
        {"priority": "urgent"},
        {"message": 1},
    ],
)
def test_closed_malicious_dto_no_echo_and_committed_peer_attempt(intake, mutation):
    c, db, _, b, h, _ = intake
    response = c.post(URL, json=b() | mutation, headers=h())
    assert response.status_code == 400 and "PRIVATE_CANARY" not in response.text
    assert len(db.attempts) == 1 and not db.reports


@pytest.mark.parametrize(
    "raw",
    [
        b'{"category":"spam","category":"fraud"}',
        b'{"a":NaN}',
        b"[]",
        b"null",
        b"{",
        b"[" * 500,
    ],
)
def test_invalid_duplicate_and_deep_json_safe(intake, raw):
    c, db, _, _, h, _ = intake
    response = c.post(
        URL, content=raw, headers=h() | {"Content-Type": "application/json"}
    )
    assert response.status_code == 400 and not db.reports


@pytest.mark.parametrize(
    "mode", ["reject", "outage", "host", "action", "binding", "stale"]
)
def test_challenge_failures_do_not_lookup_target_or_refund_budgets(intake, mode):
    _, db, _, _, _, challenge = intake
    challenge["mode"] = mode
    response = send(intake)
    assert response.status_code == (503 if mode == "outage" else 429)
    assert len(db.attempts) == 2 and not db.reports and not db.proofs


@pytest.mark.parametrize(
    "missing",
    [
        "flag",
        "policy",
        "expired",
        "revoked",
        "notice",
        "hash",
        "key",
        "crypto",
        "scope",
    ],
)
def test_policy_dependent_operations_fail_closed_without_defaults(intake, missing):
    _, db, s, _, _, challenge = intake
    if missing == "flag":
        s.abuse_reports_enabled = False
    elif missing == "policy":
        db.row = None
    elif missing == "expired":
        db.row["expires_at"] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    elif missing == "revoked":
        db.row["revoked"] = True
    elif missing == "notice":
        db.row["body"]["notice_reference"] = ""
    elif missing == "hash":
        db.row["sha256"] = "0" * 64
    elif missing == "key":
        s.abuse_report_hmac_key = None
    elif missing == "crypto":
        s.profile_data_keys = None
    else:
        db.row["body"]["intake_enabled"] = False
    response = send(intake)
    assert (
        response.status_code == 503
        and not db.attempts
        and not db.reports
        and challenge["calls"] == 0
    )


def test_replay_requires_fresh_proof_idempotency_and_semantic_coalescing(intake):
    c, db, _, b, h, _ = intake
    payload = b()
    first = c.post(URL, json=payload, headers=h())
    assert first.status_code == 202
    assert c.post(URL, json=payload, headers=h()).status_code == 429
    assert send(intake).status_code == 202
    assert (
        c.post(
            URL, json=b(), headers=h() | {"Idempotency-Key": "different_retry_0002"}
        ).status_code
        == 202
    )
    assert len(db.reports) == len(db.events) == 1
    assert send(intake, message="Different allegation").status_code == 409


@pytest.mark.parametrize("failure", ["audit", "receipt", "commit"])
def test_final_transaction_failure_rolls_back_but_attempt_and_proof_stay_committed(
    intake, failure
):
    _, db, _, _, _, _ = intake
    db.fail = failure
    assert send(intake).status_code == 503
    assert (
        not db.reports and not db.events and not db.case_rows and not db.public_receipts
    )
    assert len(db.attempts) == 2 and len(db.proofs) == 1


def test_target_and_peer_budgets_separate_and_forged_forwarding_ignored(intake):
    c, db, _, b, h, _ = intake
    for i in range(5):
        assert (
            c.post(
                URL, json=b(), headers=h() | {"X-Forwarded-For": f"192.0.2.{i}"}
            ).status_code
            == 202
        )
    assert send(intake).status_code == 429
    for i in range(14):
        assert (
            c.post(URL, json=b(qr_token=f"T{i:042d}"), headers=h()).status_code == 202
        )
    assert send(intake, qr_token="U" * 43).status_code == 429
    assert sum(kind == "peer" for kind, _ in db.attempts) == 20


def test_simultaneous_different_retry_keys_coalesce_python_fixture_only(intake):
    c, db, _, b, h, _ = intake
    values = [b(), b()]

    def invoke(i):
        return c.post(
            URL,
            json=values[i],
            headers=h() | {"Idempotency-Key": f"synthetic_retry_{i:04d}"},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(invoke, range(2)))
    assert [r.status_code for r in results] == [202, 202]
    assert len(db.public_receipts) == 2 and len(db.reports) == len(db.case_rows) == 1


def test_policy_or_activation_withdrawn_during_provider_call_prevents_submission(
    intake,
):
    _, db, s, _, _, challenge = intake
    challenge["after"] = lambda: setattr(s, "abuse_reports_enabled", False)
    assert send(intake).status_code == 503 and not db.reports


def test_transport_limits_and_method_privacy(intake):
    c, db, _, b, h, _ = intake
    assert (
        c.post(
            URL, content=b"x" * 8193, headers=h() | {"Content-Type": "application/json"}
        ).status_code
        == 413
    )
    assert c.post(URL, content=b"x", headers=h()).status_code == 415
    assert c.get(URL).status_code == 405
    assert c.post(URL + "?role=support", json=b(), headers=h()).status_code == 400
    assert (
        c.post(URL, json=b(), headers=h() | {"Idempotency-Key": "bad"}).status_code
        == 400
    )
    assert not db.reports


@pytest.mark.parametrize(
    "roles", [{"operations"}, {"finance"}, {"superadmin"}, {"security_admin"}, set()]
)
def test_staff_metadata_does_not_inherit_support(intake, roles):
    c, db, _, _, h, _ = intake
    assert send(intake).status_code == 202
    db.roles = roles
    assert c.get(CASES, headers=h()).status_code == 403


def test_assigned_support_triage_privacy_revision_and_disabled_enforcement(intake):
    c, db, s, _, h, _ = intake
    assert send(intake, message="Allegation only").status_code == 202
    cid = next(iter(db.case_rows))
    db.roles = {"support"}
    queue = c.get(CASES, headers=h()).json()["items"]
    assert queue[0]["requires_escalation"] and "description" not in queue[0]
    request = {"expected_revision": 1, "action": "claim", "confirmed": True}
    path = CASES + "/" + cid
    claimed = c.request("PATCH", path, json=request, headers=h())
    assert claimed.status_code == 200, claimed.text
    s.abuse_reports_enabled = (
        False  # existing triage policy and permanent guards remain
    )
    detail = c.get(CASES + "?case_id=" + cid, headers=h())
    assert detail.status_code == 200, detail.text
    item = detail.json()["items"][0]
    assert (
        "Allegation only" in item["description"]
        and not item["historical_creation_recorded"]
    )
    assert "S" * 43 not in detail.text and item["opened_by_user_id"] is None
    foreign = c.get(CASES + "?case_id=" + cid, headers=h(uuid4()))
    assert foreign.status_code == 404
    for status in ("resolved", "closed"):
        response = c.request(
            "PATCH",
            path,
            json={
                "expected_revision": 2,
                "action": "update",
                "status": status,
                "confirmed": True,
            },
            headers=h() | {"Idempotency-Key": "synthetic_close_" + status},
        )
        assert response.status_code == 409
    stale = c.request(
        "PATCH",
        path,
        json={
            "expected_revision": 1,
            "action": "update",
            "status": "investigating",
            "confirmed": True,
        },
        headers=h() | {"Idempotency-Key": "synthetic_stale_001"},
    )
    assert stale.status_code == 412
    db.row = None
    assert c.get(CASES + "?case_id=" + cid, headers=h()).status_code == 503
    assert c.request("PATCH", path, json=request, headers=h()).status_code == 503


def test_revoked_staff_after_case_mutation_rolls_back(intake):
    c, db, _, _, h, _ = intake
    assert send(intake).status_code == 202
    db.roles = {"support"}
    db.role_drop = True
    cid = next(iter(db.case_rows))
    response = c.request(
        "PATCH",
        CASES + "/" + cid,
        json={"expected_revision": 1, "action": "claim", "confirmed": True},
        headers=h(),
    )
    assert (
        response.status_code == 403
        and db.case_rows[cid]["assigned_staff_id"] is None
        and not db.staff_receipts
    )


def test_existing_openapi_contracts_unchanged_except_new_014(intake):
    c, _, s, _, _, _ = intake
    current = c.application.openapi()
    previous_app = create_app(s)
    previous_app.router.routes = [
        r for r in previous_app.router.routes if getattr(r, "path", None) != URL
    ]
    previous = previous_app.openapi()
    for path, contract in previous["paths"].items():
        assert current["paths"][path] == contract, path
    for name, contract in previous["components"]["schemas"].items():
        assert current["components"]["schemas"][name] == contract, name
    assert current["paths"][URL]["post"]["operationId"] == "API-014"
    assert "422" not in current["paths"][URL]["post"]["responses"]


def test_policy_and_request_are_closed_and_no_synthetic_defaults():
    assert Settings(_env_file=None).abuse_reports_enabled is False
    with pytest.raises(ValueError):
        Policy.model_validate({})
    value = fixture_policy()["body"]
    value["retention"]["budget"]["duration_seconds"] = 1
    with pytest.raises(ValueError):
        Policy.model_validate(value)
    with pytest.raises(ValueError):
        Report.model_validate(
            {
                "qr_token": "S" * 43,
                "category": "spam",
                "consent_accepted": True,
                "consent_version": "abuse-report-v1",
                "contact": "x",
            }
        )


@pytest.mark.parametrize(
    "target", ["S" * 43, "unknown" * 8, "retired" * 8, "revoked" * 8]
)
def test_unverified_target_claims_have_identical_receipt_and_no_lookup(intake, target):
    _, db, _, _, _, _ = intake
    response = send(intake, qr_token=target, message_id=str(uuid4()))
    assert response.status_code == 202 and response.content == b'{"status":"accepted"}'
    assert len(db.reports) == 1
    assert all(
        "qr_codes" not in sql
        and "finder_messages" not in sql
        and "auth.users" not in sql
        for sql in db.calls
    )


def test_same_key_concurrent_replay_uses_one_case_in_python_fixture(intake):
    c, db, _, b, h, _ = intake
    values = [b(), b()]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(lambda i: c.post(URL, json=values[i], headers=h()), range(2))
        )
    assert all(r.status_code == 202 for r in responses)
    assert len(db.reports) == len(db.public_receipts) == 1


def test_missing_migration_and_withdrawal_during_provider_are_unavailable(intake):
    _, db, _, _, _, challenge = intake
    db.capability = False
    assert send(intake).status_code == 503 and not db.attempts
    db.capability = True
    db.info.clear()
    challenge["after"] = lambda: db.row.update(revoked=True)
    assert send(intake).status_code == 503 and not db.reports


def test_staff_live_session_mfa_and_missing_bearer_are_checked(intake):
    c, db, _, _, h, _ = intake
    assert send(intake).status_code == 202
    db.roles = {"support"}
    assert c.get(CASES).status_code == 401
    db.mfa = False
    assert c.get(CASES, headers=h()).status_code == 403
    db.mfa = True
    db.active = False
    assert c.get(CASES, headers=h()).status_code == 401


def test_retained_staff_receipt_expiry_and_changed_body_do_not_mutate_case(intake):
    c, db, _, _, h, _ = intake
    assert send(intake).status_code == 202
    db.roles = {"support"}
    cid = next(iter(db.case_rows))
    body = {"expected_revision": 1, "action": "claim", "confirmed": True}
    path = CASES + "/" + cid
    assert c.request("PATCH", path, json=body, headers=h()).status_code == 200
    assert c.request("PATCH", path, json=body, headers=h()).status_code == 200
    changed = {
        "expected_revision": 2,
        "action": "update",
        "note": "Synthetic note",
        "confirmed": True,
    }
    assert c.request("PATCH", path, json=changed, headers=h()).status_code == 409
    next(iter(db.staff_receipts.values()))["receipt_live"] = False
    assert c.request("PATCH", path, json=body, headers=h()).status_code == 503
    assert db.case_rows[cid]["case_revision"] == 2


def test_ordinary_support_semantics_preserved_without_abuse_policy(intake):
    c, db, _, _, h, _ = intake
    assert send(intake).status_code == 202
    original = next(iter(db.case_rows.values()))
    ordinary = deepcopy(original)
    ordinary.update(id=str(uuid4()), assigned_staff_id=db.owner, status="investigating")
    db.case_rows[ordinary["id"]] = ordinary
    db.row = None
    db.roles = {"support"}
    listing = c.get(CASES, headers=h())
    assert listing.status_code == 200 and [
        r["id"] for r in listing.json()["items"]
    ] == [ordinary["id"]]
    assert not listing.json()["items"][0]["requires_escalation"]
    response = c.request(
        "PATCH",
        CASES + "/" + ordinary["id"],
        json={
            "expected_revision": 1,
            "action": "update",
            "status": "resolved",
            "confirmed": True,
        },
        headers=h(),
    )
    assert response.status_code == 200, response.text


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        {"allowed": "false"},
        {"allowed": 1},
        {"allowed": True, "extra": "PRIVATE_CANARY"},
    ],
)
def test_malformed_database_admission_result_is_unavailable(value):
    from types import SimpleNamespace

    from app.core.abuse_intake import Unavailable
    from app.db.abuse_intake import Repository

    with pytest.raises(Unavailable):
        Repository(SimpleNamespace(execute=lambda *a: Result(value))).call("peer", {})
