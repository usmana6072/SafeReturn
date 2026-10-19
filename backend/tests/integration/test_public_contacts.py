"""Task 4.2: real PostgreSQL, synthetic encrypted data and controlled Siteverify."""

import asyncio
import base64
import hashlib
import json
import os
import uuid
from datetime import UTC, datetime
from itertools import count

import httpx
import pytest
from pg_rehearsal import rehearsal
from pydantic import SecretStr
from sqlalchemy import text
from test_health import ASGIClient
from test_public_qr import public_sample as _public_sample

from app.core.config import Settings
from app.core.profile_crypto import encrypt
from app.core.turnstile import challenge_binding
from app.db.session import Database
from app.main import create_app

public_sample = _public_sample
TARGET = "0013_public_contact_actions"
PEERS = count(1)


@pytest.fixture(scope="module")
def public_database():
    with rehearsal(
        expected_revision=os.environ.get("SAFERETURN_CONTACT_BASE_REVISION", TARGET)
    ) as pg:
        with pg.connect() as c:
            pg.upgrade(c, "0012_public_qr_projection")
            c.commit()
            old = c.execute(
                text(
                    "SELECT pg_get_functiondef('public.sr_public_qr_projection(text)'::regprocedure)"
                )
            ).scalar_one()
            c.rollback()
            pg.upgrade(c, TARGET)
            c.rollback()
            assert c.execute(
                text(
                    "SELECT to_regprocedure('public.sr_public_ice_contact(text,uuid)') IS NULL"
                )
            ).scalar_one()
            assert (
                c.execute(
                    text(
                        "SELECT pg_get_functiondef('public.sr_public_qr_projection(text)'::regprocedure)"
                    )
                ).scalar_one()
                == old
            )
            c.rollback()
            pg.upgrade(c, TARGET)
            c.commit()
        app = create_app(Settings())
        app.state.database = Database(pg.engine)
        yield pg, ASGIClient(app)


@pytest.fixture
def contact_sample(public_sample):
    pg, client, ids, tokens, contacts, get = public_sample
    settings = Settings(
        profile_data_keys=SecretStr(
            json.dumps({"1": base64.urlsafe_b64encode(b"C" * 32).decode()})
        ),
        turnstile_secret_key=SecretStr("synthetic-turnstile-secret"),
        turnstile_expected_hostname="fixture.test",
    )
    app = client.application
    app.state.settings = settings

    def provider(r):
        proof = json.loads(r.content)["response"]
        if proof == "outage":
            raise httpx.ReadTimeout("synthetic provider outage")
        if proof == "invalid":
            return httpx.Response(200, json={"success": False})
        action, binding, _ = proof.split(":")
        return httpx.Response(
            200,
            json={
                "success": True,
                "hostname": settings.turnstile_expected_hostname,
                "action": action,
                "cdata": binding,
                "challenge_ts": datetime.now(UTC).isoformat(),
            },
        )

    app.state.turnstile_transport = httpx.MockTransport(provider)
    with pg.connect() as c:
        for cid in contacts:
            cipher, version = encrypt(
                settings, ids["ice"], "ice_phone", "+923001234567", cid
            )
            c.execute(
                text(
                    "UPDATE public.ice_contacts SET phone_ciphertext=:cipher,phone_key_version=:v WHERE id=:id"
                ),
                {"cipher": cipher, "v": version, "id": cid},
            )
        cipher, version = encrypt(
            settings, ids["lost"], "whatsapp_phone", "+923005555555"
        )
        c.execute(
            text(
                "INSERT INTO public.tag_contact_preferences(qr_id,whatsapp_enabled,whatsapp_phone_ciphertext,whatsapp_phone_key_version,whatsapp_consent_at,whatsapp_consent_version) VALUES(:qr,true,:cipher,:v,now(),'wa-public-v1')"
            ),
            {"qr": ids["lost"], "cipher": cipher, "v": version},
        )
        c.commit()
    # A fresh non-routable test peer per case; no public IP spoofing dependency.
    peer_number = next(PEERS)
    peer = f"198.18.{peer_number // 254}.{peer_number % 254 + 1}"

    def proof(kind="ice", contact=None, token=None):
        action = "ice_reveal" if kind == "ice" else "whatsapp"
        cid = contacts[0] if kind == "ice" and contact is None else contact
        return (
            action
            + ":"
            + challenge_binding(action, token or tokens[kind], cid)
            + ":"
            + uuid.uuid4().hex
        )

    def post(kind="ice", contact=None, token=None, proof_value="fresh", **kwargs):
        cid = contacts[0] if contact is None else contact
        data = {"contact_id": str(cid)} if kind == "ice" else {"intent": "open_chat"}
        data["turnstile_token"] = (
            proof(kind, cid if kind == "ice" else None, token)
            if proof_value == "fresh"
            else proof_value
        )
        data.update(kwargs.pop("body", {}))

        async def send():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app, client=(peer, 123)),
                base_url="http://test",
            ) as session:
                return await session.post(
                    "/api/v1/public/qr/"
                    + (token or tokens[kind])
                    + ("/contact-reveals" if kind == "ice" else "/whatsapp-link"),
                    json=data,
                    **kwargs,
                )

        return asyncio.run(send())

    return pg, app, ids, tokens, contacts, get, settings, post, proof, peer


