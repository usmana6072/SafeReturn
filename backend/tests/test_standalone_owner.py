"""Offline boundary checks, not PostgreSQL ownership/locking acceptance."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from test_health import ASGIClient

from app.api.auth import AccessError, get_auth_context
from app.api.v1 import standalone_owner as api
from app.core.config import Settings
from app.main import create_app


@pytest.mark.parametrize(
    "payload",
    [
        {"scanned_token": "PUBLIC_TOKEN"},
        {"logical_item_id": str(uuid4()), "owner_user_id": str(uuid4())},
        {"logical_item_id": str(uuid4()), "activation_secret": "SECRET"},
    ],
)
def test_token_and_caller_supplied_proof_are_not_entitlement(payload):
    with pytest.raises(ValidationError):
        api.Begin.model_validate(payload)


@pytest.mark.parametrize("confirmed", [False, 1, "true", None])
def test_confirmation_is_explicit_and_strict(confirmed):
    with pytest.raises(ValidationError):
        api.Confirm(intent_id=uuid4(), confirmed=confirmed)


@pytest.mark.parametrize("key", [None, "short", "x\n" * 20, "x" * 161])
def test_confirmation_requires_safe_idempotency_key(key):
    with pytest.raises(HTTPException):
        api.hashes(api.Confirm(intent_id=uuid4(), confirmed=True), key)


def context():
    return SimpleNamespace(
        session=MagicMock(),
        email_verified=True,
        principal=SimpleNamespace(user_id=uuid4(), session_id=uuid4()),
    )


def test_begin_uses_verified_session_and_item_id_only():
    ctx = context()
    iid = uuid4()
    ctx.session.execute.return_value.scalar_one.return_value = {
        "intent_id": str(uuid4())
    }
    api.begin(api.Begin(logical_item_id=iid), ctx)
    query, params = ctx.session.execute.call_args.args
    assert "sr_standalone_begin" in str(query)
    assert params == {"sid": ctx.principal.session_id, "iid": iid}


def test_unverified_customer_never_reaches_entitlement_helper():
    ctx = context()
    ctx.email_verified = False
    with pytest.raises(AccessError):
        api.begin(api.Begin(logical_item_id=uuid4()), ctx)
    ctx.session.execute.assert_not_called()


def test_confirm_retries_use_same_hash_without_raw_key():
    body = api.Confirm(intent_id=uuid4(), confirmed=True)
    assert api.hashes(body, "synthetic-key") == api.hashes(body, "synthetic-key")
    ctx = context()
    ctx.session.execute.return_value.scalar_one.return_value = {"status": "active"}
    api.confirm(body, ctx, "synthetic-key")
    _, params = ctx.session.execute.call_args.args
    assert params["sid"] == ctx.principal.session_id
    assert len(params["kh"]) == len(params["rh"]) == 64
    assert "synthetic-key" not in str(params)


@pytest.mark.parametrize(
    "value,status",
    [
        (None, 404),
        ({"error": "NOT_RELEASED"}, 409),
        ({"error": "NOT_ELIGIBLE"}, 409),
        ({"error": "VERSION_MISMATCH"}, 412),
    ],
)
def test_safe_failure_mapping(value, status):
    with pytest.raises((AccessError, HTTPException)) as error:
        api.checked(value)
    assert (
        getattr(error.value, "status", getattr(error.value, "status_code", None))
        == status
    )


def test_schema_is_additive_and_releases_nothing():
    sql = (
        Path(__file__).parents[1] / "alembic/versions/0043_standalone_activation.sql"
    ).read_text()
    assert "VALUES(true,false)" in sql
    assert "o.fulfillment_status='delivered'" in sql
    assert "h.delivered_at IS NOT NULL" in sql
    assert "AND session_id=sid" in sql
    assert "i.state_revision<>s.row_version" in sql
    assert "GRANT UPDATE" not in sql
    assert "DROP TABLE" not in sql
    assert "INSERT INTO public.tag_pairs" not in sql


def test_new_owner_endpoints_deny_anonymous_access():
    client = ASGIClient(create_app(Settings()))
    assert client.get("/api/v1/me/independent-qr").status_code == 401
    assert (
        client.post(
            "/api/v1/me/independent-qr/activation-intents",
            json={"logical_item_id": str(uuid4())},
        ).status_code
        == 401
    )


def test_oversized_activation_is_rejected_before_any_database_work():
    app, ctx = create_app(Settings()), context()
    app.dependency_overrides[get_auth_context] = lambda: ctx
    response = ASGIClient(app).post(
        "/api/v1/me/independent-qr/activation-intents",
        content=b"x" * 4097,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
    ctx.session.execute.assert_not_called()


def test_http_validation_never_echoes_public_token_as_claim_proof():
    app, ctx = create_app(Settings()), context()
    app.dependency_overrides[get_auth_context] = lambda: ctx
    response = ASGIClient(app).post(
        "/api/v1/me/independent-qr/activation-intents",
        json={"logical_item_id": str(uuid4()), "scanned_token": "PRIVATE_TOKEN_CANARY"},
    )
    assert response.status_code == 422 and "PRIVATE_TOKEN_CANARY" not in response.text
    ctx.session.execute.assert_not_called()
