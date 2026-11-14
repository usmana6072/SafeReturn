"""Task2.3D synthetic HTTP/crypto/orchestration; SQLite-adapted guard predicates.

No real Auth/PG, worker/provider execution or PostgreSQL locking/MVCC proof.
"""

import base64
import importlib.util
import io
import json
import re
import sqlite3
import time
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from threading import Event, Thread
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.exc import OperationalError
from test_auth import claims, signed
from test_auth import verifier as _verifier
from test_critical_workflow_boundaries import Result
from test_health import ASGIClient

from app.core.config import Settings
from app.main import create_app

verifier = _verifier
ORIGIN = "https://synthetic.test"
CANARY = "PRIVATE_LIFECYCLE_CANARY"
FILE = Path(__file__).parents[1] / "alembic/versions/0030_account_lifecycle.sql"
SQL = FILE.read_text()
SESSION_SQL = re.search(
    r"RETURN QUERY (SELECT u.email_confirmed_at.*?);\nEND", SQL, re.DOTALL
)[1]
SESSION_SQL = (
    SESSION_SQL.replace("public.", "")
    .replace("auth.", "")
    .replace("s.aal::text", "s.aal")
    .replace("sr_actor_id()", ":actor")
    .replace("clock_timestamp()", ":now")
    .replace("s.id=sid", "s.id=:sid")
)
EPOCH_SQL = re.search(
    r"SELECT EXISTS\(SELECT 1 FROM auth.users u LEFT JOIN.*?INTO allowed;",
    SQL,
    re.DOTALL,
)[0].replace(" INTO allowed", "")
EPOCH_SQL = (
    EPOCH_SQL.replace("public.", "")
    .replace("auth.", "")
    .replace("u.id=uid", "u.id=:uid")
    .replace("clock_timestamp()", ":now")
    .replace("issued_at>", ":issued>")
)


class Rows(Result):
    def scalars(self):
        return iter(self.value)


