"""Task 5.1 isolated PostgreSQL + signed JWT + browser acceptance."""

import base64
import json
import os
from uuid import uuid4

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from pg_rehearsal import rehearsal
from pydantic import SecretStr
from sqlalchemy import text
from test_auth import ORIGIN, claims, keyset, signed
from test_health import ASGIClient

from app.api.v1 import catalog
from app.core.auth import JWTVerifier
from app.core.config import Settings
from app.db.session import Database
from app.main import create_app

TARGET = "0015_public_catalog"


@pytest.fixture(scope="module")
def sample():
    with rehearsal(
        expected_revision=os.environ.get(
            "SAFERETURN_CATALOG_BASE_REVISION", "0014a_notification_delivery"
        )
    ) as pg:
        with pg.connect() as c:
            pg.upgrade(c, "0014a_notification_delivery")
            c.commit()
            pg.upgrade(c, TARGET)
            c.rollback()
            assert c.execute(
                text("SELECT to_regprocedure('public.sr_public_catalog(text)') IS NULL")
            ).scalar_one()
            c.rollback()
            pg.upgrade(c, TARGET)
            c.commit()
            users = {
                role: uuid4()
                for role in ("operations", "finance", "customer", "security_admin")
            }
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
                        "INSERT INTO auth.sessions(id,user_id,aal,not_after) VALUES(:sid,:uid,'aal2',now()+interval '1 hour')"
                    ),
                    {"sid": sid, "uid": uid},
                )
                if role != "customer":
                    c.execute(
                        text(
                            "INSERT INTO public.staff_roles(user_id,role) VALUES(:id,:role)"
                        ),
                        {"id": uid, "role": role},
                    )
            c.commit()
        key = ec.generate_private_key(ec.SECP256R1())
        verifier = JWTVerifier(
            Settings(supabase_url=ORIGIN),
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, json={"keys": [keyset(key)]})
            ),
        )
        app = create_app(
            Settings(
                supabase_url=ORIGIN,
                catalog_approved_templates=["synthetic@1"],
                profile_data_keys=SecretStr(
                    json.dumps({"1": base64.urlsafe_b64encode(b"C" * 32).decode()})
                ),
            ),
            verifier=verifier,
        )
        app.state.database = Database(pg.engine)
        app.state.jwt_verifier = verifier
        client = ASGIClient(app)

        def call(
            method,
            path,
            body=None,
            role="operations",
            version=None,
            key_id=None,
            mfa=True,
        ):
            data = claims(
                sub=str(users[role]),
                session_id=str(sessions[role]),
                aal="aal2" if mfa else "aal1",
            )
            headers = {
                "Authorization": "Bearer " + signed(key, data),
                "Idempotency-Key": key_id or str(uuid4()),
            }
            if version is not None:
                headers["If-Match"] = '"' + str(version) + '"'
            return client.request(method, "/api/v1" + path, json=body, headers=headers)

        app.state.catalog_fixture_token = lambda: signed(
            key,
            claims(
                sub=str(users["operations"]),
                session_id=str(sessions["operations"]),
                aal="aal2",
            ),
        )
        app.state.catalog_fixture_user = str(users["operations"])
        yield pg, client, call, app
        verifier.close()


def product(call, name="Test stickers"):
    category = call(
        "POST",
        "/admin/catalog/categories",
        {"slug": "cat-" + uuid4().hex, "name": "Test"},
    ).json()
    result = call(
        "POST",
        "/admin/products",
        {"slug": "p-" + uuid4().hex, "name": name, "category_id": category["id"]},
    )
    assert result.status_code == 201, result.text
    return result.json()


