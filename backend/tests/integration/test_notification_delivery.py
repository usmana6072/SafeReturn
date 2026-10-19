"""Real PostgreSQL worker recovery; synthetic recipients and controlled providers."""

import base64
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from pg_rehearsal import rehearsal
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from test_health import ASGIClient
from test_identity_schema import pair
from test_public_contacts import contact_sample as _contact_sample
from test_public_qr import public_sample as _public_sample

from app.core.config import Settings
from app.core.profile_crypto import decrypt, encrypt
from app.db.runtime import worker_transaction
from app.db.session import Database
from app.main import create_app
from app.workers import notifications as delivery

TARGET = "0014a_notification_delivery"
public_sample = _public_sample
contact_sample = _contact_sample


@pytest.fixture(scope="module")
def notification_database():
    with rehearsal(
        expected_revision=os.environ.get(
            "SAFERETURN_NOTIFICATION_BASE_REVISION", TARGET
        )
    ) as pg:
        with pg.connect() as c:
            pg.upgrade(c, "0014_public_finder_messages")
            c.commit()
            old = c.execute(
                text(
                    "SELECT pg_get_functiondef('public.sr_outbox_relation()'::regprocedure)"
                )
            ).scalar_one()
            c.rollback()
            pg.upgrade(c, TARGET)
            c.rollback()
            assert c.execute(
                text(
                    "SELECT to_regprocedure('public.sr_notification_recipient(uuid,integer,bytea,smallint)') IS NULL"
                )
            ).scalar_one()
            assert (
                c.execute(
                    text(
                        "SELECT pg_get_functiondef('public.sr_outbox_relation()'::regprocedure)"
                    )
                ).scalar_one()
                == old
            )
            c.rollback()
            pg.upgrade(c, TARGET)
            owner = uuid4()
            c.execute(
                text(
                    "INSERT INTO auth.users(id,email,email_confirmed_at) VALUES(:owner,'original-owner@example.test',now())"
                ),
                {"owner": owner},
            )
            pid, ids = pair(c)
            c.execute(
                text(
                    "UPDATE public.qr_codes SET public_status='active' WHERE pair_id=:pair"
                ),
                {"pair": pid},
            )
            c.execute(
                text(
                    "UPDATE public.tag_pairs SET owner_user_id=:owner,ownership_status='active',activated_at=now() WHERE id=:pair"
                ),
                {"owner": owner, "pair": pid},
            )
            c.commit()
        settings = Settings(
            profile_data_keys=SecretStr(
                json.dumps({"1": base64.urlsafe_b64encode(b"N" * 32).decode()})
            )
        )
        yield pg, Database(pg.engine), settings, owner, pid, ids["lost"]


@pytest.fixture
def sample(notification_database):
    pg, database, settings, owner, pid, qr = notification_database
    created = []

    def enqueue(*, snapshot=None, kind="finder_message.created", idempotency_key=None):
        mid, oid = uuid4(), uuid4()
        ciphertext, version = encrypt(
            settings, qr, "finder_message", "PRIVATE-FINDER-MESSAGE"
        )
        with pg.connect() as c:
            if kind == "finder_message.created":
                c.execute(
                    text(
                        "INSERT INTO public.finder_messages(id,qr_id,recipient_owner_user_id,finder_email_ciphertext,finder_contact_key_version,message_text_ciphertext,message_key_version,consent_version,consent_at) VALUES(:mid,:qr,:owner,:cipher,:version,:cipher,:version,'finder-public-v1',now())"
                    ),
                    {
                        "mid": mid,
                        "qr": qr,
                        "owner": owner,
                        "cipher": ciphertext,
                        "version": version,
                    },
                )
            c.execute(
                text(
                    "INSERT INTO public.notification_outbox(id,event_type,aggregate_type,aggregate_id,recipient_user_id,idempotency_key,recipient_email_snapshot_ciphertext,recipient_email_key_version) VALUES(:oid,:kind,:aggregate,:mid,:owner,:key,:snapshot,:version)"
                ),
                {
                    "oid": oid,
                    "kind": kind,
                    "aggregate": "finder_message"
                    if kind == "finder_message.created"
                    else "order",
                    "mid": mid,
                    "owner": owner,
                    "key": idempotency_key or f"finder-message:{mid}",
                    "snapshot": snapshot,
                    "version": 1 if snapshot is not None else None,
                },
            )
            c.commit()
        created.append(oid)
        return oid

    def row(oid):
        with pg.connect() as c:
            return (
                c.execute(
                    text("SELECT * FROM public.notification_outbox WHERE id=:id"),
                    {"id": oid},
                )
                .mappings()
                .one()
            )

    def update(sql, params=None):
        with pg.connect() as c:
            c.execute(text(sql), params or {})
            c.commit()

    def expire(oid):
        update(
            "UPDATE public.notification_outbox SET lease_until=clock_timestamp()-interval '1 second' WHERE id=:id",
            {"id": oid},
        )

    def due(oid):
        update(
            "UPDATE public.notification_outbox SET next_attempt_at=clock_timestamp()-interval '1 second' WHERE id=:id",
            {"id": oid},
        )

    value = SimpleNamespace(
        pg=pg,
        database=database,
        settings=settings,
        owner=owner,
        pair=pid,
        enqueue=enqueue,
        row=row,
        update=update,
        expire=expire,
        due=due,
    )
    try:
        yield value
    finally:
        with pg.connect() as c:
            c.execute(
                text(
                    "UPDATE public.notification_outbox SET status='dead',lease_owner=NULL,lease_until=NULL WHERE id=ANY(:ids) AND status<>'sent'"
                ),
                {"ids": created},
            )
            c.execute(
                text(
                    "UPDATE auth.users SET email='original-owner@example.test',email_confirmed_at=now(),deleted_at=NULL,banned_until=NULL WHERE id=:owner"
                ),
                {"owner": owner},
            )
            c.execute(
                text("UPDATE public.tag_pairs SET owner_user_id=:owner WHERE id=:pair"),
                {"owner": owner, "pair": pid},
            )
            c.commit()


