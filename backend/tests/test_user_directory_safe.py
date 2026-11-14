"""User directory metadata only; no business mutation or QR fixtures."""

from contextlib import contextmanager
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import FastAPI
from test_auth import claims, signed
from test_auth import verifier as _verifier
from test_health import ASGIClient

from app.api.auth import AccessError, access_error
from app.api.v1.staff_directory import router
from app.core.config import Settings

verifier = _verifier
UID = UUID(int=901)
PATH = "/api/v1/admin/users"


class Result:
    def __init__(self, value):
        self.value = value

    def one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.value

    def scalar_one_or_none(self):
        return self.value

    def __iter__(self):
        return iter(self.value)

    def mappings(self):
        return self

    def all(self):
        return self.value


class Database:
    def __init__(self):
        self.roles = {"security_admin"}
        self.mfa = True
        self.email = True
        self.active = True
        self.info = {}
        self.calls = []
        self.missing = False
        self.state_available = True
        self.user = {
            "user_id": str(UID),
            "registered_at": "2026-10-22T00:00:00Z",
            "email_verified": True,
            "provider_access": "not_banned",
        }

    @contextmanager
    def begin_nested(self):
        yield self

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
                "shipment_pairs",
                "order_pair",
                "tag_pairs",
                "qr_codes",
                "pair_print_qa",
                "order_item_qr_allocations",
                "sr_fulfillment",
                "sr_typed",
                "for update",
                "insert ",
                "update ",
                "delete ",
                "print_artifacts",
                "shipping_snapshot",
                "tracking_reference",
                "sr_lifecycle",
                "user_profiles",
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
        if sql == "SHOW statement_timeout":
            return Result("5s")
        if "sr_staff_account_state" in sql:
            return Result(
                {
                    "status": "ready",
                    "state": "active",
                    "revision": 1,
                    "as_of": "2026-10-23T00:00:00Z",
                }
            )
        if "sr_staff_directory" in sql:
            if p["mode"] == "count":
                return Result(
                    {
                        "as_of": "2026-10-23T00:00:00Z",
                        "definition": "retained_nonanonymous_auth_registrations_v1",
                        "filters": {
                            "user_id": p["uid"],
                            "email_verified": p["verified"],
                            "provider_access": p["access"],
                        },
                        "count": {"value": 0 if self.missing else 1, "is_exact": True},
                    }
                )
            return Result(
                {
                    "as_of": "2026-10-23T00:00:00Z",
                    "items": [] if self.missing else [self.user],
                }
            )
        raise AssertionError("Unexpected metadata SQL")


class GuardedClient(ASGIClient):
    def request(self, method, path, **kw):
        assert method == "GET" and path.split("?")[0] in {
            PATH,
            PATH + "/count",
            PATH + "/" + str(UID),
        }, path
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
    app.state.settings = Settings(_env_file=None, staff_directory_enabled=True)

    def headers():
        return {
            "Authorization": "Bearer "
            + signed(private, claims(sub=str(UUID(int=900)), aal="aal2"))
        }

    return GuardedClient(app), db, headers


@pytest.mark.parametrize(
    "roles,status",
    [
        ({"security_admin"}, 200),
        ({"security_admin", "finance"}, 200),
        ({"operations"}, 403),
        ({"support"}, 403),
        ({"finance"}, 403),
        ({"superadmin"}, 403),
        (set(), 403),
    ],
)
def test_roles(env, roles, status):
    c, db, h = env
    db.roles = roles
    assert c.get(PATH, headers=h()).status_code == status


def test_session_email_mfa(env):
    c, db, h = env
    assert c.get(PATH).status_code == 401
    db.mfa = False
    assert c.get(PATH, headers=h()).status_code == 403
    db.mfa = True
    db.email = False
    assert c.get(PATH, headers=h()).status_code == 403
    db.email = True
    db.active = False
    assert c.get(PATH, headers=h()).status_code == 401


def test_metadata_and_state(env):
    c, _db, h = env
    r = c.get(PATH, headers=h())
    assert r.status_code == 200
    assert set(r.json()["items"][0]) == {
        "user_id",
        "registered_at",
        "email_verified",
        "provider_access",
    }
    d = c.get(PATH + "/" + str(UID) + "?include=account_security", headers=h())
    assert d.status_code == 200
    assert d.json()["application_suspension"]["revision"] == 1
    assert d.json()["application_suspension"]["commands_available"] is False
    assert c.get(PATH + "/count", headers=h()).json()["count"] == {
        "value": 1,
        "is_exact": True,
    }


def test_empty_missing_and_queries(env):
    c, db, h = env
    db.missing = True
    assert c.get(PATH, headers=h()).json()["items"] == []
    assert c.get(PATH + "/" + str(UID), headers=h()).status_code == 404
    for query in [
        "email=x",
        "user_id=bad",
        "include=pair",
        "limit=101",
        "email_verified=yes",
        "kind=suspend",
        "provider_access=active",
        "cursor=invalid!",
    ]:
        assert c.get(PATH + "?" + query, headers=h()).status_code == 422