def test_reveal_is_requested_contact_only_and_never_in_initial_payload(
    contact_sample, caplog
):
    pg, _, _, _, contacts, get, _, post, _, _ = contact_sample
    before = get("ice")
    assert before.status_code == 200
    assert "+923001234567" not in before.text and "ciphertext" not in before.text
    r = post()
    assert r.status_code == 200, r.text
    assert r.json() == {"phone": "+923001234567", "tel_uri": "tel:+923001234567"}
    assert (
        r.headers["cache-control"] == "no-store" and r.headers["pragma"] == "no-cache"
    )
    assert str(contacts[0]) not in r.text
    assert "+923001234567" not in caplog.text
    with pg.connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.audit_events WHERE action='contact.proof'"
                )
            ).scalar_one()
            >= 1
        )


@pytest.mark.parametrize("kind", ["ice", "lost"])
@pytest.mark.parametrize("proof_value", [None, "invalid"])
def test_missing_invalid_challenge_denied_and_attempts_commit(
    contact_sample, kind, proof_value
):
    pg, _, _, _, _, _, _, post, _, peer = contact_sample
    r = post(kind, proof_value=proof_value)
    assert r.status_code == 429 and r.json()["error"]["code"] == "CHALLENGE_REQUIRED"
    with pg.connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.audit_events WHERE action='contact.peer' AND request_id=:id"
                ),
                {"id": hashlib.sha256(peer.encode()).hexdigest()},
            ).scalar_one()
            == 1
        )


@pytest.mark.parametrize("which", [1, 2, "foreign"])
def test_unpublished_removed_foreign_contacts_denied(contact_sample, which):
    _, _, _, _, contacts, _, _, post, _, _ = contact_sample
    cid = uuid.uuid4() if which == "foreign" else contacts[which]
    r = post(contact=cid)
    assert r.status_code == 404
    assert "+923001234567" not in r.text


@pytest.mark.parametrize(
    "field,value", [("published", False), ("publication_consent_version", "unapproved")]
)
def test_unpublished_or_unapproved_profile_cannot_reveal(contact_sample, field, value):
    pg, _, ids, _, _, _, _, post, _, _ = contact_sample
    with pg.connect() as c:
        c.execute(
            text(f"UPDATE public.ice_profiles SET {field}=:v WHERE qr_id=:id"),
            {"v": value, "id": ids["ice"]},
        )
        c.commit()
    assert post().status_code == 404


@pytest.mark.parametrize(
    "status", ["unactivated", "owner_disabled", "admin_suspended", "revoked"]
)
def test_unavailable_ice_tag_is_409_without_disclosure(contact_sample, status):
    pg, _, ids, _, _, _, _, post, _, _ = contact_sample
    with pg.connect() as c:
        c.execute(
            text(
                "UPDATE public.qr_codes SET public_status=CAST(:s AS varchar),revoked_at=CASE WHEN CAST(:s AS varchar)='revoked' THEN now() END WHERE id=:id"
            ),
            {"s": status, "id": ids["ice"]},
        )
        c.commit()
    assert post().status_code == 409


