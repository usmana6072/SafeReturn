"""Synthetic HTTP/crypto checks and production relational predicates in memory.

SQLite only exercises SELECT predicate/cardinality semantics after removing PG
casts/schema qualification. It does not prove PostgreSQL/RLS/locking/query plans.
"""

import base64
import importlib.util
import json
import re
import sqlite3
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import OperationalError
from test_auth import claims, signed
from test_auth import verifier as _verifier
from test_critical_workflow_boundaries import MemoryDatabase, Result
from test_health import ASGIClient

from app.api.v1.finance_reconciliation import capped, projection
from app.core.config import Settings
from app.main import create_app

verifier = _verifier
SQL_PATH = (
    Path(__file__).parents[1] / "alembic/versions/0026_finance_reconciliation.sql"
)
SQL = SQL_PATH.read_text()
QUERY = SQL.split(" RETURN QUERY\n ", 1)[1].split(";\nEND $$;", 1)[0]
for fragment in ("public.", "::text", "::uuid", "::numeric"):
    QUERY = QUERY.replace(fragment, "")
QUERY = QUERY.replace("<=cutoff", "<=:cutoff")
LIST_QUERY = SQL.split(" RETURN QUERY SELECT r.*", 1)[1].split(";\nEND $$;", 1)[0]
LIST_QUERY = "SELECT r.*" + LIST_QUERY.replace(
    "public.sr_finance_reconciliation_rows(cutoff)", "(" + QUERY + ")"
).replace("::uuid", "")
for param in (
    "filter_reason",
    "after_stamp",
    "after_order",
    "after_attempt",
    "after_reason",
    "take",
):
    LIST_QUERY = re.sub(r"\b" + param + r"\b", ":" + param, LIST_QUERY)
COUNT_QUERY = SQL.split(" WITH signals AS MATERIALIZED", 1)[1].split(";\nEND $$;", 1)[0]
COUNT_QUERY = "WITH signals AS MATERIALIZED" + COUNT_QUERY.replace(
    "SELECT * FROM public.sr_finance_reconciliation_rows(cutoff)", QUERY
)
STAMP = datetime(2026, 1, 1, tzinfo=UTC)
URL = "/api/v1/admin/finance/reconciliation"


class Rows(Result):
    def all(self):
        return self.value


class Store(MemoryDatabase):
    def __init__(self, actor):
        super().__init__(actor, uuid4())
        self.roles = {"finance", "operations"}
        self.sql = sqlite3.connect(":memory:", check_same_thread=False)
        self.sql.row_factory = sqlite3.Row
        self.sql.create_collation("C", lambda a, b: (a > b) - (a < b))
        self.sql.executescript("""
        CREATE TABLE orders(id TEXT,created_at TEXT,payment_status TEXT,total_pkr NUMERIC,currency_code TEXT);
        CREATE TABLE payment_attempts(id TEXT,order_id TEXT,state TEXT,amount NUMERIC,currency_code TEXT,created_at TEXT,verified_at TEXT);
        CREATE TABLE payment_reviews(attempt_id TEXT,decision TEXT,bank_verified BOOL,bank_reference_fingerprint BLOB);
        CREATE TABLE order_pair_units(order_id TEXT,status TEXT);
        CREATE TABLE frozen_history(snapshot TEXT);
        INSERT INTO frozen_history VALUES('synthetic immutable purchase/shipping/review snapshot');
        CREATE TABLE order_financial_fences(order_id TEXT);
        """)
        self.fail_query = False

    def add(
        self,
        state="submitted",
        payment="under_review",
        amount="100.10",
        currency="PKR",
        units=("reserved",),
        review=False,
        stamp=STAMP,
        order=None,
        fingerprint=b"synthetic",
    ):
        oid, aid = order or uuid4(), uuid4()
        if order is None:
            self.sql.execute(
                "INSERT INTO orders VALUES(?,?,?,?,?)",
                (str(oid), stamp.isoformat(), payment, "100.10", "PKR"),
            )
            self.sql.executemany(
                "INSERT INTO order_pair_units VALUES(?,?)",
                [(str(oid), status) for status in units],
            )
        self.sql.execute(
            "INSERT INTO payment_attempts VALUES(?,?,?,?,?,?,?)",
            (
                str(aid),
                str(oid),
                state,
                amount,
                currency,
                stamp.isoformat(),
                stamp.isoformat() if state == "verified" else None,
            ),
        )
        if review:
            self.sql.execute(
                "INSERT INTO payment_reviews VALUES(?,?,?,?)",
                (str(aid), "verify", True, fingerprint),
            )
        return oid, aid

    def signals(self, cutoff):
        rows = [
            dict(r) for r in self.sql.execute(QUERY, {"cutoff": cutoff.isoformat()})
        ]
        return self.convert(rows)

    def convert(self, rows):
        for r in rows:
            r["order_id"] = UUID(r["order_id"])
            r["attempt_id"] = UUID(r["attempt_id"]) if r["attempt_id"] else None
            r["observed_since"] = datetime.fromisoformat(r["observed_since"])
            for field in ("attempt_amount", "order_amount"):
                if r[field] is not None:
                    r[field] = Decimal(str(r[field])).quantize(Decimal("0.01"))
            r["private_bank"] = "PRIVATE_CANARY"
        return rows

    def execute(self, statement, params=None):
        sql, params = str(statement), params or {}
        if sql.startswith("SET LOCAL statement_timeout"):
            self.statements.append(sql)
            return Rows(None)
        if "sr_finance_reconciliation" in sql:
            self.statements.append(sql)
            if self.fail_query:
                raise OperationalError("SELECT", {}, Exception("PRIVATE_CANARY"))
            if "_counts" in sql:
                return Rows(
                    [
                        dict(r)
                        for r in self.sql.execute(
                            COUNT_QUERY, {"cutoff": params["as_of"].isoformat()}
                        )
                    ]
                )
            values = {
                "cutoff": params["as_of"].isoformat(),
                "filter_reason": params["reason"],
                "after_stamp": params["stamp"].isoformat() if params["stamp"] else None,
                "after_order": str(params["oid"]),
                "after_attempt": str(params["aid"]),
                "after_reason": params["code"],
                "take": params["take"],
            }
            return Rows(
                self.convert([dict(r) for r in self.sql.execute(LIST_QUERY, values)])
            )
        return super().execute(statement, params)


