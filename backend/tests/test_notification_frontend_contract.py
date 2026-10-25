"""Actual notification router/JWT/AEAD with scripted SQL only; no live fixtures.

No .env, database engine, migrations, Auth identities, provider or worker execution.
This validates application contracts, not installed PostgreSQL behavior.
"""

import asyncio
import base64
import copy
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
from pydantic import SecretStr
from sqlalchemy.exc import OperationalError

from app.api.auth import AccessError, access_error
from app.api.v1.notification_operations import router
from app.core.auth import JWTVerifier
from app.core.config import Settings

ACTOR, EVENT = UUID(int=71), UUID(int=81)
PATH = "/api/v1/admin/notification-outbox"
STAMP = "2026-10-24T00:00:00+00:00"


class Result:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value

    scalar_one_or_none = scalar_one
    one_or_none = scalar_one

    def mappings(self):
        return self


def event(number=81):
    return {
        "id": str(UUID(int=number)), "event_type": "finder_message.created",
        "status": "dead", "attempt_count": 3, "created_at": STAMP,
        "next_attempt_at": STAMP, "lease_until": None, "sent_at": None,
        "last_error_code": "provider_network", "first_attempt_at": STAMP,
        "due_lag_seconds": None, "retry_blocked_reason": None,
        "attempts": None, "next_attempt_before": None,
    }


class ScriptedDatabase:
    def __init__(self):
        self.info, self.calls, self.receipts = {}, [], {}
        self.roles, self.mfa, self.email = {"operations"}, True, True
        self.fail, self.domain_error = False, None
        self.retry_count, self.rollbacks = 0, 0

    @contextmanager
    def transaction(self):
        old = copy.deepcopy((self.receipts, self.retry_count))
        try:
            yield self
        except Exception:
            self.receipts, self.retry_count = old
            self.rollbacks += 1
            raise

    def execute(self, statement, params=None):
        sql, p = str(statement), params or {}
        self.calls.append((sql, p))
        for forbidden in ("tag_pairs", "qr_codes", "order_pair", "sr_support_", "sr_financial_", "sr_fulfillment_", "reservation", "allocation"):
            assert forbidden not in sql.lower(), sql
        if "SET LOCAL ROLE" in sql or "set_config(" in sql or "pg_advisory_xact_lock" in sql:
            return Result(None)
        if "sr_account_session_state" in sql:
            return Result(SimpleNamespace(email_verified=self.email, mfa_active=self.mfa))
        if "FROM public.staff_roles" in sql:
            return Result(1 if self.roles.intersection(p["roles"]) else None)
        if self.fail:
            raise OperationalError("redacted", {}, Exception("PRIVATE"))
        if "sr_notification_metadata" in sql:
            rows = [event(n) for n in (83, 82, 81)]
            if p["id"] is not None:
                rows = [r for r in rows if r["id"] == str(p["id"])]
                for row in rows:
                    row["attempts"] = [{"attempt_number": 3, "outcome": "transient_failure", "attempted_at": STAMP, "finished_at": STAMP, "error_code": "provider_network"}]
            if p["status"] is not None:
                rows = [r for r in rows if r["status"] == p["status"]]
            if p["ident"] is not None:
                rows = [r for r in rows if UUID(r["id"]) < p["ident"]]
            return Result(rows[:p["lim"]])
        if "SELECT request_hash" in sql:
            return Result(self.receipts.get(p["key"]))
        if "sr_notification_retry(" in sql:
            if self.domain_error:
                return Result({"error": self.domain_error})
            self.retry_count += 1
            return Result({"id": str(p["id"]), "status": "retry", "expected_attempt_count": p["expected"]})
        if "INSERT INTO public.idempotency_records" in sql:
            self.receipts[p["key"]] = {"request_hash": p["hash"], "response_body_ciphertext": p["cipher"], "response_key_version": p["version"]}
            return Result(None)
        raise AssertionError("Unreviewed SQL")


@pytest.fixture
def notification_app():
    private = ec.generate_private_key(ec.SECP256R1())
    jwk = json.loads(jwt.algorithms.get_default_algorithms()["ES256"].to_jwk(private.public_key()))
    jwk.update(kid="synthetic", alg="ES256", use="sig")
    settings = Settings(_env_file=None, supabase_url="https://notifications.invalid", profile_data_keys=SecretStr(json.dumps({"1": base64.b64encode(b"n" * 32).decode()})))

    def provider(request):
        assert str(request.url) == "https://notifications.invalid/auth/v1/.well-known/jwks.json"
        return httpx.Response(200, json={"keys": [jwk]})

    verifier = JWTVerifier(settings, transport=httpx.MockTransport(provider))
    app, db = FastAPI(), ScriptedDatabase()
    app.state.settings, app.state.database, app.state.jwt_verifier = settings, db, verifier
    app.add_exception_handler(AccessError, access_error)
    app.include_router(router, prefix="/api/v1")

    def send(method="GET", suffix="", auth=True, body=None, key="synthetic-key-0001"):
        assert not suffix or suffix.startswith(("?", "/"))
        assert "/" not in suffix or suffix == f"/{EVENT}/retry"
        headers = {}
        if auth:
            payload = {"iss": "https://notifications.invalid/auth/v1", "aud": "authenticated", "sub": str(ACTOR), "session_id": str(UUID(int=72)), "role": "authenticated", "aal": "aal2", "is_anonymous": False, "iat": int(time.time()) - 1, "exp": int(time.time()) + 300}
            headers["Authorization"] = "Bearer " + jwt.encode(payload, private, algorithm="ES256", headers={"kid": "synthetic"})
        if key is not None:
            headers["Idempotency-Key"] = key

        async def request():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://isolated.invalid") as client:
                return await client.request(method, PATH + suffix, headers=headers, **({"json": body} if body is not None else {}))

        return asyncio.run(request())

    yield SimpleNamespace(app=app, db=db, send=send, settings=settings)
    verifier.close()


