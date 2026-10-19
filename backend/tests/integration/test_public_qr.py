"""Task 4.1: actual PostgreSQL, explicit migration target, synthetic data only."""

import os
import uuid

import pytest
from pg_rehearsal import rehearsal
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_health import ASGIClient
from test_identity_schema import pair

from app.core.config import Settings
from app.db.session import Database
from app.main import create_app

TARGET = "0012_public_qr_projection"


@pytest.fixture(scope="module")
def public_database():
    with rehearsal(
        expected_revision=os.environ.get("SAFERETURN_PUBLIC_QR_BASE_REVISION", TARGET)
    ) as pg:
        with pg.connect() as c:
            pg.upgrade(c, "0011_profile_owner_locks")
            c.commit()
            pg.upgrade(c, TARGET)
            assert c.execute(
                text(
                    "SELECT to_regprocedure('public.sr_public_qr_projection(text)') IS NOT NULL"
                )
            ).scalar_one()
            c.rollback()
            assert c.execute(
                text(
                    "SELECT to_regprocedure('public.sr_public_qr_projection(text)') IS NULL"
                )
            ).scalar_one()
            assert (
                c.execute(
                    text("SELECT version_num FROM public.alembic_version")
                ).scalar_one()
                == "0011_profile_owner_locks"
            )
            c.rollback()
            pg.upgrade(c, TARGET)
            c.commit()
        app = create_app(Settings())
        app.state.database = Database(pg.engine)
        yield pg, ASGIClient(app)


@pytest.fixture
def public_sample(public_database):
    pg, client = public_database
    with pg.connect() as c:
        pid, ids = pair(c)
        ids["pair"] = pid
        owner = uuid.uuid4()
        ids["owner"] = owner
        c.execute(text("INSERT INTO auth.users(id) VALUES(:id)"), {"id": owner})
        c.execute(
            text(
                "UPDATE public.tag_pairs SET owner_user_id=:owner,ownership_status='active',activated_at=now() WHERE id=:id"
            ),
            {"owner": owner, "id": pid},
        )
        c.execute(
            text("UPDATE public.qr_codes SET public_status='active' WHERE pair_id=:id"),
            {"id": pid},
        )
        tokens = dict(
            c.execute(
                text(
                    "SELECT tag_type,public_token FROM public.qr_codes WHERE pair_id=:id"
                ),
                {"id": pid},
            ).all()
        )
        c.execute(
            text(
                "INSERT INTO public.lost_item_profiles(qr_id,item_label,description,reward_text,published) VALUES(:id,'Public bag','Published description','Reward',true)"
            ),
            {"id": ids["lost"]},
        )
        c.execute(
            text(
                "INSERT INTO public.ice_profiles(qr_id,display_name,blood_group,published,publication_consent_at,publication_consent_version,medical_notes_ciphertext,medical_notes_key_version) VALUES(:id,'Public alias','O+',true,now(),'ice-public-v1',decode('aabb','hex'),1)"
            ),
            {"id": ids["ice"]},
        )
        contacts = []
        for n, (published, removed) in enumerate(
            ((True, False), (False, False), (False, True))
        ):
            cid = uuid.uuid4()
            contacts.append(cid)
            c.execute(
                text(
                    "INSERT INTO public.ice_contacts(id,ice_qr_id,relationship_label,display_name,phone_ciphertext,phone_key_version,display_order,published,publication_consent_at,publication_consent_version,removed_at) VALUES(:id,:qr,:label,:name,:cipher,1,:n,:published,now(),'ice-contact-v1',CASE WHEN :removed THEN now() END)"
                ),
                {
                    "id": cid,
                    "qr": ids["ice"],
                    "label": "Parent" if n == 0 else "HIDDEN-LABEL",
                    "name": "Contact alias" if n == 0 else "HIDDEN-NAME",
                    "cipher": b"PRIVATE-PHONE-CIPHERTEXT",
                    "n": n,
                    "published": published,
                    "removed": removed,
                },
            )
        c.commit()

    def get(kind="lost", **kwargs):
        return client.get("/api/v1/public/qr/" + tokens[kind], **kwargs)

    return pg, client, ids, tokens, contacts, get


