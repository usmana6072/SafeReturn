"""Independent ASGI/JWT/AEAD checks with orders-only SQL double; not PostgreSQL."""

import base64
import json
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from test_auth import claims, signed
from test_auth import verifier as _verifier
from test_health import ASGIClient

from app.api.auth import AccessError, access_error
from app.api.v1.order_metadata import PATH, install
from app.core.config import Settings

verifier = _verifier


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
        self.active = True
        self.email = True
        self.info = {}
        self.calls = []
        self.revoke = False
        when = datetime.now(UTC) - timedelta(days=1)
        self.rows = [
            {
                "order_id": UUID(int=i),
                "order_number": f"SR-{i}",
                "order_status": "placed",
                "payment_status": "awaiting_transfer",
                "currency_code": "USD" if i == 2 else "PKR",
                "total_amount": Decimal("12.50"),
                "created_at": when,
                "placed_at": None,
            }
            for i in (1, 2, 3)
        ]

    @contextmanager
    def transaction(self):
        yield self

    def execute(self, statement, params=None):
        sql = str(statement)
        p = params or {}
        self.calls.append((sql, p))
        assert not any(
            x in sql.lower()
            for x in [
                "qr_",
                "pair",
                "fulfillment",
                "shipment",
                "payment_attempt",
                "insert ",
                "update ",
                "delete ",
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
        assert "FROM public.orders o" in sql and "SELECT *" not in sql
        rows = [
            r
            for r in self.rows
            if r["created_at"] <= p["as_of"]
            and (p["number"] is None or r["order_number"] == p["number"])
            and (p["status"] is None or r["order_status"] == p["status"])
            and (p["payment"] is None or r["payment_status"] == p["payment"])
            and (p["start"] is None or r["created_at"] >= p["start"])
            and (p["end"] is None or r["created_at"] < p["end"])
        ]
        desc = "ORDER BY o.created_at DESC" in sql
        if p["after"] is not None:
            rows = [
                r
                for r in rows
                if (
                    (r["created_at"], r["order_id"]) < (p["after"], p["ident"])
                    if desc
                    else (r["created_at"], r["order_id"]) > (p["after"], p["ident"])
                )
            ]
        rows = sorted(
            rows, key=lambda r: (r["created_at"], r["order_id"]), reverse=desc
        )[: p["lim"]]
        if self.revoke:
            self.roles = set()
        return Result(rows)


@pytest.fixture
def env(verifier):
    provider, private, _, _ = verifier
    app = FastAPI()
    settings = Settings(
        _env_file=None,
        profile_data_keys=json.dumps({"1": base64.b64encode(b"m" * 32).decode()}),
    )
    db = Database()
    app.state.settings = settings
    app.state.database = db
    app.state.jwt_verifier = provider
    app.add_exception_handler(AccessError, access_error)
    install(app)
    client = ASGIClient(app)

    def headers(actor=None, **kw):
        return {
            "Authorization": "Bearer "
            + signed(private, claims(sub=str(actor or UUID(int=500)), aal="aal2", **kw))
        }

    return client, db, headers, settings


def get(client, path=PATH, **kw):
    assert path.split("?")[0] == PATH, (
        "Only metadata endpoint may be called in these tests"
    )
    return client.get(path, **kw)


@pytest.mark.parametrize(
    "roles,status",
    [
        ({"operations"}, 200),
        ({"finance"}, 200),
        ({"operations", "finance"}, 200),
        ({"support"}, 403),
        ({"security_admin"}, 403),
        ({"superadmin"}, 403),
        (set(), 403),
    ],
)
def test_roles(env, roles, status):
    c, db, h, _ = env
    db.roles = roles
    assert get(c, headers=h()).status_code == status


def test_auth_session_and_final_recheck(env):
    c, db, h, _ = env
    assert get(c).status_code == 401
    for field in ["mfa", "email"]:
        setattr(db, field, False)
        assert get(c, headers=h()).status_code == 403
        setattr(db, field, True)
    db.active = False
    assert get(c, headers=h()).status_code == 401
    db.active = True
    db.revoke = True
    assert get(c, headers=h()).status_code == 403


def test_page_and_currency_snapshot(env):
    c, _db, h, _ = env
    r = get(c, PATH + "?limit=2", headers=h())
    assert r.status_code == 200, r.text
    p = r.json()
    assert [x["order_number"] for x in p["items"]] == ["SR-3", "SR-2"]
    assert p["items"][1]["currency_code"] == "USD"
    assert p["items"][1]["total_amount"] == "12.50"
    assert p["items"][1]["placed_at"] is None
    assert len(p["next_cursor"]) < 2048
    assert set(p["items"][0]) == {
        "order_id",
        "order_number",
        "order_status",
        "payment_status",
        "currency_code",
        "total_amount",
        "created_at",
        "placed_at",
    }
    second = get(c, PATH + "?limit=2&cursor=" + p["next_cursor"], headers=h()).json()
    assert [x["order_number"] for x in second["items"]] == ["SR-1"]
    assert second["next_cursor"] is None
    assert second["as_of"] == p["as_of"]
    assert r.headers["cache-control"] == "private, no-store"


def test_filters_and_empty(env):
    c, _db, h, _ = env
    assert (
        get(c, PATH + "?order_number=SR-2", headers=h()).json()["items"][0][
            "currency_code"
        ]
        == "USD"
    )
    assert get(c, PATH + "?order_number=sr-2", headers=h()).json()["items"] == []
    assert get(c, PATH + "?payment_status=verified", headers=h()).json()["items"] == []
    assert (
        get(c, PATH + "?sort=oldest&limit=1", headers=h()).json()["items"][0][
            "order_number"
        ]
        == "SR-1"
    )


@pytest.mark.parametrize(
    "query",
    [
        "limit=0",
        "limit=01",
        "limit=101",
        "limit=1.5",
        "path=/admin/orders",
        "customer_id=1",
        "fulfillment_status=allocated",
        "order_status=bad",
        "limit=1&limit=2",
        "cursor=bad",
        "created_from=2026-10-23",
        "created_from=2026-10-24T00:00:00Z&created_before=2026-10-23T00:00:00Z",
    ],
)
def test_invalid_queries(env, query):
    c, _, h, _ = env
    assert get(c, PATH + "?" + query, headers=h()).status_code == 422


def test_cursor_actor_filters_tamper_and_expiry(env, monkeypatch):
    c, _db, h, _ = env
    token = get(c, PATH + "?limit=1", headers=h()).json()["next_cursor"]
    for query in [
        "limit=2&cursor=" + token,
        "limit=1&sort=oldest&cursor=" + token,
        "limit=1&cursor=" + token[:-4] + "AAAA",
    ]:
        assert get(c, PATH + "?" + query, headers=h()).status_code == 422
    assert (
        get(c, PATH + "?limit=1&cursor=" + token, headers=h(uuid4())).status_code == 422
    )
    from app.api.v1 import order_metadata as module

    real = module.datetime

    class Future(real):
        @classmethod
        def now(cls, tz=None):
            return real.now(tz) + timedelta(minutes=16)

    monkeypatch.setattr(module, "datetime", Future)
    assert get(c, PATH + "?limit=1&cursor=" + token, headers=h()).status_code == 422


def test_missing_crypto_and_malformed_data(env):
    c, _db, h, settings = env
    settings.profile_data_keys = None
    assert get(c, headers=h()).status_code == 503


def test_response_extra_fields_fail_closed(env):
    c, db, h, _ = env
    db.rows[0]["private"] = "PRIVATE"
    assert get(c, headers=h()).status_code == 503


def test_no_business_writes_or_other_tables(env):
    c, db, h, _ = env
    assert get(c, headers=h()).status_code == 200
    assert all(
        not any(
            s in sql.lower()
            for s in [
                "join ",
                "for update",
                "for share",
                "fulfillment",
                "pair",
                "qr_",
                "insert ",
                "update ",
                "delete ",
            ]
        )
        for sql, _ in db.calls
    )


@pytest.mark.parametrize("value", [Decimal("0.00"), Decimal("9999999999.99")])
def test_decimal_boundaries(env, value):
    c, db, h, _ = env
    for row in db.rows:
        row["total_amount"] = value
    response = get(c, headers=h())
    assert response.status_code == 200
    assert response.json()["items"][0]["total_amount"] == format(value, ".2f")


@pytest.mark.parametrize(
    "field,value",
    [
        ("total_amount", Decimal("NaN")),
        ("total_amount", Decimal("-1.00")),
        ("total_amount", Decimal("0.001")),
        ("currency_code", "pkr"),
        ("created_at", datetime(2026, 1, 1)),
        ("order_number", "bad\x00"),
    ],
)
def test_corrupt_metadata_rejected(env, field, value):
    c, db, h, _ = env
    # A naive timestamp is rejected before the double's comparison to avoid
    # claiming the SQL adapter emulates malformed PostgreSQL timestamp columns.
    if field == "created_at":
        from app.api.v1.order_metadata import utc

        with pytest.raises(ValueError):
            utc(value)
        return
    for row in db.rows:
        row[field] = value
    assert get(c, headers=h()).status_code == 503


def test_body_and_method_rejected_and_openapi_registered(env):
    c, _db, h, _ = env
    assert c.request("GET", PATH, content=b"{}", headers=h()).status_code == 422
    assert c.post(PATH, json={}, headers=h()).status_code == 405
    from app.main import create_app

    app = create_app(Settings(_env_file=None))
    spec = app.openapi()["paths"][PATH]["get"]
    assert spec["operationId"] == "admin_order_metadata_list"
    assert len(spec["parameters"]) == 8


def test_microsecond_cursor_and_date_boundaries(env):
    c, db, h, _ = env
    exact = datetime.now(UTC) - timedelta(days=2)
    exact = exact.replace(microsecond=123456)
    for row in db.rows:
        row["created_at"] = exact
    query = "?limit=1&sort=oldest&created_from=" + exact.isoformat().replace(
        "+00:00", "Z"
    )
    first = get(c, PATH + query, headers=h()).json()
    assert first["items"][0]["created_at"].endswith("123456Z")
    second = get(
        c, PATH + query + "&cursor=" + first["next_cursor"], headers=h()
    ).json()
    assert second["items"][0]["order_number"] == "SR-2"
    assert (
        get(
            c,
            PATH + "?created_before=" + exact.isoformat().replace("+00:00", "Z"),
            headers=h(),
        ).json()["items"]
        == []
    )
