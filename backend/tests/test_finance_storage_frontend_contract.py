"""Phase12 actual router/JWT, scripted SQL only; no DB, provider or workers.

Never invoke retention mutations. No PostgreSQL/RLS/concurrency acceptance claim.
"""
import asyncio
import json
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from pydantic import ValidationError

from app.api.auth import AccessError, access_error
from app.api.v1.retention import RetentionHoldRequest, router
from app.core.auth import JWTVerifier
from app.core.config import Settings

FINANCE = "/api/v1/admin/finance/sheet-sync"
STORAGE = "/api/v1/admin/storage/artifacts"
STAMP = datetime(2026, 10, 24, tzinfo=UTC)


class Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    one_or_none = scalar_one_or_none

    def mappings(self):
        return self

    def __iter__(self):
        return iter(self.value)


class ScriptedDatabase:
    def __init__(self):
        self.info, self.calls = {}, []
        self.roles, self.email, self.mfa = {"security_admin"}, True, True
        self.retry = "eligible"

    @contextmanager
    def transaction(self):
        yield self

    def execute(self, statement, params=None):
        sql, p = str(statement), params or {}
        self.calls.append((sql, p))
        for prohibited in ("tag_pairs", "qr_codes", "order_pair", "sr_retention_retry", "sr_retention_prepare", "delete from"):
            assert prohibited not in sql.lower()
        if "SET LOCAL ROLE" in sql or "set_config(" in sql:
            return Result(None)
        if "sr_account_session_state" in sql:
            return Result(SimpleNamespace(email_verified=self.email, mfa_active=self.mfa))
        if "FROM public.staff_roles" in sql:
            return Result(1 if self.roles.intersection(p["roles"]) else None)
        if "FROM public.finance_sheet_sync s" in sql:
            rows = [{"id": UUID(int=n), "order_id": UUID(int=100+n), "sheet_row_key": "PRIVATE", "last_export_version": 1, "status": "failed", "attempt_count": 2, "last_error_code": None, "last_synced_at": None, "updated_at": STAMP, "payment_status": "paid", "fulfillment_status": "pending", "currency_code": "PKR", "total_pkr": "120.00"} for n in (3, 2, 1)]
            if p["cursor_id"] is not None:
                rows = [r for r in rows if r["id"].int < p["cursor_id"].int]
            return Result(rows[:p["fetch_limit"]])
        if "UNION ALL" in sql and "public.print_artifacts" in sql:
            return Result([{"id": UUID(int=1), "resource_type": "print_artifact", "owner_id": UUID(int=201), "bucket": "PRIVATE", "object_key": "PRIVATE", "format": "pdf", "sha256_hex": "PRIVATE", "size_bytes": 120, "retention_until": STAMP, "deletion_hold_reason": "PRIVATE", "deleted_at": None, "on_hold": True, "cleanup_job": None}])
        if "SELECT status FROM public.finance_sheet_sync" in sql:
            return Result("failed" if self.retry == "eligible" else "synced")
        if "UPDATE public.finance_sheet_sync" in sql:
            return Result({"id": UUID(int=1), "order_id": UUID(int=101), "status": "retry"} if self.retry == "eligible" else None)
        if "SELECT id, status FROM public.finance_sheet_sync" in sql:
            return Result({"id": UUID(int=1), "status": "synced"} if self.retry == "conflict" else None)
        if "INSERT INTO public.durable_jobs" in sql:
            assert "'finance.sync'" in sql and "NOT EXISTS" in sql
            return Result(None)
        if "INSERT INTO public.audit_events" in sql:
            assert p["action"] == "finance.sheet_sync_retry"
            return Result(None)
        raise AssertionError("Unreviewed SQL: " + sql)