class Provider:
    def __init__(self, error=None, callback=None):
        self.error, self.callback = error, callback
        self.calls = []
        self.delivered = {}

    def send(self, **message):
        self.calls.append(message)
        if self.callback:
            self.callback(message)
        if self.error:
            raise self.error
        return self.delivered.setdefault(
            message["idempotency_key"], f"accepted-{len(self.delivered) + 1}"
        )


def process(sample, provider, settings=None, worker="notification-test"):
    return delivery.process_one(
        sample.database, settings or sample.settings, provider, worker_id=worker
    )


def test_claim_and_encrypted_snapshot_are_committed_before_provider(sample):
    oid = sample.enqueue()

    def inspect_claim(message):
        row = sample.row(oid)
        assert row["status"] == "leased" and row["attempt_count"] == 1
        assert b"original-owner" not in bytes(
            row["recipient_email_snapshot_ciphertext"]
        )
        assert (
            decrypt(
                sample.settings,
                row["aggregate_id"],
                "owner_email",
                row["recipient_email_snapshot_ciphertext"],
                row["recipient_email_key_version"],
            )
            == message["to"]
        )
        assert "PRIVATE-FINDER" not in message["html"]
        assert str(row["aggregate_id"]) not in message["html"]

    provider = Provider(callback=inspect_claim)
    assert process(sample, provider)
    row = sample.row(oid)
    assert row["status"] == "sent" and row["sent_at"] is not None
    assert provider.calls[0]["to"] == "original-owner@example.test"
    assert not process(sample, provider)
    assert len(provider.calls) == 1


def test_transient_retry_freezes_recipient_and_provider_key(sample):
    oid = sample.enqueue()
    provider = Provider(
        delivery.NotificationProviderError(
            "provider_http_503", transient=True, retry_after=90
        )
    )
    assert process(sample, provider)
    row = sample.row(oid)
    assert row["status"] == "retry" and row["lease_owner"] is None
    with sample.pg.connect() as c:
        assert c.execute(
            text(
                "SELECT next_attempt_at>clock_timestamp()+interval '60 seconds' FROM public.notification_outbox WHERE id=:id"
            ),
            {"id": oid},
        ).scalar_one()
    frozen = bytes(row["recipient_email_snapshot_ciphertext"])
    sample.update(
        "UPDATE auth.users SET email='changed-owner@example.test' WHERE id=:id",
        {"id": sample.owner},
    )
    sample.due(oid)
    provider.error = None
    assert process(sample, provider)
    assert sample.row(oid)["status"] == "sent"
    assert bytes(sample.row(oid)["recipient_email_snapshot_ciphertext"]) == frozen
    assert provider.calls[0] == provider.calls[1]


@pytest.mark.parametrize("transient,max_attempts", [(False, 8), (True, 1)])
def test_permanent_or_exhausted_provider_failure_dead_letters(
    sample, transient, max_attempts
):
    oid = sample.enqueue()
    provider = Provider(
        delivery.NotificationProviderError("provider_failure", transient=transient)
    )
    assert process(
        sample,
        provider,
        sample.settings.model_copy(update={"notification_max_attempts": max_attempts}),
    )
    assert sample.row(oid)["status"] == "dead"
    assert not process(sample, provider)
    assert len(provider.calls) == 1


