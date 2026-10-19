"""Task 5.2: real isolated PostgreSQL, signed JWTs and synthetic addresses only."""

import base64
import json
import os
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from pg_rehearsal import rehearsal
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_auth import ORIGIN, claims, keyset, signed
from test_health import ASGIClient
from test_identity_schema import pair

from app.core.auth import JWTVerifier
from app.core.config import Settings
from app.core.profile_crypto import decrypt
from app.db.session import Database
from app.main import create_app

TARGET = "0016_checkout_quotes"
ADDRESS = {
    "recipient_name": "Synthetic recipient",
    "phone": "+923001234567",
    "address": "Synthetic private street 123",
    "city": "Lahore",
}


@pytest.fixture(scope="module")
def sample():
    with rehearsal(
        expected_revision=os.environ.get(
            "SAFERETURN_CHECKOUT_BASE_REVISION", "0015_public_catalog"
        )
    ) as pg:
        with pg.connect() as c:
            pg.upgrade(c, "0015_public_catalog")
            c.commit()
            pg.upgrade(c, TARGET)
            c.rollback()
            assert c.execute(
                text("SELECT to_regclass('public.checkout_quotes') IS NULL")
            ).scalar_one()
            c.rollback()
            pg.upgrade(c, TARGET)
            c.commit()
            users = {r: uuid4() for r in ("owner", "other")}
            sessions = {}
            for role, uid in users.items():
                sid = uuid4()
                sessions[role] = sid
                c.execute(
                    text(
                        "INSERT INTO auth.users(id,email_confirmed_at) VALUES(:id,now())"
                    ),
                    {"id": uid},
                )
                c.execute(
                    text(
                        "INSERT INTO auth.sessions(id,user_id,aal,not_after) VALUES(:sid,:uid,'aal1',now()+interval '1 hour')"
                    ),
                    {"sid": sid, "uid": uid},
                )
            cat = c.execute(
                text(
                    "INSERT INTO public.product_categories(slug,name) VALUES('qr-stickers','Synthetic stickers') RETURNING id"
                )
            ).scalar_one()
            product = c.execute(
                text(
                    "INSERT INTO public.products(category_id,slug,name,lifecycle_status,is_featured) VALUES(:cat,'synthetic-kit','Synthetic kit','published',true) RETURNING id"
                ),
                {"cat": cat},
            ).scalar_one()
            variants = []
            for n, price in enumerate(("0.10", "0.20")):
                variants.append(
                    c.execute(
                        text(
                            "INSERT INTO public.product_variants(product_id,sku,name,size_mm,unit_price,fulfillment_method,template_key) VALUES(:pid,:sku,:name,35,:price,'pdf_label','synthetic') RETURNING id"
                        ),
                        {
                            "pid": product,
                            "sku": f"SYNTHETIC-{n}",
                            "name": f"Synthetic size {n}",
                            "price": Decimal(price),
                        },
                    ).scalar_one()
                )
            inventory = []
            for _ in range(20):
                pid, tags = pair(c)
                inventory.append((pid, tags))
                c.execute(
                    text(
                        "UPDATE public.tag_pairs SET inventory_status='qa_passed' WHERE id=:id"
                    ),
                    {"id": pid},
                )
                c.execute(
                    text(
                        "INSERT INTO public.pair_activation_credentials(pair_id,secret_verifier,verifier_key_version) VALUES(:id,:cipher,1)"
                    ),
                    {"id": pid, "cipher": b"X" * 32},
                )
            c.commit()
        private = ec.generate_private_key(ec.SECP256R1())
        verifier = JWTVerifier(
            Settings(supabase_url=ORIGIN),
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, json={"keys": [keyset(private)]})
            ),
        )
        settings = Settings(
            supabase_url=ORIGIN,
            checkout_enabled=True,
            checkout_shipping_pkr=Decimal("10.25"),
            checkout_tax_pkr=Decimal("0.05"),
            catalog_approved_templates=["synthetic@1"],
            profile_data_keys=SecretStr(
                json.dumps({"1": base64.urlsafe_b64encode(b"Q" * 32).decode()})
            ),
        )
        app = create_app(settings, verifier=verifier)
        app.state.database = Database(pg.engine)
        app.state.jwt_verifier = verifier
        client = ASGIClient(app)

        def call(path, body, role="owner", key=None):
            return client.post(
                "/api/v1" + path,
                json=body,
                headers={
                    "Authorization": "Bearer "
                    + signed(
                        private,
                        claims(sub=str(users[role]), session_id=str(sessions[role])),
                    ),
                    "Idempotency-Key": key or str(uuid4()),
                },
            )

        app.state.checkout_fixture_token = lambda: signed(
            private, claims(sub=str(users["owner"]), session_id=str(sessions["owner"]))
        )
        app.state.checkout_fixture_user = str(users["owner"])
        yield pg, client, call, app, variants, users, inventory, product
        verifier.close()


