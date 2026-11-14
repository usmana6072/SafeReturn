"""034/035 HTTP/crypto with memory transactions and production history SELECT.

PL/pgSQL command helpers are stand-ins; no PostgreSQL locks/MVCC/provider proof.
"""

import base64
import importlib.util
import json
import re
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier, Lock
from uuid import uuid4

import pytest
from sqlalchemy.exc import OperationalError
from test_auth import claims, signed
from test_auth import verifier as _verifier
from test_critical_workflow_boundaries import MemoryDatabase, Result
from test_health import ASGIClient

from app.core.config import Settings
from app.main import create_app

verifier = _verifier
STAMP = datetime(2026, 1, 1, tzinfo=UTC)
ORIGIN = "https://owner.synthetic.invalid"
CANARY = "PRIVATE_OLD_OWNER_CONTACT_CREDENTIAL_CANARY"
MIGRATION = Path(__file__).parents[1] / "alembic/versions/0032_owner_qr_lifecycle.sql"
SQL = MIGRATION.read_text(encoding="utf-8")
HISTORY = (
    "SELECT a.id AS event_id"
    + SQL.split("SELECT a.id AS event_id", 1)[1].split("LIMIT take) e", 1)[0]
    + "LIMIT :take"
)
HISTORY = HISTORY.replace("p.id", ":pid").replace("p.activated_at", ":activated")
HISTORY = re.sub(r"\bactor\b", ":actor", HISTORY)
for name in ["stamp", "eid"]:
    HISTORY = re.sub(r"\b" + name + r"\b", ":" + name, HISTORY)


