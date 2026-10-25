"""Only new metadata ASGI routes, real JWT/AEAD, scripted SQL; no live DB/setup."""

import asyncio
import base64
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
from pydantic import SecretStr
from sqlalchemy.exc import OperationalError

from app.api.auth import AccessError, access_error
from app.api.v1.support_metadata import HEADERS, PATH, install
from app.core.auth import JWTVerifier
from app.core.config import Settings

ACTOR = UUID(int=999)
DENIED = (
    "tag_pairs",
    "order_pair_units",
    "qr_codes",
    "shipment",
    "allocation",
    "reservation",
    "sr_support_context",
    "sr_support_change",
    "sr_financial",
    "for update",
    "for share",
    "description_ciphertext",
    "note_ciphertext",
    "opened_by_user_id",
    "payment_",
)


class Result:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value

    def scalar_one_or_none(self):
        return self.value

    def one_or_none(self):
        return self.value

    def mappings(self):
        return self

    def all(self):
        return self.value


class Database:
    def __init__(self):
        self.info, self.calls, self.audits = {}, [], []
        self.roles, self.mfa, self.email, self.active = {"support"}, True, True, True
        self.policy_available, self.fail, self.revoke = True, False, False
        self.committed, self.rolled_back = 0, 0
        self.rows = [
            {
                "case_id": UUID(int=i),
                "case_type": "other",
                "status": "open",
                "priority": "normal",
                "case_revision": 4,
                "created_at": datetime(2026, 1, 1, tzinfo=UTC),
                "owner": ACTOR if i in (1, 2) else None,
                "readable": True,
            }
            for i in range(1, 6)
        ]
        self.rows[-1]["owner"] = UUID(int=444)
        self.rows[-2]["readable"] = False
        self.events = [
            {
                "event_id": str(UUID(int=100 + i)),
                "case_revision": i,
                "event_type": "updated",
                "from_status": "open",
                "to_status": "open",
                "priority": "normal",
                "created_at": "2026-01-01T00:00:00Z",
            }
            for i in (1, 3)
        ]

    @contextmanager
    def transaction(self):
        count = len(self.audits)
        try:
            yield self
            self.committed += 1
        except Exception:
            del self.audits[count:]
            self.rolled_back += 1
            raise

    def execute(self, statement, params=None):
        sql, p = str(statement), params or {}
        self.calls.append((sql, p))
        assert not any(term in sql.lower() for term in DENIED), sql
        assert "select *" not in sql.lower()
        if "SET LOCAL ROLE" in sql or "set_config(" in sql:
            return Result(None)
        if "sr_account_session_state" in sql:
            return Result(
                SimpleNamespace(email_verified=self.email, mfa_active=self.mfa)
                if self.active
                else None
            )
        if "FROM public.staff_roles" in sql:
            return Result(1 if self.roles.intersection(p["roles"]) else None)
        if "to_regprocedure" in sql:
            return Result(self.policy_available)
        if "INSERT INTO public.audit_events" in sql:
            assert set(json.loads(p["safe"])).issubset(
                {
                    "from_status",
                    "to_status",
                    "reason_code",
                    "version",
                    "event_id",
                    "outcome",
                }
            )
            assert p["action"] in (
                "support.metadata.list",
                "support.metadata.read",
                "support.metadata.history.read",
            )
            self.audits.append(p)
            if self.revoke:
                self.roles.clear()
            return Result(None)
        assert (
            "FROM public.support_cases c" in sql
            and "sr_abuse_case_readable(c.id)" in sql
        )
        if self.fail:
            raise OperationalError("hidden", {}, Exception("secret"))
        rows = [
            r
            for r in self.rows
            if r["readable"] and (r["owner"] is None or r["owner"] == p["actor"])
        ]
        if p.get("case_id") is not None:
            rows = [r for r in rows if r["case_id"] == p["case_id"]]
        if "jsonb_agg" in sql:
            assert "c.assigned_staff_id=:actor" in sql
            rows = [r for r in rows if r["owner"] == p["actor"]]
            if not rows:
                return Result(None)
            r = rows[0]
            events = [e for e in self.events if e["case_revision"] < p["before"]]
            return Result(
                {
                    "case_id": r["case_id"],
                    "case_revision": r["case_revision"],
                    "items": sorted(
                        events, key=lambda e: e["case_revision"], reverse=True
                    )[: p["lim"]],
                }
            )
        if "ORDER BY c.created_at" in sql:
            assert "(c.assigned_staff_id IS NULL OR c.assigned_staff_id=:actor)" in sql
            for field in ("case_type", "status", "priority"):
                rows = [r for r in rows if p[field] is None or r[field] == p[field]]
            rows = [
                r
                for r in rows
                if p["queue"] == "all"
                or (p["queue"] == "mine" and r["owner"] == ACTOR)
                or (p["queue"] == "unassigned" and r["owner"] is None)
            ]
            if p["before_time"] is not None:
                rows = [
                    r
                    for r in rows
                    if (r["created_at"], r["case_id"])
                    < (p["before_time"], p["before_id"])
                ]
            rows = sorted(
                rows, key=lambda r: (r["created_at"], r["case_id"]), reverse=True
            )[: p["lim"]]
        items = [
            {
                **{k: v for k, v in r.items() if k not in ("owner", "readable")},
                "assignment": "mine" if r["owner"] == p["actor"] else "unassigned",
                "assigned_to_me": r["owner"] == p["actor"],
            }
            for r in rows
        ]
        return Result(
            items if "ORDER BY c.created_at" in sql else items[0] if items else None
        )