def test_crash_after_provider_acceptance_reclaims_with_same_key(sample, monkeypatch):
    oid = sample.enqueue()
    provider = Provider()
    finish = delivery._finish
    with monkeypatch.context() as patch:
        patch.setattr(
            delivery,
            "_finish",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                SQLAlchemyError("synthetic ack failure")
            ),
        )
        with pytest.raises(SQLAlchemyError):
            process(sample, provider)
    assert sample.row(oid)["status"] == "leased"
    sample.expire(oid)
    assert process(sample, provider)
    assert sample.row(oid)["attempt_count"] == 2
    assert sample.row(oid)["status"] == "sent"
    assert len(provider.calls) == 2 and len(provider.delivered) == 1
    assert delivery._finish is finish
    with sample.pg.connect() as c:
        outcomes = (
            c.execute(
                text(
                    "SELECT outcome FROM public.notification_attempts WHERE outbox_id=:id ORDER BY attempt_number"
                ),
                {"id": oid},
            )
            .scalars()
            .all()
        )
        assert outcomes == ["unknown", "success"]


def test_same_worker_id_cannot_acknowledge_old_attempt(sample):
    oid = sample.enqueue()
    with worker_transaction(sample.database, "reused-id") as session:
        first = delivery._claim_one(session, "reused-id", 60)
    sample.expire(oid)
    with worker_transaction(sample.database, "reused-id") as session:
        second = delivery._claim_one(session, "reused-id", 60)
    assert first.attempt == 1 and second.attempt == 2
    assert not delivery._finish(
        sample.database, "reused-id", first, status="sent", provider_id="stale"
    )
    assert sample.row(oid)["status"] == "leased"
    assert delivery._finish(
        sample.database,
        "reused-id",
        second,
        status="dead",
        error=delivery.NotificationProviderError("synthetic_cleanup", transient=False),
    )


def test_skip_locked_claims_are_distinct(sample):
    ids = {sample.enqueue(), sample.enqueue()}
    with worker_transaction(sample.database, "first-worker") as session:
        first = delivery._claim_one(session, "first-worker", 60)

        def claim():
            with worker_transaction(sample.database, "second-worker") as other:
                return delivery._claim_one(other, "second-worker", 60)

        with ThreadPoolExecutor(max_workers=1) as pool:
            second = pool.submit(claim).result(timeout=60)
    assert {first.id, second.id} == ids


@pytest.mark.parametrize("case", ["unverified", "deleted_message", "corrupt_snapshot"])
def test_private_or_invalid_recipient_never_calls_provider(sample, case):
    oid = sample.enqueue(
        snapshot=b"INVALID-ENCRYPTED-RECIPIENT" if case == "corrupt_snapshot" else None
    )
    if case == "unverified":
        sample.update(
            "UPDATE auth.users SET email_confirmed_at=NULL WHERE id=:id",
            {"id": sample.owner},
        )
    if case == "deleted_message":
        sample.update(
            "UPDATE public.finder_messages SET status='deleted',retention_until=now()-interval '1 minute',deleted_at=now() WHERE id=:id",
            {"id": sample.row(oid)["aggregate_id"]},
        )
    provider = Provider()
    assert process(sample, provider)
    assert sample.row(oid)["status"] == "dead" and not provider.calls


def test_ownership_transfer_keeps_original_recipient(sample):
    oid = sample.enqueue()
    other = uuid4()
    sample.update(
        "INSERT INTO auth.users(id,email,email_confirmed_at) VALUES(:id,'new-owner@example.test',now())",
        {"id": other},
    )
    sample.update(
        "UPDATE public.tag_pairs SET owner_user_id=:other WHERE id=:id",
        {"other": other, "id": sample.pair},
    )
    provider = Provider()
    assert process(sample, provider)
    assert provider.calls[0]["to"] == "original-owner@example.test"
    assert sample.row(oid)["recipient_user_id"] == sample.owner


def test_expired_idempotency_window_requires_manual_review(sample):
    oid = sample.enqueue()
    with worker_transaction(sample.database, "old-worker") as session:
        delivery._claim_one(session, "old-worker", 60)
    sample.update(
        "UPDATE public.notification_attempts SET attempted_at=clock_timestamp()-interval '24 hours' WHERE outbox_id=:id",
        {"id": oid},
    )
    sample.expire(oid)
    provider = Provider()
    assert process(sample, provider)
    assert sample.row(oid)["last_error_code"] == "idempotency_window_expired"
    assert sample.row(oid)["status"] == "dead" and not provider.calls


def test_other_events_and_future_notifications_are_not_claimed(sample):
    other = sample.enqueue(kind="payment.verified")
    future = sample.enqueue()
    sample.update(
        "UPDATE public.notification_outbox SET next_attempt_at=clock_timestamp()+interval '1 hour' WHERE id=:id",
        {"id": future},
    )
    provider = Provider()
    assert not process(sample, provider)
    assert sample.row(other)["status"] == sample.row(future)["status"] == "pending"
    assert not provider.calls


