"""Phase 5 DTO/route/model checks; SQL locks/RLS require the opt-in PG suite."""

import hashlib
import hmac
import sqlite3
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import SecretStr, ValidationError
from sqlalchemy.dialects import sqlite
from sqlalchemy.schema import CreateTable
from test_health import ASGIClient

from app.api.auth import AccessError, get_auth_context
from app.api.v1 import payments
from app.core.config import Settings
from app.db.commerce import (
    OrderItemQRAllocation,
    TypedAllocationEvent,
    TypedOrderSettlement,
)
from app.main import create_app


@pytest.fixture
def fixture(monkeypatch):
    session = MagicMock()
    ctx = SimpleNamespace(
        session=session,
        email_verified=True,
        mfa_verified=True,
        principal=SimpleNamespace(user_id=uuid4(), session_id=uuid4()),
    )
    settings = SimpleNamespace(
        payment_reference_key=SecretStr("synthetic-stable-reference-key"),
        financial_review_enabled=False,
        print_enabled=False,
    )
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=settings)))
    order = {
        "id": uuid4(),
        "commerce_model": "single_qr",
        "payment_status": "under_review",
        "order_status": "placed",
        "total_pkr": Decimal("123.00"),
        "currency_code": "PKR",
    }
    attempt = {
        "state": "under_review",
        "amount": Decimal("123.00"),
        "currency_code": "PKR",
    }
    monkeypatch.setattr(
        payments, "record", lambda ctx, req, op, payload, work: work(settings)[0]
    )
    monkeypatch.setattr(payments, "lock_attempt", lambda *args: (order, attempt))
    session.execute.return_value.scalar_one_or_none.return_value = (
        1  # Actual staff guard.
    )
    return ctx, req, order, attempt


def review(**changes):
    return payments.ReviewRequest(
        **{
            "decision": "verify",
            "bank_verified": True,
            "bank_match_reference": " SYNTHETIC-BANK-REFERENCE ",
            "settled_amount": "123.00",
            "settled_currency": "PKR",
            "reason": "Synthetic independent review",
            **changes,
        }
    )


@pytest.mark.parametrize("state", ["allocated", "reconciliation_pending"])
def test_typed_review_uses_atomic_helper_not_legacy_pair_writer(fixture, state):
    ctx, req, order, _ = fixture
    result = {
        "review_id": str(uuid4()),
        "state": "verified",
        "order_id": str(order["id"]),
        "fulfillment_eligible": False,
        "allocation": {
            "state": state,
            "allocated_count": 1 if state == "allocated" else 0,
        },
    }
    ctx.session.execute.return_value.scalar_one.return_value = result
    assert payments.review_payment(uuid4(), review(), ctx, req) == result
    calls = [
        (str(c.args[0]), c.args[1] if len(c.args) > 1 else {})
        for c in ctx.session.execute.call_args_list
    ]
    helper = next(args for sql, args in calls if "sr_typed_settle" in sql)
    assert helper["sid"] == ctx.principal.session_id
    assert (
        helper["fingerprint"]
        == hmac.new(
            b"synthetic-stable-reference-key",
            b"synthetic-bank-reference",
            hashlib.sha256,
        ).digest()
    )
    assert "bank_match_reference" not in helper
    assert not any(
        "order_pair_units" in sql or "allocation.finalize" in sql for sql, _ in calls
    )
    assert any("SET CONSTRAINTS ALL IMMEDIATE" in sql for sql, _ in calls)


@pytest.mark.parametrize(
    "changes,code",
    [
        ({"bank_verified": False}, "BANK_VERIFICATION_REQUIRED"),
        ({"settled_amount": "1.00"}, "SETTLEMENT_MISMATCH"),
        ({"settled_currency": "USD"}, "SETTLEMENT_MISMATCH"),
        ({"bank_match_reference": None}, "BANK_VERIFICATION_REQUIRED"),
    ],
)
def test_screenshot_or_mismatched_settlement_cannot_allocate(fixture, changes, code):
    ctx, req, _, _ = fixture
    with pytest.raises(HTTPException) as error:
        payments.review_payment(uuid4(), review(**changes), ctx, req)
    assert error.value.detail["code"] == code
    assert not any(
        "sr_typed_settle" in str(c.args[0]) for c in ctx.session.execute.call_args_list
    )


