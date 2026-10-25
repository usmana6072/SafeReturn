"""Opt-in disposable PostgreSQL rehearsal. Never run against a shared database."""

import json
import os
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_verified_qr_allocation_postgres import (  # noqa: F401
    actor,
    claims,
    make_order,
    pg_case,
    settle,
    stock,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("SAFERETURN_TYPED_PRINT_REHEARSAL") != "1",
    reason="Explicit isolated PostgreSQL typed print rehearsal authorization required",
)


@pytest.fixture
def typed_case(pg_case):  # noqa: F811
    with pg_case[0].connect() as c:
        pg_case[0].upgrade(c, "0042_typed_print_fulfillment")
        c.commit()
    return pg_case


def worker(c):
    c.execute(text("SET LOCAL ROLE safereturn_worker"))
    c.execute(
        text(
            "SELECT set_config('safereturn.worker_id','synthetic.print',true),set_config('safereturn.actor_id','',true),set_config('safereturn.mfa_verified','false',true)"
        )
    )


def test_handoff_rollback_and_replay_never_reallocate(typed_case):
    order = make_order(typed_case, copies=9)
    stock(typed_case)
    assert settle(typed_case, order)["allocation"]["state"] == "allocated"
    original = claims(typed_case, order[0])
    with typed_case[0].connect() as c:
        worker(c)
        assert (
            c.execute(text("SELECT public.sr_typed_print_handoff()")).scalar_one() == 1
        )
        c.rollback()
        worker(c)
        assert (
            c.execute(text("SELECT public.sr_typed_print_handoff()")).scalar_one() == 1
        )
        c.commit()
        worker(c)
        assert (
            c.execute(text("SELECT public.sr_typed_print_handoff()")).scalar_one() == 0
        )
        c.commit()
    assert claims(typed_case, order[0]) == original


def test_shortage_never_hands_off_and_runtime_cannot_read_event_table(typed_case):
    order = make_order(typed_case)
    assert settle(typed_case, order)["allocation"]["state"] == "reconciliation_pending"
    with typed_case[0].connect() as c:
        worker(c)
        assert (
            c.execute(text("SELECT public.sr_typed_print_handoff()")).scalar_one() == 0
        )
        with pytest.raises(DBAPIError):
            c.execute(text("SELECT * FROM public.typed_allocation_events"))


def test_paid_size_occurrences_use_permanent_claims_not_pairs(typed_case):
    order = make_order(typed_case, kinds=("lost", "ice"), copies=7)
    stock(typed_case)
    stock(typed_case, kind="ice")
    assert settle(typed_case, order)["allocation"]["state"] == "allocated"
    with typed_case[0].connect() as c:
        actor(c, typed_case[1])
        c.execute(text("SET LOCAL ROLE safereturn_api"))
        rows = (
            c.execute(
                text("SELECT * FROM public.sr_print_occurrences(:id)"), {"id": order[0]}
            )
            .mappings()
            .all()
        )
        assert len(rows) == 2 and sum(r["copies"] for r in rows) == 14
        assert len({r["qr_id"] for r in rows}) == 2
        assert (
            c.execute(
                text("SELECT public.sr_fulfillment_eligible(:id)"), {"id": order[0]}
            ).scalar_one()
            is False
        )
        specs = c.execute(
            text("SELECT public.sr_template_order_specs(:id)"), {"id": order[0]}
        ).scalar_one()
        assert {r["use_id"] for r in specs} == {str(r["use_id"]) for r in rows}


def test_customer_cannot_get_tokens_or_acknowledge_work(typed_case):
    order = make_order(typed_case)
    stock(typed_case)
    settle(typed_case, order)
    with typed_case[0].connect() as c:
        actor(c, typed_case[2])
        c.execute(text("SET LOCAL ROLE safereturn_api"))
        assert (
            c.execute(
                text("SELECT * FROM public.sr_print_occurrences(:id)"), {"id": order[0]}
            ).all()
            == []
        )
        with pytest.raises(DBAPIError):
            c.execute(text("SELECT public.sr_typed_print_handoff()"))