class Store:
    def __init__(self):
        self.actor_id, self.subject, self.approver, self.case = (
            uuid4(),
            uuid4(),
            uuid4(),
            uuid4(),
        )
        self.now = time.time()
        self.sql = sqlite3.connect(
            ":memory:", check_same_thread=False, isolation_level=None
        )
        self.sql.executescript("""CREATE TABLE users(id TEXT PRIMARY KEY,email_confirmed_at FLOAT,deleted_at FLOAT,is_anonymous BOOL,banned_until FLOAT);
        CREATE TABLE sessions(id TEXT PRIMARY KEY,user_id TEXT,created_at FLOAT,aal TEXT,not_after FLOAT);
        CREATE TABLE account_security_state(user_id TEXT PRIMARY KEY,state TEXT,revision INT,invalidate_before FLOAT,updated_at FLOAT);""")
        self.roles = {
            self.actor_id: {"security_admin"},
            self.approver: {"security_admin"},
            self.subject: {"operations", "finance"},
        }
        self.sids = {}
        for uid in self.roles:
            self.sql.execute(
                "INSERT INTO users VALUES(?,?,NULL,0,NULL)", (str(uid), self.now - 100)
            )
            self.new_session(uid, self.now - 20)
        self.custody = {
            self.approver: {
                "verified": self.now - 50,
                "expires": self.now + 3600,
                "revoked": False,
            }
        }
        self.case_status = "investigating"
        self.binding = self.subject
        self.binding_revoked = False
        self.approvals = []
        self.events = []
        self.audit = []
        self.receipts = {}
        self.commits, self.rollbacks = 0, 0
        self.timeout = "5s"
        self.info = {}
        self.actor = None
        self.busy = set()
        self.global_busy = False
        self.hook = None
        self.fail = None
        self.history = {
            "order": "immutable paid allocation",
            "qr": "public active",
            "support": CANARY,
            "role_grants": CANARY,
        }
        self.approve("suspend", 1, "security_review")

    def new_session(self, uid, created=None):
        sid = uuid4()
        self.sql.execute(
            "INSERT INTO sessions VALUES(?,?,?,?,?)",
            (
                str(sid),
                str(uid),
                created if created is not None else self.now + 1,
                "aal2",
                self.now + 3600,
            ),
        )
        self.sids[uid] = sid
        return sid

    def state(self, uid=None):
        r = self.sql.execute(
            "SELECT state,revision,invalidate_before,updated_at FROM account_security_state WHERE user_id=?",
            (str(uid or self.subject),),
        ).fetchone()
        return (
            {"state": r[0], "revision": r[1], "epoch": r[2], "updated": r[3]}
            if r
            else {"state": "active", "revision": 1, "epoch": None, "updated": None}
        )

    def epoch(self, uid, issued):
        return (
            self.sql.execute(
                EPOCH_SQL, {"uid": str(uid), "issued": issued, "now": self.now}
            ).fetchone()[0]
            == 1
        )

    def custodian(self, uid):
        c = self.custody.get(uid)
        return bool(
            c
            and not c["revoked"]
            and c["expires"] > self.now
            and "security_admin" in self.roles.get(uid, set())
            and self.epoch(uid, c["verified"])
        )

    def approve(self, action, revision, reason):
        self.now += 0.01
        a = {
            "id": str(uuid4()),
            "subject": self.subject,
            "case": self.case,
            "executor": self.actor_id,
            "approver": self.approver,
            "action": action,
            "revision": revision,
            "reason": reason,
            "created": self.now,
            "expires": self.now + 600,
            "revoked": False,
            "used": False,
        }
        self.approvals.append(a)
        return a

    @contextmanager
    def transaction(self):
        snapshot = deepcopy((self.approvals, self.events, self.audit, self.receipts))
        timeout = self.timeout
        self.sql.execute("SAVEPOINT request")
        try:
            yield self
            if self.fail == "commit":
                raise OperationalError("COMMIT", {}, Exception(CANARY))
        except BaseException:
            self.sql.execute("ROLLBACK TO request")
            self.sql.execute("RELEASE request")
            self.approvals, self.events, self.audit, self.receipts = snapshot
            self.rollbacks += 1
            self.timeout = timeout
            raise
        else:
            self.sql.execute("RELEASE request")
            self.commits += 1
        finally:
            self.actor = None

    def context(self, p):
        if self.global_busy or p["uid"] in self.busy:
            return {"error": "CONTENTION"}
        if (
            self.actor == p["uid"]
            or self.case_status not in ("open", "investigating")
            or self.binding != p["uid"]
            or self.binding_revoked
            or p["cid"] != self.case
        ):
            return None
        old = self.receipts.get(p["scope"])
        if old and old["hash"] != p["digest"]:
            return {"error": "IDEMPOTENCY_KEY_REUSED"}
        a = next(
            (
                a
                for a in self.approvals
                if a["subject"] == p["uid"]
                and a["case"] == p["cid"]
                and a["executor"] == self.actor
                and a["action"] == p["action"]
                and a["reason"] == p["reason"]
                and a["revision"] == p["revision"]
                and not a["revoked"]
                and a["expires"] > self.now
                and (
                    a["id"] == old["approval"]
                    if old
                    else not a["used"]
                    and (
                        self.state()["updated"] is None
                        or a["created"] > self.state()["updated"]
                    )
                )
            ),
            None,
        )
        if (
            not a
            or a["approver"] in (self.actor, p["uid"])
            or not self.custodian(a["approver"])
            or not self.epoch(self.actor, a["created"])
            or not self.epoch(a["approver"], a["created"])
        ):
            return None
        if old:
            return {
                "approval_id": a["id"],
                "receipt": {
                    "cipher": old["cipher"].hex(),
                    "key_version": old["version"],
                },
            }
        if self.state()["revision"] != p["revision"]:
            return {"error": "STALE_VERSION"}
        return {"approval_id": a["id"], "receipt": None}

    def execute(self, statement, params=None):
        q, p = str(statement), params or {}
        if "SET LOCAL ROLE" in q:
            return Result(None)
        if "set_config('safereturn.actor_id'" in q:
            self.actor = UUID(p["actor"])
            return Result(None)
        if "set_config('safereturn.mfa_verified'" in q:
            return Result(None)
        if q == "SHOW statement_timeout":
            return Result(self.timeout)
        if "set_config('statement_timeout'" in q:
            self.timeout = p.get("timeout", "3000ms")
            return Result(None)
        if "sr_account_session_state" in q:
            r = self.sql.execute(
                SESSION_SQL,
                {"actor": str(self.actor), "sid": str(p["sid"]), "now": self.now},
            ).fetchone()
            return Result(
                SimpleNamespace(email_verified=bool(r[0]), mfa_active=bool(r[1]))
                if r
                else None
            )
        if "SELECT 1 FROM public.staff_roles" in q:
            return Result(
                1 if self.roles.get(p["uid"], set()).intersection(p["roles"]) else None
            )
        if "SELECT role FROM public.staff_roles" in q:
            return Rows(sorted(self.roles.get(p["uid"], set())))
        if "sr_lifecycle_" in q:
            assert self.timeout == "3000ms"
            if self.fail == "sql":
                raise OperationalError("SELECT", {}, Exception(CANARY))
            if "sr_lifecycle_context" in q:
                return Result(self.context(p))
            if "sr_lifecycle_apply" in q:
                snap = self.context(p)
                if not snap or "error" in snap:
                    return Result(snap)
                a = next(a for a in self.approvals if a["id"] == snap["approval_id"])
                state = self.state()
                if (p["action"] == "suspend" and state["state"] == "suspended") or (
                    p["action"] == "restore" and state["state"] == "active"
                ):
                    return Result({"error": "INVALID_STATE"})
                if p["action"] == "suspend" and not any(
                    uid != p["uid"] and self.custodian(uid) for uid in self.custody
                ):
                    return Result({"error": "LAST_CUSTODIAN"})
                self.now += 0.01
                epoch = (
                    self.now if p["action"] != "recovery_escalated" else state["epoch"]
                )
                new = (
                    "suspended"
                    if p["action"] == "suspend"
                    else "active"
                    if p["action"] == "restore"
                    else state["state"]
                )
                self.sql.execute(
                    "INSERT OR REPLACE INTO account_security_state VALUES(?,?,?,?,?)",
                    (str(p["uid"]), new, p["revision"] + 1, epoch, self.now),
                )
                result = {
                    "user_id": str(p["uid"]),
                    "case_id": str(p["cid"]),
                    "action": p["action"],
                    "revision": p["revision"] + 1,
                    "event_id": str(uuid4()),
                    "occurred_at": datetime.fromtimestamp(self.now, UTC).isoformat(),
                }
                if p["action"] == "recovery_escalated":
                    result["status"] = "referred"
                else:
                    result.update(state=new, fresh_sign_in_required=True)
                self.events.append(deepcopy(result))
                self.audit.append((p["action"], p["revision"] + 1))
                a["used"] = True
                if self.hook:
                    self.hook(self)
                if self.fail == "projection":
                    result["private"] = CANARY
                return Result(result)
            if "sr_lifecycle_save_receipt" in q:
                if self.fail == "save":
                    raise OperationalError("INSERT", {}, Exception(CANARY))
                self.receipts[p["scope"]] = {
                    "hash": p["digest"],
                    "approval": p["approval"],
                    "cipher": p["cipher"],
                    "version": p["version"],
                }
                return Result(True)
        raise AssertionError("Unexpected scoped query: " + q)