@pytest.mark.parametrize("target", ["attempt", "order", "cancelled"])
def test_second_review_or_cancelled_order_cannot_allocate(fixture, target):
    ctx, req, order, attempt = fixture
    if target == "attempt":
        attempt["state"] = "verified"
    elif target == "order":
        order["payment_status"] = "verified"
    else:
        order["order_status"] = "cancelled"
    with pytest.raises(HTTPException):
        payments.review_payment(uuid4(), review(), ctx, req)
    assert not any(
        "sr_typed_settle" in str(c.args[0]) for c in ctx.session.execute.call_args_list
    )


@pytest.mark.parametrize(
    "verified,mfa,role", [(False, True, 1), (True, False, 1), (True, True, None)]
)
def test_finance_authority_is_required_before_writes(fixture, verified, mfa, role):
    ctx, req, _, _ = fixture
    ctx.email_verified, ctx.mfa_verified = verified, mfa
    ctx.session.execute.return_value.scalar_one_or_none.return_value = role
    with pytest.raises(AccessError):
        payments.review_payment(uuid4(), review(), ctx, req)
    assert not any(
        "sr_typed_settle" in str(c.args[0]) for c in ctx.session.execute.call_args_list
    )


@pytest.mark.parametrize("value", [False, 1, "true", None])
def test_retry_is_closed_and_explicit(value):
    with pytest.raises(ValidationError):
        payments.AllocationRetry(confirmed=value)


def test_retry_never_accepts_identity_price_or_payment_proof():
    for field in ("qr_id", "public_token", "price", "bank_verified"):
        with pytest.raises(ValidationError):
            payments.AllocationRetry(confirmed=True, **{field: "synthetic"})


def test_retry_uses_same_transaction_and_safe_helper(fixture):
    ctx, req, order, _ = fixture
    value = {
        "order_id": str(order["id"]),
        "allocation": {"state": "allocated"},
        "fulfillment_eligible": False,
    }
    ctx.session.execute.return_value.scalar_one.return_value = value
    assert (
        payments.retry_allocation(
            order["id"], payments.AllocationRetry(confirmed=True), ctx, req
        )
        == value
    )
    assert any(
        "sr_typed_allocation_retry" in str(c.args[0])
        for c in ctx.session.execute.call_args_list
    )


def test_legacy_pair_verification_retains_original_writer(fixture):
    ctx, req, order, _ = fixture
    order["commerce_model"] = "legacy_pair"
    ctx.session.execute.return_value.all.return_value = [
        SimpleNamespace(id=uuid4(), status="reserved")
    ]
    result = payments.review_payment(uuid4(), review(), ctx, req)
    statements = [str(c.args[0]) for c in ctx.session.execute.call_args_list]
    assert result["state"] == "verified" and result["fulfillment_eligible"] is True
    assert any(
        "UPDATE public.order_pair_units SET status='allocated'" in sql
        for sql in statements
    )
    assert not any("sr_typed_settle" in sql for sql in statements)


@pytest.mark.parametrize("model", ["single_qr", "legacy_pair"])
@pytest.mark.parametrize("decision", ["reject", "request_more_info"])
def test_non_verifying_review_never_allocates(fixture, model, decision):
    ctx, req, order, _ = fixture
    order["commerce_model"] = model
    result = payments.review_payment(
        uuid4(),
        payments.ReviewRequest(decision=decision, reason="Synthetic review"),
        ctx,
        req,
    )
    statements = [str(c.args[0]) for c in ctx.session.execute.call_args_list]
    assert result["state"] in {"rejected", "under_review"}
    assert not any(
        "sr_typed_settle" in sql or "status='allocated'" in sql for sql in statements
    )


@pytest.mark.parametrize(
    "code,status",
    [
        ("FORBIDDEN", 403),
        ("NOT_FOUND", 404),
        ("SETTLEMENT_MISMATCH", 409),
        ("BANK_VERIFICATION_REQUIRED", 422),
    ],
)
def test_database_errors_are_closed(code, status):
    with pytest.raises((AccessError, HTTPException)) as error:
        payments.typed_result({"error": code})
    assert (
        getattr(error.value, "status_code", getattr(error.value, "status", None))
        == status
    )


def test_new_allocation_routes_reject_anonymous_requests():
    client = ASGIClient(create_app(Settings()))
    oid = uuid4()
    assert client.get(f"/api/v1/admin/orders/{oid}/qr-allocation").status_code == 401
    assert (
        client.post(
            f"/api/v1/admin/orders/{oid}/qr-allocation/retry", json={"confirmed": True}
        ).status_code
        == 401
    )