@pytest.fixture
def harness():
    private = ec.generate_private_key(ec.SECP256R1())
    jwk = json.loads(
        jwt.algorithms.get_default_algorithms()["ES256"].to_jwk(private.public_key())
    )
    jwk.update(kid="synthetic", alg="ES256", use="sig")
    settings = Settings(
        _env_file=None,
        supabase_url="https://metadata.invalid",
        profile_data_keys=SecretStr(
            json.dumps({"1": base64.b64encode(b"x" * 32).decode()})
        ),
    )

    def provider(request):
        assert (
            str(request.url) == "https://metadata.invalid/auth/v1/.well-known/jwks.json"
        )
        return httpx.Response(200, json={"keys": [jwk]})

    verifier = JWTVerifier(settings, transport=httpx.MockTransport(provider))
    app, db = FastAPI(), Database()
    app.add_exception_handler(AccessError, access_error)
    app.state.settings, app.state.database, app.state.jwt_verifier = (
        settings,
        db,
        verifier,
    )
    install(app)

    def token(**changes):
        payload = {
            "iss": "https://metadata.invalid/auth/v1",
            "aud": "authenticated",
            "sub": str(ACTOR),
            "session_id": str(UUID(int=888)),
            "role": "authenticated",
            "aal": "aal2",
            "is_anonymous": False,
            "iat": int(time.time()) - 1,
            "exp": int(time.time()) + 300,
        }
        payload.update(changes)
        return jwt.encode(
            payload, private, algorithm="ES256", headers={"kid": "synthetic"}
        )

    def get(path="", auth=True, method="GET", **kwargs):
        # Deny before dispatch: tests must never call excluded/legacy APIs.
        assert path == "" or path.startswith(("/", "?"))
        assert "support-cases" not in path and "/api/" not in path

        async def send():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="https://isolated.invalid",
            ) as client:
                return await client.request(
                    method,
                    PATH + path,
                    headers={
                        "Authorization": "Bearer "
                        + (auth if isinstance(auth, str) else token())
                    }
                    if auth
                    else {},
                    **kwargs,
                )

        response = asyncio.run(send())
        for k, v in HEADERS.items():
            assert response.headers[k] == v
        return response

    yield SimpleNamespace(db=db, get=get, token=token, app=app)
    verifier.close()


