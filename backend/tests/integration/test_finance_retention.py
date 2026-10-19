"""Task 5.6 real PostgreSQL checks, synthetic fixtures and providers only."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_checkout import sample as checkout_sample  # noqa: F401
from test_fulfillment import create, move
from test_fulfillment import sample as fulfillment_sample  # noqa: F401
from test_payments import sample as payment_sample  # noqa: F401
from test_printing import sample as print_sample  # noqa: F401

from app.workers.finance_retention import (
    SheetProviderError,
    run_one_finance_sync,
    run_one_retention_cleanup,
)


class Sheets:
    def __init__(self, fail=False, callback=None):
        self.fail, self.callback, self.rows = fail, callback, {}

    def upsert(self, *, row_key, values):
        if self.callback:
            self.callback()
        if self.fail:
            raise SheetProviderError("synthetic_outage")
        self.rows[row_key] = values


class Store:
    def __init__(self, fail=False, callback=None, confirmed=True):
        self.fail, self.callback, self.confirmed = fail, callback, confirmed
        self.deleted = []

    def delete(self, *, bucket, object_key):
        self.deleted.append((bucket, object_key))
        if self.callback:
            self.callback()
        if self.fail:
            raise OSError("synthetic_ambiguous_delete")
        return self.confirmed


@pytest.fixture(scope="module")
def sample(fulfillment_sample):  # noqa: F811
    s = fulfillment_sample
    with s[0].connect() as c:
        pg = s[0]
        pg.upgrade(c, "0019_retention_recovery")
        c.rollback()
        assert c.execute(
            text(
                "SELECT to_regprocedure('public.sr_retention_prepare(uuid,integer,text)') IS NULL"
            )
        ).scalar_one()
        c.rollback()
        pg.upgrade(c, "0019_retention_recovery")
        uid = c.execute(
            text(
                "SELECT id FROM auth.users WHERE id NOT IN (SELECT user_id FROM public.staff_roles) LIMIT 1"
            )
        ).scalar_one()
        # The existing 'other' fixture is used as an isolated security principal.
        uid = UUID(s[5][0][5]["other"].hex)
        c.execute(
            text(
                "INSERT INTO public.staff_roles(user_id,role) VALUES(:id,'security_admin')"
            ),
            {"id": uid},
        )
        c.execute(
            text("UPDATE auth.sessions SET aal='aal2' WHERE user_id=:id"), {"id": uid}
        )
        c.commit()
    yield s


def finance_job(s, oid):
    with s[0].connect() as c:
        return c.execute(
            text(
                "SELECT id FROM public.durable_jobs WHERE order_id=:id AND job_kind='finance.sync' ORDER BY created_at DESC LIMIT 1"
            ),
            {"id": oid},
        ).scalar_one()


def due(s, jid):
    with s[0].connect() as c:
        c.execute(
            text(
                "UPDATE public.durable_jobs SET next_attempt_at=now()-interval '1 minute' WHERE id=:id"
            ),
            {"id": jid},
        )
        c.commit()


def ready(s, delivered=False):
    if delivered:
        body, sid = create(s)
        for old, new, extra in [
            ("preparing", "packed", {"packing_confirmed": True}),
            ("packed", "dispatched", {"tracking_reference": "SYNTHETIC"}),
            ("dispatched", "delivered", {}),
        ]:
            r = move(s, sid, old, new, **extra)
            assert r.status_code == 200, r.text
        oid = body["order_id"]
    else:
        oid = s[2]()[0]["order_id"]
    with s[0].connect() as c:
        aid = c.execute(
            text(
                "SELECT a.id FROM public.print_artifacts a JOIN public.print_jobs j ON j.id=a.print_job_id WHERE j.order_id=:id"
            ),
            {"id": oid},
        ).scalar_one()
    return oid, aid


def seed_evidence(s, oid):
    import hashlib

    from retention_live import EVIDENCE_BYTES

    evidence_id = uuid4()
    data = EVIDENCE_BYTES
    with s[0].connect() as c:
        c.execute(
            text("""INSERT INTO public.payment_evidence(id,attempt_id,object_key,sha256_hex,content_type,bytes_size,retention_until)
            SELECT :id,p.id,:key,:sha,'application/pdf',:size,now()-interval '1 hour'
            FROM public.payment_attempts p WHERE p.order_id=:oid AND p.state='verified'"""),
            {
                "id": evidence_id,
                "oid": oid,
                "key": "payment-evidence/task56/" + str(evidence_id) + ".pdf",
                "sha": hashlib.sha256(data).hexdigest(),
                "size": len(data),
            },
        )
        c.commit()
    return evidence_id


def cleanup_job(s, oid, aid, kind="print_artifact"):
    jid = uuid4()
    with s[0].connect() as c:
        c.execute(
            text(
                "INSERT INTO public.durable_jobs(id,job_kind,aggregate_type,aggregate_id,order_id,idempotency_key) VALUES(:id,'retention.cleanup',:kind,:aid,:oid,:key)"
            ),
            {
                "id": jid,
                "kind": kind,
                "aid": aid,
                "oid": oid,
                "key": "task56:" + str(jid),
            },
        )
        c.commit()
    return jid


def cfg(s):
    return s[3].state.settings.model_copy(
        update={
            "print_retention_approval": "synthetic-approved-policy",
            "evidence_retention_approval": "synthetic-finance-policy",
        }
    )


def sync(s, oid):
    from app.workers.printing import run_one

    # The payment fixture queues automatic print work as well as the explicit
    # print job. Exercise its real idempotent worker path before cleanup.
    with s[0].connect() as c:
        print_requests = (
            c.execute(
                text("""SELECT id FROM public.durable_jobs
            WHERE order_id=:id AND job_kind='allocation.finalize'
            AND status IN ('pending','retry')"""),
                {"id": oid},
            )
            .scalars()
            .all()
        )
    for job_id in print_requests:
        assert run_one(s[3].state.database, cfg(s), s[5][3], job_id)
    with s[0].connect() as c:
        jobs = (
            c.execute(
                text(
                    "SELECT id FROM public.durable_jobs WHERE order_id=:id AND job_kind='finance.sync' AND status IN ('pending','retry') ORDER BY created_at,id"
                ),
                {"id": oid},
            )
            .scalars()
            .all()
        )
    for jid in jobs:
        assert run_one_finance_sync(s[3].state.database, cfg(s), Sheets(), jid)


def elapsed(s, aid):
    with s[0].connect() as c:
        c.execute(
            text(
                "UPDATE public.print_artifacts SET retention_until=now()-interval '1 hour' WHERE id=:id"
            ),
            {"id": aid},
        )
        c.commit()


def test_finance_outage_masking_retry_and_authority(sample):
    s = sample
    oid, _ = ready(s)
    jid = finance_job(s, oid)
    assert not run_one_finance_sync(s[3].state.database, cfg(s), Sheets(True), jid)
    with s[0].connect() as c:
        assert c.execute(
            text(
                "SELECT payment_status,fulfillment_status FROM public.orders WHERE id=:id"
            ),
            {"id": oid},
        ).one() == ("verified", "allocated")
        assert c.execute(
            text(
                "SELECT status,last_error_code FROM public.finance_sheet_sync WHERE order_id=:id"
            ),
            {"id": oid},
        ).one() == ("retry", "synthetic_outage")
    due(s, jid)
    provider = Sheets()
    assert run_one_finance_sync(s[3].state.database, cfg(s), provider, jid)
    values = provider.rows[str(oid)]
    assert values["sender_account"] == "masked" and values["evidence"] == "private"
    assert not any(
        x in str(values).lower() for x in ("https://", "iban", "activation", "medical")
    )
    assert not run_one_finance_sync(s[3].state.database, cfg(s), provider, jid)


def test_finance_stale_worker_and_reclaim(sample):
    s = sample
    oid, _ = ready(s)
    jid = finance_job(s, oid)

    def expire():
        with s[0].connect() as c:
            c.execute(
                text(
                    "UPDATE public.durable_jobs SET lease_until=now()-interval '1 second' WHERE id=:id"
                ),
                {"id": jid},
            )
            c.commit()

    assert not run_one_finance_sync(
        s[3].state.database, cfg(s), Sheets(callback=expire), jid
    )
    with s[0].connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT last_export_version FROM public.finance_sheet_sync WHERE order_id=:id"
                ),
                {"id": oid},
            ).scalar_one()
            == 0
        )
    assert run_one_finance_sync(s[3].state.database, cfg(s), Sheets(), jid)


def test_api_authorization_mfa_inventory_and_holds(sample):
    s = sample
    oid, aid = ready(s)
    call = s[1]
    assert (
        call("/admin/finance/sheet-sync", role="operations", method="GET").status_code
        == 403
    )
    assert (
        call(
            "/admin/finance/sheet-sync", role="finance", mfa=False, method="GET"
        ).status_code
        == 403
    )
    assert (
        call(
            "/admin/finance/sheet-sync?limit=1", role="finance", method="GET"
        ).status_code
        == 200
    )
    r = call("/admin/storage/artifacts", method="GET")
    assert r.status_code == 200, r.text
    assert "https://" not in r.text and "download_token" not in r.text
    path = f"/admin/storage/artifacts/{aid}/retention-holds"
    for role in ("operations", "finance", "owner"):
        assert call(path, {"reason_code": "LEGAL"}, role=role).status_code == 403
    assert (
        call(path, {"reason_code": "LEGAL"}, role="other", mfa=False).status_code == 403
    )
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(2) as pool:
        holds = list(
            pool.map(
                lambda _: call(path, {"reason_code": "LEGAL"}, role="other"), range(2)
            )
        )
    assert [r.status_code for r in holds] == [201, 201]
    assert holds[0].json()["hold_id"] == holds[1].json()["hold_id"]
    for reason in ("DISPUTE", "LEGAL"):
        r = call(path, {"reason_code": reason}, role="other")
        assert r.status_code == 201, r.text
    jid = cleanup_job(s, oid, aid)
    st = Store()
    result = run_one_retention_cleanup(s[3].state.database, cfg(s), st, jid)
    assert result["result"]["reason"] == "on_hold" and not st.deleted
    assert call(path, role="other", method="DELETE").status_code == 204


def test_approval_and_delivery_required(sample):
    s = sample
    oid, aid = ready(s)
    jid = cleanup_job(s, oid, aid)
    st = Store()
    assert (
        run_one_retention_cleanup(s[3].state.database, s[3].state.settings, st, jid)[
            "result"
        ]["reason"]
        == "policy_not_approved"
    )
    due(s, jid)
    elapsed(s, aid)
    assert (
        run_one_retention_cleanup(s[3].state.database, cfg(s), st, jid)["result"][
            "reason"
        ]
        == "order_fulfillment_incomplete"
    )
    assert not st.deleted


def test_retention_intent_recovery_hold_race_and_history(sample):
    s = sample
    oid, aid = ready(s, True)
    sync(s, oid)
    elapsed(s, aid)
    jid = cleanup_job(s, oid, aid)
    st = Store(fail=True)
    result = run_one_retention_cleanup(s[3].state.database, cfg(s), st, jid)
    assert result["result"]["reason"] == "worker_exception"
    with s[0].connect() as c:
        assert c.execute(
            text(
                "SELECT deletion_hold_reason,deleted_at FROM public.print_artifacts WHERE id=:id"
            ),
            {"id": aid},
        ).one() == ("retention.deleting", None)
        with pytest.raises(DBAPIError), c.begin_nested():
            uid = c.execute(
                text(
                    "SELECT user_id FROM public.staff_roles WHERE role='security_admin' LIMIT 1"
                )
            ).scalar_one()
            c.execute(
                text(
                    "INSERT INTO public.retention_holds(resource_type,resource_id,reason_code,placed_by) VALUES('order',:id,'TOO_LATE',:uid)"
                ),
                {"id": oid, "uid": uid},
            )
    due(s, jid)
    st.fail = False
    assert run_one_retention_cleanup(s[3].state.database, cfg(s), st, jid)["result"][
        "deleted"
    ]
    assert len(st.deleted) == 2
    with s[0].connect() as c:
        a = c.execute(
            text(
                "SELECT deleted_at,sha256_hex,size_bytes FROM public.print_artifacts WHERE id=:id"
            ),
            {"id": aid},
        ).one()
        assert a[0] is not None and len(a[1]) == 64 and a[2] > 0
        assert c.execute(
            text(
                "SELECT payment_status,fulfillment_status FROM public.orders WHERE id=:id"
            ),
            {"id": oid},
        ).one() == ("verified", "delivered")
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.audit_events WHERE target_id=:id AND action='storage.artifact_deleted'"
                ),
                {"id": aid},
            ).scalar_one()
            == 1
        )
    assert run_one_retention_cleanup(s[3].state.database, cfg(s), st, jid) == {
        "claimed": False
    }


def test_unconfirmed_delete_keeps_recovery_intent(sample):
    s = sample
    oid, aid = ready(s, True)
    sync(s, oid)
    elapsed(s, aid)
    jid = cleanup_job(s, oid, aid)
    result = run_one_retention_cleanup(
        s[3].state.database, cfg(s), Store(confirmed=False), jid
    )
    assert result["result"]["reason"] == "worker_exception"
    with s[0].connect() as c:
        assert c.execute(
            text("SELECT deleted_at IS NULL FROM public.print_artifacts WHERE id=:id"),
            {"id": aid},
        ).scalar_one()


def test_cleanup_stale_completion_is_fenced(sample):
    s = sample
    oid, aid = ready(s, True)
    sync(s, oid)
    elapsed(s, aid)
    jid = cleanup_job(s, oid, aid)

    def expire():
        with s[0].connect() as c:
            c.execute(
                text(
                    "UPDATE public.durable_jobs SET lease_until=now()-interval '1 second' WHERE id=:id"
                ),
                {"id": jid},
            )
            c.commit()

    assert (
        run_one_retention_cleanup(
            s[3].state.database, cfg(s), Store(callback=expire), jid
        )["error"]
        == "lease_lost"
    )
    with s[0].connect() as c:
        assert c.execute(
            text("SELECT deleted_at IS NULL FROM public.print_artifacts WHERE id=:id"),
            {"id": aid},
        ).scalar_one()
    assert run_one_retention_cleanup(s[3].state.database, cfg(s), Store(), jid)[
        "result"
    ]["deleted"]


def test_browser(sample):
    from checkout_browser import run
    from test_health import ASGIClient

    s = sample
    _, aid = ready(s)
    app = s[3]
    app.state.checkout_fixture_user = str(s[5][0][5]["owner"])
    app.state.checkout_fixture_token = lambda: s[4]("owner")
    browser_sample = list(s[5][0])
    browser_sample[1] = ASGIClient(app)
    browser_sample[3] = app
    run(
        browser_sample,
        test_files=["tests/finance-retention.spec.ts"],
        extra_env={
            "TASK56_FINANCE_TOKEN": s[4]("finance"),
            "TASK56_OPERATIONS_TOKEN": s[4]("operations"),
            "TASK56_ARTIFACT": str(aid),
        },
    )


def test_exhaustion_visibility_security_replay_and_dedupe(sample):
    s = sample
    oid, aid = ready(s)
    jid = cleanup_job(s, oid, aid)
    settings = cfg(s).model_copy(
        update={"retention_max_attempts": 1, "print_retention_approval": None}
    )
    assert (
        run_one_retention_cleanup(s[3].state.database, settings, Store(), jid)[
            "result"
        ]["reason"]
        == "policy_not_approved"
    )
    inventory = s[1](f"/admin/storage/artifacts?order_id={oid}", method="GET").json()[
        "items"
    ]
    assert (
        next(x for x in inventory if x["id"] == str(aid))["cleanup_job"]["status"]
        == "dead"
    )
    path = f"/admin/storage/artifacts/{aid}/cleanup-retry"
    assert (
        s[1](path, {"reason_code": "SYNTHETIC_REPLAY"}, role="operations").status_code
        == 403
    )
    assert (
        s[1](
            path, {"reason_code": "SYNTHETIC_REPLAY"}, role="other", mfa=False
        ).status_code
        == 403
    )
    for _ in range(2):
        r = s[1](path, {"reason_code": "SYNTHETIC_REPLAY"}, role="other")
        assert r.status_code == 202, r.text
    with s[0].connect() as c:
        assert c.execute(
            text("SELECT status,attempt_count FROM public.durable_jobs WHERE id=:id"),
            {"id": jid},
        ).one() == ("retry", 0)
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.audit_events WHERE target_id=:id AND action='storage.cleanup_retry'"
                ),
                {"id": aid},
            ).scalar_one()
            == 1
        )


def test_payment_evidence_separate_policy_and_tombstone(sample):
    s = sample
    oid, _ = ready(s, True)
    sync(s, oid)
    aid = seed_evidence(s, oid)
    # Keep connection failures outside the expected integrity-error assertion.
    with s[0].connect() as c:  # noqa: SIM117
        with pytest.raises(DBAPIError), c.begin_nested():
            c.execute(
                text(
                    "UPDATE public.payment_evidence SET object_key='unapproved/move' WHERE id=:id"
                ),
                {"id": aid},
            )
    jid = cleanup_job(s, oid, aid, "payment_evidence")
    st = Store()
    assert (
        run_one_retention_cleanup(
            s[3].state.database,
            cfg(s).model_copy(update={"evidence_retention_approval": None}),
            st,
            jid,
        )["result"]["reason"]
        == "policy_not_approved"
    )
    assert not st.deleted
    due(s, jid)
    assert run_one_retention_cleanup(s[3].state.database, cfg(s), st, jid)["result"][
        "deleted"
    ]
    with s[0].connect() as c:
        assert c.execute(
            text(
                "SELECT deleted_at IS NOT NULL AND sha256_hex IS NOT NULL FROM public.payment_evidence WHERE id=:id"
            ),
            {"id": aid},
        ).scalar_one()
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.payment_attempts WHERE order_id=:id AND state='verified'"
                ),
                {"id": oid},
            ).scalar_one()
            == 1
        )


def test_active_jobs_and_unreconciled_finance_prevent_cleanup(sample):
    s = sample
    oid, aid = ready(s, True)
    elapsed(s, aid)
    jid = cleanup_job(s, oid, aid)
    st = Store()
    assert (
        run_one_retention_cleanup(s[3].state.database, cfg(s), st, jid)["result"][
            "reason"
        ]
        == "reconciliation_pending"
    )
    sync(s, oid)
    with s[0].connect() as c:
        case_id = c.execute(
            text(
                "INSERT INTO public.support_cases(pair_id,case_type) SELECT pair_id,'ownership_dispute' FROM public.order_pair_units WHERE order_id=:id RETURNING id"
            ),
            {"id": oid},
        ).scalar_one()
        c.commit()
    due(s, jid)
    assert (
        run_one_retention_cleanup(s[3].state.database, cfg(s), st, jid)["result"][
            "reason"
        ]
        == "reconciliation_pending"
    )
    with s[0].connect() as c:
        c.execute(
            text("UPDATE public.support_cases SET status='resolved' WHERE id=:id"),
            {"id": case_id},
        )
        c.commit()
    blocking = uuid4()
    with s[0].connect() as c:
        c.execute(
            text(
                "INSERT INTO public.durable_jobs(id,job_kind,aggregate_type,aggregate_id,order_id,idempotency_key) VALUES(:job,'finance.sync','order',:oid,:oid,:key)"
            ),
            {"job": blocking, "oid": oid, "key": "task56-block:" + str(blocking)},
        )
        c.commit()
    due(s, jid)
    assert (
        run_one_retention_cleanup(s[3].state.database, cfg(s), st, jid)["result"][
            "reason"
        ]
        == "active_jobs"
    )
    assert not st.deleted


def test_hold_committing_during_cleanup_wins_before_remote_delete(sample, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from app.workers import finance_retention as worker

    s = sample
    oid, aid = ready(s, True)
    sync(s, oid)
    elapsed(s, aid)
    jid = cleanup_job(s, oid, aid)
    st = Store()
    fence = worker.fence_retention_job
    entered = Event()

    def observed(db, lease):
        fence(db, lease)
        entered.set()

    monkeypatch.setattr(worker, "fence_retention_job", observed)
    with s[0].connect() as c, ThreadPoolExecutor(1) as pool:
        c.execute(
            text("SELECT id FROM public.orders WHERE id=:id FOR UPDATE"), {"id": oid}
        )
        future = pool.submit(
            run_one_retention_cleanup, s[3].state.database, cfg(s), st, jid
        )
        assert entered.wait(20)
        uid = c.execute(
            text(
                "SELECT user_id FROM public.staff_roles WHERE role='security_admin' LIMIT 1"
            )
        ).scalar_one()
        c.execute(
            text(
                "INSERT INTO public.retention_holds(resource_type,resource_id,reason_code,placed_by) VALUES('order',:id,'CONCURRENT_HOLD',:uid)"
            ),
            {"id": oid, "uid": uid},
        )
        c.commit()
        assert future.result(timeout=30)["result"]["reason"] == "on_hold"
    assert not st.deleted


def test_policy_scheduler_is_idempotent_and_requires_worker(sample):
    from app.db.runtime import api_transaction, worker_transaction
    from app.workers.printing import claim, run_one

    s = sample
    oid, aid = ready(s, True)
    with s[0].connect() as c:
        print_request = c.execute(
            text("""SELECT id FROM public.durable_jobs
            WHERE order_id=:id AND job_kind='allocation.finalize' AND status='pending'"""),
            {"id": oid},
        ).scalar_one()
    lease = claim(s[3].state.database, cfg(s), print_request)
    assert lease
    with worker_transaction(s[3].state.database, lease["lease_owner"]) as db:
        assert (
            db.execute(
                text("SELECT id FROM public.finance_sheet_sync WHERE order_id=:id"),
                {"id": oid},
            ).all()
            == []
        )
        assert (
            db.execute(
                text(
                    "UPDATE public.finance_sheet_sync SET status='retry' WHERE order_id=:id RETURNING id"
                ),
                {"id": oid},
            ).all()
            == []
        )
    with s[0].connect() as c:
        c.execute(
            text(
                "UPDATE public.durable_jobs SET lease_until=now()-interval '1 second' WHERE id=:id"
            ),
            {"id": print_request},
        )
        c.commit()
    assert run_one(s[3].state.database, cfg(s), s[5][3], print_request)
    sync(s, oid)
    elapsed(s, aid)
    evidence_id = seed_evidence(s, oid)
    with worker_transaction(s[3].state.database, "synthetic-scheduler") as db:
        for kind in ("print_artifact", "payment_evidence"):
            db.execute(
                text("SELECT public.sr_retention_schedule(:kind)"), {"kind": kind}
            )
            db.execute(
                text("SELECT public.sr_retention_schedule(:kind)"), {"kind": kind}
            )
    with s[0].connect() as c:
        jobs = c.execute(
            text(
                "SELECT id,aggregate_id FROM public.durable_jobs WHERE order_id=:id AND job_kind='retention.cleanup' ORDER BY aggregate_type"
            ),
            {"id": oid},
        ).all()
        assert len(jobs) == 2 and {r[1] for r in jobs} == {aid, evidence_id}
    from retention_live import retention_store

    with retention_store(s, [aid, evidence_id], Store()) as store:
        for job_id, _ in jobs:
            assert run_one_retention_cleanup(
                s[3].state.database, cfg(s), store, job_id
            )["result"]["deleted"]
    with s[0].connect() as c:
        with pytest.raises(DBAPIError), c.begin_nested():
            c.execute(
                text("UPDATE public.print_artifacts SET deleted_at=NULL WHERE id=:id"),
                {"id": aid},
            )
        with pytest.raises(DBAPIError), c.begin_nested():
            c.execute(
                text("UPDATE public.payment_evidence SET deleted_at=NULL WHERE id=:id"),
                {"id": evidence_id},
            )
    with pytest.raises(DBAPIError), api_transaction(s[3].state.database) as db:
        db.execute(text("SELECT public.sr_retention_schedule('print_artifact')"))


def test_finance_permanent_failure_and_manual_retry_deduplicate(sample):
    from app.core.config import Settings
    from app.workers.finance_retention import GoogleSheetsProvider

    s = sample
    oid, _ = ready(s)
    jid = finance_job(s, oid)
    assert not run_one_finance_sync(
        s[3].state.database,
        cfg(s),
        GoogleSheetsProvider(
            Settings(
                google_sheets_spreadsheet_id=None,
                google_sheets_service_account_json=None,
                google_sheets_approved=False,
            )
        ),
        jid,
    )
    with s[0].connect() as c:
        sync_id, status, code = c.execute(
            text(
                "SELECT id,status,last_error_code FROM public.finance_sheet_sync WHERE order_id=:id"
            ),
            {"id": oid},
        ).one()
        assert status == "failed" and code == "google_sheets_not_configured"
        assert (
            c.execute(
                text("SELECT status FROM public.durable_jobs WHERE id=:id"), {"id": jid}
            ).scalar_one()
            == "dead"
        )
    for _ in range(2):
        r = s[1](f"/admin/finance/sheet-sync/{sync_id}/retry", role="finance")
        assert r.status_code == 202, r.text
    with s[0].connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.durable_jobs WHERE order_id=:id AND job_kind='finance.sync' AND status IN ('pending','retry','leased')"
                ),
                {"id": oid},
            ).scalar_one()
            == 1
        )
        assert c.execute(
            text(
                "SELECT payment_status,fulfillment_status FROM public.orders WHERE id=:id"
            ),
            {"id": oid},
        ).one() == ("verified", "allocated")


def test_concurrent_finance_workers_publish_once(sample):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    s = sample
    oid, _ = ready(s)
    jid = finance_job(s, oid)
    entered, release = Event(), Event()

    def pause():
        entered.set()
        assert release.wait(25)

    provider = Sheets(callback=pause)
    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(
            run_one_finance_sync, s[3].state.database, cfg(s), provider, jid
        )
        assert entered.wait(25)
        try:
            assert not run_one_finance_sync(s[3].state.database, cfg(s), Sheets(), jid)
        finally:
            release.set()
        assert future.result(timeout=30)
    assert len(provider.rows) == 1
    with s[0].connect() as c:
        assert c.execute(
            text("SELECT status,attempt_count FROM public.durable_jobs WHERE id=:id"),
            {"id": jid},
        ).one() == ("completed", 1)