def cart(sample):
    variants = sample[4]
    return {
        "lines": [
            {
                "variant_id": str(variants[0]),
                "quantity": 3,
                "qr_uses": [
                    {
                        "mode": "new_pair",
                        "tag_type": "lost",
                        "copies": 3,
                        "client_pair_group": "one",
                    }
                ],
            },
            {
                "variant_id": str(variants[1]),
                "quantity": 2,
                "qr_uses": [
                    {
                        "mode": "new_pair",
                        "tag_type": "ice",
                        "copies": 2,
                        "client_pair_group": "one",
                    }
                ],
            },
        ],
        "address": dict(ADDRESS),
        "contact_phone_confirmation": True,
    }


def quote(sample, body=None):
    r = sample[2]("/me/checkout/quotes", body or cart(sample))
    assert r.status_code == 201, r.text
    return r.json()


def confirm(sample, q, **kwargs):
    return sample[2](
        f"/me/checkout/quotes/{q['quote_id']}/confirm",
        {"accept_total": q["total_pkr"], "accept_currency": "PKR"},
        **kwargs,
    )


def test_decimal_quotes_and_encrypted_address(sample):
    pg, _client, call, app, *_ = sample
    key = str(uuid4())
    body = cart(sample)
    r = call("/me/checkout/quotes", body, key=key)
    assert r.status_code == 201, r.text
    q = r.json()
    assert (
        q["subtotal_pkr"] == "0.70"
        and q["total_pkr"] == "11.00"
        and q["new_pair_count"] == 1
    )
    assert call("/me/checkout/quotes", body, key=key).json() == q
    body["address"]["address"] = "Other synthetic private street"
    assert call("/me/checkout/quotes", body, key=key).status_code == 409
    assert ADDRESS["address"] not in r.text and ADDRESS["phone"] not in r.text
    assert "template_key" not in r.text and "••••4567" in r.text
    with pg.connect() as c:
        row = (
            c.execute(
                text("SELECT * FROM public.checkout_quotes WHERE id=:id"),
                {"id": q["quote_id"]},
            )
            .mappings()
            .one()
        )
        assert ADDRESS["address"] not in str(row["payload"])
        assert (
            json.loads(
                decrypt(
                    app.state.settings,
                    q["quote_id"],
                    "checkout_address",
                    row["address_ciphertext"],
                    row["address_key_version"],
                )
            )["address"]
            == ADDRESS["address"]
        )
        assert row["order_id"] is None


@pytest.mark.parametrize(
    "change",
    [
        "copies",
        "missing_ice",
        "multiple_groups",
        "reuse",
        "extra",
        "unicode_phone",
        "blank_address",
    ],
)
def test_validation_and_future_gates(sample, change):
    body = cart(sample)
    if change == "copies":
        body["lines"][0]["quantity"] = 4
    if change == "missing_ice":
        body["lines"] = body["lines"][:1]
    if change == "multiple_groups":
        other = json.loads(json.dumps(body["lines"]))
        [u.update(client_pair_group="two") for l in other for u in l["qr_uses"]]
        body["lines"] += other
    if change == "reuse":
        body["lines"][0]["qr_uses"] = [
            {
                "mode": "existing_owned",
                "tag_type": "lost",
                "copies": 3,
                "existing_qr_id": str(uuid4()),
            }
        ]
    if change == "extra":
        body["owner_user_id"] = "PRIVATE-SHOULD-NOT-ECHO"
    if change == "unicode_phone":
        body["address"]["phone"] = "+۹۲۳۰۰۱۲۳۴۵۶۷"
    if change == "blank_address":
        body["address"]["address"] = "   "
    r = sample[2]("/me/checkout/quotes", body)
    assert r.status_code == 422, r.text
    assert "PRIVATE-SHOULD-NOT-ECHO" not in r.text


