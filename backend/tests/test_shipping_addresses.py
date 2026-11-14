"""5.2A synthetic HTTP/transaction tests; deliberately no installed SQL access."""

import base64
import json
from contextlib import contextmanager
from copy import deepcopy
from threading import RLock
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError
from test_auth import claims, signed
from test_auth import verifier as _verifier
from test_critical_workflow_boundaries import MemoryDatabase, Result
from test_health import ASGIClient

from app.api.v1.checkout import Address, QuoteRequest
from app.api.v1.shipping_addresses import resolve
from app.core.config import Settings
from app.core.profile_crypto import decrypt, encrypt
from app.main import create_app

verifier = _verifier
PATH = "/api/v1/me/shipping-addresses"
ORIGIN = "https://synthetic.test"
ADDRESS = {
    "recipient_name": "Synthetic recipient",
    "phone": "+923000000001",
    "address": "Synthetic street 1",
    "city": "Synthetic city",
    "province": None,
    "postal_code": None,
}


class MemoryAddresses(MemoryDatabase):
    def __init__(self, owner):
        super().__init__(owner, uuid4())
        self.rows, self.books, self.references = {}, {}, set()
        self.lock = RLock()

    @contextmanager
    def transaction(self):
        with self.lock:
            before = deepcopy((self.rows, self.books, self.audit))
            try:
                yield self
                if self.fail_commit:
                    raise OperationalError(
                        "COMMIT", {}, Exception("PRIVATE_COMMIT_CANARY")
                    )
            except BaseException:
                self.rows, self.books, self.audit = before
                raise

    def execute(self, statement, params=None):
        sql, p = str(statement), params or {}
        if "pg_advisory_xact_lock" in sql:
            return Result(None)
        if sql.startswith("SELECT version,default_address_id"):
            return Result(deepcopy(self.books.get(p["actor"])))
        if sql.startswith("SELECT * FROM public.shipping_addresses"):
            rows = [
                r
                for r in self.rows.values()
                if r["customer_user_id"] == p["actor"] and r["is_saved"]
            ]
            return Result(
                deepcopy(next((r for r in rows if r["id"] == p["id"]), None))
                if "id" in p
                else deepcopy(rows)
            )
        if sql.startswith("SELECT count(*) FROM public.shipping_addresses"):
            return Result(
                sum(
                    r["customer_user_id"] == p["actor"] and r["is_saved"]
                    for r in self.rows.values()
                )
            )
        if sql.startswith("SELECT EXISTS("):
            return Result(p["id"] in self.references)
        if sql.startswith("INSERT INTO public.shipping_addresses"):
            self.rows[p["id"]] = {
                "id": p["id"],
                "customer_user_id": p["actor"],
                "is_saved": True,
                "version": 1,
                **{
                    f + "_ciphertext": p[f]
                    for f in ("recipient_name", "phone", "address")
                },
                **{f: p[f] for f in ("city", "province", "postal_code", "key_version")},
            }
            return Result(None)
        if sql.startswith("UPDATE public.shipping_addresses"):
            row = self.rows[p["id"]]
            assert row["customer_user_id"] == p["actor"]
            row["version"] += 1
            if "recipient_name" in p:
                row.update(
                    {
                        f + "_ciphertext": p[f]
                        for f in ("recipient_name", "phone", "address")
                    }
                )
                row.update(
                    {
                        f: p[f]
                        for f in ("city", "province", "postal_code", "key_version")
                    }
                )
            return Result(None)
        if sql.startswith("INSERT INTO public.shipping_address_books"):
            self.books[p["actor"]] = {
                "version": p["version"],
                "default_address_id": p["default"],
            }
            return Result(None)
        if sql.startswith("DELETE FROM public.shipping_addresses"):
            assert self.rows[p["id"]]["customer_user_id"] == p["actor"]
            del self.rows[p["id"]]
            return Result(None)
        return super().execute(statement, params)


@pytest.fixture
def addresses(verifier):
    provider, private, _, _ = verifier
    owner, foreign = uuid4(), uuid4()
    db = MemoryAddresses(owner)
    app = create_app(
        Settings(
            shipping_address_web_origin=ORIGIN,
            profile_data_key_version=1,
            profile_data_keys=json.dumps({"1": base64.b64encode(b"s" * 32).decode()}),
        )
    )
    app.state.database, app.state.jwt_verifier = db, provider
    client = ASGIClient(app)

    def headers(uid=owner, **overrides):
        return {
            "Authorization": "Bearer "
            + signed(private, claims(sub=str(uid), **overrides)),
            "Origin": ORIGIN,
        }

    return client, db, headers, foreign, app