def test_anonymous_allowlist_and_private_data_absence(public_sample, caplog):
    _pg, _, ids, tokens, contacts, get = public_sample
    for kind in ("lost", "ice"):
        r = get(kind, headers={"Authorization": "Bearer invalid-irrelevant-to-public"})
        assert r.status_code == 200, r.text
        assert r.headers["cache-control"] == "no-store"
        assert r.headers["referrer-policy"] == "no-referrer"
        data = r.json()
        assert data["tag_type"] == kind and data["status"] == "active"
        assert data["locale_options"] == ["en", "ur"]
        assert set(data) == (
            {
                "tag_type",
                "status",
                "locale_options",
                "lost_item",
                "features",
                "whatsapp_contact",
            }
            if kind == "lost"
            else {"tag_type", "status", "locale_options", "ice"}
        )
        for private in (
            "PRIVATE-PHONE",
            "HIDDEN-",
            str(ids["pair"]),
            str(ids["owner"]),
            "aabb",
            "phone_ciphertext",
            "medical_notes_ciphertext",
            "owner_user_id",
            "activation_secret",
        ):
            assert private not in r.text
        if kind == "ice":
            assert data["ice"]["medical_notes"] is None
            assert [x["contact_id"] for x in data["ice"]["contacts"]] == [
                str(contacts[0])
            ]
            assert set(data["ice"]["contacts"][0]) == {
                "contact_id",
                "relationship_label",
                "display_name",
                "reveal_available",
            }
        assert tokens[kind] not in caplog.text


@pytest.mark.parametrize("kind", ["lost", "ice"])
@pytest.mark.parametrize(
    "status", ["unactivated", "owner_disabled", "admin_suspended", "revoked"]
)
def test_unavailable_states_have_no_profile_content(public_sample, kind, status):
    pg, _, ids, _, _, get = public_sample
    with pg.connect() as c:
        c.execute(
            text(
                "UPDATE public.qr_codes SET public_status=CAST(:s AS varchar),revoked_at=CASE WHEN CAST(:s AS varchar)='revoked' THEN now() END WHERE id=:id"
            ),
            {"s": status, "id": ids[kind]},
        )
        c.commit()
    r = get(kind)
    assert r.status_code == 200
    assert r.json() == {
        "tag_type": kind,
        "status": status,
        "locale_options": ["en", "ur"],
    }


@pytest.mark.parametrize("kind", ["lost", "ice"])
def test_unpublished_fields_and_contact_labels_are_absent(public_sample, kind):
    pg, _, ids, _, _, get = public_sample
    table = "lost_item_profiles" if kind == "lost" else "ice_profiles"
    with pg.connect() as c:
        c.execute(
            text(f"UPDATE public.{table} SET published=false WHERE qr_id=:id"),
            {"id": ids[kind]},
        )
        c.commit()
    r = get(kind)
    assert r.status_code == 200
    assert "Public alias" not in r.text and "Public bag" not in r.text
    if kind == "ice":
        assert r.json()["ice"]["contacts"] == []


@pytest.mark.parametrize("kind", ["lost", "ice"])
def test_missing_profiles_are_safe_empty_states(public_database, kind):
    pg, client = public_database
    with pg.connect() as c:
        pid, ids = pair(c)
        c.execute(
            text("UPDATE public.qr_codes SET public_status='active' WHERE pair_id=:id"),
            {"id": pid},
        )
        token = c.execute(
            text("SELECT public_token FROM public.qr_codes WHERE id=:id"),
            {"id": ids[kind]},
        ).scalar_one()
        c.commit()
    r = client.get("/api/v1/public/qr/" + token)
    assert r.status_code == 200, r.text
    if kind == "ice":
        assert r.json()["ice"]["contacts"] == []