@pytest.mark.parametrize("kind", ["ice", "lost"])
def test_wrong_purpose_and_unknown_tokens_denied(contact_sample, kind):
    _, _, _, tokens, _, _, _, post, _, _ = contact_sample
    other = tokens["lost" if kind == "ice" else "ice"]
    assert post(kind, token=other).status_code == 404
    assert post(kind, token="unknown" * 5).status_code == 404


@pytest.mark.parametrize("kind", ["ice", "lost"])
def test_proof_replay_is_rejected(contact_sample, kind):
    _, _, _, _, _, _, _, post, proof, _ = contact_sample
    value = proof(kind)
    assert post(kind, proof_value=value).status_code == 200
    r = post(kind, proof_value=value)
    assert r.status_code == 429 and r.json()["error"]["code"] == "CHALLENGE_REQUIRED"


@pytest.mark.parametrize("kind", ["ice", "lost"])
def test_key_outage_has_no_disclosure(contact_sample, kind):
    _, _, _, _, _, _, settings, post, _, _ = contact_sample
    settings.profile_data_keys = SecretStr("{}")
    r = post(kind)
    assert r.status_code == 503
    assert "+92300" not in r.text


@pytest.mark.parametrize("provider_state", ["timeout", "bad-json", "invalid-host"])
def test_provider_outage_or_invalid_host_never_bypasses(contact_sample, provider_state):
    _, app, _, _, _, get, _, post, _, _ = contact_sample

    def failure(r):
        if provider_state == "timeout":
            raise httpx.ReadTimeout("synthetic")
        return httpx.Response(
            200,
            content="invalid"
            if provider_state == "bad-json"
            else json.dumps(
                {
                    "success": True,
                    "hostname": "attacker.test",
                    "action": "ice_reveal",
                    "cdata": "wrong",
                    "challenge_ts": datetime.now(UTC).isoformat(),
                }
            ),
        )

    app.state.turnstile_transport = httpx.MockTransport(failure)
    assert post().status_code == (429 if provider_state == "invalid-host" else 503)
    assert get("ice").status_code == 200


def test_whatsapp_consent_safe_url_and_no_message_outbox_side_effect(
    contact_sample, caplog
):
    pg, _, _, _, _, get, _, post, _, _ = contact_sample
    with pg.connect() as c:
        baseline = tuple(
            c.execute(
                text(
                    "SELECT (SELECT count(*) FROM public.finder_messages),(SELECT count(*) FROM public.notification_outbox)"
                )
            ).one()
        )
    initial = get()
    assert initial.json()["features"]["whatsapp_contact_enabled"] is True
    assert initial.json()["whatsapp_contact"]["action_available"] is True
    assert "923005555555" not in initial.text
    r = post("lost")
    assert r.status_code == 200, r.text
    assert (
        r.json()["url"]
        == "https://wa.me/923005555555?text=Hello%2C%20I%20found%20your%20item"
    )
    assert "923005555555" not in caplog.text
    with pg.connect() as c:
        assert (
            tuple(
                c.execute(
                    text(
                        "SELECT (SELECT count(*) FROM public.finder_messages),(SELECT count(*) FROM public.notification_outbox)"
                    )
                ).one()
            )
            == baseline
        )


@pytest.mark.parametrize("condition", ["off", "bad-consent", "unpublished", "disabled"])
def test_whatsapp_off_unapproved_or_disabled_denied(contact_sample, condition):
    pg, _, ids, _, _, get, _, post, _, _ = contact_sample
    with pg.connect() as c:
        if condition == "off":
            c.execute(
                text(
                    "UPDATE public.tag_contact_preferences SET whatsapp_enabled=false WHERE qr_id=:id"
                ),
                {"id": ids["lost"]},
            )
        elif condition == "bad-consent":
            c.execute(
                text(
                    "UPDATE public.tag_contact_preferences SET whatsapp_consent_version='unapproved' WHERE qr_id=:id"
                ),
                {"id": ids["lost"]},
            )
        elif condition == "unpublished":
            c.execute(
                text(
                    "UPDATE public.lost_item_profiles SET published=false WHERE qr_id=:id"
                ),
                {"id": ids["lost"]},
            )
        else:
            c.execute(
                text(
                    "UPDATE public.qr_codes SET public_status='owner_disabled' WHERE id=:id"
                ),
                {"id": ids["lost"]},
            )
        c.commit()
    r = post("lost")
    assert r.status_code == 404
    initial = get().json()
    if condition != "disabled":
        assert not initial["features"]["whatsapp_contact_enabled"]