class Store(MemoryDatabase):
    def __init__(self, owner):
        super().__init__(owner, uuid4())
        self.lock = Lock()
        self.pid, self.lost, self.ice = uuid4(), uuid4(), uuid4()
        self.roles, self.mfa = set(), False
        self.owner, self.revision, self.ownership = owner, 2, "active"
        self.tags = [
            {"qr_id": self.lost, "tag_type": "lost", "public_status": "active"},
            {"qr_id": self.ice, "tag_type": "ice", "public_status": "active"},
        ]
        self.events, self.receipts = [], {}
        self.events.append(self.event("pair.activated", self.pid, kind="tag_pair"))
        self.fail_query = self.fail_save = False
        self.revoke = None
        self.calls = 0
        self.private_history = False
        self.frozen = {
            "ownership": "synthetic immutable",
            "payment": "verified",
            "allocation": "allocated",
            "hold": "disputed",
            "publication": False,
            "credential": "consumed",
            "tokens": "unchanged",
        }

    def event(
        self, action, target, kind="qr", actor=None, at=None, before=None, after=None
    ):
        return {
            "id": str(uuid4()),
            "action": action,
            "target_id": str(target),
            "target_type": kind,
            "actor_user_id": str(actor or self.owner),
            "occurred_at": (at or STAMP).isoformat(),
            "safe_details": json.dumps(
                {"from_status": before, "to_status": after, "secret": CANARY}
            ),
        }

    def snapshot(self):
        return deepcopy(
            (
                self.revision,
                self.tags,
                self.events,
                self.audit,
                self.receipts,
                self.frozen,
            )
        )

    @contextmanager
    def transaction(self):
        # Fixture serialization only; release may run on another ASGI worker.
        self.lock.acquire()
        old = self.snapshot()
        try:
            yield self
            if self.fail_commit:
                raise OperationalError("COMMIT", {}, Exception(CANARY))
        except BaseException:
            (
                self.revision,
                self.tags,
                self.events,
                self.audit,
                self.receipts,
                self.frozen,
            ) = old
            self.rollbacks += 1
            raise
        else:
            self.commits += 1
        finally:
            self.actor = None
            self.lock.release()

    def allowed(self):
        return str(self.owner) == self.actor and self.ownership == "active"

    def history(self, params):
        if not self.allowed() or params["pid"] != self.pid:
            return None
        # Actual production history SELECT with only PL/pgSQL scalar adaptation.
        with sqlite3.connect(":memory:") as db:
            db.row_factory = sqlite3.Row
            db.execute("ATTACH DATABASE ':memory:' AS public")
            db.execute(
                "CREATE TABLE public.audit_events(id TEXT,action TEXT,target_id TEXT,target_type TEXT,actor_user_id TEXT,occurred_at TEXT,safe_details TEXT)"
            )
            db.execute(
                "CREATE TABLE public.qr_codes(id TEXT,pair_id TEXT,is_current INTEGER,tag_type TEXT)"
            )
            for event in self.events:
                db.execute(
                    "INSERT INTO public.audit_events VALUES(?,?,?,?,?,?,?)",
                    tuple(
                        event[k]
                        for k in [
                            "id",
                            "action",
                            "target_id",
                            "target_type",
                            "actor_user_id",
                            "occurred_at",
                            "safe_details",
                        ]
                    ),
                )
            for tag in self.tags:
                db.execute(
                    "INSERT INTO public.qr_codes VALUES(?,?,1,?)",
                    (str(tag["qr_id"]), str(self.pid), tag["tag_type"]),
                )
            values = {
                "pid": str(self.pid),
                "actor": str(self.owner),
                "activated": STAMP.isoformat(),
                "stamp": params.get("stamp").isoformat()
                if params.get("stamp")
                else None,
                "eid": str(params.get("eid")) if params.get("eid") else None,
                "take": params.get("take", 1),
            }
            events = [dict(r) for r in db.execute(HISTORY, values)]
        value = {
            "pair_id": str(self.pid),
            "pair_revision": self.revision,
            "current_tags": deepcopy(self.tags),
            "items": events,
        }
        if self.private_history:
            value["private"] = CANARY
        return value

    def execute(self, statement, params=None):
        sql, p = str(statement), params or {}
        if "SET LOCAL statement_timeout" in sql:
            return Result(None)
        if "sr_qr_lifecycle_" in sql:
            self.statements.append(sql)
            self.calls += 1
            if self.fail_query:
                raise OperationalError("SELECT", {}, Exception(CANARY))
            if "_history" in sql:
                result = self.history(p)
            elif "_save" in sql:
                if self.fail_save:
                    return Result(False)
                self.receipts[p["scope"]] = {
                    "digest": p["digest"],
                    "cipher": p["cipher"].hex(),
                    "key_version": p["version"],
                }
                result = True
            elif not self.allowed() or not any(
                t["qr_id"] == p["qid"] for t in self.tags
            ):
                result = None
            else:
                tag = next(t for t in self.tags if t["qr_id"] == p["qid"])
                if tag["public_status"] not in {"active", "owner_disabled"}:
                    result = {"error": "INVALID_STATE"}
                elif p["scope"] in self.receipts:
                    old = self.receipts[p["scope"]]
                    result = (
                        {"receipt": {k: old[k] for k in ["cipher", "key_version"]}}
                        if old["digest"] == p["digest"]
                        else {"error": "IDEMPOTENCY_KEY_REUSED"}
                    )
                elif p["expected"] != self.revision:
                    result = {"error": "VERSION_MISMATCH"}
                elif tag["public_status"] == p["wanted"]:
                    result = {"error": "INVALID_STATE"}
                else:
                    before = tag["public_status"]
                    tag["public_status"] = p["wanted"]
                    self.revision += 1
                    if self.fail_audit:
                        raise OperationalError("audit", {}, Exception(CANARY))
                    self.audit.append(
                        {
                            "action": "owner public availability",
                            "before": before,
                            "after": p["wanted"],
                        }
                    )
                    self.events.append(
                        self.event(
                            "qr.owner_disabled"
                            if p["wanted"] == "owner_disabled"
                            else "qr.owner_enabled",
                            tag["qr_id"],
                            before=before,
                            after=p["wanted"],
                        )
                    )
                    result = {
                        "pair_id": str(self.pid),
                        "qr_id": str(tag["qr_id"]),
                        "tag_type": tag["tag_type"],
                        "public_status": p["wanted"],
                        "pair_revision": self.revision,
                    }
            if self.revoke == "session":
                self.active = False
            elif self.revoke == "owner":
                self.owner = uuid4()
            return Result(result)
        return super().execute(statement, params)