def test_atomic_confirm_replay_and_immutable_snapshots(sample):
    pg, _, _, app, *_ = sample
    q = quote(sample)
    key = str(uuid4())
    r = confirm(sample, q, key=key)
    assert r.status_code == 201, r.text
    result = r.json()
    assert confirm(sample, q, key=key).json() == result
    assert confirm(sample, q).status_code == 409
    assert confirm(sample, q, role="other").status_code == 404
    with pg.connect() as c:
        assert (
            c.execute(
                text("SELECT count(*) FROM public.order_pair_units WHERE order_id=:id"),
                {"id": result["order_id"]},
            ).scalar_one()
            == 1
        )
        uses = c.execute(
            text(
                "SELECT tag_type_snapshot,copies,qr_code_id FROM public.order_item_qr_uses u JOIN public.order_items i ON i.id=u.order_item_id WHERE i.order_id=:id ORDER BY tag_type_snapshot"
            ),
            {"id": result["order_id"]},
        ).all()
        assert [(u[0], u[1]) for u in uses] == [("ice", 2), ("lost", 3)] and uses[0][
            2
        ] != uses[1][2]
        row = (
            c.execute(
                text(
                    "SELECT * FROM public.order_shipping_snapshots WHERE order_id=:id"
                ),
                {"id": result["order_id"]},
            )
            .mappings()
            .one()
        )
        assert (
            decrypt(
                app.state.settings,
                result["order_id"],
                "shipping_address",
                row["address_ciphertext"],
                row["key_version"],
            )
            == ADDRESS["address"]
        )
        with pytest.raises(DBAPIError), c.begin_nested():
            c.execute(
                text(
                    "UPDATE public.order_items SET product_name_snapshot='changed' WHERE order_id=:id"
                ),
                {"id": result["order_id"]},
            )


def test_quote_expiry_acceptance_and_payload_immutability(sample):
    pg, _, call, _, *_ = sample
    q = quote(sample)
    assert (
        call(
            f"/me/checkout/quotes/{q['quote_id']}/confirm",
            {"accept_total": "999.00", "accept_currency": "PKR"},
        ).status_code
        == 409
    )
    with pg.connect() as c:
        with pytest.raises(DBAPIError), c.begin_nested():
            c.execute(
                text("UPDATE public.checkout_quotes SET subtotal_pkr=100 WHERE id=:id"),
                {"id": q["quote_id"]},
            )
        c.execute(
            text("UPDATE public.checkout_quotes SET status='expired' WHERE id=:id"),
            {"id": q["quote_id"]},
        )
        c.commit()
    assert confirm(sample, q).status_code == 409


def test_failed_crypto_rolls_back_everything(sample):
    pg, _, _, app, *_ = sample
    q = quote(sample)
    settings = app.state.settings
    old = settings.profile_data_keys
    with pg.connect() as c:
        before = c.execute(text("SELECT count(*) FROM public.orders")).scalar_one()
    settings.profile_data_keys = SecretStr("{}")
    try:
        assert confirm(sample, q).status_code == 503
    finally:
        settings.profile_data_keys = old
    with pg.connect() as c:
        assert (
            c.execute(text("SELECT count(*) FROM public.orders")).scalar_one() == before
        )
    assert confirm(sample, q).status_code == 201


def test_same_key_concurrent_confirm(sample):
    q = quote(sample)
    key = str(uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: confirm(sample, q, key=key), range(2)))
    assert [r.status_code for r in results] == [201, 201]
    assert results[0].json() == results[1].json()


def test_price_changes_do_not_rewrite_quote(sample):
    pg, _, _, _, variants, *_ = sample
    q = quote(sample)
    with pg.connect() as c:
        c.execute(
            text("UPDATE public.product_variants SET unit_price=99 WHERE id=ANY(:ids)"),
            {"ids": variants},
        )
        c.commit()
    try:
        r = confirm(sample, q)
        assert r.status_code == 201, r.text
        assert r.json()["total_pkr"] == "11.00"
    finally:
        with pg.connect() as c:
            for vid, price in zip(
                variants, [Decimal("0.10"), Decimal("0.20")], strict=True
            ):
                c.execute(
                    text(
                        "UPDATE public.product_variants SET unit_price=:price WHERE id=:id"
                    ),
                    {"id": vid, "price": price},
                )
            c.commit()


def test_real_expired_deadline(sample):
    pg, _, _, _, *_ = sample
    q = quote(sample)
    expired = uuid4()
    with pg.connect() as c:
        c.execute(
            text("""INSERT INTO public.checkout_quotes(id,customer_user_id,payload,address_ciphertext,address_key_version,subtotal_pkr,shipping_pkr,tax_pkr,total_pkr,expires_at,created_at)
   SELECT :new,customer_user_id,payload,address_ciphertext,address_key_version,subtotal_pkr,shipping_pkr,tax_pkr,total_pkr,clock_timestamp()-interval '1 second',clock_timestamp()-interval '16 minutes' FROM public.checkout_quotes WHERE id=:old"""),
            {"new": expired, "old": q["quote_id"]},
        )
        c.commit()
    assert confirm(sample, {**q, "quote_id": str(expired)}).status_code == 409


