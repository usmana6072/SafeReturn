"""349/350 real routes/JWT crypto + adapted production SELECTs in SQLite :memory:.

No PostgreSQL locking/MVCC, live provider, artifact or physical printing proof.
"""

import base64
import json
import sqlite3
import time
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import OperationalError
from test_auth import claims, signed
from test_auth import verifier as _verifier
from test_critical_workflow_boundaries import MemoryDatabase, Result
from test_health import ASGIClient

from app.api.v1.print_queries import STATES
from app.core.config import Settings
from app.main import create_app

verifier = _verifier
URL = "/api/v1/admin/print-jobs"
STAMP = datetime(2026, 1, 1, tzinfo=UTC)
CANARY = "PRIVATE_PRINT_CANARY"


class Rows(Result):
    def all(self):
        return self.value

    def one(self):
        assert len(self.value) == 1
        return self.value[0]


class Store(MemoryDatabase):
    def __init__(self, actor):
        super().__init__(actor, uuid4())
        self.roles = {"operations"}
        self.sql = sqlite3.connect(":memory:", check_same_thread=False)
        self.sql.row_factory = sqlite3.Row
        self.sql.execute("ATTACH DATABASE ':memory:' AS public")
        self.sql.executescript("""
        CREATE TABLE public.orders(id TEXT,order_number TEXT,order_status TEXT,
         payment_status TEXT,fulfillment_status TEXT);
        CREATE TABLE public.print_jobs(id TEXT,order_id TEXT,job_revision INTEGER,
         status TEXT,created_at TEXT,attempt_count INTEGER,failure_code TEXT);
        """)
        self.sql.create_function("sr_is_staff", 0, lambda: "operations" in self.roles)
        self.fail_query = False
        self.revoke = None
        self.bad_projection = False

    def add(
        self,
        state="ready",
        order=None,
        order_status="placed",
        payment="verified",
        fulfillment="allocated",
        stamp=STAMP,
        failure=None,
    ):
        oid, jid = order or uuid4(), uuid4()
        if order is None:
            self.sql.execute(
                "INSERT INTO public.orders VALUES(?,?,?,?,?)",
                (str(oid), "SYNTHETIC-" + str(oid), order_status, payment, fulfillment),
            )
            # Fit the existing40-char exact order_number contract.
            self.sql.execute(
                "UPDATE public.orders SET order_number=? WHERE id=?",
                ("SYN-" + str(oid), str(oid)),
            )
        self.sql.execute(
            "INSERT INTO public.print_jobs VALUES(?,?,?,?,?,?,?)",
            (str(jid), str(oid), 1, state, stamp.isoformat(), 1, failure),
        )
        return oid, jid

    def execute(self, statement, params=None):
        sql, params = str(statement), params or {}
        if "SET LOCAL statement_timeout" in sql:
            self.statements.append(sql)
            return Result(None)
        if "JOIN public.orders o ON o.id=j.order_id" in sql:
            self.statements.append(sql)
            if self.fail_query:
                raise OperationalError("SELECT", {}, Exception(CANARY))
            adapted = sql.replace(
                "public.sr_is_staff(ARRAY['operations'])", "sr_is_staff()"
            )
            for kind in ["uuid", "timestamptz"]:
                adapted = adapted.replace(" AS " + kind, " AS TEXT")
            values = {
                k: v.isoformat()
                if isinstance(v, datetime)
                else str(v)
                if isinstance(v, UUID)
                else v
                for k, v in params.items()
            }
            rows = [dict(r) for r in self.sql.execute(adapted, values)]
            if self.bad_projection and rows:
                rows[0]["private"] = CANARY
            if self.revoke == "role":
                self.roles.clear()
            if self.revoke == "session":
                self.active = False
            if self.revoke == "mfa":
                self.mfa = False
            return Rows(rows)
        return super().execute(statement, params)


@pytest.fixture
def env(verifier):
    provider, private, _, _ = verifier
    actor = uuid4()
    db = Store(actor)
    app = create_app(
        Settings(
            profile_data_key_version=1,
            profile_data_keys=json.dumps({"1": base64.b64encode(b"p" * 32).decode()}),
        )
    )
    app.state.database, app.state.jwt_verifier = db, provider
    client = ASGIClient(app)

    def headers(**overrides):
        return {
            "Authorization": "Bearer "
            + signed(private, claims(**{"sub": str(actor), "aal": "aal2", **overrides}))
        }

    yield client, db, headers, app
    db.sql.close()


@pytest.mark.parametrize("suffix", ["", "/counts"])
def test_auth_session_mfa_role_headers_and_no_inheritance(env, suffix):
    c, db, h, _ = env
    assert c.get(URL + suffix).status_code == 401
    assert c.get(URL + suffix, headers=h(exp=int(time.time()) - 1)).status_code == 401
    assert c.get(URL + suffix, headers=h(aal="aal1")).status_code == 403
    for role in ["finance", "support", "security_admin", "superadmin"]:
        db.roles = {role}
        response = c.get(URL + suffix, headers=h())
        assert response.status_code == 403
        assert response.headers["cache-control"] == "private, no-store"
    db.roles = {"operations", "finance"}
    assert c.get(URL + suffix, headers=h()).status_code == 200
    db.active = False
    assert c.get(URL + suffix, headers=h()).status_code == 401
    db.active, db.mfa = True, False
    assert c.get(URL + suffix, headers=h()).status_code == 403