@pytest.fixture
def env(verifier):
    provider, private, _, _ = verifier
    db = Store()
    settings = Settings(
        account_lifecycle_enabled=True,
        account_lifecycle_web_origin=ORIGIN,
        profile_data_keys=json.dumps({"1": base64.b64encode(b"s" * 32).decode()}),
    )
    app = create_app(settings)
    app.state.database, app.state.jwt_verifier = db, provider

    def headers(uid=None, **overrides):
        uid = uid or db.actor_id
        return {
            "Authorization": "Bearer "
            + signed(
                private,
                claims(
                    **{
                        "sub": str(uid),
                        "session_id": str(db.sids[uid]),
                        "aal": "aal2",
                        "amr": [{"method": "totp", "timestamp": int(time.time()) - 1}],
                        **overrides,
                    }
                ),
            ),
            "Origin": ORIGIN,
            "Idempotency-Key": "synthetic-key-0001",
        }

    yield ASGIClient(app), db, headers, settings, app
    db.sql.close()


def post(
    env, action="suspensions", body=None, headers=None, uid=None, key=None, query=""
):
    db = env[1]
    body = (
        body
        if body is not None
        else {
            "case_id": str(db.case),
            "expected_revision": 1,
            "reason_code": "security_review",
            "confirmed": True,
        }
    )
    headers = headers if headers is not None else env[2]()
    if key:
        headers = {**headers, "Idempotency-Key": key}
    return env[0].post(
        "/api/v1/admin/users/" + str(uid or db.subject) + "/" + action + query,
        json=body,
        headers=headers,
    )