@pytest.fixture
def harness():
    private = ec.generate_private_key(ec.SECP256R1())
    jwk = json.loads(jwt.algorithms.get_default_algorithms()["ES256"].to_jwk(private.public_key()))
    jwk.update(kid="synthetic", alg="ES256", use="sig")
    settings = Settings(_env_file=None, supabase_url="https://metadata.invalid")

    def provider(request):
        assert str(request.url) == "https://metadata.invalid/auth/v1/.well-known/jwks.json"
        return httpx.Response(200, json={"keys": [jwk]})

    verifier = JWTVerifier(settings, transport=httpx.MockTransport(provider))
    app, db = FastAPI(), ScriptedDatabase()
    app.state.settings, app.state.database, app.state.jwt_verifier = settings, db, verifier
    app.add_exception_handler(AccessError, access_error)
    app.include_router(router, prefix="/api/v1")

    def request(storage=False, query="", retry=False, auth=True):
        assert not storage or not retry
        headers = {}
        if auth:
            claims = {"iss": "https://metadata.invalid/auth/v1", "aud": "authenticated", "sub": str(UUID(int=111)), "session_id": str(UUID(int=112)), "role": "authenticated", "aal": "aal2", "is_anonymous": False, "iat": int(time.time())-1, "exp": int(time.time())+300}
            headers["Authorization"] = "Bearer " + jwt.encode(claims, private, algorithm="ES256", headers={"kid": "synthetic"})

        async def send():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://isolated.invalid") as client:
                path = STORAGE if storage else FINANCE
                if retry:
                    return await client.post(path + "/" + str(UUID(int=1)) + "/retry", headers=headers)
                return await client.get(path + query, headers=headers)

        return asyncio.run(send())

    yield SimpleNamespace(db=db, request=request, app=app)
    verifier.close()


def test_finance_contract_and_cursor(harness):
    r = harness.request(query="?limit=1")
    assert r.status_code == 200
    page = r.json()
    assert len(page["items"][0]) == 13 and page["next_cursor"]
    next_page = harness.request(query="?limit=1&cursor=" + page["next_cursor"]).json()
    assert next_page["items"][0]["id"] != page["items"][0]["id"]


def test_storage_exact_metadata_contract(harness):
    r = harness.request(storage=True, query="?limit=20&resource_type=print_artifact")
    assert r.status_code == 200 and set(r.json()) == {"items"}
    assert len(r.json()["items"][0]) == 13 and r.json()["items"][0]["on_hold"]
    assert "next_cursor" not in r.json()


@pytest.mark.parametrize("storage", [False, True])
@pytest.mark.parametrize("role", ["finance", "operations", "security_admin", "superadmin", "support"])
def test_actual_role_matrix(harness, storage, role):
    harness.db.roles = {role}
    allowed = role in {"finance", "security_admin", "superadmin"} or storage and role == "operations"
    assert harness.request(storage=storage).status_code == (200 if allowed else 403)


@pytest.mark.parametrize("storage", [False, True])
def test_auth_and_mfa(harness, storage):
    assert harness.request(storage=storage, auth=False).status_code == 401
    harness.db.email = False
    assert harness.request(storage=storage).status_code == 403
    harness.db.email, harness.db.mfa = True, False
    assert harness.request(storage=storage).status_code == 403


@pytest.mark.parametrize("storage", [False, True])
@pytest.mark.parametrize("query", ["?limit=0", "?limit=101", "?limit=no"])
def test_actual_query_bounds(harness, storage, query):
    assert harness.request(storage=storage, query=query).status_code == 422


def test_retry_empty_post_receipt_and_audit(harness):
    response = harness.request(retry=True)
    assert response.status_code == 202 and response.json()["status"] == "retry"
    assert any("FOR UPDATE" in sql for sql, _ in harness.db.calls)
    assert any(p.get("action") == "finance.sheet_sync_retry" for _, p in harness.db.calls)


@pytest.mark.parametrize("state,code", [("conflict", 409), ("missing", 404)])
def test_retry_conflict_and_missing(harness, state, code):
    harness.db.retry = state
    assert harness.request(retry=True).status_code == code
    assert not any("INSERT INTO" in sql for sql, _ in harness.db.calls)


@pytest.mark.parametrize("body", [{}, {"reason_code": ""}, {"reason_code": "not allowed"}, {"reason_code": "x", "confirmed": True}])
def test_quarantined_reason_model_only(body):
    with pytest.raises(ValidationError):
        RetentionHoldRequest.model_validate(body)


def test_registration_and_quarantine_source_evidence(harness):
    operations = {r.operation_id for r in router.routes}
    assert {"API-238", "API-239", "API-242", "API-243", "API-244", "API-245"} <= operations
    root = Path(__file__).parents[1]
    assert 'include_router(retention_router, prefix="/api/v1")' in (root / "app/main.py").read_text()
    trigger = root / "alembic/versions/0021_support_case_console.py"
    sql = trigger.read_text()
    assert "sr_support_finder_hold_lock" in sql and "tag_pairs" in sql
    retention = (root / "alembic/versions/0019_retention_recovery.py").read_text()
    assert "sr_retention_prepare" in retention and "order_pair_units" in retention
