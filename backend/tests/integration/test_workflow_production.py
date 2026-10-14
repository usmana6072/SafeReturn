"""Print/finance persistence checks, without rendering files or external writes."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from test_commerce_schema import (
    commerce_conn as _commerce_conn,
)
from test_commerce_schema import (
    migrated as _migrated,
)
from test_commerce_schema import (
    pay,
    place,
)
from test_commerce_schema import (
    sample as _sample,
)
from test_workflow_schema import as_role

migrated = _migrated
sample = _sample
commerce_conn = _commerce_conn


def run(c, statement, ids):
    return c.execute(text(statement), ids)


def production(c, ids):
    place(c, ids)
    pay(c, ids)
    return run(
        c,
        "INSERT INTO print_jobs(order_id,job_revision,template_fingerprint,render_config) VALUES(:purchase,1,'template-v1',jsonb_build_object('locale','en','margin_mm',2)) RETURNING id",
        ids,
    ).scalar_one()


def test_print_jobs_require_verified_settlement_and_allocation(commerce_conn):
    c, ids = commerce_conn
    with pytest.raises(IntegrityError):
        run(
            c,
            "INSERT INTO print_jobs(order_id,job_revision,template_fingerprint,render_config) VALUES(:purchase,1,'test','{}')",
            ids,
        )


@pytest.mark.parametrize(
    "case",
    [
        "revision",
        "render_config",
        "artifact_bucket",
        "artifact_hash",
        "ready_without_artifact",
        "job_order_binding",
    ],
)
def test_production_privacy_integrity_and_deduplication(commerce_conn, case):
    c, ids = commerce_conn
    jid = production(c, ids)
    with pytest.raises(IntegrityError):
        if case == "revision":
            run(
                c,
                "INSERT INTO print_jobs(order_id,job_revision,template_fingerprint,render_config) VALUES(:purchase,1,'test','{}')",
                ids,
            )
        elif case == "render_config":
            run(
                c,
                "INSERT INTO print_jobs(order_id,job_revision,template_fingerprint,render_config) VALUES(:purchase,2,'test',jsonb_build_object('medical_notes','private'))",
                ids,
            )
        elif case in ("artifact_bucket", "artifact_hash"):
            run(
                c,
                "INSERT INTO print_artifacts(print_job_id,bucket,object_key,format,sha256_hex,size_bytes) VALUES(:jid,:bucket,:key,'pdf',:hash,100)",
                {
                    "jid": jid,
                    "bucket": "public"
                    if case == "artifact_bucket"
                    else "private-order-print",
                    "key": str(uuid.uuid4()),
                    "hash": "invalid" if case == "artifact_hash" else "a" * 64,
                },
            )
        elif case == "job_order_binding":
            run(
                c,
                "INSERT INTO durable_jobs(job_kind,aggregate_type,aggregate_id,order_id,print_job_id,idempotency_key) VALUES('print.render','print_job',:other,:purchase,:jid,'render-1')",
                {**ids, "jid": jid, "other": uuid.uuid4()},
            )
        else:
            run(c, "UPDATE print_jobs SET status='ready' WHERE id=:jid", {"jid": jid})
            c.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


def test_durable_render_and_finance_mirror_do_not_rewrite_payment(commerce_conn):
    c, ids = commerce_conn
    jid = production(c, ids)
    run(
        c,
        "INSERT INTO durable_jobs(job_kind,aggregate_type,aggregate_id,order_id,print_job_id,idempotency_key) VALUES('print.render','print_job',:jid,:purchase,:jid,'render-1')",
        {**ids, "jid": jid},
    )
    run(
        c,
        "INSERT INTO print_artifacts(print_job_id,object_key,format,sha256_hex,size_bytes) VALUES(:jid,'private-synthetic.pdf','pdf',repeat('a',64),100)",
        {"jid": jid},
    )
    run(c, "UPDATE print_jobs SET status='ready' WHERE id=:jid", {"jid": jid})
    run(
        c,
        "INSERT INTO finance_sheet_sync(order_id,status,attempt_count,last_error_code) VALUES(:purchase,'retry',1,'PROVIDER_UNAVAILABLE')",
        ids,
    )
    c.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert (
        run(c, "SELECT payment_status FROM orders WHERE id=:purchase", ids).scalar_one()
        == "verified"
    )
    assert (
        run(c, "SELECT count(*) FROM qr_codes WHERE pair_id=:pair", ids).scalar_one()
        == 2
    )


def test_order_hold_protects_due_artifact(commerce_conn):
    c, ids = commerce_conn
    jid = production(c, ids)
    aid = run(
        c,
        "INSERT INTO print_artifacts(print_job_id,object_key,format,sha256_hex,size_bytes,retention_until) VALUES(:jid,'held.pdf','pdf',repeat('a',64),100,now()-interval '1 minute') RETURNING id",
        {"jid": jid},
    ).scalar_one()
    run(
        c,
        "INSERT INTO retention_holds(resource_type,resource_id,reason_code,placed_by) VALUES('order',:purchase,'dispute',:customer)",
        ids,
    )
    with pytest.raises(IntegrityError):
        run(c, "UPDATE print_artifacts SET deleted_at=now() WHERE id=:id", {"id": aid})


def test_cleanup_requires_due_policy_and_preserves_metadata(commerce_conn):
    c, ids = commerce_conn
    jid = production(c, ids)
    aid = run(
        c,
        "INSERT INTO print_artifacts(print_job_id,object_key,format,sha256_hex,size_bytes,retention_until) VALUES(:jid,'due.pdf','pdf',repeat('a',64),100,now()-interval '1 minute') RETURNING id",
        {"jid": jid},
    ).scalar_one()
    run(c, "UPDATE print_artifacts SET deleted_at=now() WHERE id=:id", {"id": aid})
    c.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert run(
        c, "SELECT sha256_hex,size_bytes FROM print_artifacts WHERE id=:id", {"id": aid}
    ).one() == ("a" * 64, 100)


def test_existing_purchase_rows_survive_workflow_migration(commerce_conn):
    c, ids = commerce_conn
    place(c, ids)
    assert (
        run(c, "SELECT total_pkr,order_number FROM orders WHERE id=:purchase", ids)
        .one()[0]
        .as_tuple()
        .exponent
        == -2
    )
    assert (
        run(
            c,
            "SELECT sum(copies) FROM order_item_qr_uses WHERE pair_unit_id=:unit",
            ids,
        ).scalar_one()
        == 5
    )


def test_worker_projections_require_claimed_order_and_exclude_bank_payload(
    commerce_conn,
):
    c, ids = commerce_conn
    jid = production(c, ids)
    task = run(
        c,
        "INSERT INTO durable_jobs(job_kind,aggregate_type,aggregate_id,order_id,print_job_id,idempotency_key) VALUES('print.render','print_job',:jid,:purchase,:jid,'assigned-render') RETURNING id",
        {**ids, "jid": jid},
    ).scalar_one()
    with as_role(c, "safereturn_worker", worker="renderer"):
        assert (
            run(c, "SELECT count(id) FROM orders WHERE id=:purchase", ids).scalar_one()
            == 0
        )
        run(
            c,
            "UPDATE durable_jobs SET status='leased',lease_owner='renderer',lease_until=now()+interval '1 minute',attempt_count=1 WHERE id=:task",
            {"task": task},
        )
        assert (
            run(
                c, "SELECT payment_status FROM orders WHERE id=:purchase", ids
            ).scalar_one()
            == "verified"
        )
        assert (
            run(
                c, "SELECT count(id) FROM qr_codes WHERE pair_id=:pair", ids
            ).scalar_one()
            == 2
        )
        assert (
            run(
                c, "SELECT state FROM payment_attempts WHERE id=:attempt", ids
            ).scalar_one()
            == "verified"
        )
    with pytest.raises(DBAPIError), as_role(c, "safereturn_worker", worker="renderer"):
        run(
            c,
            "SELECT sender_account_ciphertext FROM payment_attempts WHERE id=:attempt",
            ids,
        )


@pytest.mark.parametrize("role,visible", [("finance", 0), ("operations", 1)])
def test_shipping_snapshots_are_owner_or_fulfillment_only(commerce_conn, role, visible):
    c, ids = commerce_conn
    actor = uuid.uuid4()
    run(c, "INSERT INTO auth.users(id) VALUES(:id)", {"id": actor})
    run(
        c,
        "INSERT INTO staff_roles(user_id,role) VALUES(:id,:role)",
        {"id": actor, "role": role},
    )
    with as_role(c, "safereturn_api", actor, mfa=True):
        assert (
            run(
                c,
                "SELECT count(*) FROM order_shipping_snapshots WHERE order_id=:purchase",
                ids,
            ).scalar_one()
            == visible
        )
        assert (
            run(c, "SELECT count(*) FROM orders WHERE id=:purchase", ids).scalar_one()
            == 1
        )