@pytest.fixture
def env(verifier):
    provider, private, _, _ = verifier
    owner = uuid4()
    db = Store(owner)
    app = create_app(
        Settings(
            qr_lifecycle_enabled=True,
            qr_lifecycle_web_origin=ORIGIN,
            profile_data_key_version=1,
            profile_data_keys=json.dumps({"1": base64.b64encode(b"q" * 32).decode()}),
        )
    )
    app.state.database, app.state.jwt_verifier = db, provider
    c = ASGIClient(app)

    def headers(**overrides):
        return {
            "Origin": ORIGIN,
            "Idempotency-Key": "synthetic-owner-status",
            "Authorization": "Bearer "
            + signed(
                private,
                claims(
                    **{
                        "sub": str(owner),
                        "aal": "aal1",
                        "amr": [{"method": "password", "timestamp": int(time.time())}],
                        **overrides,
                    }
                ),
            ),
        }

    def body(status="owner_disabled", revision=None):
        return {
            "public_status": status,
            "expected_revision": db.revision if revision is None else revision,
            "reason": "temporary" if status == "owner_disabled" else "resume",
            "confirmed": True,
            "public_access_acknowledged": True,
        }

    return c, db, headers, body, app


def url(db):
    return f"/api/v1/me/tag-pairs/{db.pid}/activation-history"


def target(qid):
    return f"/api/v1/me/qr/{qid}/public-status"


def patch(c, qid, h, body):
    return c.request("PATCH", target(qid), headers=h, json=body)


def test_owner_aal1_disable_sibling_history_and_reenable_no_publication_or_finance_change(
    env,
):
    c, db, h, body, _ = env
    frozen = deepcopy(db.frozen)
    first = patch(c, db.ice, h(), body())
    assert first.status_code == 200, first.text
    assert (
        db.tags[0]["public_status"] == "active"
        and db.tags[1]["public_status"] == "owner_disabled"
    )
    assert db.revision == 3 and db.frozen == frozen
    restored = patch(
        c, db.ice, {**h(), "Idempotency-Key": "synthetic-resume"}, body("active")
    )
    assert restored.status_code == 200 and db.frozen == frozen
    history = c.get(url(db), headers=h())
    assert history.status_code == 200, history.text
    assert {i["event_type"] for i in history.json()["items"]} == {
        "owner_disabled",
        "owner_enabled",
        "activation_completed",
    }
    assert CANARY not in history.text


@pytest.mark.parametrize(
    "role", ["customer", "finance", "operations", "security_admin", "superadmin"]
)
def test_foreign_owner_cannot_inherit_access_or_write(env, role):
    c, db, h, body, _ = env
    db.roles = {role}
    headers = h(sub=str(uuid4()))
    assert c.get(url(db), headers=headers).status_code == 404
    assert patch(c, db.lost, headers, body()).status_code == 404
    assert db.revision == 2 and db.audit == []


@pytest.mark.parametrize(
    "fault",
    [
        "anonymous",
        "expired",
        "session",
        "unverified_signature",
        "missing_amr",
        "stale_amr",
        "future_amr",
        "iat_only",
        "origin",
        "disabled",
    ],
)
def test_live_auth_recent_origin_and_default_gate(env, fault):
    c, db, h, body, app = env
    headers = h()
    if fault == "anonymous":
        headers.pop("Authorization")
    elif fault == "expired":
        headers = h(exp=int(time.time()) - 1)
    elif fault == "session":
        db.active = False
    elif fault == "unverified_signature":
        headers["Authorization"] += "tampered"
    elif fault in {"missing_amr", "iat_only"}:
        headers = h(amr=[], iat=int(time.time()))
    elif fault in {"stale_amr", "future_amr"}:
        headers = h(
            amr=[
                {
                    "method": "password",
                    "timestamp": int(time.time())
                    + (30 if fault == "future_amr" else -301),
                }
            ]
        )
    elif fault == "origin":
        headers["Origin"] = "https://evil.synthetic.invalid"
    else:
        app.state.settings.qr_lifecycle_enabled = False
    response = patch(c, db.lost, headers, body())
    assert response.status_code in {401, 403, 503}
    assert response.headers["cache-control"] == "private, no-store"
    assert db.revision == 2 and db.audit == []


