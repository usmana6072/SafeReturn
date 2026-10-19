"""Rollback-only end-to-end workflow and recovery acceptance checks."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from test_commerce_schema import (
    commerce_conn as _commerce_conn,
)
from test_commerce_schema import (
    migrated as _migrated,
)
from test_commerce_schema import (
    pay,
    place,
    qa,
    shipment,
)
from test_commerce_schema import sample as _sample

migrated = _migrated
commerce_conn = _commerce_conn
sample = _sample


def sql(connection, statement, values):
    return connection.execute(text(statement), values)


def test_paid_print_qa_shipment_path_preserves_pair_and_order_invariants(
    commerce_conn,
):
    connection, ids = commerce_conn
    place(connection, ids)
    pay(connection, ids)

    staff_user = uuid.uuid4()
    sql(
        connection,
        "INSERT INTO auth.users(id) VALUES (:staff)",
        {"staff": staff_user},
    )
    sql(
        connection,
        "INSERT INTO staff_roles (user_id, role, granted_by) VALUES (:staff, 'operations', :staff)",
        {"staff": staff_user},
    )
    connection.execute(
        text(
            f"SET LOCAL safereturn.actor_id = '{staff_user}'; "
            "SET LOCAL safereturn.mfa_verified = 'true';"
        )
    )

    print_job = sql(
        connection,
        """
        INSERT INTO print_jobs
          (order_id,job_revision,template_fingerprint,render_config)
        VALUES (:purchase,1,'critical-workflow-v1',
                jsonb_build_object('locale','en'))
        RETURNING id
        """,
        ids,
    ).scalar_one()
    sha = "a" * 64
    sql(
        connection,
        """
        INSERT INTO print_artifacts
          (print_job_id,object_key,format,sha256_hex,size_bytes)
        VALUES (:job,:key,'pdf',:sha,128)
        """,
        {"job": print_job, "key": f"critical/{uuid.uuid4()}.pdf", "sha": sha},
    )
    sql(
        connection,
        """
        INSERT INTO print_job_qa (print_job_id, artifact_sha256, approved, inspected_by, observations, reason)
        VALUES (:job, :sha, true, :staff, '{"alignment": "passed", "contrast": "passed"}'::jsonb, 'physical inspection passed')
        """,
        {"job": print_job, "sha": sha, "staff": staff_user},
    )
    sql(
        connection,
        "UPDATE print_jobs SET status='qa_passed' WHERE id=:job",
        {"job": print_job},
    )
    qa(connection, ids)
    shipment_id = shipment(connection, ids)
    sql(
        connection,
        """
        INSERT INTO shipment_pairs (shipment_id, pair_id, packed_qa_confirmed, packed_by, packed_at)
        VALUES (:shipment, :pair, true, :staff, now())
        """,
        {"shipment": shipment_id, "pair": ids["pair"], "staff": staff_user},
    )
    sql(
        connection,
        "UPDATE shipments SET status='packed', packed_at=now() WHERE id=:shipment",
        {"shipment": shipment_id},
    )
    sql(
        connection,
        "UPDATE shipments SET status='dispatched',dispatched_at=now() WHERE id=:shipment",
        {"shipment": shipment_id},
    )
    connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

    assert sql(
        connection,
        "SELECT payment_status,order_status FROM orders WHERE id=:purchase",
        ids,
    ).one() == ("verified", "placed")
    assert (
        sql(
            connection,
            "SELECT status FROM order_pair_units WHERE id=:unit",
            ids,
        ).scalar_one()
        == "allocated"
    )
    assert (
        sql(
            connection,
            "SELECT status FROM shipments WHERE id=:shipment",
            {"shipment": shipment_id},
        ).scalar_one()
        == "dispatched"
    )


def test_failed_print_attempt_rolls_back_without_releasing_verified_allocation(
    commerce_conn,
):
    connection, ids = commerce_conn
    place(connection, ids)
    pay(connection, ids)
    before = sql(
        connection,
        """
        SELECT payment_status,
               (SELECT status FROM order_pair_units WHERE id=:unit) AS pair_status
        FROM orders WHERE id=:purchase
        """,
        ids,
    ).one()

    with pytest.raises(IntegrityError), connection.begin_nested():
        sql(
            connection,
            """
                INSERT INTO print_artifacts
                  (print_job_id,object_key,format,sha256_hex,size_bytes)
                VALUES (:missing,'failed.pdf','pdf','invalid',1)
                """,
            {"missing": uuid.uuid4()},
        )

    after = sql(
        connection,
        """
        SELECT payment_status,
               (SELECT status FROM order_pair_units WHERE id=:unit) AS pair_status
        FROM orders WHERE id=:purchase
        """,
        ids,
    ).one()
    assert after == before == ("verified", "allocated")


def test_retryable_finance_sync_and_retention_hold_survive_provider_failure(
    commerce_conn,
):
    connection, ids = commerce_conn
    place(connection, ids)
    pay(connection, ids)
    print_job = sql(
        connection,
        """
        INSERT INTO print_jobs
          (order_id,job_revision,template_fingerprint,render_config)
        VALUES (:purchase,1,'recovery-v1','{}')
        RETURNING id
        """,
        ids,
    ).scalar_one()
    artifact_id = sql(
        connection,
        """
        INSERT INTO print_artifacts
          (print_job_id,object_key,format,sha256_hex,size_bytes,retention_until)
        VALUES (:job,'recovery.pdf','pdf',repeat('b',64),256,now()-interval '1 minute')
        RETURNING id
        """,
        {"job": print_job},
    ).scalar_one()
    sync_id = sql(
        connection,
        """
        INSERT INTO finance_sheet_sync
          (order_id,status,attempt_count,last_error_code)
        VALUES (:purchase,'retry',1,'provider_unavailable')
        RETURNING id
        """,
        ids,
    ).scalar_one()
    sql(
        connection,
        """
        INSERT INTO retention_holds
          (resource_type,resource_id,reason_code,placed_by)
        VALUES ('print_artifact',:artifact,'provider-outage',:customer)
        """,
        {**ids, "artifact": artifact_id},
    )
    connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

    assert sql(
        connection,
        "SELECT status,last_error_code FROM finance_sheet_sync WHERE id=:id",
        {"id": sync_id},
    ).one() == ("retry", "provider_unavailable")
    assert sql(
        connection,
        """
        SELECT deleted_at IS NULL
        FROM print_artifacts a
        WHERE a.id=:id AND EXISTS (
          SELECT 1 FROM retention_holds h
          WHERE h.resource_type='print_artifact'
            AND h.resource_id=a.id AND h.released_at IS NULL
        )
        """,
        {"id": artifact_id},
    ).scalar_one()


def test_unpaid_order_shipment_is_blocked_by_guard(commerce_conn):
    connection, ids = commerce_conn
    place(connection, ids)
    # Order placed but not verified/paid: sr_shipment_guard must reject shipment creation
    with pytest.raises(IntegrityError), connection.begin_nested():
        shipment(connection, ids)


def test_active_retention_hold_protects_print_artifact_from_cleanup(commerce_conn):
    connection, ids = commerce_conn
    place(connection, ids)
    pay(connection, ids)
    print_job = sql(
        connection,
        """
        INSERT INTO print_jobs
          (order_id,job_revision,template_fingerprint,render_config)
        VALUES (:purchase,1,'retention-guard-v1','{}')
        RETURNING id
        """,
        ids,
    ).scalar_one()
    artifact_id = sql(
        connection,
        """
        INSERT INTO print_artifacts
          (print_job_id,object_key,format,sha256_hex,size_bytes,retention_until)
        VALUES (:job,'retained.pdf','pdf',repeat('c',64),512,now()-interval '10 minutes')
        RETURNING id
        """,
        {"job": print_job},
    ).scalar_one()

    # Place active retention hold
    sql(
        connection,
        """
        INSERT INTO retention_holds
          (resource_type,resource_id,reason_code,placed_by)
        VALUES ('print_artifact',:artifact,'legal_hold',:customer)
        """,
        {**ids, "artifact": artifact_id},
    )

    # Verify query for cleanup candidates explicitly ignores held artifacts
    eligible_for_cleanup = sql(
        connection,
        """
        SELECT count(*) FROM print_artifacts a
        WHERE a.id = :artifact
          AND a.retention_until < now()
          AND a.deleted_at IS NULL
          AND NOT EXISTS (
            SELECT 1 FROM retention_holds h
            WHERE h.resource_type = 'print_artifact'
              AND h.resource_id = a.id
              AND h.released_at IS NULL
          )
        """,
        {"artifact": artifact_id},
    ).scalar_one()
    assert eligible_for_cleanup == 0