def test_list_projection_pagination_and_audit(harness):
    h = harness
    a = h.get("?limit=1").json()
    assert a["items"][0]["case_id"] == str(UUID(int=3))
    assert set(a) == {"as_of", "items", "next_cursor"}
    assert set(a["items"][0]) == {
        "case_id",
        "case_type",
        "status",
        "priority",
        "case_revision",
        "created_at",
        "assignment",
        "assigned_to_me",
    }
    b = h.get("?limit=1&cursor=" + a["next_cursor"]).json()
    c = h.get("?limit=1&cursor=" + b["next_cursor"]).json()
    assert [b["items"][0]["case_id"], c["items"][0]["case_id"]] == [
        str(UUID(int=2)),
        str(UUID(int=1)),
    ]
    assert c["next_cursor"] is None
    assert len(h.db.audits) == 3
    assert all("secret" not in json.dumps(audit, default=str) for audit in h.db.audits)


@pytest.mark.parametrize(
    "query,expected",
    [
        ("queue=mine", 2),
        ("queue=unassigned", 1),
        ("priority=high", 0),
        ("case_type=payment", 0),
        ("status=closed", 0),
        ("case_id=" + str(UUID(int=1)), 1),
    ],
)
def test_filters(harness, query, expected):
    r = harness.get("?" + query)
    assert r.status_code == 200
    assert len(r.json()["items"]) == expected


@pytest.mark.parametrize(
    "query,status",
    [
        ("search=secret", 400),
        ("limit=1&limit=2", 400),
        ("limit=0", 422),
        ("limit=101", 422),
        ("limit=true", 422),
        ("queue=everyone", 422),
        ("status=unknown", 422),
        ("priority=", 422),
        ("case_id=bad", 422),
        ("cursor=broken", 422),
    ],
)
def test_invalid_queries_are_redacted(harness, query, status):
    r = harness.get("?" + query)
    assert r.status_code == status
    assert set(r.json()["error"]) == {"code", "request_id"}
    assert "secret" not in r.text
    assert not harness.db.audits


def test_cursor_binding_and_tampering(harness):
    h = harness
    token = h.get("?limit=1").json()["next_cursor"]
    assert h.get("?queue=mine&cursor=" + token).status_code == 422
    assert (
        h.get("?cursor=" + token, auth=h.token(sub=str(UUID(int=998)))).status_code
        == 422
    )
    assert h.get("/" + str(UUID(int=1)) + "/history?cursor=" + token).status_code == 422
    replacement = "A" if token[-8] != "A" else "B"
    assert h.get("?cursor=" + token[:-8] + replacement + token[-7:]).status_code == 422


@pytest.mark.parametrize(
    "case_id,status", [(1, 200), (3, 200), (4, 404), (5, 404), (99, 404)]
)
def test_detail_scope_and_content_blocked(harness, case_id, status):
    r = harness.get("/" + str(UUID(int=case_id)))
    assert r.status_code == status
    if status == 200:
        assert r.json()["content_available"] is False
        assert set(r.json()) == {
            "case_id",
            "case_type",
            "status",
            "priority",
            "case_revision",
            "created_at",
            "assignment",
            "assigned_to_me",
            "content_available",
        }


def test_history_order_cursor_gaps_and_stale_revision(harness):
    h = harness
    path = "/" + str(UUID(int=1)) + "/history"
    a = h.get(path + "?limit=1").json()
    assert a["items"][0]["case_revision"] == 3
    assert set(a["items"][0]) == {
        "event_id",
        "case_revision",
        "event_type",
        "from_status",
        "to_status",
        "priority",
        "created_at",
    }
    b = h.get(path + "?limit=1&cursor=" + a["next_cursor"]).json()
    assert b["items"][0]["case_revision"] == 1 and b["next_cursor"] is None
    h.db.rows[0]["case_revision"] += 1
    assert h.get(path + "?cursor=" + a["next_cursor"]).status_code == 409


@pytest.mark.parametrize("case_id", [3, 4, 5, 99])
def test_history_requires_own_assignment(harness, case_id):
    assert harness.get("/" + str(UUID(int=case_id)) + "/history").status_code == 404


