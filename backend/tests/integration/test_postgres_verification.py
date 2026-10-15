"""Task 1.5: real installs, preserved upgrades, commits, and concurrent races."""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from pg_rehearsal import rehearsal
from sqlalchemy import event, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from test_commerce_schema import sample as commerce_sample
from test_identity_schema import pair, qr
from test_workflow_schema import workflow_sample


def sql(c, statement, params=None):
    return c.execute(text(statement), params or {})


@pytest.fixture(scope="module")
def pg():
    with rehearsal() as isolated:
        verify_migrations(isolated)
        yield isolated


def verify_migrations(pg):
    with pg.connect() as c:
        # Roll back a genuine successful initial upgrade, then recover by retry.
        pg.upgrade(c, "0001_identity_profiles")
        assert inspect(c).has_table("qr_codes", schema="public")
        c.rollback()
        assert not inspect(c).has_table("qr_codes", schema="public")
        assert not inspect(c).has_table("alembic_version", schema="public")
        c.rollback()
        pg.upgrade(c, "0001_identity_profiles")
        _pid, tags = pair(c)
        sql(
            c,
            "INSERT INTO lost_item_profiles(qr_id,item_label,profile_version) VALUES(:id,'پہلے سے موجود 🎒',7)",
            {"id": tags["lost"]},
        )
        sql(
            c,
            "INSERT INTO ice_profiles(qr_id,medical_notes_ciphertext,medical_notes_key_version) VALUES(:id,decode('abcdef','hex'),3)",
            {"id": tags["ice"]},
        )
        c.commit()
        identity_before = {
            table: sql(
                c,
                f"SELECT row_to_json(t)::text FROM {table} t ORDER BY row_to_json(t)::text",
            )
            .scalars()
            .all()
            for table in (
                "qr_batches",
                "tag_pairs",
                "qr_codes",
                "lost_item_profiles",
                "ice_profiles",
            )
        }
        c.rollback()
        pg.upgrade(c, "0002_commerce")
        for table, rows in identity_before.items():
            assert (
                sql(
                    c,
                    f"SELECT row_to_json(t)::text FROM {table} t ORDER BY row_to_json(t)::text",
                )
                .scalars()
                .all()
                == rows
            )
        ids = commerce_sample.__wrapped__(c)
        c.commit()
        # Snapshot previous-revision data, including bytea, Decimal and timestamps.
        before = {
            table: sql(
                c,
                f"SELECT row_to_json(t)::text FROM {table} t ORDER BY row_to_json(t)::text",
            )
            .scalars()
            .all()
            for table in (
                "tag_pairs",
                "qr_codes",
                "lost_item_profiles",
                "ice_profiles",
                "orders",
                "order_items",
                "order_item_qr_uses",
                "order_shipping_snapshots",
                "payment_attempts",
            )
        }
        c.rollback()

        # Inject a real PostgreSQL error partway through revision 0003.
        # The earlier tables and any revision writes must roll back together.
        def fail_ddl(conn, cursor, statement, parameters, context, executemany):
            if statement.startswith("CREATE TABLE durable_jobs"):
                return "SELECT 1/0", {}
            return statement, parameters

        event.listen(c, "before_cursor_execute", fail_ddl, retval=True)
        try:
            with pytest.raises(DBAPIError) as failed:
                pg.upgrade(c, "0003_workflows_security")
            assert failed.value.orig.sqlstate == "22012"
        finally:
            event.remove(c, "before_cursor_execute", fail_ddl)
        c.rollback()
        assert not inspect(c).has_table("durable_jobs", schema="public")
        assert not inspect(c).has_table("finder_messages", schema="public")
        assert (
            sql(c, "SELECT version_num FROM alembic_version").scalar_one()
            == "0002_commerce"
        )
        assert (
            sql(
                c,
                "SELECT count(*) FROM pg_roles WHERE rolname=:role",
                {"role": "safereturn_worker"},
            ).scalar_one()
            == 0
        )
        c.rollback()
        # Successful role creation is transactional as well.
        pg.upgrade(c, "0003_workflows_security")
        assert (
            sql(
                c,
                "SELECT count(*) FROM pg_roles WHERE rolname=:role",
                {"role": "safereturn_worker"},
            ).scalar_one()
            == 1
        )
        c.rollback()
        assert (
            sql(
                c,
                "SELECT count(*) FROM pg_roles WHERE rolname=:role",
                {"role": "safereturn_worker"},
            ).scalar_one()
            == 0
        )
        c.rollback()
        pg.upgrade(c)
        c.commit()
        for table, rows in before.items():
            assert (
                sql(
                    c,
                    f"SELECT row_to_json(t)::text FROM {table} t ORDER BY row_to_json(t)::text",
                )
                .scalars()
                .all()
                == rows
            )
        assert (
            sql(c, "SELECT version_num FROM alembic_version").scalar_one()
            == "0005_account_session_guard"
        )
        assert len(inspect(c).get_table_names(schema="public")) == 41
        pg.assert_catalog(c)
        assert (
            sql(
                c,
                "SELECT count(*) FROM pg_class JOIN pg_namespace n ON n.oid=relnamespace WHERE n.nspname='public' AND relkind='r' AND relrowsecurity",
            ).scalar_one()
            == 40
        )
        assert (
            sql(
                c,
                "SELECT count(*) FROM pg_constraint WHERE connamespace=(SELECT oid FROM pg_namespace WHERE nspname='public') AND contype='f'",
            ).scalar_one()
            > 50
        )
        assert (
            sql(
                c,
                "SELECT count(*) FROM pg_trigger t JOIN pg_class r ON r.oid=t.tgrelid JOIN pg_namespace n ON n.oid=r.relnamespace WHERE n.nspname='public' AND NOT t.tgisinternal",
            ).scalar_one()
            > 40
        )
        c.commit()
        pg.upgrade(c)  # Repeated head upgrade is a no-op with populated records.
        c.commit()
        assert (
            sql(
                c, "SELECT count(*) FROM orders WHERE id=:id", {"id": ids["purchase"]}
            ).scalar_one()
            == 1
        )