@pytest.mark.parametrize(
    "token",
    ["short", "bad.token.but.long.enough", "z" * 81, "UNKNOWN_TOKEN_" + "z" * 24],
)
def test_invalid_and_unknown_tokens_are_generic(public_database, token):
    r = public_database[1].get("/api/v1/public/qr/" + token)
    assert r.status_code == 404 and r.headers["cache-control"] == "no-store"
    assert r.json()["error"]["code"] == "NOT_FOUND"
    assert token not in r.text


def test_retired_token_is_not_resolved(public_sample):
    pg, _, ids, _, _, get = public_sample
    with pg.connect() as c:
        # Replacement maintains exactly two current children at COMMIT.
        old = c.execute(
            text("SELECT pair_id FROM public.qr_codes WHERE id=:id"),
            {"id": ids["lost"]},
        ).scalar_one()
        c.execute(
            text(
                "UPDATE public.qr_codes SET is_current=false,public_status='revoked',revoked_at=now() WHERE id=:id"
            ),
            {"id": ids["lost"]},
        )
        from test_identity_schema import qr

        qr(c, old, "lost", old=ids["lost"])
        c.commit()
    assert get().status_code == 404


def test_api_has_projection_only_and_other_roles_cannot_execute(public_database):
    pg, _ = public_database
    with pg.connect() as c:
        c.execute(text("SET LOCAL ROLE safereturn_api"))
        assert (
            c.execute(
                text("SELECT public.sr_public_qr_projection('unknown')")
            ).scalar_one()
            is None
        )
        assert (
            c.execute(text("SELECT count(*) FROM public.ice_contacts")).scalar_one()
            == 0
        )
        c.rollback()
        for role in ("anon", "authenticated", "safereturn_worker"):
            with pytest.raises(DBAPIError), c.begin_nested():
                c.execute(text("SET LOCAL ROLE " + role))
                c.execute(text("SELECT public.sr_public_qr_projection('unknown')"))
            c.rollback()


def test_enumeration_budget_counts_unknowns_and_ignores_forwarded_ip(public_database):
    pg, client = public_database
    import hashlib

    digest = hashlib.sha256(b"203.0.113.9").hexdigest()
    with pg.connect() as c:
        # Exhaust only this isolated synthetic peer, without 100 HTTP round trips.
        c.execute(
            text(
                "SELECT bool_and(public.sr_public_scan_rate(:d)) FROM generate_series(1,100)"
            ),
            {"d": digest},
        )
        c.commit()
    import asyncio

    import httpx

    async def request():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(
                app=client.application, client=("203.0.113.9", 123)
            ),
            base_url="http://test",
        ) as session:
            return await session.get(
                "/api/v1/public/qr/" + "unknown" * 5,
                headers={"X-Forwarded-For": "203.0.113.50"},
            )

    r = asyncio.run(request())
    assert r.status_code == 429 and r.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("scope", ["profile", "contact"])
def test_unknown_consent_versions_do_not_publish_ice(public_sample, scope):
    pg, _, ids, _, contacts, get = public_sample
    with pg.connect() as c:
        if scope == "profile":
            c.execute(
                text(
                    "UPDATE public.ice_profiles SET publication_consent_version='unapproved' WHERE qr_id=:id"
                ),
                {"id": ids["ice"]},
            )
        else:
            c.execute(
                text(
                    "UPDATE public.ice_contacts SET publication_consent_version='unapproved' WHERE id=:id"
                ),
                {"id": contacts[0]},
            )
        c.commit()
    r = get("ice")
    assert r.status_code == 200
    assert r.json()["ice"]["contacts"] == []
    if scope == "profile":
        assert r.json()["ice"]["display_name"] is None


def test_database_outage_is_safe():
    r = ASGIClient(create_app(Settings())).get("/api/v1/public/qr/" + "unknown" * 5)
    assert r.status_code == 503 and r.headers["cache-control"] == "no-store"


def test_real_anonymous_scan_browser(public_sample):
    from public_qr_browser import run

    run(public_sample)
