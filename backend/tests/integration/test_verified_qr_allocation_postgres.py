"""Opt-in real PostgreSQL races/rollback in disposable rehearsal namespaces.

Synthetic privileged catalog/approval records exercise allocation, not physical QA
or publication-evidence acceptance. No guards/functions are disabled or replaced.
Each test owns a fresh namespace so stock from another case cannot affect races.
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from pg_rehearsal import rehearsal
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_print_templates import content

from app.core.inventory_secrets import new_public_token

pytestmark = pytest.mark.skipif(
    os.environ.get("SAFERETURN_VERIFIED_ALLOCATION_REHEARSAL") != "1",
    reason="Explicit isolated PostgreSQL allocation rehearsal authorization is required",
)


def actor(c, uid):
    c.execute(
        text(
            "SELECT set_config('safereturn.actor_id',:id,true),set_config('safereturn.mfa_verified','true',true)"
        ),
        {"id": str(uid)},
    )


@pytest.fixture
def pg_case():
    with rehearsal(
        expected_revision=os.environ.get(
            "SAFERETURN_VERIFIED_ALLOCATION_BASE_REVISION", "0021_support_case_console"
        )
    ) as pg:
        staff, customer, sid, category, asset, policy = (uuid4() for _ in range(6))
        catalog = {}
        with pg.connect() as c:
            pg.upgrade(c, "0040_item_checkout")
            for uid in (staff, customer):
                c.execute(
                    text(
                        "INSERT INTO auth.users(id,email_confirmed_at) VALUES(:id,now())"
                    ),
                    {"id": uid},
                )
            c.execute(
                text(
                    "INSERT INTO auth.sessions(id,user_id,aal,not_after) VALUES(:id,:uid,'aal2',now()+interval '1 hour')"
                ),
                {"id": sid, "uid": staff},
            )
            for role in ("finance", "operations"):
                c.execute(
                    text(
                        "INSERT INTO public.staff_roles(user_id,role) VALUES(:id,:role)"
                    ),
                    {"id": staff, "role": role},
                )
            legacy = c.execute(
                text(
                    "INSERT INTO public.orders(order_number,customer_user_id,subtotal_pkr,total_pkr) VALUES(:ref,:uid,9.50,9.50) RETURNING id"
                ),
                {"ref": "LEGACY-" + uuid4().hex, "uid": customer},
            ).scalar_one()
            c.commit()
            before = c.execute(
                text("SELECT to_jsonb(o) FROM public.orders o WHERE id=:id"),
                {"id": legacy},
            ).scalar_one()
            pg.upgrade(c, "0041_verified_qr_allocation")
            c.commit()
            assert (
                c.execute(
                    text("SELECT to_jsonb(o) FROM public.orders o WHERE id=:id"),
                    {"id": legacy},
                ).scalar_one()
                == before
            )
            assert (
                c.execute(
                    text("SELECT public.sr_single_checkout_enabled()")
                ).scalar_one()
                is False
            )
            # This release row exists only inside this test's isolated namespace.
            c.execute(text("UPDATE public.single_checkout_release SET enabled=true"))
            actor(c, staff)
            c.execute(
                text(
                    "INSERT INTO public.product_categories(id,slug,name) VALUES(:id,'qr-stickers','Synthetic QR stickers')"
                ),
                {"id": category},
            )
            c.execute(
                text(
                    "INSERT INTO public.print_template_asset_sets(asset_set_id,font_path,font_sha256,logo_path,logo_sha256,review_reference,reviewed_at) VALUES(:id,'synthetic/font.ttf',:hash,'synthetic/logo.svg',:hash,'SYNTHETIC fixture',now())"
                ),
                {"id": asset, "hash": "a" * 64},
            )
            c.execute(
                text(
                    "INSERT INTO public.template_production_policies(policy_id,version,sha256,body,reviewed_by,archive_reference) VALUES(:id,1,:hash,CAST(:body AS jsonb),:staff,'SYNTHETIC-fixture')"
                ),
                {
                    "id": policy,
                    "hash": "b" * 64,
                    "body": json.dumps(
                        {"canonical_origin": "https://synthetic.invalid"}
                    ),
                    "staff": staff,
                },
            )
            for kind in ("lost", "ice"):
                pid, vid, tid, rid, approval = (uuid4() for _ in range(5))
                key = "synthetic-" + uuid4().hex
                body = {**content(), "asset_set_id": str(asset)}
                c.execute(
                    text(
                        "INSERT INTO public.print_templates(template_id,key,name,purpose,created_by) VALUES(:id,:key,'Synthetic',:kind,:staff)"
                    ),
                    {"id": tid, "key": key, "kind": kind, "staff": staff},
                )
                c.execute(
                    text(
                        "INSERT INTO public.print_template_revisions(revision_id,template_id,version,content,version_note,created_by,updated_by) VALUES(:id,:tid,1,CAST(:content AS jsonb),'SYNTHETIC fixture',:staff,:staff)"
                    ),
                    {
                        "id": rid,
                        "tid": tid,
                        "content": json.dumps(body),
                        "staff": staff,
                    },
                )
                c.execute(
                    text("""INSERT INTO public.template_qa_approvals(approval_id,evidence_id,revision_id,revision_row_version,revision_fingerprint_sha256,evidence_sha256,policy_id,policy_version,summary,ciphertext,key_version,importer_human,expires_at,consumed_at,consumed_by)
                 VALUES(:id,:evidence,:rid,1,:hash,:hash,:policy,1,'{"attestations":[],"archive_references":[]}'::jsonb,:cipher,1,:staff,now()+interval '1 day',now(),:staff)"""),
                    {
                        "id": approval,
                        "evidence": uuid4(),
                        "rid": rid,
                        "hash": "c" * 64,
                        "policy": policy,
                        "cipher": b"s" * 40,
                        "staff": staff,
                    },
                )
                c.execute(
                    text(
                        "UPDATE public.print_template_revisions SET status='published',fingerprint_sha256=:hash,published_at=now(),approval_id=:approval WHERE revision_id=:rid"
                    ),
                    {"hash": "c" * 64, "approval": approval, "rid": rid},
                )
                c.execute(
                    text(
                        "INSERT INTO public.products(id,category_id,slug,name,price_per_copy,max_order_copies,commerce_model,qr_type,allows_new_pair) VALUES(:id,:cat,:slug,:name,1.00,100,'single_qr',:kind,false)"
                    ),
                    {
                        "id": pid,
                        "cat": category,
                        "slug": "synthetic-" + uuid4().hex,
                        "name": "Synthetic " + kind,
                        "kind": kind,
                    },
                )
                c.execute(
                    text(
                        "INSERT INTO public.product_variants(id,product_id,sku,name,size_mm,material,unit_price,fulfillment_method,template_key,template_version) VALUES(:id,:pid,:sku,'35 mm',35,'synthetic-paper',1,'pdf_label',:key,1)"
                    ),
                    {
                        "id": vid,
                        "pid": pid,
                        "sku": "SYNTHETIC-" + uuid4().hex,
                        "key": key,
                    },
                )
                c.execute(
                    text(
                        "INSERT INTO public.template_registry_sources(variant_id) VALUES(:id)"
                    ),
                    {"id": vid},
                )
                c.execute(
                    text(
                        "INSERT INTO public.print_template_variant_bindings(variant_id,tag_type,revision_id) VALUES(:vid,:kind,:rid)"
                    ),
                    {"vid": vid, "kind": kind, "rid": rid},
                )
                c.execute(
                    text(
                        "INSERT INTO public.product_images(product_id,cloudinary_public_id,alt_text,is_primary,verified_public_url) VALUES(:id,:public_id,'Synthetic fixture',true,'https://res.cloudinary.com/synthetic/image/upload/v1/fixture.png')"
                    ),
                    {"id": pid, "public_id": "synthetic/" + uuid4().hex},
                )
                c.execute(
                    text(
                        "UPDATE public.products SET lifecycle_status='published' WHERE id=:id"
                    ),
                    {"id": pid},
                )
                catalog[kind] = (pid, vid)
            c.commit()
        yield pg, staff, customer, sid, catalog


def make_order(case, kinds=("lost",), copies=3):
    pg, _staff, customer, _, catalog = case
    oid, address = uuid4(), uuid4()
    with pg.connect() as c:
        actor(c, customer)
        c.execute(
            text(
                "INSERT INTO public.orders(id,order_number,customer_user_id,commerce_model,payment_instructions_snapshot,subtotal_pkr,total_pkr) VALUES(:id,:ref,:uid,'single_qr',jsonb_build_object('version','SYNTHETIC'),:total,:total)"
            ),
            {
                "id": oid,
                "ref": "SYNTHETIC-" + uuid4().hex,
                "uid": customer,
                "total": len(kinds) * copies,
            },
        )
        c.execute(
            text(
                "INSERT INTO public.shipping_addresses(id,customer_user_id,recipient_name_ciphertext,phone_ciphertext,address_ciphertext,city,key_version) VALUES(:id,:uid,:cipher,:cipher,:cipher,'Synthetic',1)"
            ),
            {"id": address, "uid": customer, "cipher": b"synthetic-ciphertext"},
        )
        c.execute(
            text(
                "INSERT INTO public.order_shipping_snapshots(order_id,source_address_id,recipient_name_ciphertext,phone_ciphertext,address_ciphertext,city,key_version) VALUES(:id,:address,:cipher,:cipher,:cipher,'Synthetic',1)"
            ),
            {"id": oid, "address": address, "cipher": b"synthetic-ciphertext"},
        )
        for index, kind in enumerate(kinds):
            pid, vid = catalog[kind]
            iid = c.execute(
                text(
                    "INSERT INTO public.order_logical_items(order_id,product_id,identity_group,product_name_snapshot,qr_type_snapshot,quantity,unit_price_snapshot,line_total,max_copies_snapshot,product_version_snapshot) SELECT :oid,p.id,:group,p.name,p.qr_type,:copies,p.price_per_copy,:copies*p.price_per_copy,p.max_order_copies,p.catalog_version FROM public.products p WHERE p.id=:pid RETURNING id"
                ),
                {
                    "oid": oid,
                    "group": "distinct-" + str(index),
                    "copies": copies,
                    "pid": pid,
                },
            ).scalar_one()
            c.execute(
                text(
                    "INSERT INTO public.order_item_sizes(logical_item_id,variant_id,variant_name_snapshot,sku_snapshot,size_mm_snapshot,material_snapshot,copies,variant_version_snapshot,print_spec_snapshot) SELECT :iid,v.id,v.name,v.sku,v.size_mm,v.material,:copies,v.catalog_version,public.sr_template_resolve(v.id,jsonb_build_array(jsonb_build_object('tag_type',CAST(:kind AS text))))->0 FROM public.product_variants v WHERE id=:vid"
                ),
                {"iid": iid, "copies": copies, "kind": kind, "vid": vid},
            )
        c.execute(
            text(
                "UPDATE public.orders SET order_status='placed',placed_at=clock_timestamp() WHERE id=:id"
            ),
            {"id": oid},
        )
        aid = c.execute(
            text(
                "INSERT INTO public.payment_attempts(order_id,provider_key,idempotency_key,amount,state) VALUES(:id,'manual_bank',:key,:amount,'submitted') RETURNING id"
            ),
            {"id": oid, "key": uuid4().hex, "amount": len(kinds) * copies},
        ).scalar_one()
        c.commit()
    return oid, aid, len(kinds) * copies


def stock(case, kind="lost", quantity=1):
    pg, staff, _, sid, _ = case
    with pg.connect() as c:
        actor(c, staff)
        c.execute(
            text(
                "SELECT public.sr_typed_inventory_generate(:sid,:label,:kind,:quantity,'Q',:key,CAST(:tokens AS jsonb))"
            ),
            {
                "sid": sid,
                "label": "STOCK-" + uuid4().hex[:20],
                "kind": kind,
                "quantity": quantity,
                "key": uuid4().hex,
                "tokens": json.dumps([new_public_token() for _ in range(quantity)]),
            },
        )
        c.commit()


def settle(case, order, fingerprint=None, barrier=None):
    pg, staff, _, sid, _ = case
    with pg.connect() as c:
        actor(c, staff)
        c.execute(text("SET LOCAL ROLE safereturn_api"))
        if barrier:
            barrier.wait(timeout=20)
        try:
            result = c.execute(
                text(
                    "SELECT public.sr_typed_settle(:sid,:aid,true,:amount,'PKR',:fingerprint,'Synthetic independent bank review')"
                ),
                {
                    "sid": sid,
                    "aid": order[1],
                    "amount": order[2],
                    "fingerprint": fingerprint or os.urandom(32),
                },
            ).scalar_one()
            c.commit()
            return result
        except DBAPIError:
            c.rollback()
            return {"error": "TRANSACTION_CONFLICT"}


def claims(case, oid):
    with case[0].connect() as c:
        return c.execute(
            text(
                "SELECT logical_item_id,qr_id FROM public.order_item_qr_allocations WHERE order_id=:id ORDER BY logical_item_id"
            ),
            {"id": oid},
        ).all()


def test_same_attempt_different_review_transactions_race(pg_case):
    order = make_order(pg_case)
    stock(pg_case)
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda _: settle(pg_case, order, barrier=barrier), range(2))
        )
    assert sum(result.get("state") == "verified" for result in results) == 1
    assert len(claims(pg_case, order[0])) == 1


def test_different_attempts_for_same_order_cannot_verify_twice(pg_case):
    first = make_order(pg_case)
    pg, _, customer, _, _ = pg_case
    with pg.connect() as c:
        actor(c, customer)
        aid = c.execute(
            text(
                "INSERT INTO public.payment_attempts(order_id,provider_key,idempotency_key,amount,state) VALUES(:id,'manual_bank',:key,:amount,'submitted') RETURNING id"
            ),
            {"id": first[0], "key": uuid4().hex, "amount": first[2]},
        ).scalar_one()
        c.commit()
    stock(pg_case)
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda order: settle(pg_case, order, barrier=barrier),
                (first, (first[0], aid, first[2])),
            )
        )
    assert sum(r.get("state") == "verified" for r in results) == 1
    assert len(claims(pg_case, first[0])) == 1


def test_settlement_replay_cannot_replace_permanent_qr(pg_case):
    order = make_order(pg_case)
    stock(pg_case, quantity=2)
    assert settle(pg_case, order)["state"] == "verified"
    original = claims(pg_case, order[0])
    assert settle(pg_case, order)["error"] == "PAYMENT_CLOSED"
    assert claims(pg_case, order[0]) == original


def test_last_identity_is_never_allocated_to_two_orders(pg_case):
    first, second = make_order(pg_case), make_order(pg_case)
    stock(pg_case)
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda order: settle(pg_case, order, barrier=barrier), (first, second)
            )
        )
    assert all(result["state"] == "verified" for result in results)
    assert sorted(result["allocation"]["allocated_count"] for result in results) == [
        0,
        1,
    ]
    assert len(claims(pg_case, first[0])) + len(claims(pg_case, second[0])) == 1


def test_same_bank_reference_across_orders_rolls_back_loser(pg_case):
    first, second = make_order(pg_case), make_order(pg_case)
    stock(pg_case, quantity=2)
    barrier, fingerprint = Barrier(2), os.urandom(32)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda order: settle(pg_case, order, fingerprint, barrier),
                (first, second),
            )
        )
    assert sum(result.get("state") == "verified" for result in results) == 1
    assert len(claims(pg_case, first[0])) + len(claims(pg_case, second[0])) == 1


def test_shortage_preserves_payment_without_partial_allocation_and_retry_is_permanent(
    pg_case,
):
    order = make_order(pg_case, kinds=("lost", "ice"), copies=7)
    stock(pg_case)
    result = settle(pg_case, order)
    assert (
        result["state"] == "verified"
        and result["allocation"]["state"] == "reconciliation_pending"
    )
    assert claims(pg_case, order[0]) == []
    stock(pg_case, kind="ice")
    pg, staff, _, sid, _ = pg_case
    for _ in range(2):
        with pg.connect() as c:
            actor(c, staff)
            c.execute(text("SET LOCAL ROLE safereturn_api"))
            result = c.execute(
                text("SELECT public.sr_typed_allocation_retry(:sid,:oid)"),
                {"sid": sid, "oid": order[0]},
            ).scalar_one()
            c.commit()
            assert result["allocation"]["allocated_count"] == 2
        current = claims(pg_case, order[0])
        if _ == 0:
            original = current
        else:
            assert current == original
    assert (
        len({row.qr_id for row in original}) == 2
    )  # 14 copies still use two identities.


@pytest.mark.parametrize(
    "table,event",
    [
        ("audit_events", "INSERT"),
        ("typed_allocation_events", "INSERT"),
        ("durable_jobs", "INSERT"),
        ("standalone_qr_states", "UPDATE"),
    ],
)
def test_allocation_audit_or_enqueue_failure_rolls_back_everything(
    pg_case, table, event
):
    order = make_order(pg_case)
    stock(pg_case)
    pg, staff, _, sid, _ = pg_case
    with pg.connect() as c:
        c.execute(
            text(
                "CREATE FUNCTION public.sr_fixture_failure() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'SYNTHETIC transaction failure'; END $$"
            )
        )
        c.execute(
            text(
                f"CREATE TRIGGER sr_fixture_failure BEFORE {event} ON public.{table} FOR EACH ROW EXECUTE FUNCTION public.sr_fixture_failure()"
            )
        )
        actor(c, staff)
        c.execute(text("SET LOCAL ROLE safereturn_api"))
        with pytest.raises(DBAPIError):
            c.execute(
                text(
                    "SELECT public.sr_typed_settle(:sid,:aid,true,:amount,'PKR',:fingerprint,'Synthetic review')"
                ),
                {
                    "sid": sid,
                    "aid": order[1],
                    "amount": order[2],
                    "fingerprint": os.urandom(32),
                },
            )
            c.commit()
        c.rollback()  # Also removes only this test's injected function/trigger.
    with pg.connect() as c:
        assert (
            c.execute(
                text("SELECT payment_status FROM public.orders WHERE id=:id"),
                {"id": order[0]},
            ).scalar_one()
            == "awaiting_transfer"
        )
        assert (
            c.execute(
                text("SELECT state FROM public.payment_attempts WHERE id=:id"),
                {"id": order[1]},
            ).scalar_one()
            == "submitted"
        )
    assert claims(pg_case, order[0]) == []


def test_cancellation_request_wins_lock_and_holds_verified_order(pg_case):
    order = make_order(pg_case)
    stock(pg_case)
    pg, _, customer, _, _ = pg_case
    with pg.connect() as c:
        actor(c, customer)
        revision = c.execute(
            text("SELECT revision FROM public.orders WHERE id=:id FOR UPDATE"),
            {"id": order[0]},
        ).scalar_one()
        c.execute(
            text(
                "SELECT public.sr_cancellation_command(:id,NULL,'request',jsonb_build_object('confirmed',true,'expected_revision',:revision,'reason_code','other'))"
            ),
            {"id": order[0], "revision": revision},
        )
        c.commit()
    result = settle(pg_case, order)
    assert (
        result["state"] == "verified"
        and result["allocation"]["reason_code"] == "cancellation_review"
    )
    assert claims(pg_case, order[0]) == []


def test_cancellation_and_settlement_race_never_recycles_a_claim(pg_case):
    order = make_order(pg_case)
    stock(pg_case)
    barrier = Barrier(2)

    def cancellation():
        pg, _, customer, _, _ = pg_case
        with pg.connect() as c:
            actor(c, customer)
            barrier.wait(timeout=20)
            revision = c.execute(
                text("SELECT revision FROM public.orders WHERE id=:id FOR UPDATE"),
                {"id": order[0]},
            ).scalar_one()
            result = c.execute(
                text(
                    "SELECT public.sr_cancellation_command(:id,NULL,'request',jsonb_build_object('confirmed',true,'expected_revision',:revision,'reason_code','other'))"
                ),
                {"id": order[0], "revision": revision},
            ).scalar_one()
            c.commit()
            return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        settled, cancelled = (
            pool.submit(settle, pg_case, order, None, barrier),
            pool.submit(cancellation),
        )
        result, request = settled.result(), cancelled.result()
    assert result["state"] == "verified" and request["request_status"] == "requested"
    assigned = claims(pg_case, order[0])
    assert len(assigned) == result["allocation"]["allocated_count"]
    assert len(assigned) in (0, 1)


@pytest.mark.parametrize(
    "denial", ["finance_role", "mfa", "expired_session", "wrong_session"]
)
def test_sql_helper_rechecks_live_finance_authority(pg_case, denial):
    order = make_order(pg_case)
    stock(pg_case)
    pg, staff, _, sid, _ = pg_case
    with pg.connect() as c:
        actor(c, staff)
        if denial == "finance_role":
            c.execute(
                text(
                    "UPDATE public.staff_roles SET revoked_at=now() WHERE user_id=:id AND role='finance'"
                ),
                {"id": staff},
            )
        if denial == "expired_session":
            c.execute(
                text(
                    "UPDATE auth.sessions SET not_after=now()-interval '1 second' WHERE id=:id"
                ),
                {"id": sid},
            )
        if denial == "mfa":
            c.execute(text("SELECT set_config('safereturn.mfa_verified','false',true)"))
        c.execute(text("SET LOCAL ROLE safereturn_api"))
        result = c.execute(
            text(
                "SELECT public.sr_typed_settle(:sid,:aid,true,:amount,'PKR',:fingerprint,'Synthetic bank review')"
            ),
            {
                "sid": uuid4() if denial == "wrong_session" else sid,
                "aid": order[1],
                "amount": order[2],
                "fingerprint": os.urandom(32),
            },
        ).scalar_one()
        assert result["error"] == "FORBIDDEN"
        c.rollback()
    assert claims(pg_case, order[0]) == []


def test_runtime_has_no_claim_or_event_table_writes_and_no_customer_settlement_grant(
    pg_case,
):
    with pg_case[0].connect() as c:
        for role in ("safereturn_api", "safereturn_worker", "anon", "authenticated"):
            for table in (
                "typed_order_settlements",
                "order_item_qr_allocations",
                "typed_allocation_events",
            ):
                assert not c.execute(
                    text("SELECT has_table_privilege(:role,:relation,'INSERT')"),
                    {"role": role, "relation": "public." + table},
                ).scalar_one()
        assert not c.execute(
            text(
                "SELECT has_function_privilege('authenticated','public.sr_typed_settle(uuid,uuid,boolean,numeric,text,bytea,text)','EXECUTE')"
            )
        ).scalar_one()