def test_clean_install_upgrade_preservation_and_ddl_recovery(pg):
    # The module fixture performs this verification before any race, including
    # when pytest selects only a single race test.
    with pg.connect() as c:
        assert (
            sql(c, "SELECT version_num FROM alembic_version").scalar_one()
            == "0005_account_session_guard"
        )


def race(pg, actions):
    """Start independent backend sessions together; assert expected SQLSTATEs."""
    barrier = threading.Barrier(len(actions), timeout=15)

    def run(action):
        with pg.connect() as c:
            backend = sql(c, "SELECT pg_backend_pid()").scalar_one()
            barrier.wait()
            try:
                value = action(c)
                c.commit()
                return backend, "ok", value
            except DBAPIError as error:
                state = error.orig.sqlstate
                c.rollback()
                # Demonstrate the same connection is usable after failure.
                assert sql(c, "SELECT 1").scalar_one() == 1
                return backend, state, None

    with ThreadPoolExecutor(max_workers=len(actions)) as pool:
        futures = [pool.submit(run, action) for action in actions]
        results = [future.result(timeout=35) for future in futures]
    assert len({row[0] for row in results}) == len(actions)
    return [(state, value) for _, state, value in results]


def new_pair(pg):
    with pg.connect() as c:
        pid, tags = pair(c)
        c.commit()
        return pid, tags


@pytest.mark.parametrize("repeat", range(3))
def test_concurrent_retire_different_tags_cannot_leave_incomplete_pair(pg, repeat):
    pid, tags = new_pair(pg)

    def retire(qid):
        return lambda c: (
            sql(
                c,
                "UPDATE qr_codes SET is_current=false,public_status='revoked',revoked_at=now() WHERE id=:id",
                {"id": qid},
            ).rowcount
        )

    assert sorted(
        state for state, _ in race(pg, [retire(tags["lost"]), retire(tags["ice"])])
    ) == ["23514", "23514"]
    with pg.connect() as c:
        assert sql(
            c,
            "SELECT tag_type FROM qr_codes WHERE pair_id=:id AND is_current ORDER BY tag_type",
            {"id": pid},
        ).scalars().all() == ["ice", "lost"]


@pytest.mark.parametrize("repeat", range(3))
def test_concurrent_replacement_preserves_history_and_one_current_child(pg, repeat):
    pid, tags = new_pair(pg)

    def replace(c):
        sql(
            c,
            "UPDATE qr_codes SET is_current=false,public_status='revoked',revoked_at=now() WHERE id=:id",
            {"id": tags["lost"]},
        )
        return qr(c, pid, "lost", old=tags["lost"])

    results = race(pg, [replace, replace])
    assert sorted(state for state, _ in results) == ["23505", "ok"]
    with pg.connect() as c:
        assert sql(
            c,
            "SELECT count(*),count(*) FILTER(WHERE is_current) FROM qr_codes WHERE pair_id=:id",
            {"id": pid},
        ).one() == (3, 2)
        assert sql(
            c,
            "SELECT is_current,public_status FROM qr_codes WHERE id=:id",
            {"id": tags["lost"]},
        ).one() == (False, "revoked")


