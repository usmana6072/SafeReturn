"""Opt-in isolated schema checks. Never run against an unidentified database."""

import os
from uuid import uuid4

import pytest
from pg_rehearsal import rehearsal
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

pytestmark = pytest.mark.skipif(
    os.environ.get("SAFERETURN_SINGLE_CATALOG_REHEARSAL") != "1",
    reason="An explicitly authorized isolated PostgreSQL catalog rehearsal is required",
)


@pytest.fixture(scope="module")
def catalog_pg():
    with rehearsal(
        expected_revision=os.environ.get(
            "SAFERETURN_SINGLE_CATALOG_BASE_REVISION", "0021_support_case_console"
        )
    ) as pg:
        with pg.connect() as connection:
            pg.upgrade(connection, "0038_typed_inventory")
            legacy = uuid4()
            connection.execute(
                text(
                    "INSERT INTO public.products(id,slug,name,price_per_copy) VALUES(:id,:slug,'Legacy product',12.30)"
                ),
                {"id": legacy, "slug": "legacy-" + uuid4().hex},
            )
            connection.commit()
            before = connection.execute(
                text(
                    "SELECT id,slug,name,price_per_copy FROM public.products WHERE id=:id"
                ),
                {"id": legacy},
            ).one()
            pg.upgrade(connection, "0039_single_qr_catalog")
            connection.commit()
            assert (
                connection.execute(
                    text(
                        "SELECT id,slug,name,price_per_copy FROM public.products WHERE id=:id"
                    ),
                    {"id": legacy},
                ).one()
                == before
            )
            assert connection.execute(
                text("SELECT commerce_model,qr_type FROM public.products WHERE id=:id"),
                {"id": legacy},
            ).one() == ("legacy_pair", None)
        yield pg, legacy


def test_typed_draft_persists_type_and_uniform_price(catalog_pg):
    pg, _ = catalog_pg
    identity = uuid4()
    with pg.connect() as connection:
        connection.execute(
            text(
                "INSERT INTO public.products(id,slug,name,price_per_copy,commerce_model,qr_type) VALUES(:id,:slug,'Emergency sticker',18.75,'single_qr','ice')"
            ),
            {"id": identity, "slug": "typed-" + uuid4().hex},
        )
        connection.commit()
    with pg.connect() as connection:
        assert connection.execute(
            text(
                "SELECT qr_type,price_per_copy::text,lifecycle_status FROM public.products WHERE id=:id"
            ),
            {"id": identity},
        ).one() == ("ice", "18.75", "draft")


def test_published_product_without_verified_image_and_approved_sizes_fails_commit(
    catalog_pg,
):
    pg, _ = catalog_pg
    identity = uuid4()
    with pg.connect() as connection:
        connection.execute(
            text(
                "INSERT INTO public.products(id,slug,name,price_per_copy,commerce_model,qr_type) VALUES(:id,:slug,'Unapproved',12.30,'single_qr','lost')"
            ),
            {"id": identity, "slug": "unapproved-" + uuid4().hex},
        )
        connection.execute(
            text(
                "UPDATE public.products SET lifecycle_status='published' WHERE id=:id"
            ),
            {"id": identity},
        )
        with pytest.raises(DBAPIError):
            connection.commit()
        connection.rollback()
        assert (
            connection.execute(
                text("SELECT count(*) FROM public.products WHERE id=:id"),
                {"id": identity},
            ).scalar_one()
            == 0
        )


def test_legacy_type_and_commerce_model_cannot_be_converted(catalog_pg):
    pg, legacy = catalog_pg
    for sql in (
        "UPDATE public.products SET qr_type='lost' WHERE id=:id",
        "UPDATE public.products SET commerce_model='single_qr',qr_type='lost' WHERE id=:id",
    ):
        with pg.connect() as connection:
            with pytest.raises(DBAPIError):
                connection.execute(text(sql), {"id": legacy})
            connection.rollback()


def test_typed_product_without_selected_type_rejected(catalog_pg):
    pg, _ = catalog_pg
    with pg.connect() as connection:
        with pytest.raises(DBAPIError):
            connection.execute(
                text(
                    "INSERT INTO public.products(slug,name,price_per_copy,commerce_model) VALUES(:slug,'Missing type',12.30,'single_qr')"
                ),
                {"slug": "missing-" + uuid4().hex},
            )
        connection.rollback()