@pytest.fixture
def env(verifier):
    provider, private, _, _ = verifier
    actor = uuid4()
    db = Store(actor)
    app = create_app(
        Settings(
            finance_reconciliation_enabled=True,
            profile_data_key_version=1,
            profile_data_keys=json.dumps({"1": base64.b64encode(b"r" * 32).decode()}),
        )
    )
    app.state.database, app.state.jwt_verifier = db, provider
    client = ASGIClient(app)

    def headers(**overrides):
        return {
            "Authorization": "Bearer "
            + signed(private, claims(sub=str(actor), aal="aal2", **overrides))
        }

    yield client, db, headers, app, actor, private
    db.sql.close()


@pytest.mark.parametrize("suffix", ["", "/counts"])
def test_auth_live_role_mfa_and_private_errors(env, suffix):
    c, db, h, _, _, _ = env
    assert c.get(URL + suffix).status_code == 401
    assert c.get(URL + suffix, headers=h(exp=int(time.time()) - 1)).status_code == 401
    db.active = False
    assert c.get(URL + suffix, headers=h()).status_code == 401
    db.active = True
    db.mfa = False
    assert c.get(URL + suffix, headers=h()).status_code == 403
    db.mfa = True
    db.roles = {"operations"}
    denied = c.get(URL + suffix, headers=h())
    assert denied.status_code == 403
    assert denied.headers["cache-control"] == "private, no-store"
    assert not any("sr_finance_reconciliation" in s for s in db.statements)


def test_closed_projection_exact_money_readonly_history_and_provider_absence(env):
    c, db, h, _, _, _ = env
    db.add()
    before = list(db.sql.iterdump())
    response = c.get(URL, headers=h())
    assert response.status_code == 200, response.text
    data = response.json()
    assert set(data) == {"as_of", "items", "next_cursor", "unavailable_checks"}
    item = data["items"][0]
    assert item["attempt_amount"] == item["order_amount"] == "100.10"
    assert item["next_action"] == "review_payment"
    assert "PRIVATE_CANARY" not in response.text
    assert data["unavailable_checks"] == [
        "BANK_LEDGER_AMOUNT_COMPARISON",
        "REJECTED_REFERENCE_MATCHES",
    ]
    assert before == list(db.sql.iterdump())
    assert len(db.audit) == 1
    assert db.roles == {"finance", "operations"}
    assert all(
        not any(x in s for x in ("UPDATE ", "DELETE ", "FOR UPDATE", "durable_jobs"))
        for s in db.statements
    )