def test_failed_reveals_consume_contact_budget_and_spoofed_ip_does_not_reset(
    contact_sample,
):
    _, _, _, _, _, _, _, post, _, _ = contact_sample
    for _ in range(5):
        assert (
            post(proof_value="invalid").json()["error"]["code"] == "CHALLENGE_REQUIRED"
        )
    r = post(headers={"X-Forwarded-For": "203.0.113.55"})
    assert r.status_code == 429 and r.json()["error"]["code"] == "RATE_LIMITED"


def test_invalid_and_oversized_input_does_not_echo_secret(contact_sample):
    _, _, _, _, _, _, _, post, _, _ = contact_sample
    secret = "PRIVATE-INPUT" * 1000
    r = post(body={"extra": secret})
    assert r.status_code == 413 and "PRIVATE-INPUT" not in r.text
    r = post(body={"contact_id": "invalid", "turnstile_token": "PRIVATE-INPUT"})
    assert r.status_code == 400 and "PRIVATE-INPUT" not in r.text


@pytest.mark.parametrize("kind", ["ice", "lost"])
def test_corrupt_or_misbound_ciphertext_never_discloses(contact_sample, kind):
    pg, _, ids, _, contacts, _, settings, post, _, _ = contact_sample
    cipher, version = encrypt(
        settings, uuid.uuid4(), "ice_phone", "+923001234567", contacts[0]
    )
    with pg.connect() as c:
        if kind == "ice":
            c.execute(
                text(
                    "UPDATE public.ice_contacts SET phone_ciphertext=:cipher,phone_key_version=:v WHERE id=:id"
                ),
                {"cipher": cipher, "v": version, "id": contacts[0]},
            )
        else:
            c.execute(
                text(
                    "UPDATE public.tag_contact_preferences SET whatsapp_phone_ciphertext=:cipher,whatsapp_phone_key_version=:v WHERE qr_id=:id"
                ),
                {"cipher": cipher, "v": version, "id": ids["lost"]},
            )
        c.commit()
    assert post(kind).status_code == 503


def test_simultaneous_same_proof_yields_one_disclosure(contact_sample):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    _, _, _, _, _, _, _, post, proof, _ = contact_sample
    value = proof()
    barrier = Barrier(2)

    def reveal():
        barrier.wait(timeout=10)
        return post(proof_value=value).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        tasks = [pool.submit(reveal) for _ in range(2)]
        assert sorted(f.result(timeout=40) for f in tasks) == [200, 429]


@pytest.mark.parametrize("kind", ["ice", "lost"])
def test_waiting_disclosure_rechecks_committed_revocation(contact_sample, kind):
    import threading
    import time
    from concurrent.futures import ThreadPoolExecutor

    from sqlalchemy import event

    pg, _, ids, _, contacts, _, _, post, _, _ = contact_sample
    attempted = threading.Event()
    requester = {}
    function = "sr_public_ice_contact" if kind == "ice" else "sr_public_whatsapp_link"

    def capture(connection, cursor, statement, parameters, context, executemany):
        if function in statement:
            requester["pid"] = connection.exec_driver_sql(
                "SELECT pg_backend_pid()"
            ).scalar_one()
            attempted.set()

    with pg.connect() as blocker:
        if kind == "ice":
            blocker.execute(
                text("UPDATE public.ice_contacts SET published=false WHERE id=:id"),
                {"id": contacts[0]},
            )
        else:
            blocker.execute(
                text(
                    "UPDATE public.tag_contact_preferences SET whatsapp_enabled=false WHERE qr_id=:id"
                ),
                {"id": ids["lost"]},
            )
        event.listen(pg.engine, "before_cursor_execute", capture)
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                task = pool.submit(post, kind)
                try:
                    assert attempted.wait(timeout=15)
                    deadline = time.monotonic() + 8
                    while time.monotonic() < deadline:
                        if blocker.execute(
                            text("SELECT cardinality(pg_blocking_pids(:pid))>0"),
                            {"pid": requester["pid"]},
                        ).scalar_one():
                            break
                        time.sleep(0.05)
                    else:
                        raise AssertionError(
                            "Expected actual PostgreSQL lock contention"
                        )
                finally:
                    blocker.commit()
                assert task.result(timeout=25).status_code == 404
        finally:
            event.remove(pg.engine, "before_cursor_execute", capture)