def body(env, revision=1, reason="review_cleared"):
    return {
        "case_id": str(env[1].case),
        "expected_revision": revision,
        "reason_code": reason,
        "confirmed": True,
    }


@pytest.mark.parametrize(
    "roles",
    [
        set(),
        {"support"},
        {"operations"},
        {"finance"},
        {"superadmin"},
        {"operations", "finance"},
        {"security_admin"},
        {"security_admin", "finance"},
    ],
)
def test_explicit_roles_no_inheritance(env, roles):
    env[1].roles[env[1].actor_id] = roles
    r = post(env)
    assert r.status_code == (200 if "security_admin" in roles else 403)
    assert (
        r.headers["cache-control"] == "private, no-store"
        and r.headers["x-content-type-options"] == "nosniff"
    )


@pytest.mark.parametrize(
    "fault,status",
    [
        ("anonymous", 401),
        ("expired", 401),
        ("foreign_sid", 401),
        ("signed_aal1", 403),
        ("provider_aal1", 403),
        ("unverified", 403),
        ("missing_amr", 403),
        ("stale_amr", 403),
        ("iat_only", 403),
        ("future_amr", 403),
        ("origin", 403),
        ("missing_key", 400),
        ("disabled", 503),
        ("query", 422),
    ],
)
def test_session_mfa_recent_amr_and_transport(env, fault, status):
    db = env[1]
    h = env[2]()
    q = ""
    if fault == "anonymous":
        h = {}
    if fault == "expired":
        h = env[2](exp=int(time.time()) - 60)
    if fault == "foreign_sid":
        h = env[2](session_id=str(uuid4()))
    if fault == "signed_aal1":
        h = env[2](aal="aal1")
    if fault == "provider_aal1":
        db.sql.execute("UPDATE sessions SET aal='aal1'")
    if fault == "unverified":
        db.sql.execute(
            "UPDATE users SET email_confirmed_at=NULL WHERE id=?", (str(db.actor_id),)
        )
    if fault in ("missing_amr", "iat_only"):
        h = env[2](amr=[])
    if fault == "stale_amr":
        h = env[2](amr=[{"method": "totp", "timestamp": int(time.time()) - 301}])
    if fault == "future_amr":
        h = env[2](amr=[{"method": "totp", "timestamp": int(time.time()) + 60}])
    if fault == "origin":
        h["Origin"] = "https://untrusted.test"
    if fault == "missing_key":
        h.pop("Idempotency-Key")
    if fault == "disabled":
        env[3].account_lifecycle_enabled = False
    if fault == "query":
        q = "?anything=" + CANARY
    assert post(env, headers=h, query=q).status_code == status
    assert db.state()["revision"] == 1 and db.events == []


@pytest.mark.parametrize(
    "change",
    [
        {"confirmed": False},
        {"confirmed": 1},
        {"expected_revision": True},
        {"expected_revision": 0},
        {"reason_code": "arbitrary"},
        {"private": CANARY},
        {"case_id": "bad"},
    ],
)
def test_closed_command_schema(env, change):
    b = body(env, reason="security_review")
    b.update(change)
    r = post(env, body=b)
    assert r.status_code == 422 and CANARY not in r.text and env[1].events == []


@pytest.mark.parametrize(
    "fault",
    [
        "binding",
        "closed_case",
        "expired_approval",
        "revoked_approval",
        "same_approver",
        "missing_custody",
        "expired_custody",
        "revoked_approver",
        "self",
        "wrong_case",
        "wrong_subject",
        "preissued_approval",
    ],
)
def test_case_authority_independent_custody_and_protected_targets(env, fault):
    db = env[1]
    a = db.approvals[0]
    uid = None
    b = None
    if fault == "binding":
        db.binding_revoked = True
    if fault == "closed_case":
        db.case_status = "closed"
    if fault == "expired_approval":
        a["expires"] = db.now - 1
    if fault == "revoked_approval":
        a["revoked"] = True
    if fault == "same_approver":
        a["approver"] = db.actor_id
    if fault == "missing_custody":
        db.custody = {}
    if fault == "expired_custody":
        db.custody[db.approver]["expires"] = db.now - 1
    if fault == "revoked_approver":
        db.roles[db.approver] = set()
    if fault == "self":
        uid = db.actor_id
    if fault == "wrong_subject":
        uid = uuid4()
    if fault == "wrong_case":
        b = body(env, reason="security_review")
        b["case_id"] = str(uuid4())
    if fault == "preissued_approval":
        db.sql.execute(
            "INSERT INTO account_security_state VALUES(?,?,?,?,?)",
            (str(db.subject), "active", 1, None, db.now + 1),
        )
    assert post(env, uid=uid, body=b).status_code == 404
    assert db.events == []


