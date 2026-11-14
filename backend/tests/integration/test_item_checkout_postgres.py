"""Opt-in isolated Phase 4 migration/ACL checks; never invoked on shared state."""

import os
from uuid import uuid4

import pytest
from pg_rehearsal import rehearsal
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

pytestmark = pytest.mark.skipif(
    os.environ.get("SAFERETURN_ITEM_CHECKOUT_REHEARSAL") != "1",
    reason="Explicit isolated PostgreSQL checkout rehearsal authorization is required",
)


@pytest.fixture(scope="module")
def checkout_pg():
    with rehearsal(
        expected_revision=os.environ.get(
            "SAFERETURN_ITEM_CHECKOUT_BASE_REVISION", "0021_support_case_console"
        )
    ) as pg:
        actor, oid = uuid4(), uuid4()
        with pg.connect() as c:
            pg.upgrade(c, "0039_single_qr_catalog")
            c.execute(
                text("INSERT INTO auth.users(id,email_confirmed_at) VALUES(:id,now())"),
                {"id": actor},
            )
            c.execute(
                text(
                    "INSERT INTO public.orders(id,order_number,customer_user_id,subtotal_pkr,total_pkr) VALUES(:id,:number,:actor,10,10)"
                ),
                {"id": oid, "number": "SYNTHETIC-" + uuid4().hex, "actor": actor},
            )
            c.commit()
            before = c.execute(
                text(
                    "SELECT id,order_number,customer_user_id,subtotal_pkr,total_pkr FROM public.orders WHERE id=:id"
                ),
                {"id": oid},
            ).one()
            pg.upgrade(c, "0040_item_checkout")
            c.commit()
            assert (
                c.execute(
                    text(
                        "SELECT id,order_number,customer_user_id,subtotal_pkr,total_pkr FROM public.orders WHERE id=:id"
                    ),
                    {"id": oid},
                ).one()
                == before
            )
        yield pg, actor, oid


def test_upgrade_preserves_legacy_and_disables_admission(checkout_pg):
    pg, _, oid = checkout_pg
    with pg.connect() as c:
        assert c.execute(
            text(
                "SELECT commerce_model,payment_instructions_snapshot FROM public.orders WHERE id=:id"
            ),
            {"id": oid},
        ).one() == ("legacy_pair", None)
        assert (
            c.execute(text("SELECT public.sr_single_checkout_enabled()")).scalar_one()
            is False
        )
        assert (
            c.execute(
                text("SELECT public.sr_checkout_payment_instructions()")
            ).scalar_one()
            is None
        )


def test_runtime_cannot_enable_release_or_edit_payee(checkout_pg):
    pg, _, _ = checkout_pg
    with pg.connect() as c:
        for role in ("safereturn_api", "safereturn_worker", "anon", "authenticated"):
            for table in ("single_checkout_release", "checkout_payment_instructions"):
                assert (
                    c.execute(
                        text("SELECT has_table_privilege(:role,:relation,'UPDATE')"),
                        {"role": role, "relation": "public." + table},
                    ).scalar_one()
                    is False
                )


def test_snapshot_tables_have_rls_and_no_update_delete_grants(checkout_pg):
    pg, _, _ = checkout_pg
    with pg.connect() as c:
        for table in ("order_logical_items", "order_item_sizes"):
            assert c.execute(
                text(
                    "SELECT relrowsecurity FROM pg_class WHERE oid=CAST(:name AS regclass)"
                ),
                {"name": "public." + table},
            ).scalar_one()
            for privilege in ("UPDATE", "DELETE"):
                assert not c.execute(
                    text(
                        "SELECT has_table_privilege('safereturn_api',:name,:privilege)"
                    ),
                    {"name": "public." + table, "privilege": privilege},
                ).scalar_one()


def test_legacy_order_model_cannot_be_converted(checkout_pg):
    pg, _, oid = checkout_pg
    with pg.connect() as c:
        with pytest.raises(DBAPIError):
            c.execute(
                text(
                    "UPDATE public.orders SET commerce_model='single_qr',payment_instructions_snapshot='{}'::jsonb WHERE id=:id"
                ),
                {"id": oid},
            )
            c.commit()
        c.rollback()


def test_typed_order_cannot_be_created_with_release_closed(checkout_pg):
    pg, actor, _ = checkout_pg
    with pg.connect() as c:
        with pytest.raises(DBAPIError):
            c.execute(
                text(
                    "INSERT INTO public.orders(order_number,customer_user_id,commerce_model,payment_instructions_snapshot,subtotal_pkr,total_pkr) VALUES(:number,:actor,'single_qr','{}'::jsonb,10,10)"
                ),
                {"number": "SYNTHETIC-" + uuid4().hex, "actor": actor},
            )
            c.commit()
        c.rollback()


def test_typed_order_cannot_be_placed_without_items_and_shipping(checkout_pg):
    pg, actor, _ = checkout_pg
    with pg.connect() as c:
        c.execute(text("UPDATE public.single_checkout_release SET enabled=true"))
        oid = c.execute(
            text(
                "INSERT INTO public.orders(order_number,customer_user_id,commerce_model,payment_instructions_snapshot,subtotal_pkr,total_pkr) VALUES(:number,:actor,'single_qr','{}'::jsonb,10,10) RETURNING id"
            ),
            {"number": "SYNTHETIC-" + uuid4().hex, "actor": actor},
        ).scalar_one()
        with pytest.raises(DBAPIError):
            c.execute(
                text(
                    "UPDATE public.orders SET order_status='placed',placed_at=now() WHERE id=:id"
                ),
                {"id": oid},
            )
            c.commit()
        c.rollback()  # Restores disabled release too.