@pytest.mark.parametrize(
    "query",
    [
        "limit=0",
        "limit=101",
        "limit=true",
        "limit=20&limit=20",
        "sort=unknown",
        "job_status=dead",
        "order_status=verified",
        "payment_status=disputed",
        "fulfillment_status=qa_passed",
        "order_id=bad",
        "private=x",
        "created_from=2026-01-01",
        "created_from=0",
        "created_from=2026-01-02T00:00:00Z&created_before=2026-01-01T00:00:00Z",
        "order_number=%20SYN%20",
    ],
)
def test_closed_exact_filters(env, query):
    c, _, h, _ = env
    assert c.get(URL + "?" + query, headers=h()).status_code == 422


@pytest.mark.parametrize("sort", ["oldest", "newest"])
def test_production_sql_ties_live_pages_ceiling_and_cursor_bindings(env, sort):
    c, db, h, _ = env
    rows = [db.add() for _ in range(5)]
    db.add(stamp=datetime.now(UTC) + timedelta(days=1))
    first = c.get(URL + "?limit=2&sort=" + sort, headers=h()).json()
    assert first["next_cursor"]
    seen = first["items"][:]
    token = first["next_cursor"]
    while token:
        page = c.get(
            URL + "?limit=2&sort=" + sort + "&cursor=" + token, headers=h()
        ).json()
        assert page["as_of"] == first["as_of"]
        seen.extend(page["items"])
        token = page["next_cursor"]
    assert len(seen) == len({r["job_id"] for r in seen}) == 5
    assert [r["job_id"] for r in seen] == sorted(
        [str(r[1]) for r in rows], reverse=sort == "newest"
    )
    token = first["next_cursor"]
    for extra in [
        "&job_status=ready",
        "&order_id=" + str(rows[0][0]),
        "&sort=" + ("newest" if sort == "oldest" else "oldest"),
    ]:
        assert (
            c.get(
                URL + "?cursor=" + token + "&sort=" + sort + extra, headers=h()
            ).status_code
            == 422
        )
    assert (
        c.get(URL + "?cursor=" + token, headers=h(sub=str(uuid4()))).status_code == 422
    )
    assert c.get(URL + "?cursor=" + token + "x", headers=h()).status_code == 422


def test_exact_search_half_open_dates_and_distinct_financial_states(env):
    c, db, h, _ = env
    oid, jid = db.add(
        order_status="cancelled", payment="under_review", fulfillment="unallocated"
    )
    db.add(order=oid, state="failed", failure="physical_qa_failed")
    db.add(state="qa_passed", failure=CANARY)
    data = c.get(URL, headers=h()).json()
    assert len(data["items"]) == 3
    assert CANARY not in json.dumps(data)
    assert {r["failure_category"] for r in data["items"]} == {
        None,
        "PHYSICAL_QA_FAILED",
        "PRINT_FAILURE_RECORDED",
    }
    for query, expected in [
        ("order_id=" + str(oid), 2),
        ("job_id=" + str(jid), 1),
        ("order_number=SYN-" + str(oid), 2),
        ("order_number=SYN", 0),
        ("payment_status=under_review", 2),
        ("order_status=cancelled", 2),
        ("job_status=failed", 1),
        ("created_from=2026-01-01T00:00:00Z", 3),
        ("created_before=2026-01-01T00:00:00Z", 0),
    ]:
        response = c.get(URL + "?" + query, headers=h())
        assert response.status_code == 200, response.text
        assert len(response.json()["items"]) == expected
    counts = c.get(URL + "/counts?order_id=" + str(oid), headers=h()).json()
    assert counts["matching_jobs"] == {"value": 2, "is_exact": True}
    assert counts["affected_orders"] == {"value": 1, "is_exact": True}
    assert counts["by_job_status"]["ready"]["value"] == 1
    filtered = c.get(
        URL + "/counts?order_id=" + str(oid) + "&job_status=failed", headers=h()
    ).json()
    assert filtered["matching_jobs"]["value"] == 1
    assert filtered["by_job_status"]["ready"]["value"] == 0


@pytest.mark.parametrize("number", [0, 999, 1000, 1001])
def test_independent_capped_single_statement_counts(env, number):
    c, db, h, _ = env
    for _ in range(number):
        db.add()
    response = c.get(URL + "/counts", headers=h())
    assert response.status_code == 200, response.text
    data = response.json()
    assert set(data["by_job_status"]) == set(STATES)
    expected = {"value": min(number, 1000), "is_exact": number < 1000}
    assert (
        data["matching_jobs"]
        == data["affected_orders"]
        == data["by_job_status"]["ready"]
        == expected
    )
    assert len([s for s in db.statements if "WITH selected AS" in s]) == 1


