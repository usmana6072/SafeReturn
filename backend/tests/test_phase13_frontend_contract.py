"""Actual Phase13 read routers/JWT with scripted SQL; never invoke summary.

No .env, database engine, migrations, provider, readiness, worker or identities.
These are contract checks, not PostgreSQL/RLS or real authentication acceptance.
"""
import asyncio
import json
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI

from app.api.auth import AccessError, access_error
from app.api.v1.account import router as account_router
from app.api.v1.audit_events import router as audit_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.health import health_router
from app.core.auth import JWTVerifier
from app.core.config import Settings

PATHS = {"audit": "/api/v1/admin/audit-events", "trends": "/api/v1/admin/dashboard/trends", "security": "/api/v1/me/staff-security", "liveness": "/api/v1/health/live"}
ACTOR = UUID(int=111)


class Result:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value

    scalar_one_or_none = scalar_one
    one_or_none = scalar_one

    def mappings(self):
        return self

    def all(self):
        return self.value

    def scalars(self):
        return self.value


class ScriptedDatabase:
    def __init__(self):
        self.info, self.calls = {}, []
        self.roles, self.mfa, self.email = {"security_admin"}, True, True
        self.audit_rows = True

    @contextmanager
    def transaction(self):
        yield self

    @contextmanager
    def begin_nested(self):
        yield self

    def execute(self, statement, params=None):
        sql, p = str(statement), params or {}
        self.calls.append((sql, p))
        for forbidden in ("sr_dashboard_summary", "sr_fulfillment_eligible", "tag_pairs", "qr_codes", "order_pair", "pair_print", "delete from", "update public"):
            assert forbidden not in sql.lower()
        if "SET LOCAL" in sql or "set_config(" in sql:
            return Result(None)
        if "SHOW statement_timeout" in sql:
            return Result("0")
        if "sr_account_session_state" in sql:
            return Result(SimpleNamespace(email_verified=self.email, mfa_active=self.mfa))
        if "SELECT role FROM public.staff_roles" in sql:
            assert p["uid"] == ACTOR
            return Result(sorted(self.roles))
        if "FROM public.staff_roles" in sql:
            return Result(1 if self.roles.intersection(p["roles"]) else None)
        if "sr_dashboard_trend" in sql:
            assert p["series"] in {"notifications_created", "shipments_dispatched"}
            end = p["end"]
            return Result([{"start": end-timedelta(days=30-i), "end": end-timedelta(days=29-i), "n": 1000 if i == 29 else i} for i in range(30)])
        if "FROM public.audit_events WHERE" in sql:
            stamp = datetime.now(UTC)-timedelta(seconds=10)
            rows = [{"id": UUID(int=n), "occurred_at": stamp, "actor_kind": "system", "actor_user_id": None, "action": "PRIVATE_CANARY" if n == 3 else "audit.search", "target_type": "PRIVATE_CANARY" if n == 3 else "audit_search", "target_id": None} for n in (3, 2, 1)] if self.audit_rows else []
            if p["ident"] is not None:
                rows = [r for r in rows if r["id"].int < p["ident"].int]
            return Result(rows[:p["lim"]])
        if "INSERT INTO public.audit_events" in sql:
            assert "'audit.search','audit_search'" in sql and set(p) == {"uid"}
            return Result(None)
        raise AssertionError("Unreviewed SQL: " + sql)


@pytest.fixture
def harness():
    private = ec.generate_private_key(ec.SECP256R1())
    jwk = json.loads(jwt.algorithms.get_default_algorithms()["ES256"].to_jwk(private.public_key()))
    jwk.update(kid="synthetic", alg="ES256", use="sig")
    settings = Settings(_env_file=None, supabase_url="https://phase13.invalid", dashboard_enabled=True)

    def jwks(request):
        assert str(request.url) == "https://phase13.invalid/auth/v1/.well-known/jwks.json"
        return httpx.Response(200, json={"keys": [jwk]})

    verifier = JWTVerifier(settings, transport=httpx.MockTransport(jwks))
    app, db = FastAPI(), ScriptedDatabase()
    app.state.settings, app.state.database, app.state.jwt_verifier = settings, db, verifier
    app.add_exception_handler(AccessError, access_error)
    for router in (account_router, audit_router, dashboard_router, health_router(settings)):
        app.include_router(router, prefix="/api/v1")

    def request(kind="trends", query="", auth=True, age=1):
        assert kind in PATHS and (not query or query.startswith("?"))
        headers = {}
        if auth:
            claims = {"iss": "https://phase13.invalid/auth/v1", "aud": "authenticated", "sub": str(ACTOR), "session_id": str(UUID(int=112)), "role": "authenticated", "aal": "aal2", "is_anonymous": False, "iat": int(time.time())-1, "exp": int(time.time())+300}
            if age is not None:
                claims["amr"] = [{"method": "password", "timestamp": int(time.time())-age}]
            headers["Authorization"] = "Bearer " + jwt.encode(claims, private, algorithm="ES256", headers={"kid": "synthetic"})

        async def send():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://isolated.invalid") as client:
                return await client.get(PATHS[kind]+query, headers=headers)

        return asyncio.run(send())

    yield SimpleNamespace(db=db, request=request, app=app, settings=settings)
    verifier.close()


