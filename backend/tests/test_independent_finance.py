"""Offline service/authorization checks; not PostgreSQL concurrency evidence."""

import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import SecretStr
from starlette.datastructures import Headers

from app.api.auth import AccessError
from app.api.v1 import independent_finance as routes
from app.api.v1.payments import AllocationRetry, ReviewRequest
from app.services import independent_finance as service


@pytest.fixture
def setup(monkeypatch):
    ctx = SimpleNamespace(
        session=MagicMock(),
        email_verified=True,
        mfa_verified=True,
        principal=SimpleNamespace(
            user_id=uuid4(), session_id=uuid4(), authentication_time=time.time()
        ),
    )
    ctx.session.info = {}
    ctx.session.execute.return_value.scalar_one_or_none.return_value = 1
    settings = SimpleNamespace(
        payment_reference_key=SecretStr("synthetic-reference-key"),
        financial_review_web_origin="https://finance.test",
    )
    req = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(settings=settings)),
        headers=Headers({"origin": "https://finance.test"}),
    )
    result = {
        "order_id": str(uuid4()),
        "review_id": str(uuid4()),
        "state": "verified",
        "allocation": {
            "state": "allocated",
            "requested_count": 2,
            "allocated_count": 2,
            "reason_code": None,
        },
    }

    def execute(sql, params=None):
        out = MagicMock()
        out.scalar_one_or_none.return_value = 1
        out.scalar_one.return_value = (
            True if "sr_independent_finance_authorize" in str(sql) else result
        )
        return out

    ctx.session.execute.side_effect = execute
    monkeypatch.setattr(
        service, "record", lambda c, r, op, payload, work: work(settings)[0]
    )
    return ctx, req, result


def body(**changes):
    return ReviewRequest(
        **{
            "decision": "verify",
            "bank_verified": True,
            "bank_match_reference": "SYNTHETIC-REFERENCE",
            "settled_amount": "123.00",
            "settled_currency": "PKR",
            "reason": "Independent synthetic bank confirmation",
            **changes,
        }
    )


@pytest.mark.parametrize(
    "field,value", [("email_verified", False), ("mfa_verified", False)]
)
def test_identity_and_mfa_required(setup, field, value):
    ctx, req, _ = setup
    setattr(ctx, field, value)
    with pytest.raises(AccessError):
        service.review(ctx, req, uuid4(), body())
    ctx.session.execute.assert_not_called()


@pytest.mark.parametrize("age", [301, -60, None])
def test_existing_freshness_window_preserved(setup, age):
    ctx, req, _ = setup
    ctx.principal.authentication_time = None if age is None else time.time() - age
    with pytest.raises(HTTPException) as error:
        service.review(ctx, req, uuid4(), body())
    assert error.value.detail["code"] == "REAUTH_REQUIRED"


def test_unauthorized_role(setup):
    ctx, req, _ = setup
    ctx.session.execute.side_effect = None
    ctx.session.execute.return_value.scalar_one_or_none.return_value = None
    with pytest.raises(AccessError):
        service.review(ctx, req, uuid4(), body())


@pytest.mark.parametrize(
    "changes",
    [
        {"bank_verified": False},
        {"bank_match_reference": None},
        {"settled_amount": None},
        {"settled_currency": None},
    ],
)
def test_independent_settlement_required(setup, changes):
    ctx, req, _ = setup
    with pytest.raises(HTTPException) as error:
        service.review(ctx, req, uuid4(), body(**changes))
    assert error.value.detail["code"] == "BANK_VERIFICATION_REQUIRED"


def test_cross_origin_denied(setup):
    ctx, req, _ = setup
    req.headers = Headers({"origin": "https://other.test"})
    with pytest.raises(AccessError):
        service.review(ctx, req, uuid4(), body())


def test_db_authority_checked_before_receipt_replay(setup, monkeypatch):
    ctx, req, _ = setup
    original = ctx.session.execute.side_effect

    def execute(sql, params=None):
        result = original(sql, params)
        if "sr_independent_finance_authorize" in str(sql):
            result.scalar_one.return_value = False
        return result

    ctx.session.execute.side_effect = execute
    receipt = MagicMock()
    monkeypatch.setattr(service, "record", receipt)
    with pytest.raises(AccessError):
        service.review(ctx, req, uuid4(), body())
    receipt.assert_not_called()


