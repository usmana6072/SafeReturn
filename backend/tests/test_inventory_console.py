"""5.7D synthetic route/transaction stand-ins and SQLite predicate rehearsal.

No PostgreSQL locks, MVCC, managed roles or provider writes are exercised here.
"""

import base64
import json
import sqlite3
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from pydantic import SecretStr
from sqlalchemy.exc import IntegrityError, OperationalError
from test_critical_workflow_boundaries import Result

from app.api.auth import AccessError
from app.api.v1.inventory import BatchRequest, create_qr_batch
from app.api.v1.inventory_queries import AVAILABLE, list_batches, list_pairs
from app.api.v1.owner_qr import encode_cursor
from app.api.v1.printing import PrintQARequest, record_print_qa
from app.core.config import Settings


class Memory:
    def __init__(self):
        # This stand-in models the legacy schema without template registry helpers.
        self.info = {"template_registry_available": False}
        self.rows = {
            k: [] for k in ("batches", "pairs", "tags", "credentials", "qa", "audit")
        }
        self.receipts = {}
        self.roles = {"operations"}
        self.failure = None
        self.pair = uuid4()
        self.eligible = True
        self.inventory_status = "generated"

    @contextmanager
    def begin_nested(self):
        old = deepcopy((self.rows, self.receipts, self.inventory_status))
        try:
            yield self
        except BaseException:
            self.rows, self.receipts, self.inventory_status = old
            raise

    @contextmanager
    def transaction(self):
        with self.begin_nested():
            yield self
            if self.failure == "commit":
                raise OperationalError("COMMIT", {}, Exception("PRIVATE_CANARY"))

    def execute(self, statement, params=None):
        q, p = str(statement), params or {}
        if "FROM public.staff_roles" in q:
            return Result(1 if self.roles.intersection(p["roles"]) else None)
        if "pg_advisory_xact_lock" in q:
            return Result(None)  # Orchestration only: no lock guarantee.
        if "FROM public.idempotency_records" in q:
            return Result(self.receipts.get(p.get("key")))
        if "SELECT 1 FROM public.qr_batches" in q:
            return Result(
                1 if any(r["code"] == p["code"] for r in self.rows["batches"]) else None
            )
        if "SELECT target_id FROM public.audit_events" in q:
            return Result(self.rows["audit"][-1]["batch"])
        if "SELECT id FROM public.tag_pairs" in q:
            return Result(self.pair if self.eligible and p["id"] == self.pair else None)
        if "INSERT INTO public.idempotency_records" in q:
            self.receipts[p["key"]] = {
                "request_hash": p.get("request_hash", p.get("hash")),
                "state": "completed" if "cipher" in p else "pending",
                "response_status": p.get("status"),
                "response_body_ciphertext": p.get("cipher"),
                "response_key_version": p.get("version"),
            }
            return Result(None)
        if "UPDATE public.idempotency_records" in q:
            self.receipts[p["key"]].update(
                state="completed",
                response_body_ciphertext=p["body"],
                response_status=201,
                response_key_version=1,
            )
            return Result(None)
        if "UPDATE public.tag_pairs" in q:
            self.inventory_status = "qa_passed"
            return Result(None)
        table = next(
            (
                name
                for name in (
                    "qr_batches",
                    "tag_pairs",
                    "qr_codes",
                    "pair_activation_credentials",
                    "pair_print_qa",
                    "audit_events",
                )
                if f"INSERT INTO public.{name}" in q
            ),
            None,
        )
        if table:
            key = {
                "qr_batches": "batches",
                "tag_pairs": "pairs",
                "qr_codes": "tags",
                "pair_activation_credentials": "credentials",
                "pair_print_qa": "qa",
                "audit_events": "audit",
            }[table]
            if self.failure == key:
                raise OperationalError("INSERT", {}, Exception("PRIVATE_CANARY"))
            if key == "qa" and any(
                r["qa_round"] == p["qa_round"] for r in self.rows["qa"]
            ):
                raise IntegrityError("INSERT", {}, Exception("duplicate QA round"))
            self.rows[key].extend(deepcopy(p if isinstance(p, list) else [p]))
            return Result(None)
        raise AssertionError(q)


@pytest.fixture(scope="module")
def settings():
    private = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    public = (
        private.public_key()
        .public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        .decode()
    )
    key = base64.urlsafe_b64encode(bytes(range(32))).decode().rstrip("=")
    return Settings(
        activation_verifier_key=SecretStr(key),
        print_recipient_public_key=SecretStr(public),
        profile_data_keys=SecretStr(json.dumps({"1": key})),
    )