def drafts(pg):
    with pg.connect() as c:
        uid = uuid.uuid4()
        sql(c, "INSERT INTO auth.users(id) VALUES(:id)", {"id": uid})
        orders = [
            sql(
                c,
                "INSERT INTO orders(order_number,customer_user_id,subtotal_pkr,total_pkr) VALUES(:n,:u,0,0) RETURNING id",
                {"n": uuid.uuid4().hex, "u": uid},
            ).scalar_one()
            for _ in range(2)
        ]
        c.commit()
        return orders


@pytest.mark.parametrize("repeat", range(3))
def test_last_pair_concurrent_reservations_have_one_winner(pg, repeat):
    pid, _ = new_pair(pg)
    orders = drafts(pg)

    def reserve(oid):
        return lambda c: sql(
            c,
            "INSERT INTO order_pair_units(order_id,pair_id,reserved_until) VALUES(:o,:p,now()+interval '1 hour') RETURNING id",
            {"o": oid, "p": pid},
        ).scalar_one()

    assert sorted(state for state, _ in race(pg, [reserve(oid) for oid in orders])) == [
        "23505",
        "ok",
    ]
    with pg.connect() as c:
        assert (
            sql(
                c,
                "SELECT count(*) FROM order_pair_units WHERE pair_id=:p AND status IN ('reserved','allocated')",
                {"p": pid},
            ).scalar_one()
            == 1
        )


def test_deferred_commit_failure_savepoint_and_disconnect_recovery(pg):
    with pg.connect() as c:
        marker = uuid.uuid4().hex
        bid = sql(
            c,
            "INSERT INTO qr_batches(batch_code,ecc_level) VALUES(:m,'Q') RETURNING id",
            {"m": marker},
        ).scalar_one()
        sql(
            c,
            "INSERT INTO tag_pairs(pair_reference,batch_id) VALUES(:m,:b)",
            {"m": marker, "b": bid},
        )
        with pytest.raises(IntegrityError) as failed:
            c.commit()
        assert failed.value.orig.sqlstate == "23514"
        c.rollback()
        assert (
            sql(
                c, "SELECT count(*) FROM qr_batches WHERE id=:id", {"id": bid}
            ).scalar_one()
            == 0
        )
        pid, tags = pair(c)
        with c.begin_nested() as savepoint:
            sql(
                c,
                "UPDATE qr_codes SET is_current=false WHERE id=:id",
                {"id": tags["ice"]},
            )
            with pytest.raises(IntegrityError):
                sql(c, "SET CONSTRAINTS ALL IMMEDIATE")
            savepoint.rollback()
        c.commit()
        assert (
            sql(
                c,
                "SELECT count(*) FROM qr_codes WHERE pair_id=:id AND is_current",
                {"id": pid},
            ).scalar_one()
            == 2
        )
        c.rollback()
        # Closing the client with pending changes must roll back server-side.
        sql(c, "UPDATE lost_item_profiles SET item_label='never committed'")
    with pg.connect() as c:
        assert (
            sql(
                c,
                "SELECT count(*) FROM lost_item_profiles WHERE item_label='never committed'",
            ).scalar_one()
            == 0
        )


@pytest.mark.parametrize("repeat", range(3))
def test_concurrent_paid_allocation_is_once_and_cannot_be_recycled(pg, repeat):
    with pg.connect() as c:
        ids = commerce_sample.__wrapped__(c)
        sql(
            c,
            "UPDATE orders SET order_status='placed',placed_at=now() WHERE id=:purchase",
            ids,
        )
        sql(
            c,
            "INSERT INTO payment_reviews(attempt_id,reviewed_by,decision,bank_verified,bank_reference_fingerprint,bank_reference_key_version) VALUES(:attempt,:customer,'verify',true,:fingerprint,1)",
            {**ids, "fingerprint": uuid.uuid4().bytes},
        )
        sql(
            c,
            "UPDATE payment_attempts SET state='verified',verified_at=now(),reviewed_by=:customer WHERE id=:attempt",
            ids,
        )
        sql(c, "UPDATE orders SET payment_status='verified' WHERE id=:purchase", ids)
        c.commit()

    def allocate(c):
        return sql(
            c,
            "UPDATE order_pair_units SET status='allocated',allocated_at=now(),allocated_by=:customer WHERE id=:unit AND status='reserved'",
            ids,
        ).rowcount

    assert sorted(race(pg, [allocate, allocate])) == [("ok", 0), ("ok", 1)]
    with pg.connect() as c:
        assert sql(
            c, "SELECT status,allocated_by FROM order_pair_units WHERE id=:unit", ids
        ).one() == ("allocated", ids["customer"])
        c.rollback()
        with pytest.raises(IntegrityError) as failed:
            sql(c, "UPDATE order_pair_units SET status='released' WHERE id=:unit", ids)
        assert failed.value.orig.sqlstate == "23514"
        c.rollback()
        assert (
            sql(
                c,
                "SELECT count(*) FROM order_pair_units WHERE pair_id=:pair AND status='allocated'",
                ids,
            ).scalar_one()
            == 1
        )