def test_http_validation_does_not_echo_token_or_price(fixture):
    ctx, _, _, _ = fixture
    app = create_app(Settings())
    app.dependency_overrides[get_auth_context] = lambda: ctx
    response = ASGIClient(app).post(
        f"/api/v1/admin/orders/{uuid4()}/qr-allocation/retry",
        json={"confirmed": True, "public_token": "PRIVATE_TOKEN_CANARY"},
    )
    assert response.status_code == 422 and "PRIVATE_TOKEN_CANARY" not in response.text


@pytest.fixture
def db():
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.create_function("gen_random_uuid", 0, lambda: str(uuid4()))
    connection.create_function("now", 0, lambda: "2026-10-22T00:00:00Z")
    connection.create_function("clock_timestamp", 0, lambda: "2026-10-22T00:00:00Z")
    for name in ("orders", "payment_attempts", "order_logical_items", "qr_codes"):
        connection.execute(f"CREATE TABLE {name}(id TEXT PRIMARY KEY)")
        for ident in ("one", "two"):
            connection.execute(f"INSERT INTO {name} VALUES(?)", (ident,))
    for model in (TypedOrderSettlement, OrderItemQRAllocation, TypedAllocationEvent):
        connection.execute(
            str(CreateTable(model.__table__).compile(dialect=sqlite.dialect()))
        )
    connection.execute(
        "INSERT INTO typed_order_settlements(order_id,attempt_id,state,reason_code) VALUES('one','one','reconciliation_pending','stock_shortage')"
    )
    yield connection
    connection.close()


def claim(db, item="one", qr="one"):
    db.execute(
        "INSERT INTO order_item_qr_allocations(logical_item_id,qr_id,order_id,purchaser_user_id,allocated_by) VALUES(?,?,'one','purchaser','finance')",
        (item, qr),
    )


def test_one_per_item_and_one_per_qr_are_independent_unique_constraints(db):
    claim(db)
    with pytest.raises(sqlite3.IntegrityError):
        claim(db, item="one", qr="two")
    with pytest.raises(sqlite3.IntegrityError):
        claim(db, item="two", qr="one")
    claim(db, item="two", qr="two")
    assert (
        db.execute("SELECT count(*) FROM order_item_qr_allocations").fetchone()[0] == 2
    )


def test_invalid_foreign_identity_and_duplicate_settlement_fail(db):
    with pytest.raises(sqlite3.IntegrityError):
        claim(db, qr="absent")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO typed_order_settlements(order_id,attempt_id,state,reason_code) VALUES('two','one','reconciliation_pending','stock_shortage')"
        )


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE typed_order_settlements SET state='allocated'",
        "UPDATE typed_order_settlements SET reason_code=NULL",
        "UPDATE typed_order_settlements SET reason_code='auto_refund'",
        "UPDATE typed_order_settlements SET revision=0",
    ],
)
def test_reconciliation_state_is_explicit_and_consistent(db, sql):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(sql)


def test_migration_retains_legacy_finance_behavior_and_private_boundaries():
    root = Path(__file__).parents[1] / "alembic/versions"
    sql = (root / "0041_verified_qr_allocation.sql").read_text(encoding="utf-8")
    assert "GRANT SELECT" not in sql and "GRANT UPDATE" not in sql
    assert "SKIP LOCKED LIMIT wanted" in sql and "pg_advisory_xact_lock(51410001" in sql
    assert "Permanent QR claims cannot be rewritten or recycled" in sql
    assert "Allocated typed inventory requires a permanent claim" in sql
    assert "Typed allocation must be all or nothing" in sql
    assert "Typed production is not released" in sql
    assert (
        "public_token" not in sql
    )  # Never a settlement, entitlement or audit input/output.
    old = (root / "0019_retention_recovery.py").read_text(encoding="utf-8")
    a = old.index("CREATE FUNCTION public.sr_finance_changed()")
    expected = old[a : old.index("END $$;", a) + 7]
    a = sql.index("CREATE OR REPLACE FUNCTION public.sr_finance_changed()")
    actual = (
        sql[a : sql.index("END $$;", a) + 7]
        .replace("CREATE OR REPLACE FUNCTION", "CREATE FUNCTION", 1)
        .replace(" IF NEW.commerce_model='single_qr' THEN RETURN NEW; END IF;\n", "")
    )
    assert actual == expected