@pytest.mark.parametrize(
    "field,value,status",
    [
        ("roles", {"finance"}, 403),
        ("roles", {"superadmin"}, 403),
        ("roles", {"security_admin"}, 403),
        ("mfa", False, 403),
        ("email", False, 403),
        ("active", False, 401),
        ("policy_available", False, 503),
        ("fail", True, 503),
    ],
)
def test_security_and_dependency_denials(harness, field, value, status):
    setattr(harness.db, field, value)
    assert harness.get().status_code == status
    assert not harness.db.audits


def test_signed_mfa_authentication_and_recheck(harness):
    h = harness
    assert h.get(auth=False).status_code == 401
    assert h.get(auth="invalid").status_code == 401
    assert h.get(auth=h.token(aal="aal1")).status_code == 403
    h.db.revoke = True
    assert h.get().status_code == 403
    assert h.db.rolled_back and not h.db.audits


def test_validation_unavailable_and_unimplemented_content(harness):
    h = harness
    assert h.get("/bad-id").status_code == 422
    assert h.get("/" + str(UUID(int=1)) + "?unknown=secret").status_code == 400
    assert h.get("/" + str(UUID(int=1)) + "/content").status_code == 404
    assert h.get(method="POST", json={"note": "secret"}).status_code == 405
    h.db.rows[0]["case_revision"] = 0
    assert h.get("/" + str(UUID(int=1))).status_code == 503
    assert not h.db.audits


def test_missing_crypto_and_malformed_history_fail_closed(harness):
    h = harness
    h.app.state.settings.profile_data_keys = None
    assert h.get("?limit=1").status_code == 503
    assert not h.db.audits
    h.db.events[0]["raw_note"] = "secret"
    assert h.get("/" + str(UUID(int=1)) + "/history").status_code == 503


def test_registration_schemas_and_source_isolation(harness):
    schema = harness.app.openapi()
    paths = {path for path in schema["paths"] if path.startswith(PATH)}
    assert paths == {PATH, PATH + "/{case_id}", PATH + "/{case_id}/history"}
    assert {p["name"] for p in schema["paths"][PATH]["get"]["parameters"]} == {
        "limit",
        "cursor",
        "case_id",
        "case_type",
        "status",
        "priority",
        "queue",
    }
    assert all(set(schema["paths"][p]) == {"get"} for p in paths)
    root = Path(__file__).resolve().parents[2]
    source = (root / "backend/app/services/support_metadata.py").read_text()
    assert not any(term in source.lower() for term in DENIED)
    assert "from app.api.v1" not in source
    main = (root / "backend/app/main.py").read_text()
    assert 'application.include_router(support_cases_router, prefix="/api/v1")' in main
    assert "install_financial_disputes(application)" in main
    assert "install_order_metadata(application)" in main
    assert "install_support_metadata(application)" in main


def test_policy_rechecked_on_continuation_and_no_fabricated_history(harness):
    h = harness
    cursor = h.get("?limit=1").json()["next_cursor"]
    h.db.rows[1]["readable"] = False
    page = h.get("?limit=1&cursor=" + cursor).json()
    assert [r["case_id"] for r in page["items"]] == [str(UUID(int=1))]
    h.db.events.clear()
    assert h.get("/" + str(UUID(int=1)) + "/history").json()["items"] == []


def test_expired_jwt_and_get_body_rejected(harness):
    h = harness
    assert h.get(auth=h.token(exp=int(time.time()) - 600)).status_code == 401
    assert h.get(content=b"private").status_code == 400
    assert not h.db.audits


def test_timestamp_validation_and_normalization(harness):
    h = harness
    h.db.rows[0]["created_at"] = datetime.fromisoformat("2026-01-01T05:00:00+05:00")
    assert h.get("/" + str(UUID(int=1))).json()["created_at"] == "2026-01-01T00:00:00Z"
    h.db.rows[0]["created_at"] = datetime(2026, 1, 1)
    assert h.get("/" + str(UUID(int=1))).status_code == 503


def test_history_includes_maximum_revision(harness):
    h = harness
    h.db.rows[0]["case_revision"] = 2147483647
    h.db.events[0]["case_revision"] = 2147483647
    r = h.get("/" + str(UUID(int=1)) + "/history?limit=1")
    assert r.status_code == 200
    assert r.json()["items"][0]["case_revision"] == 2147483647
