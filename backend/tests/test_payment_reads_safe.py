"""Only API-240/evidence reads; actual auth/crypto/storage adapter, scripted SQL."""

import base64
import hashlib
import json
from contextlib import contextmanager
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI
from test_auth import claims, signed
from test_auth import verifier as _verifier
from test_health import ASGIClient

from app.api.auth import AccessError, access_error
from app.api.v1.payments import router
from app.core.config import Settings
from app.core.profile_crypto import encrypt

verifier = _verifier
OID, AID, EID = UUID(int=701), UUID(int=702), UUID(int=703)
ATTEMPTS = f"/api/v1/admin/orders/{OID}/payment-attempts"
EVIDENCE = f"/api/v1/admin/payment-evidence/{EID}"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jcdkAAAAASUVORK5CYII="
)


class Result:
    def __init__(self, value):
        self.value = value

    def one_or_none(self):
        return self.value

    def scalar_one_or_none(self):
        return self.value

    def mappings(self):
        return self

    def all(self):
        return self.value


class Database:
    def __init__(self, settings):
        self.roles = {"finance"}
        self.mfa = True
        self.active = True
        self.email = True
        self.info = {}
        self.calls = []
        self.audits = []
        self.empty = False
        self.missing = False
        account, version = encrypt(settings, AID, "sender_account", "SYNTHETIC_ACCOUNT")
        holder, _ = encrypt(
            settings,
            AID,
            "sender_holder",
            json.dumps({"holder": "Synthetic Person", "transfer_reference": None}),
        )
        self.attempt = {
            "id": AID,
            "state": "under_review",
            "amount": Decimal("19.25"),
            "currency_code": "USD",
            "sender_account_ciphertext": account,
            "sender_holder_ciphertext": holder,
            "sender_key_version": version,
        }
        self.evidence = {
            "id": EID,
            "content_type": "image/png",
            "bytes_size": len(PNG),
            "object_key": "synthetic-evidence",
            "sha256_hex": hashlib.sha256(PNG).hexdigest(),
        }

    @contextmanager
    def transaction(self):
        yield self

    def execute(self, statement, params=None):
        sql = str(statement)
        p = params or {}
        self.calls.append(sql)
        assert not any(
            v in sql.lower()
            for v in [
                "qr_",
                "pair",
                "fulfillment",
                "reconciliation",
                "update ",
                "delete ",
                "for update",
            ]
        ), sql
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
        if "FROM public.payment_attempts" in sql:
            return Result([] if self.empty else [self.attempt])
        if "SELECT id,content_type,bytes_size FROM public.payment_evidence" in sql:
            return Result(
                [{k: self.evidence[k] for k in ["id", "content_type", "bytes_size"]}]
            )
        if "SELECT * FROM public.payment_evidence" in sql:
            return Result(None if self.missing else self.evidence)
        if "INSERT INTO public.audit_events" in sql:
            self.audits.append(p)
            return Result(None)
        raise AssertionError("Unexpected SQL")


class GuardedClient(ASGIClient):
    def request(self, method, path, **kw):
        assert method == "GET" and path in [ATTEMPTS, EVIDENCE], path
        return super().request(method, path, **kw)


@pytest.fixture
def env(verifier):
    provider, private, _, _ = verifier
    settings = Settings(
        _env_file=None,
        profile_data_keys=json.dumps({"1": base64.b64encode(b"p" * 32).decode()}),
        supabase_url="https://storage.test",
        supabase_storage_service_key="synthetic-storage-key",
    )
    db = Database(settings)
    app = FastAPI()
    app.add_exception_handler(AccessError, access_error)
    app.include_router(router, prefix="/api/v1")
    app.state.database = db
    app.state.jwt_verifier = provider
    app.state.settings = settings
    storage = {"data": PNG, "type": "image/png", "status": 200, "calls": []}

    def transport(request):
        assert (
            request.method == "GET"
            and str(request.url)
            == "https://storage.test/storage/v1/object/authenticated/private-payment-evidence/synthetic-evidence"
        )
        storage["calls"].append(True)
        return httpx.Response(
            storage["status"],
            content=storage["data"],
            headers={"content-type": storage["type"]},
        )

    app.state.payment_storage_transport = httpx.MockTransport(transport)

    def headers():
        return {
            "Authorization": "Bearer "
            + signed(private, claims(sub=str(UUID(int=700)), aal="aal2"))
        }

    return GuardedClient(app), db, headers, storage, settings