def test_trends_exact_range_precision_and_timezone(harness):
    response = harness.request(query="?display_timezone=Asia/Karachi")
    assert response.status_code == 200
    data = response.json()
    assert data["bucket_timezone"] == "UTC" and data["display_timezone"] == "Asia/Karachi"
    series = data["series"][0]
    assert series["series_id"] == "notifications_created" and len(series["buckets"]) == 30
    assert series["buckets"][-1]["count"] == {"value": 1000, "is_exact": False}


@pytest.mark.parametrize("role", ["operations", "finance", "support", "security_admin", "superadmin"])
def test_trends_explicit_role_projection(harness, role):
    harness.db.roles = {role}
    response = harness.request()
    assert response.status_code == 200
    data = response.json()
    if role in {"support", "superadmin"}:
        assert data["series"] == []
    if role in {"operations", "finance"}:
        orders = next(r for r in data["series"] if r["series_id"] == "orders_placed")
        assert orders["status"] == "unavailable" and orders["buckets"] == []


@pytest.mark.parametrize("query", ["?range=7d", "?interval=hour", "?display_timezone=bad", "?display_timezone=UTC&display_timezone=UTC"])
def test_trends_unsupported_query(harness, query):
    assert harness.request(query=query).status_code == 422


def test_dashboard_feature_disabled(harness):
    harness.settings.dashboard_enabled = False
    assert harness.request().status_code == 503


def test_audit_metadata_redaction_cursor_and_search_audit(harness):
    response = harness.request("audit", "?limit=1")
    assert response.status_code == 200 and "PRIVATE_CANARY" not in response.text
    data = response.json()
    assert data["scope"] == "security_metadata" and len(data["items"][0]) == 7
    assert data["items"][0]["actor_user_id"] is None
    assert data["items"][0]["action"] == "restricted_event"
    second = harness.request("audit", "?limit=1&cursor="+data["next_cursor"]).json()
    assert second["items"][0]["id"] != data["items"][0]["id"]
    assert any("INSERT INTO public.audit_events" in sql for sql, _ in harness.db.calls)


@pytest.mark.parametrize("role", ["operations", "finance", "support", "superadmin"])
def test_audit_security_admin_only(harness, role):
    harness.db.roles = {role}
    assert harness.request("audit").status_code == 403


@pytest.mark.parametrize("age", [301, None])
def test_audit_signed_recent_amr_required_not_token_iat(harness, age):
    assert harness.request("audit", age=age).status_code == 403


@pytest.mark.parametrize("query", ["?limit=101", "?actor_id=bad", "?action=delete", "?cursor=bad", "?start=2026-01-01T00:00:00Z&end=2026-03-01T00:00:00Z"])
def test_audit_query_validation(harness, query):
    assert harness.request("audit", query).status_code == 422


def test_staff_current_subject_only_and_missing_mfa(harness):
    response = harness.request("security")
    assert response.status_code == 200 and set(response.json()) == {"roles", "mfa_verified", "capabilities"}
    assert response.json()["roles"] == ["security_admin"]
    harness.db.mfa = False
    data = harness.request("security").json()
    assert data["mfa_verified"] is False and data["capabilities"] == []


@pytest.mark.parametrize("kind", ["audit", "trends", "security"])
def test_auth_verified_email_and_mfa(harness, kind):
    assert harness.request(kind, auth=False).status_code == 401
    harness.db.email = False
    assert harness.request(kind).status_code == 403
    harness.db.email, harness.db.mfa = True, False
    assert harness.request(kind).status_code == (200 if kind == "security" else 403)


def test_public_liveness_uses_no_auth_or_database(harness):
    assert harness.request("liveness", auth=False).json() == {"status": "ok"}
    assert harness.db.calls == []


def test_source_summary_quarantine_and_safe_trend_graph():
    root = Path(__file__).parents[1]
    helpers = (root / "alembic/versions/0028_dashboard_reads.sql").read_text()
    summary, trend = helpers.split("CREATE FUNCTION public.sr_dashboard_trend", 1)
    assert "sr_fulfillment_eligible" in summary
    eligible = (root / "alembic/versions/0018_fulfillment_eligibility.py").read_text()
    assert "order_pair_units" in eligible and "pair_print_qa" in eligible
    assert "public.shipments" in trend and "public.notification_outbox" in trend
    for forbidden in ("tag_pairs", "order_pair", "sr_fulfillment_eligible", "qr_codes", "INSERT", "UPDATE", "DELETE"):
        assert forbidden not in trend
    main = (root / "app/main.py").read_text()
    assert "install_dashboard(application)" in main
    assert 'include_router(audit_events_router, prefix="/api/v1")' in main
    assert 'include_router(account_router, prefix="/api/v1")' in main