def test_draft_idempotency_and_parameters(sample):
    pg, client, call, _ = sample
    body = {"slug": "idempotent-stickers", "name": "Safe name"}
    key = str(uuid4())
    r = call("POST", "/admin/products", body, key_id=key)
    assert r.status_code == 201, r.text
    assert call("POST", "/admin/products", body, key_id=key).json() == r.json()
    assert (
        call(
            "POST", "/admin/products", {**body, "name": "Changed"}, key_id=key
        ).status_code
        == 409
    )
    assert call("POST", "/admin/products", body).status_code == 409
    assert (
        call(
            "POST",
            "/admin/products",
            {**body, "slug": "published-at-create", "lifecycle_status": "published"},
        ).status_code
        == 422
    )
    assert client.get("/api/v1/public/products/idempotent-stickers").status_code == 404
    with pg.connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.audit_events WHERE action='catalog.product.create' AND target_id=:id"
                ),
                {"id": r.json()["id"]},
            ).scalar_one()
            == 1
        )


@pytest.mark.parametrize(
    "role,mfa", [("finance", True), ("customer", True), ("operations", False)]
)
def test_role_mfa_denials(sample, role, mfa):
    _, client, call, _ = sample
    assert (
        call(
            "POST",
            "/admin/products",
            {"slug": "deny-test", "name": "Denied"},
            role=role,
            mfa=mfa,
        ).status_code
        == 403
    )
    assert call("GET", "/admin/products", role=role, mfa=mfa).status_code == 403
    assert (
        client.post(
            "/api/v1/admin/products", json={"slug": "deny-test", "name": "Denied"}
        ).status_code
        == 401
    )


def test_publication_edits_archive_and_versions(sample, monkeypatch):
    _pg, client, call, _app = sample
    p = product(call)
    # Future category publishing is independently gated.
    update = {
        k: p[k]
        for k in (
            "slug",
            "name",
            "category_id",
            "description",
            "is_featured",
            "featured_sort_order",
        )
    }
    update["lifecycle_status"] = "published"
    assert (
        call("PATCH", "/admin/products/" + p["id"], update, version=1).status_code
        == 422
    )
    cat = call(
        "POST",
        "/admin/catalog/categories",
        {"slug": "qr-stickers", "name": "QR Stickers"},
    ).json()
    update["category_id"] = cat["id"]
    update["lifecycle_status"] = "draft"
    p = call("PATCH", "/admin/products/" + p["id"], update, version=1).json()
    variant = {
        "sku": "SYNTHETIC-KIT",
        "name": "Synthetic variant",
        "size_mm": "35.00",
        "unit_price": "123.45",
        "fulfillment_method": "pdf_label",
        "template_key": "synthetic",
    }
    v = call(
        "POST",
        f"/admin/products/{p['id']}/variants",
        variant,
        version=p["catalog_version"],
    )
    assert v.status_code == 201, v.text
    v = v.json()
    p["catalog_version"] += 1
    assert (
        call(
            "POST",
            f"/admin/products/{p['id']}/images",
            {
                "cloudinary_public_id": "safereturn/catalog/test",
                "alt_text": "Synthetic kit",
            },
            version=p["catalog_version"],
        ).status_code
        == 503
    )
    monkeypatch.setattr(
        catalog,
        "verified_asset",
        lambda *a: (
            "https://res.cloudinary.com/synthetic/image/upload/v1/safereturn/catalog/test.png"
        ),
    )
    image = call(
        "POST",
        f"/admin/products/{p['id']}/images",
        {
            "cloudinary_public_id": "safereturn/catalog/test",
            "alt_text": "Synthetic kit",
            "is_primary": True,
        },
        version=p["catalog_version"],
    )
    assert image.status_code == 201, image.text
    p["catalog_version"] += 1
    update.update(lifecycle_status="published", is_featured=True)
    saved = call(
        "PATCH", "/admin/products/" + p["id"], update, version=p["catalog_version"]
    )
    assert saved.status_code == 200, saved.text
    p = saved.json()
    r = client.get("/api/v1/public/products/SYNTHETIC-KIT")
    assert r.status_code == 200, r.text
    assert r.headers["cache-control"] == "no-store"
    assert r.json()["variants"][0]["unit_price_pkr"] == "123.45"
    assert set(r.json()) == {
        "product_id",
        "slug",
        "name",
        "description",
        "featured",
        "catalog_version",
        "category",
        "images",
        "variants",
    }
    assert "template_key" not in r.text and "cloudinary_public_id" not in r.text
    assert client.get("/api/v1/public/products/" + p["slug"]).status_code == 404
    assert len(client.get("/api/v1/public/catalog/featured").json()["items"]) == 1
    assert (
        call("PATCH", "/admin/products/" + p["id"], update, version=1).status_code
        == 412
    )
    assert (
        call(
            "DELETE",
            f"/admin/products/{p['id']}/images/{image.json()['id']}",
            version=p["catalog_version"],
        ).status_code
        == 422
    )
    # Invalid physical change cannot mutate a published variant.
    assert (
        call(
            "PATCH",
            "/admin/product-variants/" + v["id"],
            {**variant, "size_mm": "20"},
            version=1,
        ).status_code
        == 422
    )
    assert (
        call(
            "PATCH",
            "/admin/product-variants/" + v["id"],
            {**variant, "unit_price": "234.56"},
            version=1,
        ).status_code
        == 200
    )
    p["catalog_version"] += 1
    assert (
        client.get("/api/v1/public/products/SYNTHETIC-KIT").json()["variants"][0][
            "unit_price_pkr"
        ]
        == "234.56"
    )
    update["lifecycle_status"] = "archived"
    r = call(
        "PATCH", "/admin/products/" + p["id"], update, version=p["catalog_version"]
    )
    assert r.status_code == 200, r.text
    assert client.get("/api/v1/public/products/SYNTHETIC-KIT").status_code == 404
    assert client.get("/api/v1/public/catalog/featured").json()["items"] == []