@pytest.mark.parametrize(
    "changes",
    [
        {"confirmed": False},
        {"confirmed": "true"},
        {"public_access_acknowledged": False},
        {"expected_revision": True},
        {"expected_revision": 0},
        {"public_status": "admin_suspended"},
        {"reason": "resume"},
        {"private": CANARY},
    ],
)
def test_closed_confirmation_and_command_schema(env, changes):
    c, db, h, body, _ = env
    assert patch(c, db.lost, h(), {**body(), **changes}).status_code == 422
    assert db.audit == []


@pytest.mark.parametrize("state", ["admin_suspended", "revoked", "unactivated"])
def test_owner_cannot_restore_security_or_unactivated_tag(env, state):
    c, db, h, body, _ = env
    db.tags[0]["public_status"] = state
    response = patch(c, db.lost, h(), body("active"))
    assert response.status_code == 409 and db.revision == 2


def test_shared_revision_stales_sibling_and_encrypted_replay_rechecks_owner(env):
    c, db, h, body, _ = env
    original = body()
    first = patch(c, db.lost, h(), original)
    assert first.status_code == 200
    assert patch(c, db.ice, h(), original).status_code == 412
    replay = patch(c, db.lost, h(), original)
    assert replay.json() == first.json() and len(db.audit) == 1
    assert patch(c, db.lost, h(), body("active")).status_code == 409
    assert all("public_status" not in json.dumps(r) for r in db.receipts.values())
    db.owner = uuid4()
    assert patch(c, db.lost, h(), original).status_code == 404


def test_production_history_predicates_hide_prior_owner_old_identity_and_private_events(
    env,
):
    c, db, h, _, _ = env
    db.events += [
        db.event("pair.activated", db.pid, kind="tag_pair", actor=uuid4()),
        db.event("qr.owner_disabled", uuid4(), before="active", after="owner_disabled"),
        db.event("contact.revealed", db.ice),
        db.event(
            "qr.owner_disabled",
            db.lost,
            at=datetime(2025, 1, 1, tzinfo=UTC),
            before="active",
            after="owner_disabled",
        ),
    ]
    response = c.get(url(db), headers=h())
    assert response.status_code == 200 and len(response.json()["items"]) == 1
    assert CANARY not in response.text


