"""Finder transaction acceptance using synthetic data in an isolated schema."""

import asyncio
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import httpx
import pytest
from pg_rehearsal import rehearsal
from sqlalchemy import text
from test_health import ASGIClient
from test_public_contacts import contact_sample as _contact_sample
from test_public_qr import public_sample as _public_sample

from app.core.config import Settings
from app.core.profile_crypto import decrypt
from app.core.turnstile import challenge_binding
from app.db.session import Database
from app.main import create_app

public_sample = _public_sample
contact_sample = _contact_sample


@pytest.fixture(scope="module")
def public_database():
    with rehearsal(
        expected_revision=os.environ.get(
            "SAFERETURN_FINDER_BASE_REVISION", "0014_public_finder_messages"
        )
    ) as pg:
        with pg.connect() as c:
            pg.upgrade(c, "0013_public_contact_actions")
            c.commit()
            projection = c.execute(
                text(
                    "SELECT pg_get_functiondef('public.sr_public_qr_projection(text)'::regprocedure)"
                )
            ).scalar_one()
            c.rollback()
            pg.upgrade(c, "0014_public_finder_messages")
            c.rollback()
            assert c.execute(
                text(
                    "SELECT to_regprocedure('public.sr_public_finder_budget(text,text)') IS NULL"
                )
            ).scalar_one()
            c.rollback()
            pg.upgrade(c, "0014_public_finder_messages")
            c.commit()
            assert c.execute(
                text(
                    "SELECT pg_get_functiondef('public.sr_public_qr_projection(text)'::regprocedure)"
                )
            ).scalar_one() == projection.replace(
                "'finder_form_enabled', false",
                f"'finder_form_enabled', EXISTS(SELECT 1 FROM {pg.schema}.lost_item_profiles WHERE qr_id=qr.id AND published)",
            ).replace(
                "'location_sharing_available', false",
                f"'location_sharing_available', EXISTS(SELECT 1 FROM {pg.schema}.lost_item_profiles WHERE qr_id=qr.id AND published)",
            )
        app = create_app(Settings())
        app.state.database = Database(pg.engine)
        yield pg, ASGIClient(app)


def submit(sample, *, key=None, changes=None):
    _, app, _, tokens, _, _, _, _, _, _ = sample
    body = {
        "finder_email": "finder@example.test",
        "message": "I found your keys.",
        "contact_consent_accepted": True,
        "consent_version": "finder-public-v1",
        "turnstile_token": "finder_message:"
        + challenge_binding("finder_message", tokens["lost"])
        + ":"
        + uuid.uuid4().hex,
        **(changes or {}),
    }

    async def send():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=(sample[-1], 123)),
            base_url="http://test",
        ) as client:
            return await client.post(
                f"/api/v1/public/qr/{tokens['lost']}/finder-messages",
                json=body,
                headers={"Idempotency-Key": key} if key else {},
            )

    return asyncio.run(send())


def counts(sample):
    pg, _, ids, *_ = sample
    with pg.connect() as c:
        return tuple(
            c.execute(text(query), {"qr": ids["lost"]}).scalar_one()
            for query in (
                "SELECT count(*) FROM public.finder_messages WHERE qr_id=:qr",
                "SELECT count(*) FROM public.finder_message_locations l JOIN public.finder_messages m ON m.id=l.finder_message_id WHERE m.qr_id=:qr",
                "SELECT count(*) FROM public.notification_outbox o JOIN public.finder_messages m ON m.id=o.aggregate_id WHERE m.qr_id=:qr",
            )
        )


def test_atomic_encrypted_message_location_and_retry(contact_sample):
    key = uuid.uuid4().hex
    changes = {
        "location": {"latitude": 0.0, "longitude": 0.0},
        "location_consent": True,
    }
    response = submit(contact_sample, key=key, changes=changes)
    assert response.status_code == 202, response.text
    assert response.headers["cache-control"] == "no-store"
    assert counts(contact_sample) == (1, 1, 1)
    assert submit(contact_sample, key=key, changes=changes).status_code == 202
    assert counts(contact_sample) == (1, 1, 1)
    assert submit(contact_sample, key=key).status_code == 409
    assert counts(contact_sample) == (1, 1, 1)
    pg, _, ids, _, _, _, settings, *_ = contact_sample
    with pg.connect() as c:
        row = c.execute(
            text(
                "SELECT finder_email_ciphertext,finder_contact_key_version FROM public.finder_messages WHERE qr_id=:qr"
            ),
            {"qr": ids["lost"]},
        ).one()
        assert b"finder@example.test" not in bytes(row[0])
        assert (
            decrypt(settings, ids["lost"], "finder_email", row[0], row[1])
            == "finder@example.test"
        )


