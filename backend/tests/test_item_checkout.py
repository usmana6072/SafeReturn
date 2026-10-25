"""Phase 4 contracts and orchestration against synthetic records, never live DB."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.auth import AccessError
from app.api.v1 import item_checkout as api

P, V1, V2, ACTOR = (UUID(int=n) for n in (10, 1, 2, 100))
ADDRESS = {
    "recipient_name": "Synthetic",
    "phone": "+923001234567",
    "address": "Synthetic street",
    "city": "Lahore",
}
INSTRUCTIONS = {
    "version": "synthetic-v1",
    "bank_name": "Synthetic bank",
    "account_title": "Synthetic payee",
    "account_number": "SYNTHETIC",
    "raast_id": "SYNTHETIC",
    "instructions_en": "Synthetic instructions",
    "instructions_ur": "Synthetic instructions",
    "currency_code": "PKR",
}


def item(pid=P, sizes=((V1, 2), (V2, 3)), group=None):
    return api.Item(
        product_id=pid,
        identity_group=group,
        sizes=[{"variant_id": vid, "copies": qty} for vid, qty in sizes],
    )


def request(**changes):
    return api.ItemQuoteRequest.model_validate(
        {
            "commerce_model": "single_qr",
            "items": [item().model_dump()],
            "address": ADDRESS,
            "contact_phone_confirmation": True,
            **changes,
        }
    )


@pytest.fixture
def setup(monkeypatch):
    session = MagicMock()
    ctx = SimpleNamespace(session=session, principal=SimpleNamespace(user_id=ACTOR))
    settings = SimpleNamespace(
        checkout_shipping_pkr=Decimal("50.00"),
        checkout_tax_pkr=Decimal("2.50"),
        profile_data_key_version=1,
    )
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=settings)))
    rows = [
        {
            "id": str(vid),
            "product_id": str(P),
            "qr_type": "lost",
            "price_per_copy": "12.30",
            "max_order_copies": 5,
            "product_name": "Sticker",
            "product_version": 1,
            "catalog_version": 1,
            "name": str(mm) + " mm",
            "size_mm": str(mm),
            "sku": "SIZE-" + str(mm),
            "material": "Vinyl",
        }
        for vid, mm in ((V1, 35), (V2, 45))
    ]
    session.execute.return_value.scalar_one.return_value = rows
    monkeypatch.setattr(
        api,
        "resolve",
        lambda session, line: [
            {
                "revision_id": str(UUID(int=90)),
                "variant_id": line["variant_id"],
                "tag_type": "lost",
                "content": {"approved": True},
            }
        ],
    )
    return ctx, req, settings, rows


def test_default_merge_is_product_not_size():
    result = api.normalize([item(sizes=((V1, 2),)), item(sizes=((V1, 1), (V2, 4)))])
    assert len(result) == 1
    assert [size["copies"] for size in result[0]["sizes"]] == [3, 4]


def test_explicit_identity_groups_stay_distinct():
    assert len(api.normalize([item(), item(group="second"), item(group="third")])) == 3


def test_multi_size_price_is_authoritative_and_exact(setup):
    ctx, _, settings, _ = setup
    snapshots, subtotal = api.snapshots(ctx, [item()], settings)
    assert subtotal == Decimal("61.50")
    assert len(snapshots) == 1
    assert snapshots[0]["unit_price"] == "12.30"
    assert snapshots[0]["quantity"] == 5
    assert [size["copies"] for size in snapshots[0]["sizes"]] == [2, 3]
    assert "registry_specs" not in repr(api.public_items(snapshots))
    assert "public_token" not in repr(snapshots)


def test_merge_cannot_bypass_combined_copy_limit(setup):
    ctx, _, settings, _ = setup
    with pytest.raises(HTTPException, match="422") as error:
        api.snapshots(ctx, [item(), item(sizes=((V1, 1),))], settings)
    assert error.value.detail["code"] == "MAX_ORDER_COPIES_EXCEEDED"


def test_separate_identities_have_independent_limits(setup):
    ctx, _, settings, _ = setup
    snapshots, subtotal = api.snapshots(ctx, [item(), item(group="separate")], settings)
    assert len(snapshots) == 2 and subtotal == Decimal("123.00")


def test_multiple_products_and_types_need_no_pair(setup, monkeypatch):
    ctx, _, settings, rows = setup
    other_pid, other_vid = UUID(int=11), UUID(int=3)
    rows.append(
        {
            **rows[0],
            "id": str(other_vid),
            "product_id": str(other_pid),
            "qr_type": "ice",
            "price_per_copy": "3.75",
        }
    )
    monkeypatch.setattr(
        api,
        "resolve",
        lambda session, line: [
            {"tag_type": "ice" if line["variant_id"] == str(other_vid) else "lost"}
        ],
    )
    snapshots, subtotal = api.snapshots(
        ctx, [item(), item(pid=other_pid, sizes=((other_vid, 4),))], settings
    )
    assert subtotal == Decimal("76.50")
    assert {i["qr_type"] for i in snapshots} == {"lost", "ice"}


@pytest.mark.parametrize("level", ["request", "item", "size"])
@pytest.mark.parametrize(
    "field", ["price_per_copy", "unit_price", "subtotal_pkr", "qr_type", "public_token"]
)
def test_customer_cannot_supply_price_type_or_identity(level, field):
    payload = {
        "commerce_model": "single_qr",
        "items": [item().model_dump(mode="json")],
        "address": ADDRESS,
        "contact_phone_confirmation": True,
    }
    target = (
        payload
        if level == "request"
        else payload["items"][0]
        if level == "item"
        else payload["items"][0]["sizes"][0]
    )
    target[field] = "0.01"
    with pytest.raises(ValidationError):
        api.ItemQuoteRequest.model_validate(payload)


@pytest.mark.parametrize("qty", [True, "2", 0, -1, 1.5, 101])
def test_copy_counts_are_strict(qty):
    with pytest.raises(ValidationError):
        item(sizes=((V1, qty),))


@pytest.mark.parametrize(
    "changes",
    [
        {"contact_phone_confirmation": False},
        {"address": None},
        {"shipping_address_id": str(P)},
        {"lines": []},
        {"commerce_model": "legacy_pair"},
    ],
)
def test_delivery_and_version_contract(changes):
    with pytest.raises(ValidationError):
        request(**changes)


@pytest.mark.parametrize("change", ["missing", "wrong_product", "unpriced"])
def test_unavailable_variants_and_no_price_fallback(setup, change):
    ctx, _, settings, rows = setup
    if change == "missing":
        rows.pop()
    elif change == "wrong_product":
        rows[0]["product_id"] = str(UUID(int=99))
    else:
        rows[0]["price_per_copy"] = None
    with pytest.raises(HTTPException):
        api.snapshots(ctx, [item()], settings)


@pytest.mark.parametrize("specs", [None, [], [{"tag_type": "ice"}]])
def test_matching_type_approved_snapshot_required(setup, monkeypatch, specs):
    ctx, _, settings, _ = setup
    monkeypatch.setattr(api, "resolve", lambda *args: specs)
    with pytest.raises(HTTPException):
        api.snapshots(ctx, [item()], settings)


def test_price_or_version_change_invalidates_quote(setup, monkeypatch):
    ctx, _, settings, rows = setup
    snapshots, _ = api.snapshots(ctx, [item()], settings)
    rows[0]["price_per_copy"] = "13.00"
    rows[1]["price_per_copy"] = "13.00"
    with pytest.raises(HTTPException) as error:
        api.revalidate(ctx, {"items": snapshots}, settings)
    assert error.value.detail["code"] == "QUOTE_STALE"


def test_release_gate_is_fail_closed(setup):
    ctx, _, _, _ = setup
    ctx.session.execute.return_value.scalar_one.return_value = False
    with pytest.raises(HTTPException) as error:
        api.admission(ctx.session)
    assert error.value.status_code == 503


def confirmation(setup, monkeypatch, **changes):
    ctx, req, settings, _ = setup
    snapshots, subtotal = api.snapshots(ctx, [item()], settings)
    now = datetime.now(UTC)
    quote = {
        "commerce_model": "single_qr",
        "status": "open",
        "expires_at": now + timedelta(minutes=10),
        "total_pkr": subtotal + Decimal("52.50"),
        "subtotal_pkr": subtotal,
        "shipping_pkr": Decimal(50),
        "tax_pkr": Decimal("2.50"),
        "currency_code": "PKR",
        "payload": {"items": snapshots, "payment_instructions": INSTRUCTIONS},
        "address_ciphertext": b"synthetic",
        "address_key_version": 1,
        **changes,
    }
    statements = []

    def execute(statement, params=None):
        sql = str(statement)
        statements.append((sql, params))
        result = MagicMock()
        result.mappings.return_value.one_or_none.return_value = quote
        result.scalar_one.return_value = (
            INSTRUCTIONS if "sr_checkout_payment_instructions" in sql else now
        )
        return result

    ctx.session.execute.side_effect = execute
    monkeypatch.setattr(api, "admission", lambda *args: None)
    monkeypatch.setattr(api, "revalidate", lambda *args: None)
    monkeypatch.setattr(api, "decrypt", lambda *args: __import__("json").dumps(ADDRESS))
    monkeypatch.setattr(api, "encrypt", lambda *args: (b"synthetic-cipher", 1))
    monkeypatch.setattr(
        api, "record", lambda ctx, req, op, payload, work: work(settings)[0]
    )
    return ctx, req, quote, statements


def test_confirmation_snapshots_without_any_allocation(setup, monkeypatch):
    ctx, req, quote, statements = confirmation(setup, monkeypatch)
    result = api.confirm_quote(
        UUID(int=30),
        api.ConfirmRequest(accept_total=str(quote["total_pkr"]), accept_currency="PKR"),
        ctx,
        req,
    )
    assert (
        result["payment_status"] == "awaiting_transfer"
        and result["identity_count"] == 1
    )
    assert (
        sum("INSERT INTO public.order_logical_items" in sql for sql, _ in statements)
        == 1
    )
    assert (
        sum("INSERT INTO public.order_item_sizes" in sql for sql, _ in statements) == 2
    )
    assert not any(
        word in sql
        for sql, _ in statements
        for word in (
            "sr_checkout_reserve",
            "INSERT INTO public.order_item_qr_uses",
            "UPDATE public.qr_codes",
            "UPDATE public.tag_pairs",
        )
    )
    assert any("SET CONSTRAINTS ALL IMMEDIATE" in sql for sql, _ in statements)


@pytest.mark.parametrize(
    "changes",
    [
        {"status": "confirmed"},
        {"expires_at": datetime.now(UTC) - timedelta(seconds=1)},
        {"commerce_model": "legacy_pair"},
    ],
)
def test_confirmation_rejects_closed_expired_and_wrong_model(
    setup, monkeypatch, changes
):
    ctx, req, quote, statements = confirmation(setup, monkeypatch, **changes)
    with pytest.raises(HTTPException):
        api.confirm_quote(
            UUID(int=30),
            api.ConfirmRequest(
                accept_total=str(quote["total_pkr"]), accept_currency="PKR"
            ),
            ctx,
            req,
        )
    assert not any("INSERT INTO public.orders" in sql for sql, _ in statements)


def test_confirmation_cannot_read_another_customers_quote(setup, monkeypatch):
    ctx, req, _, _statements = confirmation(setup, monkeypatch)
    ctx.session.execute.side_effect = None
    ctx.session.execute.return_value.mappings.return_value.one_or_none.return_value = (
        None
    )
    with pytest.raises(AccessError) as error:
        api.confirm_quote(
            UUID(int=30),
            api.ConfirmRequest(accept_total="114.00", accept_currency="PKR"),
            ctx,
            req,
        )
    assert error.value.status == 404
    assert "customer_user_id=:actor" in str(ctx.session.execute.call_args.args[0])


def test_migration_preserves_legacy_body_and_gates_runtime():
    root = Path(__file__).parents[1] / "alembic/versions"
    old = (root / "0002_commerce.py").read_text(encoding="utf-8")
    new = (root / "0040_item_checkout.sql").read_text(encoding="utf-8")
    start = old.index("CREATE FUNCTION public.sr_check_order()")
    frozen = old[start : old.index("END $$;", start) + 7]
    start = new.index("CREATE OR REPLACE FUNCTION public.sr_check_order()")
    current = new[start : new.index("END $$;", start) + 7]
    current = current.replace("CREATE OR REPLACE", "CREATE", 1).replace(
        "LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog",
        "LANGUAGE plpgsql SET search_path = pg_catalog, public",
    )
    current = current.replace(
        " IF o.commerce_model='single_qr' THEN PERFORM public.sr_check_item_order(oid); RETURN NULL; END IF;\n",
        "",
    )
    assert current == frozen
    assert "enabled boolean NOT NULL DEFAULT false" in new
    assert (
        "GRANT SELECT,INSERT ON public.order_logical_items,public.order_item_sizes"
        in new
    )
    assert "Item snapshots are append only" in new
    assert "Cannot mix purchase models" in new


def test_quote_persists_private_address_and_exposes_only_safe_totals(
    setup, monkeypatch
):
    ctx, req, settings, _ = setup
    frozen, subtotal = api.snapshots(ctx, [item()], settings)
    monkeypatch.setattr(api, "snapshots", lambda *args: (frozen, subtotal))
    monkeypatch.setattr(api, "admission", lambda *args: None)
    monkeypatch.setattr(
        api, "record", lambda ctx, req, op, payload, work: work(settings)[0]
    )
    monkeypatch.setattr(api, "encrypt", lambda *args: (b"encrypted-private-address", 1))
    statements = []

    def execute(sql, params=None):
        statements.append((str(sql), params))
        result = MagicMock()
        result.scalar_one.return_value = (
            INSTRUCTIONS
            if "sr_checkout_payment_instructions" in str(sql)
            else datetime.now(UTC) + timedelta(minutes=15)
        )
        return result

    ctx.session.execute.side_effect = execute
    result = api.create_quote(request(), ctx, req)
    assert result["subtotal_pkr"] == "61.50" and result["total_pkr"] == "114.00"
    assert result["identity_count"] == 1 and not result["stock_reserved"]
    assert "registry_specs" not in repr(result)
    assert ADDRESS["address"] not in repr(result)
    assert statements[-1][1]["cipher"] == b"encrypted-private-address"


def test_missing_official_payment_instructions_blocks_quote(setup, monkeypatch):
    ctx, req, settings, _ = setup
    monkeypatch.setattr(api, "admission", lambda *args: None)
    monkeypatch.setattr(
        api, "record", lambda ctx, req, op, payload, work: work(settings)[0]
    )
    ctx.session.execute.return_value.scalar_one.return_value = None
    with pytest.raises(HTTPException) as error:
        api.create_quote(request(), ctx, req)
    assert error.value.detail["code"] == "PAYMENT_INSTRUCTIONS_UNAVAILABLE"


def test_new_routes_require_authentication_and_verified_account(setup):
    from test_health import ASGIClient

    from app.api.auth import get_auth_context
    from app.core.config import Settings
    from app.main import create_app

    app = create_app(Settings())
    client = ASGIClient(app)
    for path in ("/me/checkout/item-quotes", f"/me/checkout/item-quotes/{P}/confirm"):
        assert client.post("/api/v1" + path, json={}).status_code == 401
    assert client.get(f"/api/v1/me/orders/{P}/payment-instructions").status_code == 401
    ctx, _, _, _ = setup
    ctx.email_verified = False
    app.dependency_overrides[get_auth_context] = lambda: ctx
    result = client.post(
        "/api/v1/me/checkout/item-quotes", json=request().model_dump(mode="json")
    )
    assert result.status_code == 403
    ctx.session.execute.assert_not_called()


def test_shared_receipt_wrapper_replays_without_duplicate_order_work(
    setup, monkeypatch
):
    import json

    from app.api.v1 import checkout

    ctx, req, settings, _ = setup
    ctx.email_verified = True
    settings.checkout_enabled = True
    req.headers = {"idempotency-key": "synthetic-confirm-key"}
    req.state = SimpleNamespace(request_id="synthetic-request")
    monkeypatch.setattr("app.db.template_registry.gate", lambda *args: None)
    monkeypatch.setattr(
        checkout, "encrypt", lambda s, actor, field, value: (value.encode(), 1)
    )
    monkeypatch.setattr(
        checkout, "decrypt", lambda s, actor, field, cipher, version: cipher.decode()
    )
    receipts = []

    def execute(sql, params=None):
        result = MagicMock()
        if "SELECT * FROM public.idempotency_records" in str(sql):
            result.mappings.return_value.one_or_none.return_value = (
                receipts[0] if receipts else None
            )
        if "INSERT INTO public.idempotency_records" in str(sql):
            receipts.append(
                {
                    "request_hash": params["hash"],
                    "response_body_ciphertext": params["cipher"],
                    "response_key_version": 1,
                }
            )
        return result

    ctx.session.execute.side_effect = execute
    work = MagicMock(
        return_value=({"order_id": str(P), "payment_status": "awaiting_transfer"}, P)
    )
    payload = {"quote_id": str(P), "accept_total": "114.00"}
    first = checkout.record(ctx, req, "checkout.item_confirm", payload, work)
    second = checkout.record(ctx, req, "checkout.item_confirm", payload, work)
    assert json.dumps(first) == json.dumps(second)
    work.assert_called_once()
    with pytest.raises(HTTPException) as error:
        checkout.record(
            ctx, req, "checkout.item_confirm", {**payload, "accept_total": "0.01"}, work
        )
    assert error.value.detail["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_typed_reviewer_still_requires_independent_bank_verification(setup, monkeypatch):
    from app.api.v1 import payments

    ctx, req, settings, _ = setup
    monkeypatch.setattr(payments, "require_staff", lambda *args: None)
    monkeypatch.setattr(
        payments, "record", lambda ctx, req, op, payload, work: work(settings)[0]
    )
    monkeypatch.setattr(
        payments,
        "lock_attempt",
        lambda *args: (
            {"id": P, "commerce_model": "single_qr", "payment_status": "under_review", "order_status": "placed"},
            {"state": "under_review"},
        ),
    )
    with pytest.raises(HTTPException) as error:
        payments.review_payment(
            V1,
            payments.ReviewRequest(decision="verify", reason="Synthetic review"),
            ctx,
            req,
        )
    assert error.value.detail["code"] == "BANK_VERIFICATION_REQUIRED"
    ctx.session.execute.assert_not_called()