@pytest.fixture
def fixture(settings):
    db = Memory()
    context = SimpleNamespace(
        session=db,
        principal=SimpleNamespace(user_id=uuid4()),
        email_verified=True,
        mfa_verified=True,
    )
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(settings=settings)),
        state=SimpleNamespace(request_id="synthetic"),
        headers={"idempotency-key": "synthetic-qa-key"},
    )
    return db, context, request


def batch_body():
    return BatchRequest(
        pair_count=2,
        batch_label="SYNTHETIC-57D",
        logo_template_key="safe-return-primary",
        qr_ecc="Q",
        print_material="Synthetic material",
        intended_environment="outdoor",
        lost_symbol_size_mm="35",
        ice_symbol_size_mm="35",
    )


def qa_body(approved=False, **changes):
    values = {
        k: approved
        for k in (
            "lost_scan_passed",
            "ice_scan_passed",
            "pair_match_passed",
            "credential_concealed",
            "bilingual_label_passed",
            "quiet_zone_passed",
            "indoor_size_passed",
            "outdoor_size_passed",
            "tamper_evidence_passed",
        )
    }
    return PrintQARequest(
        qa_round=1,
        approved=approved,
        packaging_method="sealed_sleeve",
        **{**values, **changes},
    )


def test_generation_complete_and_replay_no_extra_identity(fixture):
    db, ctx, req = fixture
    with db.transaction():
        first = create_qr_batch(batch_body(), ctx, req, "synthetic-generation")
    assert first.status_code == 201
    assert [
        len(db.rows[k]) for k in ("batches", "pairs", "tags", "credentials", "audit")
    ] == [1, 2, 4, 2, 1]
    assert len({r["token"] for r in db.rows["tags"]}) == 4
    for pair in db.rows["pairs"]:
        assert {r["tag_type"] for r in db.rows["tags"] if r["pair"] == pair["id"]} == {
            "lost",
            "ice",
        }
    before = deepcopy(db.rows)
    with db.transaction():
        second = create_qr_batch(batch_body(), ctx, req, "synthetic-generation")
    assert json.loads(first.body) == json.loads(second.body) and db.rows == before
    assert b"activation_secret" not in first.body and b"public_token" not in first.body


@pytest.mark.parametrize(
    "fault", ["batches", "pairs", "tags", "credentials", "audit", "commit"]
)
def test_generation_outer_transaction_rollback(fixture, fault):
    db, ctx, req = fixture
    db.failure = fault
    with pytest.raises(OperationalError), db.transaction():
        create_qr_batch(batch_body(), ctx, req, "synthetic-generation")
    assert all(not rows for rows in db.rows.values()) and db.receipts == {}


@pytest.mark.parametrize("role", ["support", "finance", "security_admin", "superadmin"])
@pytest.mark.parametrize("action", ["generation", "qa"])
def test_no_inherited_operations(fixture, role, action):
    db, ctx, req = fixture
    db.roles = {role}
    with pytest.raises(AccessError) as error:
        if action == "generation":
            create_qr_batch(batch_body(), ctx, req, "synthetic-generation")
        else:
            record_print_qa(db.pair, qa_body(), ctx, req)
    assert error.value.status == 403 and all(not rows for rows in db.rows.values())


def test_pair_qa_replay_conflicting_round_and_negative_not_quarantine(fixture):
    db, ctx, req = fixture
    with db.transaction():
        first = record_print_qa(db.pair, qa_body(True), ctx, req)
    assert first["approved"] and db.inventory_status == "qa_passed"
    with db.transaction():
        assert record_print_qa(db.pair, qa_body(True), ctx, req) == first
    assert len(db.rows["qa"]) == 1
    req.headers["idempotency-key"] = "synthetic-second-key"
    with pytest.raises(HTTPException) as error, db.transaction():
        record_print_qa(db.pair, qa_body(True), ctx, req)
    assert error.value.status_code == 409 and len(db.rows["qa"]) == 1
    with db.transaction():
        record_print_qa(
            db.pair, qa_body(False).model_copy(update={"qa_round": 2}), ctx, req
        )
    assert db.inventory_status == "qa_passed" and not db.rows["qa"][-1]["approved"]


@pytest.mark.parametrize("fault", ["qa", "audit", "commit"])
def test_pair_qa_atomic_rollback(fixture, fault):
    db, ctx, req = fixture
    db.failure = fault
    with pytest.raises(OperationalError), db.transaction():
        record_print_qa(db.pair, qa_body(True), ctx, req)
    assert not db.rows["qa"] and not db.rows["audit"] and not db.receipts
    assert db.inventory_status == "generated"