@pytest.mark.parametrize(
    "query",
    [
        "?limit=0",
        "?limit=101",
        "?limit=bad",
        "?reason=unknown",
        "?reason=REVIEW_PENDING&reason=REVIEW_PENDING",
        "?bank_reference=secret",
        "?limit=2&limit=3",
    ],
)
def test_bounds_and_closed_filters(env, query):
    assert env[0].get(URL + query, headers=env[2]()).status_code == 422


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({}, {"REVIEW_PENDING"}),
        ({"amount": "100.11"}, {"REVIEW_PENDING", "ATTEMPT_ORDER_AMOUNT_MISMATCH"}),
        ({"currency": "USD"}, {"REVIEW_PENDING", "ATTEMPT_ORDER_CURRENCY_MISMATCH"}),
        (
            {
                "state": "verified",
                "payment": "verified",
                "units": ("allocated",),
                "review": True,
            },
            set(),
        ),
        (
            {"state": "verified", "payment": "verified", "units": ("allocated",)},
            {"VERIFIED_HISTORY_MISMATCH"},
        ),
        ({"state": "rejected", "review": True}, {"VERIFIED_HISTORY_MISMATCH"}),
        (
            {"state": "verified", "review": True, "units": ("allocated",)},
            {"ORDER_SETTLEMENT_MISMATCH"},
        ),
        (
            {"payment": "verified"},
            {
                "REVIEW_PENDING",
                "ORDER_SETTLEMENT_MISMATCH",
                "VERIFIED_ALLOCATION_MISMATCH",
            },
        ),
        (
            {"state": "verified", "payment": "verified", "review": True, "units": ()},
            {"VERIFIED_ALLOCATION_MISMATCH"},
        ),
        (
            {
                "state": "verified",
                "payment": "verified",
                "review": True,
                "units": ("allocated", "cancelled"),
            },
            {"VERIFIED_ALLOCATION_MISMATCH"},
        ),
    ],
)
def test_production_select_predicates_in_memory(env, kwargs, expected):
    env[1].add(**kwargs)
    assert {r["reason_code"] for r in env[1].signals(datetime.now(UTC))} == expected


def test_duplicate_verified_reference_fanout_and_no_mask_inference(env):
    db = env[1]
    for _ in range(2):
        _, aid = db.add(
            state="verified", payment="verified", units=("allocated",), review=True
        )
        # Simulate legacy/corrupt duplicates impossible under current PG uniqueness.
        db.sql.execute(
            "INSERT INTO payment_reviews VALUES(?,?,?,?)",
            (str(aid), "verify", True, b"synthetic"),
        )
    rows = db.signals(datetime.now(UTC))
    assert len(rows) == 2 and all(
        r["reason_code"] == "DUPLICATE_VERIFIED_REFERENCE" for r in rows
    )
    db.sql.execute("DELETE FROM payment_reviews")
    assert all(
        r["reason_code"] != "DUPLICATE_VERIFIED_REFERENCE"
        for r in db.signals(datetime.now(UTC))
    )


def test_oldest_first_ties_paging_filter_and_asof(env):
    c, db, h, _, _, _ = env
    for _ in range(5):
        db.add()
    db.add(stamp=datetime.now(UTC) + timedelta(days=1))
    first = c.get(URL + "?limit=2&reason=REVIEW_PENDING", headers=h()).json()
    seen = first["items"][:]
    token = first["next_cursor"]
    while token:
        page = c.get(
            URL + "?limit=2&reason=REVIEW_PENDING&cursor=" + token, headers=h()
        ).json()
        assert page["as_of"] == first["as_of"]
        seen.extend(page["items"])
        token = page["next_cursor"]
    assert len(seen) == 5 and len({r["attempt_id"] for r in seen}) == 5
    assert seen == sorted(
        seen,
        key=lambda r: (
            r["observed_since"],
            r["order_id"],
            r["attempt_id"],
            r["reason_code"],
        ),
    )


def test_cursor_actor_filter_tamper_and_revocation(env):
    c, db, h, _, _, private = env
    db.add()
    db.add()
    token = c.get(URL + "?limit=1", headers=h()).json()["next_cursor"]
    for suffix in ("?cursor=broken", "?reason=REVIEW_PENDING&cursor=" + token):
        assert c.get(URL + suffix, headers=h()).status_code == 422
    foreign = {
        "Authorization": "Bearer "
        + signed(private, claims(sub=str(uuid4()), aal="aal2"))
    }
    assert c.get(URL + "?cursor=" + token, headers=foreign).status_code == 422
    db.roles = set()
    assert c.get(URL + "?cursor=" + token, headers=h()).status_code == 403


def test_counts_overlap_not_orders_and_zero_is_known(env):
    c, db, h, _, _, _ = env
    zero = c.get(URL + "/counts", headers=h()).json()
    assert zero["affected_orders"] == {"value": 0, "is_exact": True}
    oid, _ = db.add(amount="100.11")
    for _ in range(4):
        db.add(order=oid)
    value = c.get(URL + "/counts", headers=h()).json()
    assert value["affected_orders"] == {"value": 1, "is_exact": True}
    assert value["by_reason"]["REVIEW_PENDING"] == {"value": 5, "is_exact": True}
    assert value["by_reason"]["ATTEMPT_ORDER_AMOUNT_MISMATCH"]["value"] == 1


def test_actual_capped_counts_keep_distinct_orders_after_many_attempts(env):
    c, db, h, _, _, _ = env
    oid, _ = db.add()
    for _ in range(1004):
        db.add(order=oid)
    db.add()
    value = c.get(URL + "/counts", headers=h()).json()
    assert value["by_reason"]["REVIEW_PENDING"] == {"value": 1000, "is_exact": False}
    assert value["affected_orders"] == {"value": 2, "is_exact": True}


