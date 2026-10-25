"""Synthetic HTTP/DTO/helper-boundary tests; not PostgreSQL transaction proof."""

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from test_critical_workflow_boundaries import Result
from test_health import ASGIClient

from app.api.auth import get_auth_context
from app.api.v1.owner_qr import decode_cursor
from app.api.v1.typed_inventory import GenerationReceipt
from app.core.config import Settings
from app.main import create_app

BASE = "/api/v1/admin/qr-inventory"
STAMP = datetime(2026, 10, 22, tzinfo=UTC).isoformat()


@pytest.fixture
def fixture():
    session = MagicMock()
    context = SimpleNamespace(
        session=session,
        email_verified=True,
        mfa_verified=True,
        principal=SimpleNamespace(user_id=uuid4(), session_id=uuid4()),
    )
    state = {"role": True, "result": None, "error": None}
    calls = []

    def execute(statement, params=None):
        sql = str(statement)
        calls.append((sql, params))
        if "FROM public.staff_roles" in sql:
            assert params["roles"] == ["operations"]
            return Result(1 if state["role"] else None)
        if state["error"]:
            raise state["error"]
        return Result(state["result"])

    session.execute.side_effect = execute
    app = create_app(Settings())
    app.dependency_overrides[get_auth_context] = lambda: context
    return ASGIClient(app), context, state, calls


def receipt(kind="lost", quantity=3):
    return {
        "batch_id": str(uuid4()),
        "batch_label": "TYPED-TEST",
        "qr_type": kind,
        "generated_quantity": quantity,
        "status": "generated",
        "created_at": STAMP,
    }


def post(client, body=None, **kwargs):
    return client.post(
        BASE + "/batches",
        json=body
        or {
            "batch_label": "TYPED-TEST",
            "qr_type": "lost",
            "quantity": 3,
        },
        headers=kwargs.pop("headers", {"Idempotency-Key": "typed-test-key"}),
        **kwargs,
    )


@pytest.mark.parametrize("kind", ["lost", "ice"])
def test_generate_passes_one_type_and_exact_token_count_without_returning_tokens(
    fixture, kind
):
    client, ctx, state, calls = fixture
    state["result"] = receipt(kind)
    response = post(
        client, {"batch_label": "TYPED-TEST", "qr_type": kind, "quantity": 3}
    )
    assert response.status_code == 201
    assert response.json() == GenerationReceipt.model_validate(
        state["result"]
    ).model_dump(mode="json")
    sql, args = calls[-1]
    assert "sr_typed_inventory_generate" in sql
    assert args["sid"] == ctx.principal.session_id
    assert args["kind"] == kind and args["quantity"] == 3
    tokens = json.loads(args["tokens"])
    assert len(tokens) == len(set(tokens)) == 3
    assert all(re.fullmatch(r"[A-Za-z0-9_-]{43}", token) for token in tokens)
    assert all(token not in response.text for token in tokens)
    assert "public_token" not in response.text and "activation" not in response.text
    assert "no-store" in response.headers["cache-control"]
    ctx.session.begin_nested.assert_called_once()


@pytest.mark.parametrize(
    "change",
    [
        {"quantity": 0},
        {"quantity": 1001},
        {"quantity": True},
        {"quantity": "3"},
        {"quantity": 1.5},
        {"qr_type": "both"},
        {"qr_type": "emergency"},
        {"qr_type": None},
        {"batch_label": "bad label"},
        {"batch_label": "x"},
        {"ecc_level": "L"},
        {"public_token": "PRIVATE_INPUT_CANARY"},
        {"pair_count": 3},
        {"owner_user_id": str(uuid4())},
    ],
)
def test_closed_generation_contract_rejects_client_identity_and_invalid_quantities(
    fixture, change
):
    client, _, _, calls = fixture
    response = post(
        client,
        {"batch_label": "TYPED-TEST", "qr_type": "lost", "quantity": 3, **change},
    )
    assert response.status_code == 422
    assert "PRIVATE_INPUT_CANARY" not in response.text
    assert not any("sr_typed_inventory_generate" in sql for sql, _ in calls)


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Idempotency-Key": "short"},
        [("Idempotency-Key", "first-key"), ("Idempotency-Key", "second-key")],
    ],
)
def test_mutations_require_one_valid_idempotency_key(fixture, headers):
    client, _, _, calls = fixture
    assert post(client, headers=headers).status_code == 400
    assert len(calls) == 1  # authorization only