def test_suspend_restore_fresh_session_and_preserved_roles_business_history(env):
    db = env[1]
    history = deepcopy(db.history)
    roles = deepcopy(db.roles)
    old_sid = db.sids[db.subject]
    assert post(env).status_code == 200
    cutoff1 = db.state()["epoch"]
    env[3].account_lifecycle_enabled = False
    assert (
        env[0].get("/api/v1/me/staff-security", headers=env[2](db.subject)).status_code
        == 401
    )
    env[3].account_lifecycle_enabled = True
    db.approve("restore", 2, "review_cleared")
    r = post(env, "restorations", body(env, 2), key="synthetic-restore")
    assert r.status_code == 200 and r.json()["fresh_sign_in_required"] is True
    assert db.state()["epoch"] > cutoff1
    assert (
        env[0].get("/api/v1/me/staff-security", headers=env[2](db.subject)).status_code
        == 401
    )
    # An existing pre-restoration session acquiring new AMR still fails.
    assert (
        env[0]
        .get(
            "/api/v1/me/staff-security",
            headers=env[2](
                db.subject,
                session_id=str(old_sid),
                amr=[{"method": "totp", "timestamp": int(time.time())}],
            ),
        )
        .status_code
        == 401
    )
    db.new_session(db.subject, db.state()["epoch"])
    assert (
        env[0].get("/api/v1/me/staff-security", headers=env[2](db.subject)).status_code
        == 401
    )
    db.new_session(db.subject, db.state()["epoch"] + 0.001)
    r = env[0].get("/api/v1/me/staff-security", headers=env[2](db.subject))
    assert r.status_code == 200 and set(r.json()["roles"]) == {"operations", "finance"}
    assert db.roles == roles and db.history == history
    db.roles[db.subject] = {"finance"}
    assert set(
        env[0]
        .get("/api/v1/me/staff-security", headers=env[2](db.subject))
        .json()["roles"]
    ) == {"finance"}


def test_recovery_referral_preserves_state_epoch_and_case(env):
    db = env[1]
    history = deepcopy(db.history)
    db.approve("recovery_escalated", 1, "factor_loss")
    r = post(env, "recovery-escalations", body(env, 1, "factor_loss"))
    assert r.status_code == 202 and r.json()["status"] == "referred"
    assert (
        db.state()["state"] == "active"
        and db.state()["epoch"] is None
        and db.state()["revision"] == 2
    )
    assert db.history == history and db.case_status == "investigating"


@pytest.mark.parametrize("fault", ["approval", "case", "approver", "amr"])
def test_replay_rechecks_current_authority(env, fault):
    assert post(env).status_code == 200
    db = env[1]
    if fault == "approval":
        db.approvals[0]["revoked"] = True
    if fault == "case":
        db.case_status = "closed"
    if fault == "approver":
        db.roles[db.approver] = set()
    h = env[2](amr=[]) if fault == "amr" else None
    assert post(env, headers=h).status_code == (403 if fault == "amr" else 404)
    assert len(db.events) == 1


def test_encrypted_idempotency_conflict_consumption_and_later_state_replay(env):
    db = env[1]
    first = post(env)
    assert first.status_code == 200
    assert post(env).json() == first.json() and len(db.events) == 1
    assert CANARY.encode() not in next(iter(db.receipts.values()))["cipher"]
    assert post(env, body=body(env, reason="abuse_review")).status_code == 409
    db.approve("restore", 2, "review_cleared")
    assert (
        post(env, "restorations", body(env, 2), key="synthetic-restore").status_code
        == 200
    )
    assert post(env).json() == first.json() and db.state()["state"] == "active"
    assert len(db.events) == 2


