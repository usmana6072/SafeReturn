"""API-330 router/JWT contract with scripted SQL; never call API-327/exports.

No .env, database engine, migrations, provider identities, worker or storage.
Case authority/RLS results here are scripted, not PostgreSQL acceptance.
"""

import asyncio
import json
import time
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError

from app.api.auth import AccessError, access_error
from app.api.v1.privacy_exports import Decision, router
from app.core.auth import JWTVerifier
from app.core.config import Settings

ACTOR = UUID(int=111)
PATH = "/api/v1/admin/privacy/exports"
STAMP = "2026-10-24T00:00:00+00:00"


class Result:
    def __init__(self, value):
        self.value = value

    def one_or_none(self):
        return self.value

    scalar_one_or_none = one_or_none

    def scalars(self):
        return self.value


def row(number):
    return {
        "request_id": str(UUID(int=number)), "case_id": str(UUID(int=200 + number)),
        "status": "requested", "revision": number, "scope_version": "basic_v1",
        "manifest_version": "basic_v1:1", "manifest_id": str(UUID(int=300 + number)),
        "categories": None, "created_at": STAMP, "ready_at": None, "expires_at": None,
    }


class ScriptedDatabase:
    def __init__(self):
        self.info, self.calls = {}, []
        self.roles, self.email, self.mfa = {"security_admin"}, True, True
        self.authority, self.fail = True, False

    @contextmanager
    def transaction(self):
        yield self

    def execute(self, statement, params=None):
        sql, p = str(statement), params or {}
        self.calls.append((sql, p))
        for forbidden in ("tag_pairs", "qr_codes", "order_pair", "sr_export_decide", "sr_export_page", "sr_export_preflight", "sr_export_request", "sr_export_consume", "sr_export_grant", "sr_support_", "sr_financial_", "insert into", "update public", "delete from"):
            assert forbidden not in sql.lower(), sql
        if "SET LOCAL ROLE" in sql or "set_config(" in sql:
            return Result(None)
        if "sr_account_session_state" in sql:
            return Result(SimpleNamespace(email_verified=self.email, mfa_active=self.mfa))
        if "FROM public.staff_roles" in sql:
            return Result(1 if self.roles.intersection(p["roles"]) else None)
        if "sr_export_list" in sql:
            if self.fail:
                raise OperationalError("redacted", {}, Exception("PRIVATE_CANARY"))
            rows = [row(n) for n in (3, 2, 1)] if self.authority else []
            if p["id"] is not None:
                rows = [r for r in rows if UUID(r["request_id"]) < p["id"]]
            return Result(rows[:p["lim"]])
        raise AssertionError("Unreviewed SQL")


@pytest.fixture
def privacy_app():
    private = ec.generate_private_key(ec.SECP256R1())
    jwk = json.loads(jwt.algorithms.get_default_algorithms()["ES256"].to_jwk(private.public_key()))
    jwk.update(kid="synthetic", alg="ES256", use="sig")
    settings = Settings(_env_file=None, supabase_url="https://privacy.invalid")

    def provider(request):
        assert str(request.url) == "https://privacy.invalid/auth/v1/.well-known/jwks.json"
        return httpx.Response(200, json={"keys": [jwk]})

    verifier = JWTVerifier(settings, transport=httpx.MockTransport(provider))
    app, db = FastAPI(), ScriptedDatabase()
    app.state.settings, app.state.database, app.state.jwt_verifier = settings, db, verifier
    app.add_exception_handler(AccessError, access_error)
    app.include_router(router, prefix="/api/v1")

    def get(query="", auth=True):
        assert not query or query.startswith("?")  # Never address another API.
        headers = {}
        if auth:
            claims = {"iss": "https://privacy.invalid/auth/v1", "aud": "authenticated", "sub": str(ACTOR), "session_id": str(UUID(int=112)), "role": "authenticated", "aal": "aal2", "is_anonymous": False, "iat": int(time.time()) - 1, "exp": int(time.time()) + 300}
            headers["Authorization"] = "Bearer " + jwt.encode(claims, private, algorithm="ES256", headers={"kid": "synthetic"})

        async def send():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://isolated.invalid") as client:
                return await client.get(PATH + query, headers=headers)

        return asyncio.run(send())

    yield SimpleNamespace(app=app, db=db, get=get)
    verifier.close()