@pytest.mark.parametrize("reason", ["email", "mfa", "role"])
@pytest.mark.parametrize(
    "path",
    [
        "/batches",
        "/codes",
        "/summary",
        "/batches/" + str(uuid4()),
        "/codes/" + str(uuid4()),
    ],
)
def test_every_read_requires_operations_verified_email_and_mfa(fixture, reason, path):
    client, ctx, state, calls = fixture
    if reason == "email":
        ctx.email_verified = False
    elif reason == "mfa":
        ctx.mfa_verified = False
    else:
        state["role"] = False
    assert client.get(BASE + path).status_code == 403
    assert not any("sr_typed_inventory_read" in sql for sql, _ in calls)


@pytest.mark.parametrize("reason", ["email", "mfa", "role"])
def test_generation_denies_before_token_generation_or_sql_helper(
    fixture, monkeypatch, reason
):
    client, ctx, state, calls = fixture
    if reason == "email":
        ctx.email_verified = False
    elif reason == "mfa":
        ctx.mfa_verified = False
    else:
        state["role"] = False
    monkeypatch.setattr(
        "app.api.v1.typed_inventory.new_public_token",
        lambda: pytest.fail("Unauthorized mint"),
    )
    assert post(client).status_code == 403
    assert not any("sr_typed_inventory_generate" in sql for sql, _ in calls)


@pytest.mark.parametrize(
    "code,status",
    [
        ("FORBIDDEN", 403),
        ("IDEMPOTENCY_KEY_REUSED", 409),
        ("BATCH_LABEL_CONFLICT", 409),
    ],
)
def test_database_replay_and_authority_conflicts_are_closed(fixture, code, status):
    client, _, state, _ = fixture
    state["result"] = {"error": code}
    assert post(client).status_code == status


def test_unique_collision_rolls_back_savepoint_and_hides_private_sql(fixture):
    client, ctx, state, _ = fixture
    state["error"] = IntegrityError(
        "PRIVATE_SQL_CANARY", {}, Exception("PRIVATE_TOKEN_CANARY")
    )
    response = post(client)
    assert response.status_code == 409
    assert "PRIVATE" not in response.text
    assert (
        ctx.session.begin_nested.return_value.__exit__.call_args[0][0] is IntegrityError
    )


def metadata(identity=None):
    return {
        "qr_id": str(identity or uuid4()),
        "batch_id": str(uuid4()),
        "batch_label": "TYPED-TEST",
        "qr_type": "lost",
        "serial_number": "SR-SYNTHETIC",
        "public_status": "unactivated",
        "inventory_status": "available",
        "ownership_status": "unclaimed",
        "row_version": 1,
        "created_at": STAMP,
        "allocatable": True,
    }


def test_filtered_keyset_page_has_safe_metadata_and_no_extra_row(fixture):
    client, _, state, calls = fixture
    first, second = metadata(), metadata()
    state["result"] = {"as_of": STAMP, "items": [first, second]}
    response = client.get(
        BASE + "/codes?qr_type=lost&inventory_status=available&limit=1"
    )
    assert response.status_code == 200
    value = response.json()
    assert len(value["items"]) == 1 and value["items"][0]["qr_id"] == first["qr_id"]
    position = decode_cursor(value["next_cursor"])
    assert str(position[0]) == first["qr_id"]
    filters = json.loads(calls[-1][1]["filters"])
    assert filters["qr_type"] == "lost" and filters["inventory_status"] == "available"
    assert filters["limit"] == 1 and calls[-1][1]["view"] == "codes"
    assert "owner_user_id" not in response.text and "public_token" not in response.text