def test_last_pair_race_and_recovery(sample):
    pg, _, _, _, *_ = sample
    with pg.connect() as c:
        eligible = (
            c.execute(
                text(
                    "SELECT id FROM public.tag_pairs WHERE inventory_status='qa_passed' AND ownership_status='unclaimed' ORDER BY id"
                )
            )
            .scalars()
            .all()
        )
        assert len(eligible) > 1
        c.execute(
            text(
                "UPDATE public.tag_pairs SET inventory_status='rejected' WHERE id=ANY(:ids)"
            ),
            {"ids": eligible[1:]},
        )
        c.commit()
    try:
        q1, q2 = quote(sample), quote(sample)
        with pg.connect() as c:
            before = c.execute(text("SELECT count(*) FROM public.orders")).scalar_one()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda q: confirm(sample, q), [q1, q2]))
        assert sorted(r.status_code for r in results) == [201, 409], [
            r.text for r in results
        ]
        with pg.connect() as c:
            assert (
                c.execute(text("SELECT count(*) FROM public.orders")).scalar_one()
                == before + 1
            )
            assert (
                c.execute(
                    text(
                        "SELECT count(*) FROM public.order_pair_units WHERE pair_id=:id AND status='reserved'"
                    ),
                    {"id": eligible[0]},
                ).scalar_one()
                == 1
            )
    finally:
        with pg.connect() as c:
            c.execute(
                text(
                    "UPDATE public.tag_pairs SET inventory_status='qa_passed' WHERE id=ANY(:ids) AND inventory_status='rejected'"
                ),
                {"ids": eligible[1:]},
            )
            c.commit()
    loser = q1 if results[0].status_code == 409 else q2
    assert confirm(sample, loser).status_code == 201


def test_future_reuse_owner_tag_and_revalidation(sample):
    pg, _, call, app, _, users, inventory, product = sample
    with pg.connect() as c:
        pair_id = c.execute(
            text(
                "SELECT id FROM public.tag_pairs WHERE ownership_status='unclaimed' AND inventory_status='qa_passed' ORDER BY id LIMIT 1"
            )
        ).scalar_one()
    tags = next(tags for pid, tags in inventory if pid == pair_id)
    with pg.connect() as c:
        c.execute(
            text(
                "UPDATE public.tag_pairs SET owner_user_id=:uid,ownership_status='active',activated_at=now() WHERE id=:id"
            ),
            {"uid": users["owner"], "id": pair_id},
        )
        c.execute(
            text("UPDATE public.qr_codes SET public_status='active' WHERE pair_id=:id"),
            {"id": pair_id},
        )
        c.execute(
            text("UPDATE public.products SET allows_existing_qr=true WHERE id=:id"),
            {"id": product},
        )
        c.commit()
    app.state.settings.checkout_existing_qr_reuse_enabled = True
    body = cart(sample)
    for line, tag in zip(body["lines"], ["lost", "ice"], strict=True):
        line["qr_uses"] = [
            {
                "mode": "existing_owned",
                "tag_type": tag,
                "copies": line["quantity"],
                "existing_qr_id": str(tags[tag]),
            }
        ]
    try:
        assert call("/me/checkout/quotes", body, role="other").status_code == 404
        q = quote(sample, body)
        assert q["new_pair_count"] == 0
        result = confirm(sample, q)
        assert result.status_code == 201, result.text
        assert result.json()["reservation_state"] == "not_required"
        changed = json.loads(json.dumps(body))
        changed["lines"][1]["qr_uses"][0]["existing_qr_id"] = str(tags["lost"])
        assert call("/me/checkout/quotes", changed).status_code == 404
        q = quote(sample, body)
        with pg.connect() as c:
            c.execute(
                text(
                    "UPDATE public.qr_codes SET public_status='owner_disabled' WHERE id=:id"
                ),
                {"id": tags["lost"]},
            )
            c.commit()
        assert confirm(sample, q).status_code == 404
    finally:
        app.state.settings.checkout_existing_qr_reuse_enabled = False
        with pg.connect() as c:
            c.execute(
                text(
                    "UPDATE public.products SET allows_existing_qr=false WHERE id=:id"
                ),
                {"id": product},
            )
            c.commit()


def test_browser(sample):
    from checkout_browser import run

    run(sample)