@pytest.mark.parametrize("state", ["allocated", "reconciliation_pending"])
def test_verification_uses_only_independent_wrapper_and_hmac(setup, state):
    ctx, req, result = setup
    result["allocation"]["state"] = state
    assert service.review(ctx, req, uuid4(), body()) == result
    calls = [
        (str(c.args[0]), c.args[1] if len(c.args) > 1 else {})
        for c in ctx.session.execute.call_args_list
    ]
    _sql, params = next(c for c in calls if "sr_independent_finance_review" in c[0])
    assert len(params["fingerprint"]) == 32 and params["amount"] == 123
    assert "SYNTHETIC-REFERENCE" not in str(params)
    assert not any(
        "order_pair_units" in q or "sr_finance_reconciliation" in q for q, _ in calls
    )
    assert any("SET CONSTRAINTS ALL IMMEDIATE" in q for q, _ in calls)


@pytest.mark.parametrize(
    "code", ["SETTLEMENT_MISMATCH", "PAYMENT_CLOSED", "DUPLICATE_BANK_REFERENCE"]
)
def test_db_conflicts_do_not_report_success(setup, code):
    ctx, req, result = setup
    result.clear()
    result["error"] = code
    with pytest.raises(HTTPException) as error:
        service.review(ctx, req, uuid4(), body())
    assert error.value.status_code == 409


@pytest.mark.parametrize("decision", ["reject", "request_more_info"])
def test_non_verifying_decision_has_no_settlement_claim(setup, decision):
    ctx, req, _ = setup
    service.review(
        ctx,
        req,
        uuid4(),
        ReviewRequest(decision=decision, reason="Synthetic review notes"),
    )
    call = next(
        c
        for c in ctx.session.execute.call_args_list
        if "sr_independent_finance_review" in str(c.args[0])
    )
    assert call.args[1]["fingerprint"] is None and call.args[1]["amount"] is None
    with pytest.raises(HTTPException):
        service.review(ctx, req, uuid4(), body(decision=decision))


def test_retry_uses_existing_allocator_wrapper(setup):
    ctx, req, _ = setup
    service.retry(ctx, req, uuid4(), AllocationRetry(confirmed=True))
    assert any(
        "sr_independent_finance_retry" in str(c.args[0])
        for c in ctx.session.execute.call_args_list
    )


def test_route_is_closed_even_to_authorized_finance(setup):
    ctx, _, _ = setup
    with pytest.raises(HTTPException) as error:
        routes.admission(ctx)
    assert error.value.detail["code"] == "INDEPENDENT_FINANCE_NOT_RELEASED"


def test_http_replacement_never_reaches_service(setup, monkeypatch):
    from fastapi import FastAPI
    from test_health import ASGIClient

    from app.api.auth import access_error, get_auth_context

    ctx, _, _ = setup
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")
    app.add_exception_handler(AccessError, access_error)
    app.dependency_overrides[get_auth_context] = lambda: ctx
    work = MagicMock()
    monkeypatch.setattr(service, "review", work)
    response = ASGIClient(app).post(
        f"/api/v1/admin/payment-attempts/{uuid4()}/reviews", json=body().model_dump()
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "INDEPENDENT_FINANCE_NOT_RELEASED"
    work.assert_not_called()


def test_migration_is_additive_without_grants_or_legacy_calls():
    root = Path(__file__).parents[1]
    sql = (root / "alembic/versions/0051_independent_finance.sql").read_text()
    assert "CREATE OR REPLACE" not in sql and "GRANT EXECUTE" not in sql
    for excluded in [
        "order_pair_units",
        "tag_pairs",
        "sr_checkout_reserve",
        "allocation.finalize",
        "sr_finance_reconciliation(",
    ]:
        assert excluded not in sql
    assert (
        "public.sr_typed_settle(" in sql and "public.sr_typed_allocation_retry(" in sql
    )
    assert "customer_user_id<>public.sr_actor_id()" in sql
    assert "NOT BETWEEN 0 AND 300" in sql
    assert "FOR UPDATE" in sql and "payment_reviews" in sql and "audit_events" in sql
    assert "independent_finance" not in (root / "app/main.py").read_text()


def test_missing_auth_denied_at_http_boundary():
    from fastapi import FastAPI
    from test_health import ASGIClient

    from app.api.auth import access_error

    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")
    app.add_exception_handler(AccessError, access_error)
    response = ASGIClient(app).get(
        f"/api/v1/admin/finance/reconciliation?order_id={uuid4()}"
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    "changes",
    [{"allocated_count": 1}, {"reason_code": None}, {"requested_count": True}],
)
def test_partial_or_inconsistent_allocations_rejected(changes):
    from pydantic import ValidationError

    from app.api.v1.independent_finance_contract import Allocation

    with pytest.raises(ValidationError):
        Allocation.model_validate(
            {
                "state": "reconciliation_pending",
                "reason_code": "stock_shortage",
                "requested_count": 2,
                "allocated_count": 0,
                **changes,
            }
        )
