"""Known shipment item metadata only; no listing, creation, packing or QR fixture."""

from contextlib import contextmanager
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import FastAPI
from test_auth import claims, signed
from test_auth import verifier as _verifier
from test_health import ASGIClient

from app.api.auth import AccessError, access_error
from app.api.v1.fulfillment import router
from app.core.config import Settings

verifier = _verifier
SID, IID, JID = UUID(int=901), UUID(int=902), UUID(int=903)
PATH = f"/api/v1/admin/shipments/{SID}/items"


class Result:
    def __init__(self, value):
        self.value = value

    def one_or_none(self):
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
        self.roles = {"operations"}
        self.mfa = True
        self.email = True
        self.active = True
        self.info = {}
        self.calls = []
        self.missing = False
        self.model = "single_qr"
        self.items = [
            {
                "logical_item_id": IID,
                "print_job_id": JID,
                "packed_qa_confirmed": False,
                "packed_at": None,
            }
        ]

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
        if "SELECT o.commerce_model FROM public.shipments" in sql:
            return Result([] if self.missing else [{"commerce_model": self.model}])
        if (
            "SELECT logical_item_id,print_job_id,packed_qa_confirmed,packed_at FROM public.shipment_items"
            in sql
        ):
            return Result(self.items)
        raise AssertionError("Unexpected metadata SQL")


class GuardedClient(ASGIClient):
    def request(self, method, path, **kw):
        assert method == "GET" and path == PATH, path
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
            + signed(private, claims(sub=str(UUID(int=900)), aal="aal2"))
        }

    return GuardedClient(app), db, headers


@pytest.mark.parametrize(
    "roles,status",
    [
        ({"operations"}, 200),
        ({"operations", "finance"}, 200),
        ({"finance"}, 403),
        ({"support"}, 403),
        ({"security_admin"}, 403),
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


def test_metadata_only_and_nullable_timestamp(env):
    c, db, h = env
    r = c.get(PATH, headers=h())
    assert r.status_code == 200
    data = r.json()
    assert set(data) == {"commerce_model", "items"}
    assert data["commerce_model"] == "single_qr"
    assert set(data["items"][0]) == {
        "logical_item_id",
        "print_job_id",
        "packed_qa_confirmed",
        "packed_at",
    }
    assert data["items"][0]["packed_at"] is None
    assert len([s for s in db.calls if "FROM public.shipment_items" in s]) == 1


def test_empty_legacy_and_missing(env):
    c, db, h = env
    db.items = []
    assert c.get(PATH, headers=h()).json() == {
        "commerce_model": "single_qr",
        "items": [],
    }
    db.model = "legacy_pair"
    assert c.get(PATH, headers=h()).json() == {
        "commerce_model": "legacy_pair",
        "items": [],
    }
    db.missing = True
    assert c.get(PATH, headers=h()).status_code == 404