@pytest.mark.parametrize(
    "query",
    [
        "limit=0",
        "limit=101",
        "qr_type=both",
        "cursor=not-base64",
        "owner_user_id=x",
        "inventory_status=reserved",
    ],
)
def test_invalid_inventory_filters_fail_before_metadata_helper(fixture, query):
    client, _, _, calls = fixture
    assert client.get(BASE + "/codes?" + query).status_code == 422
    assert not any("sr_typed_inventory_read" in sql for sql, _ in calls)


def test_detail_unknown_or_legacy_identity_is_concealed(fixture):
    client, _, state, _ = fixture
    state["result"] = None
    assert client.get(BASE + "/codes/" + str(uuid4())).status_code == 404
    assert client.get(BASE + "/batches/" + str(uuid4())).status_code == 404


def test_empty_summary_keeps_types_separate(fixture):
    client, _, state, _ = fixture
    state["result"] = {
        "as_of": STAMP,
        "items": [
            {
                "qr_type": tag,
                "total": 0,
                "available": 0,
                "allocated": 0,
                "retired": 0,
                "allocatable": 0,
            }
            for tag in ("ice", "lost")
        ],
    }
    response = client.get(BASE + "/summary")
    assert response.status_code == 200 and len(response.json()["items"]) == 2


def test_typed_batch_metadata_and_filter_are_separate_from_legacy_contract(fixture):
    client, _, state, calls = fixture
    batch = {
        "batch_id": str(uuid4()),
        "batch_label": "ICE-BATCH",
        "qr_type": "ice",
        "requested_quantity": 10,
        "generated_quantity": 10,
        "status": "generated",
        "ecc_level": "Q",
        "created_at": STAMP,
    }
    state["result"] = {"as_of": STAMP, "items": [batch]}
    response = client.get(BASE + "/batches?qr_type=ice&batch_label=ICE-BATCH")
    assert (
        response.status_code == 200
        and response.json()["items"][0]["generated_quantity"] == 10
    )
    assert response.json()["next_cursor"] is None
    filters = json.loads(calls[-1][1]["filters"])
    assert filters["qr_type"] == "ice" and filters["batch_label"] == "ICE-BATCH"
    state["result"] = batch
    assert client.get(BASE + "/batches/" + batch["batch_id"]).status_code == 200
    schema = client.application.openapi()
    legacy = schema["paths"]["/api/v1/admin/qr-batches"]["post"]["requestBody"][
        "content"
    ]["application/json"]["schema"]
    assert legacy["$ref"].endswith("/BatchRequest")


def test_database_denial_after_http_guard_is_not_treated_as_empty_inventory(fixture):
    client, _, state, _ = fixture
    state["result"] = {"error": "FORBIDDEN"}
    assert client.get(BASE + "/summary").status_code == 403


def test_anonymous_inventory_is_denied_by_real_auth_dependency():
    client = ASGIClient(create_app(Settings()))
    assert client.get(BASE + "/summary").status_code == 401
    assert post(client).status_code == 401


def test_phase2_migration_surface_is_narrow_and_does_not_enable_customer_workflows():
    directory = Path(__file__).parents[1] / "alembic/versions"
    sql = (directory / "0038_typed_inventory.sql").read_text(encoding="utf-8")
    assert "ENABLE ROW LEVEL SECURITY" in sql
    grants = sql[sql.index("GRANT EXECUTE") :]
    assert "TO safereturn_api" in grants and "TO safereturn_worker" not in grants
    assert "GRANT INSERT" not in sql and "CREATE POLICY" not in sql
    assert (
        "pg_advisory_xact_lock" in sql and "UNIQUE REFERENCES public.qr_batches" in sql
    )
    assert "DEFERRABLE INITIALLY DEFERRED" in sql
    assert "sr_checkout" not in sql and "sr_public_qr_projection" not in sql
    assert "INSERT INTO public.tag_pairs" not in sql