def test_false_observation_and_ineligible_pair_fail(fixture):
    db, ctx, req = fixture
    with pytest.raises(HTTPException) as error:
        record_print_qa(db.pair, qa_body(True, lost_scan_passed=False), ctx, req)
    assert error.value.status_code == 422
    db.eligible = False
    with pytest.raises(HTTPException) as error:
        record_print_qa(db.pair, qa_body(), ctx, req)
    assert error.value.status_code == 409 and not db.rows["qa"]


@pytest.mark.parametrize("kind", ["pairs", "batches"])
def test_read_search_and_keyset_are_bound_not_interpolated(fixture, kind):
    db, ctx, _ = fixture
    original = db.execute
    calls = []

    def execute(statement, params=None):
        if "WITH selected" not in str(statement):
            return original(statement, params)
        calls.append((str(statement), params))
        return SimpleNamespace(mappings=lambda: SimpleNamespace(all=list))

    db.execute = execute
    stamp, ident = datetime(2026, 10, 20, tzinfo=UTC), uuid4()
    opaque = encode_cursor(ident, stamp)
    probe = "' OR TRUE --"
    if kind == "pairs":
        value = list_pairs(
            ctx,
            limit=20,
            cursor_value=opaque,
            pair_reference=probe,
            inventory_status="qa_passed",
            ownership_status="unclaimed",
        )
    else:
        value = list_batches(
            ctx, limit=20, cursor_value=opaque, batch_label=probe, status="generated"
        )
    sql, bound = calls[0]
    assert value == {"items": [], "next_cursor": None}
    assert probe not in sql and probe in bound.values()
    assert bound["lim"] == 21 and bound["ident"] == ident and bound["stamp"] == stamp
    assert "created_at DESC" in sql and "id DESC" in sql


@pytest.mark.parametrize("limit", [0, 101, -1])
@pytest.mark.parametrize("kind", ["pairs", "batches"])
def test_read_limit_denies_before_metadata_query(fixture, limit, kind):
    _, ctx, _ = fixture
    with pytest.raises(HTTPException) as error:
        (list_pairs if kind == "pairs" else list_batches)(
            ctx, limit=limit, cursor_value=None
        )
    assert error.value.status_code == 422


@pytest.mark.parametrize(
    "change,available",
    [
        ("none", True),
        ("past_reserved", False),
        ("allocated", False),
        ("credential_locked", False),
        ("one_tag", False),
        ("suspended", False),
        ("owned", False),
        ("qa_held", False),
    ],
)
def test_exact_available_predicate_sqlite_rehearsal(change, available):
    with sqlite3.connect(":memory:") as sql:
        sql.executescript(
            "CREATE TABLE tag_pairs(id TEXT,ownership_status TEXT,inventory_status TEXT);CREATE TABLE order_pair_units(pair_id TEXT,status TEXT,reserved_until TEXT);CREATE TABLE qr_codes(pair_id TEXT,is_current BOOL,public_status TEXT);CREATE TABLE pair_activation_credentials(pair_id TEXT,status TEXT);INSERT INTO tag_pairs VALUES('p','unclaimed','qa_passed');INSERT INTO qr_codes VALUES('p',true,'unactivated'),('p',true,'unactivated');INSERT INTO pair_activation_credentials VALUES('p','unused');"
        )
        if change in ("past_reserved", "allocated"):
            sql.execute(
                "INSERT INTO order_pair_units VALUES('p',?,'2000-01-01')",
                ("reserved" if change == "past_reserved" else "allocated",),
            )
        elif change == "credential_locked":
            sql.execute("UPDATE pair_activation_credentials SET status='locked'")
        elif change == "one_tag":
            sql.execute("DELETE FROM qr_codes WHERE rowid=1")
        elif change == "suspended":
            sql.execute(
                "UPDATE qr_codes SET public_status='admin_suspended' WHERE rowid=1"
            )
        elif change == "owned":
            sql.execute("UPDATE tag_pairs SET ownership_status='active'")
        elif change == "qa_held":
            sql.execute("UPDATE tag_pairs SET inventory_status='generated'")
        assert (
            bool(
                sql.execute(
                    "SELECT " + AVAILABLE.replace("public.", "") + " FROM tag_pairs p"
                ).fetchone()[0]
            )
            is available
        )