@pytest.mark.parametrize("suffix", ["", "/counts"])
@pytest.mark.parametrize(
    "failure", ["query", "audit", "commit", "role", "session", "mfa"]
)
def test_failure_rollback_and_final_live_denial(env, suffix, failure):
    c, db, h, _ = env
    db.add()
    before = list(db.sql.iterdump())
    if failure in ["query", "audit", "commit"]:
        setattr(db, "fail_" + failure, True)
    else:
        db.revoke = failure
    response = c.get(URL + suffix, headers=h())
    assert response.status_code == (
        401 if failure == "session" else 403 if failure in ["role", "mfa"] else 503
    )
    assert db.audit == [] and db.rollbacks == 1
    assert before == list(db.sql.iterdump())
    assert CANARY not in response.text
    assert response.headers["cache-control"] == "private, no-store"


def test_closed_projection_key_failure_route_registry_and_no_production_calls(env):
    c, db, h, app = env
    db.add()
    db.bad_projection = True
    assert c.get(URL, headers=h()).status_code == 503
    db.bad_projection = False
    app.state.settings.profile_data_keys = "{}"
    assert c.get(URL, headers=h()).status_code == 503
    assert c.get(URL + "/counts?limit=20", headers=h()).status_code == 422
    assert c.post(URL + "/counts", headers=h()).status_code == 405
    schema = app.openapi()
    assert schema["paths"][URL]["get"]["operationId"] == "API-349"
    assert schema["paths"][URL + "/counts"]["get"]["operationId"] == "API-350"
    assert not any(
        token in sql
        for sql in db.statements
        for token in [
            "FOR UPDATE",
            "durable_jobs",
            "print_artifacts",
            "UPDATE public.print",
            "sender",
            "payload_ciphertext",
        ]
    )


def test_live_resolution_preserves_ceiling_and_filter_bound_paging(env):
    c, db, h, _ = env
    for _ in range(5):
        db.add()
    first = c.get(URL + "?limit=2&job_status=ready", headers=h()).json()
    ids = {r["job_id"] for r in first["items"]}
    remaining = [
        r[0]
        for r in db.sql.execute("SELECT id FROM public.print_jobs ORDER BY id")
        if r[0] not in ids
    ]
    db.sql.execute(
        "UPDATE public.print_jobs SET status='failed' WHERE id=?", (remaining[-1],)
    )
    db.add(stamp=datetime.fromisoformat(first["as_of"]) + timedelta(seconds=1))
    page = c.get(
        URL + "?limit=20&job_status=ready&cursor=" + first["next_cursor"], headers=h()
    ).json()
    assert page["as_of"] == first["as_of"]
    assert len(page["items"]) == 2
    assert not ids.intersection(r["job_id"] for r in page["items"])


def test_aware_offset_normalizes_to_utc(env):
    c, db, h, _ = env
    db.add()
    response = c.get(URL + "?created_from=2026-01-01T05:00:00%2B05:00", headers=h())
    assert response.status_code == 200 and len(response.json()["items"]) == 1


@pytest.mark.parametrize(
    "mode,code",
    [
        ("stale", "VERSION_MISMATCH"),
        ("active", "PRINT_ALREADY_ACTIVE"),
        ("binding", "PRINT_BINDING_CHANGED"),
    ],
)
def test_existing_enqueue_early_conflicts_never_render_or_mutate(
    monkeypatch, mode, code
):
    from fastapi import HTTPException

    from app.api.v1 import financial_disputes, printing

    oid, jid, use, qr = uuid4(), uuid4(), uuid4(), uuid4()
    statements = []

    def execute(statement, params):
        sql = str(statement)
        statements.append(sql)
        if "sr_print_order_lock" in sql:
            return Result(oid)
        if "FROM public.print_jobs" in sql:
            return Result(
                {
                    "id": jid,
                    "job_revision": 1,
                    "status": "queued" if mode == "active" else "ready",
                }
            )
        if "FROM public.durable_jobs" in sql:
            return Result("leased")
        raise AssertionError("No write/provider/render operation permitted")

    monkeypatch.setattr(financial_disputes, "require_order_clear", lambda *a, **k: None)
    monkeypatch.setattr(
        printing,
        "occurrences",
        lambda *a: [
            {"use_id": use, "qr_id": qr, "tag_type": "lost", "size_mm": 35, "copies": 1, "public_token": "synthetic"}
        ],
    )
    monkeypatch.setattr(
        printing,
        "frozen",
        lambda *a: {
            "occurrences": [
                {
                    "use_id": str(use),
                    "qr_id": str(qr),
                    "copies": 1,
                    "template": {"tag_type": "lost", "symbol_mm": 35},
                    "url": "https://synthetic.invalid/q/changed",
                }
            ]
        },
    )
    with pytest.raises(HTTPException) as error:
        printing.enqueue(
            SimpleNamespace(execute=execute, info={"template_registry_available": False}),
            Settings(),
            oid,
            0 if mode == "stale" else 1,
            "Synthetic review only",
        )
    assert error.value.detail["code"] == code
    assert not any(
        sql.lstrip().startswith(("UPDATE ", "INSERT ", "DELETE ")) for sql in statements
    )