def test_recipient_projection_is_worker_only_and_lease_scoped(sample):
    oid = sample.enqueue()
    with worker_transaction(sample.database, "no-lease") as session:
        assert (
            session.execute(
                text("SELECT public.sr_notification_recipient(:id,1,NULL,NULL)"),
                {"id": oid},
            ).scalar_one()
            is None
        )
    with pytest.raises(DBAPIError), sample.pg.engine.begin() as c:
        c.execute(text("SET LOCAL ROLE safereturn_api"))
        c.execute(
            text("SELECT public.sr_notification_recipient(:id,1,NULL,NULL)"),
            {"id": oid},
        )
    with (
        pytest.raises(DBAPIError),
        worker_transaction(sample.database, "no-auth-read") as session,
    ):
        session.execute(text("SELECT email FROM auth.users"))


def test_encrypted_snapshot_cannot_be_replaced(sample):
    oid = sample.enqueue()
    provider = Provider(
        delivery.NotificationProviderError("provider_http_503", transient=True)
    )
    assert process(sample, provider)
    before = bytes(sample.row(oid)["recipient_email_snapshot_ciphertext"])
    with pytest.raises(DBAPIError), sample.pg.engine.begin() as c:
        c.execute(
            text(
                "UPDATE public.notification_outbox SET recipient_email_snapshot_ciphertext=:cipher WHERE id=:id"
            ),
            {"cipher": b"OTHER-ENCRYPTED-RECIPIENT", "id": oid},
        )
    assert bytes(sample.row(oid)["recipient_email_snapshot_ciphertext"]) == before


@pytest.fixture(scope="module")
def public_database(notification_database):
    pg, database, settings, *_ = notification_database
    app = create_app(settings)
    app.state.database = database
    return pg, ASGIClient(app)


def test_finder_parent_lock_contention_deduplicates_without_upgrade_deadlock(
    contact_sample,
):
    from test_finder_submission import submit

    pg, app, ids, *_ = contact_sample
    with ExitStack() as warmup:
        for _ in range(4):
            warmup.enter_context(pg.engine.connect())
    barrier = Barrier(2)
    original = app.state.turnstile_transport

    def verify(request):
        barrier.wait(timeout=15)
        return original.handle_request(request)

    app.state.turnstile_transport = httpx.MockTransport(verify)
    blocker = pg.engine.connect()
    blocker.execute(
        text("SELECT id FROM public.tag_pairs WHERE id=:id FOR NO KEY UPDATE"),
        {"id": ids["pair"]},
    )
    key = uuid4().hex
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(submit, contact_sample, key=key) for _ in range(2)]
            try:
                deadline = time.monotonic() + 15
                waiters = 0
                while time.monotonic() < deadline:
                    with pg.connect() as observer:
                        waiters = observer.execute(
                            text(
                                "SELECT count(*) FROM pg_stat_activity WHERE pid<>pg_backend_pid() AND wait_event_type='Lock' AND cardinality(pg_blocking_pids(pid))>0 AND query LIKE '%sr_public_submit_finder_message%' "
                            )
                        ).scalar_one()
                    if waiters == 2:
                        break
                    time.sleep(0.05)
                assert waiters == 2, (
                    "Both submissions must reach a real parent-lock wait"
                )
            finally:
                blocker.rollback()
                blocker.close()
            responses = [future.result(timeout=90) for future in futures]
            assert [response.status_code for response in responses] == [202, 202], [
                response.text for response in responses
            ]
    finally:
        blocker.close()
        app.state.turnstile_transport = original
    with pg.connect() as c:
        assert (
            c.execute(
                text("SELECT count(*) FROM public.finder_messages WHERE qr_id=:id"),
                {"id": ids["lost"]},
            ).scalar_one()
            == 1
        )
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.notification_outbox o JOIN public.finder_messages m ON m.id=o.aggregate_id WHERE m.qr_id=:id"
                ),
                {"id": ids["lost"]},
            ).scalar_one()
            == 1
        )


def test_notification_scan_privacy_browser(contact_sample):
    from public_qr_browser import run

    pg, app, ids, tokens, contacts, get, *_ = contact_sample
    projection = get("lost")
    assert projection.status_code == 200, projection.text
    assert projection.json()["features"]["finder_form_enabled"]
    run(
        (pg, ASGIClient(app), ids, tokens, contacts, get),
        test_files=[
            "tests/finder-message.spec.ts",
            "tests/notification-privacy.spec.ts",
        ],
        extra_env={"NEXT_PUBLIC_SAFERETURN_TURNSTILE_SITE_KEY": "synthetic-widget-key"},
    )