@pytest.mark.parametrize(
    "action,state,reason",
    [
        ("suspensions", "suspended", "security_review"),
        ("restorations", "active", "review_cleared"),
    ],
)
def test_same_state_and_stale_revision(env, action, state, reason):
    db = env[1]
    if state == "suspended":
        assert post(env).status_code == 200
    rev = db.state()["revision"]
    db.approve("suspend" if action == "suspensions" else "restore", rev, reason)
    assert (
        post(
            env, action, body(env, rev, reason), key="synthetic-new-action"
        ).status_code
        == 409
    )
    if state == "suspended":
        db.approve("restore", 1, "review_cleared")
        assert (
            post(
                env, "restorations", body(env, 1), key="synthetic-stale-action"
            ).status_code
            == 412
        )


@pytest.mark.parametrize(
    "fault",
    [
        "sql",
        "save",
        "commit",
        "projection",
        "crypto",
        "final_role",
        "final_mfa",
        "final_approval",
    ],
)
def test_atomic_rollback_and_safe_errors(env, fault, caplog):
    db = env[1]
    if fault == "crypto":
        env[3].profile_data_keys = None
    elif fault == "final_role":
        db.hook = lambda d: d.roles.__setitem__(d.actor_id, set())
    elif fault == "final_mfa":
        db.hook = lambda d: d.sql.execute(
            "UPDATE sessions SET aal='aal1' WHERE user_id=?", (str(d.actor_id),)
        )
    elif fault == "final_approval":
        db.hook = lambda d: d.approvals[0].__setitem__("revoked", True)
    else:
        db.fail = fault
    r = post(env)
    assert r.status_code in (401, 403, 404, 503) and CANARY not in r.text + caplog.text
    assert (
        db.state()["revision"] == 1
        and not db.events
        and not db.audit
        and not db.receipts
    )
    assert not db.approvals[0]["used"] and db.rollbacks == 1 and db.timeout == "5s"


@pytest.mark.parametrize("busy", ["global", "target"])
def test_nonblocking_contention_and_retry(env, busy):
    db = env[1]
    if busy == "global":
        db.global_busy = True
    else:
        db.busy.add(db.subject)
    assert post(env).status_code == 409 and not db.events
    db.global_busy = False
    db.busy.clear()
    assert post(env).status_code == 200


def test_inflight_request_scheduler_and_single_revision_winner(env):
    # Synthetic shared-lock scheduler only; not a PostgreSQL race/deadlock test.
    db = env[1]
    held, release = Event(), Event()

    def inflight():
        db.busy.add(db.subject)
        held.set()
        release.wait(10)
        db.busy.remove(db.subject)

    thread = Thread(target=inflight)
    thread.start()
    assert held.wait(3)
    try:
        assert post(env).status_code == 409
    finally:
        release.set()
        thread.join(3)
    first = post(env)
    assert first.status_code == 200
    second = post(env, key="synthetic-competing-command")
    assert second.status_code == 404 and len(db.events) == 1


@pytest.mark.parametrize(
    "grant",
    [
        "print",
        "privacy_request",
        "privacy_approval",
        "manufacturing_approval",
        "manufacturing_job",
        "finance_authority",
        "untimestamped_authority",
    ],
)
def test_production_epoch_predicate_permanently_fences_old_authority(env, grant):
    db = env[1]
    issued = None if grant == "untimestamped_authority" else db.now - 5
    assert db.epoch(db.subject, issued)
    assert post(env).status_code == 200 and not db.epoch(db.subject, issued)
    db.approve("restore", 2, "review_cleared")
    assert (
        post(env, "restorations", body(env, 2), key="synthetic-restore").status_code
        == 200
    )
    assert not db.epoch(db.subject, issued)
    if issued is not None:
        assert db.epoch(db.subject, db.now + 1)
    assert db.history["qr"] == "public active"


@pytest.mark.parametrize(
    "fault", ["deleted", "anonymous", "provider_banned", "session_expired"]
)
def test_existing_provider_predicates_remain_authoritative(env, fault):
    db = env[1]
    if fault == "session_expired":
        db.sql.execute(
            "UPDATE sessions SET not_after=? WHERE user_id=?",
            (db.now - 1, str(db.actor_id)),
        )
    else:
        field = {
            "deleted": "deleted_at",
            "anonymous": "is_anonymous",
            "provider_banned": "banned_until",
        }[fault]
        db.sql.execute(
            "UPDATE users SET " + field + "=? WHERE id=?",
            (1 if fault == "anonymous" else db.now + 10, str(db.actor_id)),
        )
    assert post(env).status_code == 401