def test_actual_list_contract_and_cursor(privacy_app):
    h = privacy_app
    response = h.get("?limit=1")
    assert response.status_code == 200 and response.headers["cache-control"] == "private, no-store"
    page = response.json()
    assert set(page) == {"items", "next_cursor"} and page["next_cursor"]
    assert set(page["items"][0]) == set(row(1))
    assert not {"subject_id", "object_key", "snapshot_ciphertext", "checksum", "download_url"}.intersection(page["items"][0])
    next_page = h.get("?limit=1&cursor=" + page["next_cursor"]).json()
    assert next_page["items"][0]["request_id"] != page["items"][0]["request_id"]
    assert all(p["lim"] == 2 for sql, p in h.db.calls if "sr_export_list" in sql)


def test_no_case_authority_returns_no_rows_scripted(privacy_app):
    privacy_app.db.authority = False
    assert privacy_app.get().json() == {"items": [], "next_cursor": None}


@pytest.mark.parametrize("role", ["support", "operations", "finance", "superadmin"])
def test_explicit_role_only(privacy_app, role):
    privacy_app.db.roles = {role}
    assert privacy_app.get().status_code == 403
    assert not any("sr_export_list" in sql for sql, _ in privacy_app.db.calls)


def test_auth_email_and_mfa(privacy_app):
    h = privacy_app
    assert h.get(auth=False).status_code == 401 and not h.db.calls
    h.db.email = False
    assert h.get().status_code == 403
    h.db.email, h.db.mfa = True, False
    assert h.get().status_code == 403


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "limit=no", "cursor=bad"])
def test_invalid_page_input(privacy_app, query):
    assert privacy_app.get("?" + query).status_code == 422


def test_database_failure_redacted(privacy_app):
    privacy_app.db.fail = True
    response = privacy_app.get()
    assert response.status_code == 503 and "PRIVATE_CANARY" not in response.text
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("changes", [{"expected_revision": 0}, {"expected_revision": "1"}, {"decision": "delete"}, {"reason_code": "arbitrary"}, {"confirmed": False}, {"confirmed": "true"}])
def test_quarantined_decision_model_only_no_endpoint_invocation(changes):
    with pytest.raises(ValidationError):
        Decision.model_validate({"case_id": str(UUID(int=22)), "expected_revision": 1, "decision": "approve", "scope_version": "basic_v1", "reason_code": "scope_reviewed", "confirmed": True, **changes})


def test_source_list_graph_and_decision_quarantine():
    root = Path(__file__).parents[1]
    original = (root / "alembic/versions/0022_privacy_exports.sql").read_text()
    listing = original.split("CREATE FUNCTION public.sr_export_list", 1)[1].split("END $$;", 1)[0]
    assert "sr_export_status(r)" in listing and "sr_export_authorized(r.case_id" in listing
    for forbidden in ("tag_pairs", "order_pair_units", "sr_export_current", "sr_export_decide", "sr_export_page", "INSERT", "UPDATE"):
        assert forbidden not in listing
    latest = (root / "alembic/versions/0030_account_lifecycle.sql").read_text()
    authority = latest.split("CREATE OR REPLACE FUNCTION public.sr_export_authorized", 1)[1].split("$$;", 1)[0]
    assert "privacy_export_authorities" in authority and "sr_account_epoch_allows" in authority
    assert "tag_pairs" not in authority and "order_pair_units" not in authority
    worker = (root / "app/workers/privacy_exports.py").read_text()
    assert '"pairs"' in worker and '"occurrences"' in worker and "sr_export_page" in worker
    projection = original.split("CREATE FUNCTION public.sr_export_page", 1)[1].split("END $$;", 1)[0]
    assert "public.tag_pairs" in projection and "public.order_item_qr_uses" in projection
    assert 'include_router(privacy_exports_router, prefix="/api/v1")' in (root / "app/main.py").read_text()
    operations = {route.operation_id: route.path for route in router.routes}
    assert operations["API-330"] == "/admin/privacy/exports"
    assert operations["API-327"] == "/admin/privacy/exports/{request_id}/decisions"
