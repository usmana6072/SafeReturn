"""Only233/235 metadata reads, real auth and scripted SQL; no production action."""

from contextlib import contextmanager
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import FastAPI
from test_auth import claims, signed
from test_auth import verifier as _verifier
from test_health import ASGIClient

from app.api.auth import AccessError, access_error
from app.api.v1.printing import router
from app.core.config import Settings

verifier = _verifier
JID, OID, AID = UUID(int=801), UUID(int=802), UUID(int=803)
DETAIL = f"/api/v1/admin/print-jobs/{JID}"
HISTORY = f"/api/v1/admin/orders/{OID}/print-jobs"


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
    def __init__(self):
        self.roles = {"operations"}
        self.mfa = True
        self.email = True
        self.active = True
        self.info = {}
        self.calls = []
        self.missing = False
        self.empty = False

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
                "order_pair",
                "tag_pairs",
                "qr_codes",
                "pair_print_qa",
                "payload_ciphertext",
                "object_key",
                "bucket",
                "durable_jobs",
                "for update",
                "for share",
                "insert ",
                "update ",
                "delete ",
                "sr_fulfillment",
                "sr_template_order",
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
        base = {
            "id": JID,
            "job_revision": 1,
            "status": "ready",
            "template_fingerprint": "a" * 64,
            "failure_code": "PRIVATE_PROVIDER_CANARY",
        }
        if "FROM public.print_jobs WHERE order_id" in sql:
            return Result([] if self.empty else [base])
        if "FROM public.print_jobs WHERE id" in sql:
            return Result(
                None if self.missing else dict(base, order_id=OID, attempt_count=2)
            )
        if "FROM public.print_artifacts WHERE print_job_id" in sql:
            return Result(
                [
                    {
                        "id": AID,
                        "format": "pdf",
                        "size_bytes": 1234,
                        "sha256_hex": "b" * 64,
                        "deleted_at": None,
                    }
                ]
            )
        if "FROM public.order_logical_items" in sql:
            return Result(
                [
                    {
                        "id": UUID(int=804),
                        "product_name_snapshot": "Synthetic purchase name",
                        "qr_type_snapshot": "lost",
                    }
                ]
            )
        raise AssertionError("Unexpected metadata SQL")


class GuardedClient(ASGIClient):
    def request(self, method, path, **kw):
        assert method == "GET" and path in [DETAIL, HISTORY], path
        return super().request(method, path, **kw)


@pytest.fixture
def env(verifier):
    provider, private, _, _ = verifier
    db = Database()
    app = FastAPI()
    app.add_exception_handler(AccessError, access_error)
    app.include_router(router, prefix="/api/v1")
    app.state.database = db
    app.state.jwt_verifier = provider
    app.state.settings = Settings(_env_file=None)

    def headers():
        return {
            "Authorization": "Bearer "
            + signed(private, claims(sub=str(UUID(int=800)), aal="aal2"))
        }

    return GuardedClient(app), db, headers


@pytest.mark.parametrize(
    "roles,status",
    [
        ({"operations"}, 200),
        ({"operations", "finance"}, 200),
        ({"finance"}, 403),
        ({"superadmin"}, 403),
        ({"security_admin"}, 403),
        ({"support"}, 403),
    ],
)
@pytest.mark.parametrize("path", [DETAIL, HISTORY])
def test_roles(env, roles, status, path):
    c, db, h = env
    db.roles = roles
    assert c.get(path, headers=h()).status_code == status


@pytest.mark.parametrize("path", [DETAIL, HISTORY])
def test_session_email_mfa(env, path):
    c, db, h = env
    assert c.get(path).status_code == 401
    db.mfa = False
    assert c.get(path, headers=h()).status_code == 403
    db.mfa = True
    db.email = False
    assert c.get(path, headers=h()).status_code == 403
    db.email = True
    db.active = False
    assert c.get(path, headers=h()).status_code == 401


def test_detail_is_metadata_only(env):
    c, db, h = env
    r = c.get(DETAIL, headers=h())
    assert r.status_code == 200
    r = r.json()
    assert r["template_fingerprint"] == "a" * 64
    assert r["artifacts"][0]["format"] == "pdf"
    assert set(r["artifacts"][0]) == {
        "id",
        "format",
        "size_bytes",
        "sha256_hex",
        "deleted_at",
    }
    assert set(r) == {
        "id",
        "order_id",
        "job_revision",
        "status",
        "template_fingerprint",
        "attempt_count",
        "failure_code",
        "artifacts",
        "inspection_items",
    }
    assert all("SELECT *" not in sql for sql in db.calls)


def test_missing_and_empty(env):
    c, db, h = env
    db.missing = True
    assert c.get(DETAIL, headers=h()).status_code == 404
    db.empty = True
    assert c.get(HISTORY, headers=h()).json() == {"items": []}


def test_order_history_no_other_services(env):
    c, db, h = env
    r = c.get(HISTORY, headers=h())
    assert r.status_code == 200
    assert set(r.json()["items"][0]) == {
        "id",
        "job_revision",
        "status",
        "template_fingerprint",
        "failure_code",
    }
    assert not any(
        "public.orders" in sql or "print_artifacts" in sql for sql in db.calls
    )