def test_offline_migration_emission_guarded_rollback_and_contracts(env):
    path = FILE.with_suffix(".py")
    spec = importlib.util.spec_from_file_location("lifecycle_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    capture = io.StringIO()
    ctx = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": capture}
    )
    with Operations.context(ctx):
        module.upgrade()
        with pytest.raises(RuntimeError, match="Security history downgrade disabled"):
            module.downgrade()
    target = Path(__file__).parents[2] / "output/task23d"
    target.mkdir(parents=True, exist_ok=True)
    (target / "offline-upgrade.sql").write_text(capture.getvalue())
    (target / "offline-downgrade.txt").write_text(
        "REFUSED: Security history downgrade disabled; use reviewed forward correction.\n"
    )
    assert module.down_revision == "0029_staff_directory"
    assert "GRANT SELECT ON auth." not in SQL and not re.search(
        r"(UPDATE|DELETE FROM|INSERT INTO) auth\.", SQL
    )
    assert "pg_try_advisory_xact_lock" in SQL and "pg_advisory_xact_lock_shared" in SQL
    assert (
        "s.created_at>a.invalidate_before" in SQL
        and "SET search_path=pg_catalog" in SQL
    )
    for name in (
        "sr_account_session_state",
        "sr_export_current",
        "sr_export_authorized",
        "sr_mfg_authorized",
        "sr_financial_case_context",
    ):
        assert "CREATE OR REPLACE FUNCTION public." + name in SQL
    assert (
        "ALTER POLICY sr_print_grant_use" in SQL
        and "ALTER POLICY sr_export_worker" in SQL
    )
    paths = env[4].openapi()["paths"]
    for suffix, op in [
        ("suspensions", "API-320"),
        ("restorations", "API-321"),
        ("recovery-escalations", "API-322"),
    ]:
        assert (
            paths["/api/v1/admin/users/{user_id}/" + suffix]["post"]["operationId"]
            == op
        )
    assert paths["/api/v1/admin/users/count"]["get"]["operationId"] == "API-348"
    assert (
        not Settings().account_lifecycle_enabled
        and Settings().account_lifecycle_web_origin is None
    )


def test_last_qualifying_custodian_is_not_suspended_without_independent_custody(env):
    db = env[1]
    db.custody = {
        db.subject: {
            "verified": db.now - 50,
            "expires": db.now + 3600,
            "revoked": False,
        }
    }
    db.roles[db.subject] = {"security_admin"}
    assert db.custodian(db.subject)
    assert post(env).status_code == 404
    assert (
        db.state()["state"] == "active" and db.custodian(db.subject) and not db.events
    )


def test_referral_while_suspended_does_not_restore_or_invalidate_again(env):
    db = env[1]
    assert post(env).status_code == 200
    epoch = db.state()["epoch"]
    db.approve("recovery_escalated", 2, "factor_loss")
    r = post(
        env,
        "recovery-escalations",
        body(env, 2, "factor_loss"),
        key="synthetic-referral",
    )
    assert (
        r.status_code == 202
        and db.state()["state"] == "suspended"
        and db.state()["epoch"] == epoch
    )


def test_encrypted_receipt_tampering_rolls_back_without_new_security_event(env, caplog):
    assert post(env).status_code == 200
    db = env[1]
    saved = next(iter(db.receipts.values()))
    saved["cipher"] = b"PRIVATE_LIFECYCLE_CANARY"
    r = post(env)
    assert (
        r.status_code == 503
        and CANARY not in r.text + caplog.text
        and len(db.events) == 1
    )