def print_fixture(case, order, *, qa=True):
    """Privileged synthetic artifact records, never provider/physical acceptance."""
    jid, aid = uuid4(), uuid4()
    with case[0].connect() as c:
        actor(c, case[1])
        c.execute(
            text(
                "SELECT public.sr_insert_print_job(:jid,:oid,1,:fp,CAST(:cfg AS jsonb),:payload,CAST(1 AS smallint))"
            ),
            {
                "jid": jid,
                "oid": order[0],
                "fp": "a" * 64,
                "cfg": json.dumps({"template_key": "safereturn-locked-v1"}),
                "payload": b"synthetic" * 8,
            },
        )
        c.execute(
            text(
                "INSERT INTO public.print_artifacts(id,print_job_id,object_key,format,sha256_hex,size_bytes) VALUES(:id,:jid,:key,'pdf',:sha,123)"
            ),
            {"id": aid, "jid": jid, "key": "synthetic/" + str(aid), "sha": "b" * 64},
        )
        c.execute(
            text("UPDATE public.print_jobs SET status='ready' WHERE id=:id"),
            {"id": jid},
        )
        ids = (
            c.execute(
                text(
                    "SELECT id FROM public.order_logical_items WHERE order_id=:id ORDER BY id"
                ),
                {"id": order[0]},
            )
            .scalars()
            .all()
        )
        if qa:
            obs = {
                key: True
                for key in (
                    "scan_passed",
                    "logo_quiet_zone_passed",
                    "bilingual_passed",
                    "cutting_packaging_passed",
                    "actual_scale_passed",
                )
            }
            obs.update(
                inspected_item_ids=[str(i) for i in ids],
                observed=[
                    dict(r)
                    for r in c.execute(
                        text(
                            "SELECT i.qr_type_snapshot AS tag_type,z.size_mm_snapshot::text AS symbol_mm,sum(z.copies)::integer AS copies FROM public.order_item_sizes z JOIN public.order_logical_items i ON i.id=z.logical_item_id WHERE i.order_id=:id GROUP BY 1,2"
                        ),
                        {"id": order[0]},
                    ).mappings()
                ],
            )
            c.execute(
                text(
                    "INSERT INTO public.print_job_qa(print_job_id,inspected_by,approved,artifact_sha256,observations,reason) VALUES(:id,:uid,true,:sha,CAST(:obs AS jsonb),'Synthetic physical attestation')"
                ),
                {"id": jid, "uid": case[1], "sha": "b" * 64, "obs": json.dumps(obs)},
            )
            c.execute(
                text("UPDATE public.print_jobs SET status='qa_passed' WHERE id=:id"),
                {"id": jid},
            )
        c.commit()
    return jid, ids


def test_shipment_commit_requires_all_items_and_packing_before_dispatch(typed_case):
    order = make_order(typed_case)
    stock(typed_case)
    settle(typed_case, order)
    jid, ids = print_fixture(typed_case, order)
    sid = uuid4()
    with typed_case[0].connect() as c:
        actor(c, typed_case[1])
        c.execute(text("SET LOCAL ROLE safereturn_api"))
        c.execute(
            text(
                "INSERT INTO public.shipments(id,order_id,shipping_address_id,carrier) SELECT :sid,order_id,source_address_id,'Synthetic' FROM public.order_shipping_snapshots WHERE order_id=:oid"
            ),
            {"sid": sid, "oid": order[0]},
        )
        with pytest.raises(DBAPIError):
            c.commit()  # The missing membership is rejected at commit.
        c.rollback()
        actor(c, typed_case[1])
        c.execute(text("SET LOCAL ROLE safereturn_api"))
        c.execute(
            text(
                "INSERT INTO public.shipments(id,order_id,shipping_address_id,carrier) SELECT :sid,order_id,source_address_id,'Synthetic' FROM public.order_shipping_snapshots WHERE order_id=:oid"
            ),
            {"sid": sid, "oid": order[0]},
        )
        for iid in ids:
            c.execute(
                text(
                    "INSERT INTO public.shipment_items(shipment_id,logical_item_id,print_job_id) VALUES(:sid,:iid,:jid)"
                ),
                {"sid": sid, "iid": iid, "jid": jid},
            )
        c.commit()
        actor(c, typed_case[1])
        c.execute(text("SET LOCAL ROLE safereturn_api"))
        c.execute(
            text(
                "UPDATE public.shipments SET status='packed',packed_at=now() WHERE id=:id"
            ),
            {"id": sid},
        )
        with pytest.raises(DBAPIError):
            c.commit()  # Physical packing flags cannot be skipped.
        c.rollback()
        actor(c, typed_case[1])
        c.execute(text("SET LOCAL ROLE safereturn_api"))
        c.execute(
            text(
                "UPDATE public.shipment_items SET packed_qa_confirmed=true,packed_by=:uid,packed_at=now() WHERE shipment_id=:id"
            ),
            {"uid": typed_case[1], "id": sid},
        )
        c.execute(
            text(
                "UPDATE public.shipments SET status='packed',packed_at=now() WHERE id=:id"
            ),
            {"id": sid},
        )
        c.execute(
            text("UPDATE public.orders SET fulfillment_status='packed' WHERE id=:id"),
            {"id": order[0]},
        )
        c.commit()


def test_stale_print_revision_cannot_be_published(typed_case):
    order = make_order(typed_case)
    stock(typed_case)
    settle(typed_case, order)
    jid, _ = print_fixture(typed_case, order, qa=False)
    with typed_case[0].connect() as c:
        actor(c, typed_case[1])
        c.execute(
            text("UPDATE public.print_jobs SET status='superseded' WHERE id=:id"),
            {"id": jid},
        )
        c.execute(
            text(
                "SELECT public.sr_insert_print_job(:jid,:oid,2,:fp,CAST(:cfg AS jsonb),:payload,CAST(1 AS smallint))"
            ),
            {
                "jid": uuid4(),
                "oid": order[0],
                "fp": "c" * 64,
                "cfg": json.dumps({"template_key": "safereturn-locked-v1"}),
                "payload": b"synthetic" * 8,
            },
        )
        c.commit()
        actor(c, typed_case[1])
        with pytest.raises(DBAPIError):
            c.execute(
                text("UPDATE public.print_jobs SET status='ready' WHERE id=:id"),
                {"id": jid},
            )