def work_item(pg, table):
    with pg.connect() as c:
        if table == "notification_outbox":
            ids = workflow_sample.__wrapped__(c)
            item = ids["oa"]
        else:
            item = sql(
                c,
                "INSERT INTO durable_jobs(job_kind,aggregate_type,aggregate_id,idempotency_key) VALUES('retention.cleanup','finder_message',:id,:key) RETURNING id",
                {"id": uuid.uuid4(), "key": uuid.uuid4().hex},
            ).scalar_one()
        c.commit()
        return item


def worker(c, name):
    sql(c, "SET LOCAL ROLE safereturn_worker")
    sql(c, "SELECT set_config('safereturn.worker_id',:name,true)", {"name": name})


def claim(table, item, name, *, skip_locked=False):
    def action(c):
        worker(c, name)
        where = "id=:id"
        if skip_locked:
            where = f"id IN (SELECT id FROM {table} WHERE id=:id AND (status IN ('pending','retry') OR (status='leased' AND lease_until<=now())) AND next_attempt_at<=now() FOR UPDATE SKIP LOCKED)"
        return sql(
            c,
            f"UPDATE {table} SET status='leased',lease_owner=:name,lease_until=now()+interval '1 minute',attempt_count=attempt_count+1 WHERE {where}",
            {"id": item, "name": name},
        ).rowcount

    return action


@pytest.mark.parametrize("table", ["notification_outbox", "durable_jobs"])
@pytest.mark.parametrize("skip_locked", [False, True])
def test_concurrent_worker_claim_has_one_live_owner(pg, table, skip_locked):
    item = work_item(pg, table)
    results = race(
        pg,
        [claim(table, item, name, skip_locked=skip_locked) for name in ("one", "two")],
    )
    assert sorted(results) == [("ok", 0), ("ok", 1)]
    with pg.connect() as c:
        status, owner, attempts = sql(
            c,
            f"SELECT status,lease_owner,attempt_count FROM {table} WHERE id=:id",
            {"id": item},
        ).one()
        assert status == "leased" and owner in ("one", "two") and attempts == 1


@pytest.mark.parametrize("table", ["notification_outbox", "durable_jobs"])
def test_crashed_and_expired_worker_lease_recovery_rejects_stale_ack(pg, table):
    item = work_item(pg, table)
    with pg.connect() as c:
        # A worker connection closes before commit: its claim must disappear.
        assert claim(table, item, "crashed")(c) == 1
    with pg.connect() as c:
        assert sql(
            c, f"SELECT status,attempt_count FROM {table} WHERE id=:id", {"id": item}
        ).one() == ("pending", 0)
        assert claim(table, item, "old")(c) == 1
        c.commit()
        # Fixture clock setup only; workers cannot rewrite an expired deadline.
        sql(
            c,
            f"UPDATE {table} SET lease_until=now()-interval '1 second' WHERE id=:id",
            {"id": item},
        )
        c.commit()
    results = race(
        pg, [claim(table, item, name) for name in ("recovery-one", "recovery-two")]
    )
    assert sorted(results) == [("ok", 0), ("ok", 1)]
    with pg.connect() as c:
        owner, attempts = sql(
            c,
            f"SELECT lease_owner,attempt_count FROM {table} WHERE id=:id",
            {"id": item},
        ).one()
        assert owner in ("recovery-one", "recovery-two") and attempts == 2
        c.rollback()
        worker(c, "old")
        done, stamp = (
            ("sent", "sent_at")
            if table == "notification_outbox"
            else ("completed", "completed_at")
        )
        assert (
            sql(
                c,
                f"UPDATE {table} SET status=:done,{stamp}=now(),lease_owner=NULL,lease_until=NULL WHERE id=:id",
                {"done": done, "id": item},
            ).rowcount
            == 0
        )
        c.commit()
        worker(c, owner)
        assert (
            sql(
                c,
                f"UPDATE {table} SET status=:done,{stamp}=now(),lease_owner=NULL,lease_until=NULL WHERE id=:id",
                {"done": done, "id": item},
            ).rowcount
            == 1
        )
        c.commit()
        assert sql(
            c,
            f"SELECT status,attempt_count,lease_owner FROM {table} WHERE id=:id",
            {"id": item},
        ).one() == (done, 2, None)