def test_missing_proof_and_consent_create_nothing(contact_sample):
    assert submit(contact_sample, changes={"turnstile_token": None}).status_code == 429
    assert (
        submit(contact_sample, changes={"contact_consent_accepted": False}).status_code
        == 400
    )
    assert counts(contact_sample) == (0, 0, 0)


def test_location_omitted_is_valid(contact_sample):
    response = submit(contact_sample)
    assert response.status_code == 202, response.text
    assert counts(contact_sample) == (1, 0, 1)


@pytest.mark.parametrize("state", ["owner_disabled", "admin_suspended", "revoked"])
def test_disabled_tag_creates_nothing(contact_sample, state):
    pg, _, ids, *_ = contact_sample
    with pg.connect() as c:
        c.execute(
            text(
                "UPDATE public.qr_codes SET public_status=CAST(:state AS varchar),revoked_at=CASE WHEN :state='revoked' THEN now() END WHERE id=:id"
            ),
            {"state": state, "id": ids["lost"]},
        )
        c.commit()
    assert submit(contact_sample).status_code == 404
    assert counts(contact_sample) == (0, 0, 0)


def test_missing_proofs_consume_persistent_budget(contact_sample):
    for _ in range(5):
        assert (
            submit(contact_sample, changes={"turnstile_token": None}).status_code == 429
        )
    response = submit(contact_sample)
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
    assert counts(contact_sample) == (0, 0, 0)


def test_proof_cannot_create_a_second_message(contact_sample):
    tokens = contact_sample[3]
    proof = (
        "finder_message:"
        + challenge_binding("finder_message", tokens["lost"])
        + ":"
        + uuid.uuid4().hex
    )
    assert submit(contact_sample, changes={"turnstile_token": proof}).status_code == 202
    assert submit(contact_sample, changes={"turnstile_token": proof}).status_code == 429
    assert counts(contact_sample) == (1, 0, 1)


def test_concurrent_retry_creates_one_message_and_outbox(contact_sample):
    key = uuid.uuid4().hex
    barrier = Barrier(2)

    def send():
        barrier.wait(timeout=10)
        return submit(contact_sample, key=key).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [pool.submit(send) for _ in range(2)]
        assert [result.result(timeout=90) for result in results] == [202, 202]
    assert counts(contact_sample) == (1, 0, 1)


def test_peer_budget_limits_rotated_tokens(public_database):
    pg, _ = public_database
    peer = uuid.uuid4().hex * 2
    with pg.connect() as c:
        c.execute(text("SET LOCAL ROLE safereturn_api"))
        results = (
            c.execute(
                text(
                    "SELECT public.sr_public_finder_budget(lpad(to_hex(n),64,'0'),:peer) FROM generate_series(1,21) AS n ORDER BY n"
                ),
                {"peer": peer},
            )
            .scalars()
            .all()
        )
        assert results == [True] * 20 + [False]


def test_outbox_failure_rolls_back_message_location_and_retry(contact_sample):
    pg, *_ = contact_sample
    with pg.connect() as c:
        c.execute(
            text(
                "CREATE FUNCTION public.finder_test_fault() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic outbox fault'; END $$"
            )
        )
        c.execute(
            text(
                "CREATE TRIGGER finder_test_fault BEFORE INSERT ON public.notification_outbox FOR EACH ROW EXECUTE FUNCTION public.finder_test_fault()"
            )
        )
        c.commit()
    key = uuid.uuid4().hex
    try:
        response = submit(contact_sample, key=key)
        assert response.status_code == 503, response.text
        assert counts(contact_sample) == (0, 0, 0)
    finally:
        with pg.connect() as c:
            c.execute(
                text("DROP TRIGGER finder_test_fault ON public.notification_outbox")
            )
            c.execute(text("DROP FUNCTION public.finder_test_fault()"))
            c.commit()
    assert submit(contact_sample, key=key).status_code == 202
    assert counts(contact_sample) == (1, 0, 1)


def test_finder_browser(contact_sample, public_database):
    from public_qr_browser import run

    projection = contact_sample[5]("lost")
    assert projection.status_code == 200, projection.text
    assert projection.json()["features"]["finder_form_enabled"] is True
    run(
        public_database_sample(contact_sample),
        test_files=["tests/finder-message.spec.ts"],
        extra_env={"NEXT_PUBLIC_SAFERETURN_TURNSTILE_SITE_KEY": "synthetic-widget-key"},
    )


def public_database_sample(sample):
    pg, app, ids, tokens, contacts, get, *_ = sample
    return pg, ASGIClient(app), ids, tokens, contacts, get