def create(client, headers, version=0, default=False):
    return client.request(
        "POST",
        PATH,
        headers=headers,
        json={**ADDRESS, "expected_book_version": version, "is_default": default},
    )


def patch(client, headers, item, book_version, default=False, **changes):
    return client.request(
        "PATCH",
        PATH + "/" + item["id"],
        headers=headers,
        json={
            "address": {**ADDRESS, **changes},
            "expected_version": item["version"],
            "expected_book_version": book_version,
            "is_default": default,
        },
    )


def test_crud_safe_projection_and_historical_exclusion(addresses):
    client, db, headers, _, _ = addresses
    response = create(client, headers(), default=True)
    assert response.status_code == 201
    assert response.headers["cache-control"] == "private, no-store"
    item = response.json()["item"]
    assert set(item) == {"id", "version", "is_default", *ADDRESS}
    assert item["is_default"] and item["version"] == 1
    row = db.rows[UUID(item["id"])]
    assert b"Synthetic recipient" not in row["recipient_name_ciphertext"]
    historical = deepcopy(row)
    historical.update(id=uuid4(), is_saved=False)
    db.rows[historical["id"]] = historical
    listed = client.get(PATH, headers=headers()).json()
    assert len(listed["items"]) == 1 and listed["book_version"] == 1
    assert (
        patch(client, headers(), item, 1, city="Changed synthetic city").status_code
        == 200
    )
    updated = client.get(PATH, headers=headers()).json()["items"][0]
    assert updated["version"] == 2 and not updated["is_default"]
    deleted = client.request(
        "DELETE",
        PATH + "/" + item["id"] + "?expected_version=2&expected_book_version=2",
        headers=headers(),
    )
    assert deleted.status_code == 204 and not deleted.content
    assert db.rows == {historical["id"]: historical}
    assert all("Synthetic" not in str(a) for a in db.audit)


def test_cross_owner_crud_and_versions(addresses):
    client, _, headers, foreign, _ = addresses
    item = create(client, headers()).json()["item"]
    assert client.get(PATH, headers=headers(foreign)).json()["items"] == []
    assert patch(client, headers(foreign), item, 99).status_code == 404
    response = client.request(
        "DELETE",
        PATH + "/" + item["id"] + "?expected_version=1&expected_book_version=99",
        headers=headers(foreign),
    )
    assert response.status_code == 404 and "Synthetic" not in response.text
    assert patch(client, headers(), item, 0).status_code == 409
    assert patch(client, headers(), {**item, "version": 99}, 1).status_code == 409


@pytest.mark.parametrize("method", ["GET", "POST", "PATCH", "DELETE"])
def test_anonymous_expired_revoked_sessions(addresses, method):
    client, db, headers, _, _ = addresses
    path = PATH if method in ("GET", "POST") else PATH + "/" + str(uuid4())
    if method == "DELETE":
        path += "?expected_version=1&expected_book_version=0"
    body = (
        {**ADDRESS, "expected_book_version": 0}
        if method == "POST"
        else {
            "address": ADDRESS,
            "expected_version": 1,
            "expected_book_version": 0,
            "is_default": False,
        }
    )
    for h in ({}, headers(exp=1)):
        assert client.request(method, path, headers=h, json=body).status_code == 401
    db.active = False
    assert client.request(method, path, headers=headers(), json=body).status_code == 401


def test_origin_validation_and_safe_errors(addresses):
    client, _, headers, _, _ = addresses
    for origin in ("https://foreign.test", ""):
        r = create(client, {**headers(), "Origin": origin})
        assert (
            r.status_code == 403 and r.headers["cache-control"] == "private, no-store"
        )
    r = client.request(
        "POST",
        PATH,
        headers=headers(),
        json={
            **ADDRESS,
            "expected_book_version": True,
            "secret": "PRIVATE_INPUT_CANARY",
        },
    )
    assert r.status_code == 422 and "PRIVATE_INPUT_CANARY" not in r.text