def test_history_paging_actor_pair_binding_and_closed_queries(env):
    c, db, h, _, _ = env
    for _ in range(4):
        db.events.append(
            db.event(
                "qr.owner_disabled", db.lost, before="active", after="owner_disabled"
            )
        )
    first = c.get(url(db) + "?limit=2", headers=h()).json()
    seen, cursor = first["items"][:], first["next_cursor"]
    while cursor:
        page = c.get(url(db) + "?limit=2&cursor=" + cursor, headers=h()).json()
        seen.extend(page["items"])
        cursor = page["next_cursor"]
    assert len(seen) == len({e["event_id"] for e in seen}) == 5
    for suffix in [
        "?limit=101",
        "?limit=1&limit=2",
        "?private=x",
        "?cursor=../private",
    ]:
        assert c.get(url(db) + suffix, headers=h()).status_code == 422
    assert (
        c.get(
            url(db) + "?cursor=" + first["next_cursor"], headers=h(sub=str(uuid4()))
        ).status_code
        == 422
    )
    assert (
        c.get(
            f"/api/v1/me/tag-pairs/{uuid4()}/activation-history?cursor="
            + first["next_cursor"],
            headers=h(),
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "fault", ["query", "audit", "save", "commit", "session", "owner"]
)
def test_mutation_failure_rolls_back_status_revision_audit_and_receipt(env, fault):
    c, db, h, body, _ = env
    old = db.snapshot()
    if fault in {"query", "audit", "save", "commit"}:
        setattr(db, "fail_" + fault, True)
    else:
        db.revoke = fault
    response = patch(c, db.lost, h(), body())
    assert response.status_code in {401, 404, 503}, response.text
    assert db.snapshot() == old and db.rollbacks == 1
    assert CANARY not in response.text


def test_fail_closed_read_key_projection_and_canonical_routes(env):
    c, db, h, _, app = env
    db.private_history = True
    assert c.get(url(db), headers=h()).status_code == 503
    db.private_history = False
    app.state.settings.profile_data_keys = "{}"
    assert c.get(url(db), headers=h()).status_code == 503
    schema = app.openapi()["paths"]
    assert (
        schema["/api/v1/me/qr/{qr_id}/public-status"]["patch"]["operationId"]
        == "API-035"
    )
    assert (
        schema["/api/v1/me/tag-pairs/{pair_id}/activation-history"]["get"][
            "operationId"
        ]
        == "API-034"
    )
    assert not any("suspend" in path and "tag-pairs" in path for path in schema)


def test_offline_helper_only_upgrade_downgrade_and_existing_fence_contracts(
    monkeypatch,
):
    module_path = MIGRATION.with_suffix(".py")
    spec = importlib.util.spec_from_file_location(
        "offline_owner_lifecycle", module_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    emitted = []
    monkeypatch.setattr(module.op, "execute", lambda value: emitted.append(str(value)))
    module.upgrade()
    module.downgrade()
    out = Path(__file__).parents[2] / "output/task35b/offline-upgrade-downgrade.sql"
    out.write_text(
        ";\n".join(value.rstrip().rstrip(";") for value in emitted) + ";\n",
        encoding="utf-8",
    )
    assert module.down_revision == "0031_staff_account_state"
    assert SQL.count("CREATE FUNCTION") == 3
    assert "CREATE TABLE" not in SQL and "ALTER TABLE" not in SQL
    assert all(
        "search_path=pg_catalog" in part for part in SQL.split("CREATE FUNCTION")[1:]
    )
    assert sum(s.startswith("DROP FUNCTION") for s in emitted) == 3
    old = Path(__file__).parents[1] / "alembic/versions"
    prints = (old / "0017_print_download_grants.py").read_text(encoding="utf-8")
    assert "n<>(SELECT count(*) FROM public.order_item_qr_uses" in prints
    assert "q.public_status IN('unactivated','active')" in prints
    fulfillment = (old / "0018_fulfillment_eligibility.py").read_text(encoding="utf-8")
    assert "q.public_status NOT IN ('unactivated','active')" in fulfillment


@pytest.mark.parametrize(
    "ownership", ["unclaimed", "transfer_pending", "disputed", "revoked"]
)
def test_owner_command_cannot_cross_pair_ownership_state(env, ownership):
    c, db, h, body, _ = env
    db.ownership = ownership
    assert patch(c, db.lost, h(), body()).status_code == 404
    assert db.revision == 2 and not db.receipts


def test_simultaneous_sibling_commands_have_one_fixture_revision_winner(env):
    c, db, h, body, _ = env
    barrier = Barrier(2)
    original = body()

    def run(qid):
        headers = h()
        barrier.wait()
        return patch(c, qid, headers, original).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(run, [db.lost, db.ice]))
    assert sorted(statuses) == [200, 412]
    assert db.revision == 3 and len(db.receipts) == len(db.audit) == 1
    assert sorted(t["public_status"] for t in db.tags) == ["active", "owner_disabled"]
    # A Python lock in the stand-in proves orchestration, not PG lock/MVCC behavior.


@pytest.mark.parametrize(
    "status", ["active", "owner_disabled", "admin_suspended", "revoked", "unactivated"]
)
def test_existing_production_contact_and_print_predicates_in_sqlite(status):
    old = Path(__file__).parents[1] / "alembic/versions"
    contact = (old / "0013_public_contact_actions.py").read_text(encoding="utf-8")
    contact = (
        "SELECT q.id FROM public.qr_codes q\n    JOIN public.ice_profiles"
        + contact.split("FROM public.qr_codes q\n    JOIN public.ice_profiles", 1)[
            1
        ].split("FOR SHARE OF q,i,c", 1)[0]
    )
    contact = contact.replace("$1", ":token").replace("$2", ":contact")
    source = (old / "0017_print_download_grants.py").read_text(encoding="utf-8")
    prints = (
        "SELECT "
        + source.split("RETURN QUERY SELECT ", 1)[1].split("FOR SHARE OF q,p", 1)[0]
    )
    prints = prints.replace("::text", "")
    prints = re.sub(r"\boid\b", ":oid", prints)
    with sqlite3.connect(":memory:") as db:
        db.execute("ATTACH DATABASE ':memory:' AS public")
        db.executescript("""
        CREATE TABLE public.qr_codes(id TEXT,pair_id TEXT,tag_type TEXT,public_token TEXT,is_current INTEGER,public_status TEXT,revoked_at TEXT);
        CREATE TABLE public.ice_profiles(qr_id TEXT,published INTEGER,publication_consent_version TEXT);
        CREATE TABLE public.ice_contacts(id TEXT,ice_qr_id TEXT,published INTEGER,publication_consent_at TEXT,publication_consent_version TEXT,removed_at TEXT);
        CREATE TABLE public.orders(id TEXT,customer_user_id TEXT);
        CREATE TABLE public.tag_pairs(id TEXT,owner_user_id TEXT,revoked_at TEXT);
        CREATE TABLE public.order_items(id TEXT,order_id TEXT,fulfillment_method_snapshot TEXT,size_mm_snapshot INTEGER,template_key_snapshot TEXT,template_version_snapshot INTEGER,variant_id TEXT);
        CREATE TABLE public.order_item_qr_uses(id TEXT,order_item_id TEXT,qr_code_id TEXT,pair_unit_id TEXT,use_kind TEXT,tag_type_snapshot TEXT,copies INTEGER);
        CREATE TABLE public.order_pair_units(id TEXT,order_id TEXT,pair_id TEXT,status TEXT);
        INSERT INTO public.orders VALUES('synthetic-order','synthetic-owner');
        INSERT INTO public.tag_pairs VALUES('synthetic-pair','synthetic-owner',NULL);
        INSERT INTO public.order_items VALUES('line','synthetic-order','pdf_label',35,'synthetic',1,'variant');
        INSERT INTO public.order_pair_units VALUES('unit','synthetic-order','synthetic-pair','allocated');
        INSERT INTO public.ice_profiles VALUES('ice',1,'ice-public-v1');
        INSERT INTO public.ice_contacts VALUES('contact','ice',1,'2026-01-01','ice-contact-v1',NULL);
        """)
        for kind in ["lost", "ice"]:
            db.execute(
                "INSERT INTO public.qr_codes VALUES(?,?,?,?,1,?,NULL)",
                (
                    kind,
                    "synthetic-pair",
                    kind,
                    "synthetic-" + kind,
                    status if kind == "ice" else "active",
                ),
            )
            db.execute(
                "INSERT INTO public.order_item_qr_uses VALUES(?,?,?,?,?,?,1)",
                (kind, "line", kind, "unit", "new_pair", kind),
            )
        contacts = db.execute(
            contact, {"token": "synthetic-ice", "contact": "contact"}
        ).fetchall()
        occurrences = db.execute(prints, {"oid": "synthetic-order"}).fetchall()
        assert len(contacts) == (1 if status == "active" else 0)
        assert len(occurrences) == (2 if status in {"active", "unactivated"} else 1)
        # PG helper's all-or-nothing row-count guard rejects partial1-of2 results;
        # this test does not execute PL/pgSQL or establish PostgreSQL locks.