@pytest.mark.parametrize(
    "roles,status",
    [
        ({"finance"}, 200),
        ({"finance", "operations"}, 200),
        ({"operations"}, 403),
        ({"support"}, 403),
        ({"superadmin"}, 403),
        ({"security_admin"}, 403),
    ],
)
@pytest.mark.parametrize("path", [ATTEMPTS, EVIDENCE])
def test_read_roles(env, roles, status, path):
    c, db, h, _, _ = env
    db.roles = roles
    assert c.get(path, headers=h()).status_code == status


@pytest.mark.parametrize("path", [ATTEMPTS, EVIDENCE])
def test_session_and_mfa(env, path):
    c, db, h, _, _ = env
    assert c.get(path).status_code == 401
    db.mfa = False
    assert c.get(path, headers=h()).status_code == 403
    db.mfa = True
    db.email = False
    assert c.get(path, headers=h()).status_code == 403
    db.email = True
    db.active = False
    assert c.get(path, headers=h()).status_code == 401


def test_attempt_crypto_projection_and_audit(env):
    c, db, h, storage, _ = env
    r = c.get(ATTEMPTS, headers=h())
    assert r.status_code == 200
    a = r.json()["items"][0]
    assert a["currency_code"] == "USD" and a["amount"] == "19.25"
    assert a["sender_account"] == "SYNTHETIC_ACCOUNT"
    assert a["evidence"][0]["id"] == str(EID)
    assert len(db.audits) == 1
    assert storage["calls"] == []
    db.empty = True
    assert c.get(ATTEMPTS, headers=h()).json() == {"items": []}


def test_crypto_unavailable(env):
    c, _db, h, _, settings = env
    settings.profile_data_keys = None
    assert c.get(ATTEMPTS, headers=h()).status_code == 503


def test_private_binary_and_audit(env):
    c, db, h, storage, _ = env
    r = c.get(EVIDENCE, headers=h())
    assert r.status_code == 200
    assert r.content == PNG
    assert r.headers["content-type"] == "image/png"
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["content-security-policy"] == "sandbox"
    assert len(db.audits) == 1 and len(storage["calls"]) == 1
    db.missing = True
    assert c.get(EVIDENCE, headers=h()).status_code == 404


@pytest.mark.parametrize(
    "case,status",
    [
        ("provider", 503),
        ("missing", 409),
        ("type", 422),
        ("hash", 422),
        ("size", 413),
        ("signature", 422),
        ("active_pdf", 422),
    ],
)
def test_evidence_rejects_unsafe_or_unavailable(env, case, status):
    c, db, h, storage, _ = env
    if case == "provider":
        storage["status"] = 500
    elif case == "missing":
        storage["status"] = 404
    elif case == "type":
        storage["type"] = "text/html"
    elif case == "hash":
        db.evidence["sha256_hex"] = "0" * 64
    elif case == "size":
        storage["data"] = b"x" * 5000001
    elif case == "signature":
        storage["data"] = b"not image"
        db.evidence.update(
            bytes_size=len(storage["data"]),
            sha256_hex=hashlib.sha256(storage["data"]).hexdigest(),
        )
    else:
        storage.update(data=b"%PDF-1.4 /JavaScript %%EOF", type="application/pdf")
        db.evidence.update(
            content_type=storage["type"],
            bytes_size=len(storage["data"]),
            sha256_hex=hashlib.sha256(storage["data"]).hexdigest(),
        )
    r = c.get(EVIDENCE, headers=h())
    assert r.status_code == status, r.text
    assert db.audits == []