def test_default_selection_stale_competitor_and_no_automatic_reassignment(addresses):
    client, db, headers, _, _ = addresses
    first = create(client, headers(), default=True).json()["item"]
    second = create(client, headers(), 1).json()["item"]
    assert patch(client, headers(), second, 2, True).status_code == 200
    assert patch(client, headers(), first, 2, True).status_code == 409
    book = client.get(PATH, headers=headers()).json()
    assert sum(a["is_default"] for a in book["items"]) == 1
    old = next(a for a in book["items"] if a["id"] == first["id"])
    assert old["version"] == 2
    response = client.request(
        "DELETE",
        PATH + "/" + second["id"] + "?expected_version=2&expected_book_version=3",
        headers=headers(),
    )
    assert response.status_code == 204
    assert not any(
        a["is_default"] for a in client.get(PATH, headers=headers()).json()["items"]
    )
    assert len(db.rows) == 1


@pytest.mark.parametrize(
    "reference_kind", ["order_snapshot", "active_shipment", "terminal_shipment"]
)
def test_references_preserve_rows(addresses, reference_kind):
    client, db, headers, _, _ = addresses
    item = create(client, headers()).json()["item"]
    db.references.add(
        UUID(item["id"])
    )  # all three are intentionally the same deny rule
    before = deepcopy(db.rows)
    assert patch(client, headers(), item, 1).status_code == 409
    assert (
        client.request(
            "DELETE",
            PATH + "/" + item["id"] + "?expected_version=1&expected_book_version=1",
            headers=headers(),
        ).status_code
        == 409
    )
    assert db.rows == before


@pytest.mark.parametrize("failure", ["fail_audit", "fail_commit"])
def test_atomic_rollback_and_safe_failure(addresses, failure):
    client, db, headers, _, _ = addresses
    first = create(client, headers(), default=True).json()["item"]
    before = deepcopy((db.rows, db.books, db.audit))
    setattr(db, failure, True)
    response = create(client, headers(), 1, True)
    assert response.status_code == 503 and "PRIVATE_" not in response.text
    assert (db.rows, db.books, db.audit) == before
    setattr(db, failure, False)
    assert patch(client, headers(), first, 1, True).status_code == 200


def test_saved_quote_resolution_version_ownership_and_frozen_ciphertext(addresses):
    from types import SimpleNamespace

    from fastapi import HTTPException

    from app.api.auth import AccessError

    client, db, headers, foreign, app = addresses
    item = create(client, headers()).json()["item"]
    context = SimpleNamespace(session=db, principal=SimpleNamespace(user_id=db.owner))
    value = resolve(context, app.state.settings, UUID(item["id"]), 1)
    qid, oid = uuid4(), uuid4()
    quote_cipher, version = encrypt(
        app.state.settings, qid, "checkout_address", value.model_dump_json()
    )
    assert (
        patch(client, headers(), item, 1, city="Edited after quote").status_code == 200
    )
    with pytest.raises(HTTPException):
        resolve(context, app.state.settings, UUID(item["id"]), 1)
    with pytest.raises(AccessError):
        resolve(
            SimpleNamespace(session=db, principal=SimpleNamespace(user_id=foreign)),
            app.state.settings,
            UUID(item["id"]),
            2,
        )
    assert (
        client.request(
            "DELETE",
            PATH + "/" + item["id"] + "?expected_version=2&expected_book_version=2",
            headers=headers(),
        ).status_code
        == 204
    )
    frozen = Address.model_validate_json(
        decrypt(app.state.settings, qid, "checkout_address", quote_cipher, version)
    )
    assert frozen.model_dump() == ADDRESS
    historical, v = encrypt(app.state.settings, oid, "shipping_address", frozen.address)
    assert (
        decrypt(app.state.settings, oid, "shipping_address", historical, v)
        == ADDRESS["address"]
    )


def test_quote_dto_requires_exactly_one_source():
    base = {
        "lines": [
            {
                "variant_id": str(uuid4()),
                "quantity": 1,
                "qr_uses": [
                    {
                        "mode": "new_pair",
                        "tag_type": "lost",
                        "copies": 1,
                        "client_pair_group": "synthetic",
                    }
                ],
            }
        ],
        "contact_phone_confirmation": True,
    }
    QuoteRequest(**base, address=ADDRESS)
    QuoteRequest(**base, shipping_address_id=uuid4(), shipping_address_version=1)
    for extra in (
        {},
        {"shipping_address_id": uuid4()},
        {
            "address": ADDRESS,
            "shipping_address_id": uuid4(),
            "shipping_address_version": 1,
        },
    ):
        with pytest.raises(ValidationError):
            QuoteRequest(**base, **extra)