def test_actual_manufacturing_admission_sql_keeps_original_identity_role_and_epoch_checks(
    env,
):
    db = env[1]
    db.sql.executescript("""CREATE TABLE staff_roles(user_id TEXT,role TEXT,revoked_at FLOAT);
    CREATE TABLE manufacturing_sources(batch_id TEXT,manifest_sha256 TEXT,printer_key_fingerprint TEXT);
    CREATE TABLE manufacturing_approvals(batch_id TEXT,executor TEXT,approver TEXT,revoked_at FLOAT,manifest_sha256 TEXT,printer_key_fingerprint TEXT,created_at FLOAT);
    CREATE TABLE manufacturing_exports(batch_id TEXT,created_at FLOAT);""")
    for uid, roles in db.roles.items():
        for role in roles:
            db.sql.execute("INSERT INTO staff_roles VALUES(?,?,NULL)", (str(uid), role))
    db.sql.execute(
        "INSERT INTO manufacturing_sources VALUES('batch','hash','fingerprint')"
    )
    db.sql.execute(
        "INSERT INTO manufacturing_approvals VALUES('batch',?,?,NULL,'hash','fingerprint',?)",
        (str(db.subject), str(db.approver), db.now - 2),
    )
    db.sql.execute("INSERT INTO manufacturing_exports VALUES('batch',?)", (db.now - 1,))
    db.sql.create_function(
        "sr_account_epoch_allows", 2, lambda uid, issued: db.epoch(UUID(uid), issued)
    )
    sql = re.search(
        r"CREATE OR REPLACE FUNCTION public.sr_mfg_authorized.*?AS \$\$(.*?)\$\$;",
        SQL,
        re.DOTALL,
    )[1]
    sql = re.sub(r"\bbid\b", ":bid", sql.replace("public.", ""))

    def allowed():
        return db.sql.execute(sql, {"bid": "batch"}).fetchone()[0] == 1

    assert allowed()
    db.sql.execute("UPDATE manufacturing_sources SET manifest_sha256='changed'")
    assert not allowed()
    db.sql.execute("UPDATE manufacturing_sources SET manifest_sha256='hash'")
    assert post(env).status_code == 200 and not allowed()
    db.approve("restore", 2, "review_cleared")
    assert (
        post(env, "restorations", body(env, 2), key="synthetic-restore").status_code
        == 200
        and not allowed()
    )
    db.sql.execute("UPDATE manufacturing_approvals SET created_at=?", (db.now + 1,))
    assert (
        not allowed()
    )  # original job still predates invalidation; cannot silently restart
    db.sql.execute("UPDATE manufacturing_exports SET created_at=?", (db.now + 2,))
    assert allowed()
    db.sql.execute(
        "UPDATE staff_roles SET revoked_at=1 WHERE user_id=? AND role='operations'",
        (str(db.subject),),
    )
    assert not allowed()


def test_finance_authority_guards_are_additive_to_both_original_checks():
    original = (FILE.parent / "0025_financial_disputes.sql").read_text()
    before = re.search(
        r"CREATE FUNCTION public.sr_financial_case_context.*?END \$\$;",
        original,
        re.DOTALL,
    )[0]
    after = re.search(
        r"CREATE OR REPLACE FUNCTION public.sr_financial_case_context.*?END \$\$;",
        SQL,
        re.DOTALL,
    )[0]
    fence = " AND public.sr_account_epoch_allows(finance_user_id,created_at) AND public.sr_account_epoch_allows(provisioned_by,created_at)"
    assert after.count(fence) == 2
    assert (
        after.replace(fence, "").replace(
            "CREATE OR REPLACE FUNCTION", "CREATE FUNCTION", 1
        )
        == before
    )


def test_privacy_subject_and_untimestamped_authority_fences_are_present():
    assert "public.sr_account_epoch_allows(reviewer,NULL)" in SQL
    assert "public.sr_account_epoch_allows(a.authorized_by,NULL)" in SQL
    assert "public.sr_account_epoch_allows(r.subject_id,r.created_at)" in SQL
    assert "public.sr_account_epoch_allows(r.approver_id,r.approved_at)" in SQL
    assert "public.sr_account_epoch_allows(subject_id,created_at)" in SQL
    assert "WITH CHECK" in SQL and "sr_export_current(privacy_exports)" in SQL


@pytest.mark.parametrize(
    "value",
    [
        "null",
        "https://user:secret@example.test",
        "https://example.test/path",
        "https://example.test?token=secret",
        "http://remote.test",
    ],
)
def test_configured_origin_is_a_fixed_secure_origin(value):
    with pytest.raises(ValueError):
        Settings(account_lifecycle_web_origin=value)


def test_restoration_preserves_role_revocation_during_suspension(env):
    db = env[1]
    assert post(env).status_code == 200
    db.roles[db.subject] = {"finance"}
    db.approve("restore", 2, "review_cleared")
    assert (
        post(env, "restorations", body(env, 2), key="synthetic-restore").status_code
        == 200
    )
    db.new_session(db.subject, db.now + 1)
    response = env[0].get("/api/v1/me/staff-security", headers=env[2](db.subject))
    assert response.status_code == 200 and response.json()["roles"] == ["finance"]
    assert (
        "INSERT INTO public.staff_roles" not in SQL
        and "UPDATE public.staff_roles" not in SQL
    )