def test_dispute_fence_and_frozen_history_preserved_and_not_projected(env):
    c, db, h, _, _, _ = env
    oid, _ = db.add()
    db.sql.execute("INSERT INTO order_financial_fences VALUES(?)", (str(oid),))
    before = list(db.sql.iterdump())
    for suffix in ("", "/counts"):
        response = c.get(URL + suffix, headers=h())
        assert response.status_code == 200
        assert "case_id" not in response.text and "fence" not in response.text
    assert list(db.sql.iterdump()) == before


def test_missing_crypto_fails_closed_and_low_assurance_denied(env):
    c, _, h, app, actor, private = env
    low = {
        "Authorization": "Bearer " + signed(private, claims(sub=str(actor), aal="aal1"))
    }
    assert c.get(URL, headers=low).status_code == 403
    app.state.settings.profile_data_keys = None
    assert c.get(URL, headers=h()).status_code == 503


def test_affected_order_count_cap_in_production_query(env):
    c, db, h, _, _, _ = env
    for _ in range(1001):
        db.add()
    response = c.get(URL + "/counts", headers=h())
    assert response.status_code == 200
    assert response.json()["affected_orders"] == {"value": 1000, "is_exact": False}


def test_sheets_outage_never_participates_in_read_or_changes_authority(
    env, monkeypatch
):
    def forbidden_provider(*args, **kwargs):
        pytest.fail("reconciliation must not contact Sheets")

    monkeypatch.setattr(
        "app.workers.finance_retention.GoogleSheetsProvider", forbidden_provider
    )
    c, db, h, _, _, _ = env
    db.add(state="verified", payment="verified", units=("allocated",), review=True)
    before = list(db.sql.iterdump())
    assert c.get(URL, headers=h()).json()["items"] == []
    assert c.get(URL + "/counts", headers=h()).json()["affected_orders"]["value"] == 0
    assert list(db.sql.iterdump()) == before


def test_ciphertext_tamper_rejected(env):
    c, db, h, _, _, _ = env
    db.add()
    db.add()
    token = c.get(URL + "?limit=1", headers=h()).json()["next_cursor"]
    offset = len(token) // 2
    changed = (
        token[:offset] + ("A" if token[offset] != "A" else "B") + token[offset + 1 :]
    )
    assert c.get(URL + "?cursor=" + changed, headers=h()).status_code == 422


@pytest.mark.parametrize("n", [999, 1000, 1001])
def test_counts_cap_contract(n):
    assert capped(n).model_dump() == {"value": min(n, 1000), "is_exact": n < 1000}


@pytest.mark.parametrize("failure", ["fail_audit", "fail_commit", "fail_query"])
def test_failure_safe_rollback_unknown_not_zero(env, failure):
    c, db, h, _, _, _ = env
    db.add()
    before = list(db.sql.iterdump())
    setattr(db, failure, True)
    r = c.get(URL + "/counts", headers=h())
    assert r.status_code == 503 and "PRIVATE_CANARY" not in r.text
    assert "affected_orders" not in r.json()
    assert not db.audit and list(db.sql.iterdump()) == before


def test_disabled_and_writes_unavailable(env):
    c, db, h, app, _, _ = env
    app.state.settings.finance_reconciliation_enabled = False
    assert c.get(URL, headers=h()).status_code == 503
    assert c.post(URL, headers=h(), json={"repair": True}).status_code == 405
    assert not db.audit


def test_projection_rejects_float_or_private_fields():
    row = {
        "order_id": uuid4(),
        "attempt_id": None,
        "reason_code": "ORDER_SETTLEMENT_MISMATCH",
        "observed_since": STAMP,
        "attempt_amount": None,
        "order_amount": 100.1,
        "currency": None,
        "order_currency": "PKR",
    }
    with pytest.raises(Exception) as exc:
        projection(row)
    assert exc.value.status == 503


def test_offline_migration_capture_and_openapi(env, monkeypatch):
    path = SQL_PATH.with_suffix(".py")
    spec = importlib.util.spec_from_file_location("reconciliation_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    captured = []
    monkeypatch.setattr(module.op, "execute", captured.append)
    module.upgrade()
    assert captured == ["SET LOCAL lock_timeout='5s'", SQL]
    module.downgrade()
    assert len(captured) == 5 and module.down_revision == "0025_financial_disputes"
    assert "TO safereturn_api" in SQL and "TO safereturn_worker" not in SQL
    schema = env[3].openapi()
    assert schema["paths"][URL]["get"]["operationId"] == "API-342"
    assert schema["paths"][URL + "/counts"]["get"]["operationId"] == "API-343"