def test_invalid_input_non_echo(sample):
    _, client, call, _ = sample
    for body in (
        {"slug": "valid-slug", "name": "   "},
        {"slug": "valid-slug", "name": "ok", "SECRET-FIELD": "PRIVATE-INPUT"},
    ):
        r = call("POST", "/admin/products", body)
        assert r.status_code == 422 and "PRIVATE-INPUT" not in r.text
    assert client.get("/api/v1/public/products/UNKNOWN-SKU").status_code == 404


def test_projection_filters_and_order(sample):
    pg, client, _, _ = sample
    with pg.connect() as c:
        cat = c.execute(
            text("SELECT id FROM public.product_categories WHERE slug='qr-stickers'")
        ).scalar_one()
        for n, status, active in (
            (2, "published", True),
            (1, "published", True),
            (3, "draft", True),
            (4, "archived", True),
            (5, "published", False),
        ):
            pid = c.execute(
                text(
                    "INSERT INTO public.products(category_id,slug,name,lifecycle_status,is_featured,featured_sort_order) VALUES(:cat,:slug,:name,:status,true,:n) RETURNING id"
                ),
                {
                    "cat": cat,
                    "slug": f"projection-{n}",
                    "name": f"Synthetic card {n}",
                    "status": status,
                    "n": n,
                },
            ).scalar_one()
            c.execute(
                text(
                    "INSERT INTO public.product_variants(product_id,sku,name,size_mm,unit_price,fulfillment_method,is_active) VALUES(:id,:sku,'Synthetic',35,150.25,'pdf_label',:active)"
                ),
                {"id": pid, "sku": f"PROJECTION-{n}", "active": active},
            )
        c.commit()
    cards = client.get("/api/v1/public/catalog/featured").json()["items"]
    assert [p["name"] for p in cards] == ["Synthetic card 1", "Synthetic card 2"]
    for n in (3, 4, 5):
        assert client.get(f"/api/v1/public/products/PROJECTION-{n}").status_code == 404
    assert len(client.get("/api/v1/public/products?limit=1").json()) == 1
    assert (
        client.get("/api/v1/public/catalog/categories").json()["items"][0]["slug"]
        == "qr-stickers"
    )
    assert (
        client.get(
            f"/api/v1/public/catalog/products/{cards[0]['product_id']}/variants"
        ).status_code
        == 200
    )
    # Projection is not executable by browser or worker database roles.
    with pg.connect() as c:
        for role in ("anon", "authenticated", "safereturn_worker"):
            assert not c.execute(
                text(
                    "SELECT has_function_privilege(:role,'public.sr_public_catalog(text)','EXECUTE')"
                ),
                {"role": role},
            ).scalar_one()