def retry_body():
    return {"expected_attempt_count": 3, "reason": "provider_recovered", "confirmed": True}


def test_list_pagination_filter_and_detail(notification_app):
    h = notification_app
    response = h.send(suffix="?limit=1")
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"items", "next_cursor", "current_template"}
    assert data["next_cursor"] and len(data["items"]) == 1
    page = h.send(suffix="?limit=1&cursor=" + data["next_cursor"]).json()
    assert page["items"][0]["id"] != data["items"][0]["id"]
    assert h.send(suffix="?status=sent").json()["items"] == []
    detail = h.send(suffix=f"?id={EVENT}").json()["items"][0]
    assert detail["attempts"][0]["attempt_number"] == 3
    assert not {"recipient_user_id", "email", "payload_ciphertext", "provider_message_id", "aggregate_id"}.intersection(detail)


@pytest.mark.parametrize("role", ["support", "finance", "superadmin"])
def test_forbidden_roles(notification_app, role):
    notification_app.db.roles = {role}
    assert notification_app.send().status_code == 403
    assert notification_app.send("POST", f"/{EVENT}/retry", body=retry_body()).status_code == 403
    assert not any("sr_notification_" in sql for sql, _ in notification_app.db.calls)


def test_auth_email_and_mfa(notification_app):
    h = notification_app
    assert h.send(auth=False).status_code == 401
    assert not h.db.calls
    h.db.email = False
    assert h.send().status_code == 403
    h.db.email, h.db.mfa = True, False
    assert h.send().status_code == 403


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "status=delivered", "cursor=bad", "attempt_before=0", "attempt_limit=101", "id=bad"])
def test_invalid_filters(notification_app, query):
    assert notification_app.send(suffix="?" + query).status_code == 422


@pytest.mark.parametrize("changes", [{"confirmed": False}, {"confirmed": "true"}, {"reason": "send_now"}, {"expected_attempt_count": 0}, {"expected_attempt_count": "3"}, {"email": "PRIVATE"}])
def test_retry_model_rejects_bad_input(notification_app, changes):
    assert notification_app.send("POST", f"/{EVENT}/retry", body={**retry_body(), **changes}).status_code == 422
    assert notification_app.db.retry_count == 0


def test_retry_key_receipt_replay_and_conflict(notification_app):
    h = notification_app
    assert h.send("POST", f"/{EVENT}/retry", body=retry_body(), key=None).status_code == 400
    first = h.send("POST", f"/{EVENT}/retry", body=retry_body())
    replay = h.send("POST", f"/{EVENT}/retry", body=retry_body())
    assert first.status_code == replay.status_code == 202
    assert first.json() == replay.json() == {"id": str(EVENT), "status": "retry", "expected_attempt_count": 3}
    assert h.db.retry_count == 1 and len(h.db.receipts) == 1
    assert h.send("POST", f"/{EVENT}/retry", body={**retry_body(), "reason": "recipient_reverified"}).status_code == 409


@pytest.mark.parametrize("error,status", [("STALE_ATTEMPT", 412), ("RETRY_NOT_ALLOWED", 409), ("NOT_FOUND", 404), ("INVALID_REQUEST", 422)])
def test_retry_domain_refusal(notification_app, error, status):
    notification_app.db.domain_error = error
    assert notification_app.send("POST", f"/{EVENT}/retry", body=retry_body()).status_code == status
    assert not notification_app.db.receipts


def test_backend_failure_redacted(notification_app):
    notification_app.db.fail = True
    response = notification_app.send()
    assert response.status_code == 503 and "PRIVATE" not in response.text
    assert response.headers["cache-control"] == "no-store"


def test_crypto_failure_rolls_back_scripted_transaction(notification_app):
    h = notification_app
    h.app.state.settings = h.settings.model_copy(update={"profile_data_keys": None})
    assert h.send("POST", f"/{EVENT}/retry", body=retry_body()).status_code == 503
    assert h.db.retry_count == 0 and h.db.receipts == {} and h.db.rollbacks == 1


def test_registered_route_budget_only():
    registered = {(next(iter(route.methods)), route.path) for route in router.routes}
    assert registered == {("GET", "/admin/notification-outbox"), ("POST", "/admin/notification-outbox/{id}/retry")}
    source = Path(__file__).parents[1] / "app/main.py"
    assert 'include_router(notification_operations_router, prefix="/api/v1")' in source.read_text()