def test_parallel_default_writers_one_wins(addresses):
    from concurrent.futures import ThreadPoolExecutor

    client, _, headers, _, _ = addresses
    first = create(client, headers()).json()["item"]
    second = create(client, headers(), 1).json()["item"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                lambda item: patch(client, headers(), item, 2, True), [first, second]
            )
        )
    assert sorted(r.status_code for r in responses) == [200, 409]
    assert (
        sum(
            item["is_default"]
            for item in client.get(PATH, headers=headers()).json()["items"]
        )
        == 1
    )


def test_quote_http_freezes_selected_version_and_historical_order(
    addresses, monkeypatch
):
    """Execute real quote/confirm orchestration with only catalog/SQL stand-ins."""
    from datetime import UTC, datetime, timedelta
    from decimal import Decimal

    from app.api.v1 import checkout

    client, db, headers, foreign, app = addresses
    app.state.settings.checkout_enabled = True
    app.state.settings.checkout_shipping_pkr = Decimal("1.00")
    app.state.settings.checkout_tax_pkr = Decimal("0.00")
    item = create(client, headers()).json()["item"]
    quotes, orders, snapshots, receipts = {}, {}, {}, {}
    original = db.execute

    @contextmanager
    def nested():
        yield

    db.begin_nested = nested

    def execute(statement, params=None):
        sql, p = str(statement), params or {}
        if "FROM public.idempotency_records" in sql:
            return Result(receipts.get((p["actor"], p["op"], p["key"])))
        if sql.startswith("INSERT INTO public.idempotency_records"):
            receipts[(p["actor"], p["op"], p["key"])] = {
                "request_hash": p["hash"],
                "response_body_ciphertext": p["cipher"],
                "response_key_version": p["version"],
            }
            return Result(None)
        if sql.startswith("INSERT INTO public.checkout_quotes"):
            expires = datetime.now(UTC) + timedelta(minutes=15)
            quotes[p["id"]] = {
                "id": p["id"],
                "customer_user_id": p["actor"],
                "payload": json.loads(p["payload"]),
                "address_ciphertext": p["cipher"],
                "address_key_version": p["version"],
                "total_pkr": p["total"],
                "subtotal_pkr": p["subtotal"],
                "shipping_pkr": p["shipping"],
                "tax_pkr": p["tax"],
                "currency_code": "PKR",
                "status": "open",
                "expires_at": expires,
            }
            return Result(expires)
        if sql.startswith("SELECT * FROM public.checkout_quotes"):
            row = quotes.get(p["id"])
            return Result(
                row if row and row["customer_user_id"] == p["actor"] else None
            )
        if sql == "SELECT clock_timestamp()":
            return Result(datetime.now(UTC))
        if sql.startswith("INSERT INTO public.orders"):
            orders[p["id"]] = deepcopy(p)
            return Result(None)
        if sql.startswith("INSERT INTO public.order_shipping_snapshots"):
            snapshots[p["order"]] = deepcopy(p)
            return Result(None)
        if (
            sql.startswith("INSERT INTO public.shipping_addresses")
            and "is_saved" not in sql
        ):
            # Historical rows remain excluded from saved-entry projection.
            db.rows[p["id"]] = {
                "id": p["id"],
                "customer_user_id": p["actor"],
                "is_saved": False,
                **deepcopy(p),
            }
            return Result(None)
        if sql.startswith(("UPDATE public.orders", "SET CONSTRAINTS")):
            return Result(None)
        if sql.startswith("UPDATE public.checkout_quotes"):
            quotes[p["id"]]["status"] = "confirmed"
            return Result(None)
        return original(statement, params)

    db.execute = execute
    monkeypatch.setattr(checkout, "catalog_lines", lambda *_: ([], Decimal("10.00"), 0))
    body = {
        "lines": [
            {
                "variant_id": str(uuid4()),
                "quantity": 1,
                "qr_uses": [
                    {
                        "mode": "new_pair",
                        "tag_type": "lost",
                        "copies": 1,
                        "client_pair_group": "synthetic",
                    }
                ],
            }
        ],
        "shipping_address_id": item["id"],
        "shipping_address_version": 1,
        "contact_phone_confirmation": True,
    }
    quote_path = "/api/v1/me/checkout/quotes"

    def quote(h, key):
        return client.request(
            "POST", quote_path, headers={**h, "Idempotency-Key": key}, json=body
        )

    assert quote(headers(foreign), "foreign-quote-key").status_code == 404
    assert (
        quote(
            {**headers(), "Origin": "https://foreign.test"}, "foreign-origin-key"
        ).status_code
        == 403
    )
    response = quote(headers(), "synthetic-quote-key")
    assert response.status_code == 201
    assert response.headers["cache-control"] == "private, no-store"
    assert (
        ADDRESS["address"] not in response.text
        and ADDRESS["recipient_name"] not in response.text
    )
    qid = UUID(response.json()["quote_id"])
    assert "shipping_address_id" not in str(quotes[qid]["payload"])
    assert patch(client, headers(), item, 1, city="After quote city").status_code == 200
    assert quote(headers(), "new-stale-quote-key").status_code == 409
    assert quote(headers(), "synthetic-quote-key").json() == response.json()
    assert (
        client.request(
            "DELETE",
            PATH + "/" + item["id"] + "?expected_version=2&expected_book_version=2",
            headers=headers(),
        ).status_code
        == 204
    )
    confirmed = client.request(
        "POST",
        quote_path + "/" + str(qid) + "/confirm",
        headers={**headers(), "Idempotency-Key": "synthetic-confirm-key"},
        json={"accept_total": "11.00", "accept_currency": "PKR"},
    )
    assert confirmed.status_code == 201
    oid = UUID(confirmed.json()["order_id"])
    snap = snapshots[oid]
    assert snap["city"] == ADDRESS["city"]
    assert (
        decrypt(
            app.state.settings,
            oid,
            "shipping_address",
            snap["address"],
            snap["version"],
        )
        == ADDRESS["address"]
    )
    historical_id = str(snap["id"])
    assert historical_id != item["id"]
    assert client.get(PATH, headers=headers()).json()["items"] == []
    assert (
        patch(client, headers(), {"id": historical_id, "version": 1}, 3).status_code
        == 404
    )
    assert snapshots[oid] == snap and orders[oid]["actor"] == db.owner