def test_concurrent_idempotency_and_version(sample):
    from concurrent.futures import ThreadPoolExecutor

    _, _, call, _ = sample
    body = {"slug": "race-" + uuid4().hex, "name": "Concurrent draft"}
    key = str(uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: call("POST", "/admin/products", body, key_id=key), range(2)
            )
        )
    assert [r.status_code for r in results] == [201, 201]
    assert results[0].json() == results[1].json()
    product_id = results[0].json()["id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda n: call(
                    "PATCH",
                    "/admin/products/" + product_id,
                    {**body, "name": f"Concurrent {n}"},
                    version=1,
                ),
                range(2),
            )
        )
    assert sorted(r.status_code for r in results) == [200, 412]


def test_catalog_edits_preserve_order_snapshots(sample):
    from test_commerce_schema import sample as commerce_sample

    pg, _, call, _ = sample
    with pg.connect() as c:
        ids = commerce_sample.__wrapped__(c)
        old = (
            c.execute(
                text(
                    "SELECT to_jsonb(i) FROM public.order_items i WHERE product_id=:id ORDER BY id"
                ),
                {"id": ids["product"]},
            )
            .scalars()
            .all()
        )
        p = dict(
            c.execute(
                text("SELECT * FROM public.products WHERE id=:id"),
                {"id": ids["product"]},
            )
            .mappings()
            .one()
        )
        c.commit()
    body = {
        k: p[k]
        for k in (
            "name",
            "slug",
            "category_id",
            "description",
            "is_featured",
            "featured_sort_order",
        )
    }
    body.update(name="Archived revised name", lifecycle_status="archived")
    r = call("PATCH", "/admin/products/" + str(p["id"]), body, version=1)
    assert r.status_code == 200, r.text
    with pg.connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT to_jsonb(i) FROM public.order_items i WHERE product_id=:id ORDER BY id"
                ),
                {"id": ids["product"]},
            )
            .scalars()
            .all()
            == old
        )


def test_signed_upload_authorization_is_scoped_and_idempotent(sample):
    _, _, call, app = sample
    p = product(call, "Upload draft")
    path = f"/admin/products/{p['id']}/images?authorize_upload=true"
    body = {
        "cloudinary_public_id": "safereturn/catalog/pending",
        "alt_text": "Public test",
    }
    assert call("POST", path, body, version=1).status_code == 503
    settings = app.state.settings
    settings.cloudinary_cloud_name = "synthetic"
    settings.cloudinary_api_key = SecretStr("synthetic-public-key")
    settings.cloudinary_api_secret = SecretStr("synthetic-provider-secret")
    settings.cloudinary_upload_preset = "bounded-public-raster"
    key = str(uuid4())
    grant = call("POST", path, body, version=1, key_id=key)
    assert grant.status_code == 201, grant.text
    assert call("POST", path, body, version=1, key_id=key).json() == grant.json()
    assert grant.json()["public_id"].startswith("safereturn/catalog/" + p["id"] + "/")
    assert "synthetic-provider-secret" not in grant.text
    assert call("POST", path, body, version=1, role="finance").status_code == 403
    assert call("POST", path, body, version=999).status_code == 412


def test_browser(sample):
    from catalog_browser import run

    run(sample)