def test_wrong_contact_from_another_real_pair_is_denied(contact_sample):
    pg, _, _, _, _, _, settings, post, _, _ = contact_sample
    from test_identity_schema import pair

    foreign = uuid.uuid4()
    with pg.connect() as c:
        _, other = pair(c)
        c.execute(
            text("UPDATE public.qr_codes SET public_status='active' WHERE id=:id"),
            {"id": other["ice"]},
        )
        c.execute(
            text(
                "INSERT INTO public.ice_profiles(qr_id,published,publication_consent_at,publication_consent_version) VALUES(:id,true,now(),'ice-public-v1')"
            ),
            {"id": other["ice"]},
        )
        cipher, v = encrypt(
            settings, other["ice"], "ice_phone", "+923009876543", foreign
        )
        c.execute(
            text(
                "INSERT INTO public.ice_contacts(id,ice_qr_id,relationship_label,phone_ciphertext,phone_key_version,published,publication_consent_at,publication_consent_version) VALUES(:id,:qr,'Foreign',:cipher,:v,true,now(),'ice-contact-v1')"
            ),
            {"id": foreign, "qr": other["ice"], "cipher": cipher, "v": v},
        )
        c.commit()
    assert post(contact=foreign).status_code == 404


def test_cross_action_proof_is_denied(contact_sample):
    _, _, _, _, _, _, _, post, proof, _ = contact_sample
    r = post("lost", proof_value=proof("ice"))
    assert r.status_code == 429 and r.json()["error"]["code"] == "CHALLENGE_REQUIRED"


def test_peer_budget_cannot_be_reset_by_rotating_tokens(contact_sample):
    pg, _, _, _, _, _, _, post, _, peer = contact_sample
    with pg.connect() as c:
        assert c.execute(
            text(
                "SELECT bool_and(public.sr_public_contact_budget(:peer,md5(n::text)||md5(n::text),md5(n::text)||md5(n::text))) FROM generate_series(1,20) n"
            ),
            {"peer": hashlib.sha256(peer.encode()).hexdigest()},
        ).scalar_one()
        c.commit()
    r = post(token="unknown" * 5)
    assert r.status_code == 429 and r.json()["error"]["code"] == "RATE_LIMITED"


def test_real_contact_browser_and_public_scan_regression(contact_sample, public_sample):
    from public_qr_browser import run

    pg, app, ids, _, contacts, _, _, _, _, _ = contact_sample

    @app.post("/fixture/contact-state/{state}")
    def contact_state(state: str):
        assert state in ("on", "off")
        with pg.connect() as c:
            c.execute(
                text("UPDATE public.ice_contacts SET published=:v WHERE id=:id"),
                {"v": state == "on", "id": contacts[0]},
            )
            c.commit()
        return {"ok": True}

    @app.post("/fixture/whatsapp-state/{state}")
    def whatsapp_state(state: str):
        assert state in ("on", "off")
        with pg.connect() as c:
            c.execute(
                text(
                    "UPDATE public.tag_contact_preferences SET whatsapp_enabled=:v WHERE qr_id=:id"
                ),
                {"v": state == "on", "id": ids["lost"]},
            )
            c.commit()
        return {"ok": True}

    with pg.connect() as c:
        baseline = tuple(
            c.execute(
                text(
                    "SELECT (SELECT count(*) FROM public.finder_messages),(SELECT count(*) FROM public.notification_outbox)"
                )
            ).one()
        )
    run(
        public_sample,
        test_files=["tests/public-qr.spec.ts", "tests/public-contacts.spec.ts"],
        extra_env={"NEXT_PUBLIC_SAFERETURN_TURNSTILE_SITE_KEY": "synthetic-public-sitekey"},
    )
    with pg.connect() as c:
        assert (
            tuple(
                c.execute(
                    text(
                        "SELECT (SELECT count(*) FROM public.finder_messages),(SELECT count(*) FROM public.notification_outbox)"
                    )
                ).one()
            )
            == baseline
        )