def test_unavailable_crypto_rolls_back_without_plaintext(addresses):
    client, db, headers, _, app = addresses
    app.state.settings.profile_data_keys = None
    response = create(client, headers(), default=True)
    assert (
        response.status_code == 503 and ADDRESS["recipient_name"] not in response.text
    )
    assert db.rows == {} and db.books == {} and db.audit == []


def test_corrupt_saved_row_returns_safe_unavailable(addresses):
    client, db, headers, _, _ = addresses
    item = create(client, headers()).json()["item"]
    db.rows[UUID(item["id"])]["city"] = ""
    response = client.get(PATH, headers=headers())
    assert response.status_code == 503
    assert ADDRESS["recipient_name"] not in response.text
    assert response.headers["cache-control"] == "private, no-store"


def test_forward_migration_offline_capture_and_mapping_compilation(monkeypatch):
    """DDL capture only. Does not execute SQL or prove PostgreSQL semantics."""
    import importlib.util
    from pathlib import Path

    from sqlalchemy.dialects import postgresql
    from sqlalchemy.schema import CreateTable

    from app.db.commerce import ShippingAddress, ShippingAddressBook

    source = (
        Path(__file__).parents[1] / "alembic/versions/0023_saved_shipping_addresses.py"
    )
    spec = importlib.util.spec_from_file_location("saved_address_migration", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.down_revision == "0022_privacy_exports"
    captured = []
    monkeypatch.setattr(module.op, "execute", captured.append)
    module.upgrade()
    assert captured == [
        "SET LOCAL lock_timeout='5s'",
        source.with_suffix(".sql").read_text(encoding="utf-8"),
    ]
    with pytest.raises(RuntimeError):
        module.downgrade()
    for model in (ShippingAddress, ShippingAddressBook):
        ddl = str(CreateTable(model.__table__).compile(dialect=postgresql.dialect()))
        assert "version" in ddl
    assert "ON DELETE CASCADE" not in captured[1]
