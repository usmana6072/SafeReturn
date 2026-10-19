"""Task 5.4 isolated PostgreSQL, real vector PDFs and synthetic users only."""

import json
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from print_fixture import bundle
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_auth import ORIGIN, claims, keyset, signed
from test_checkout import sample as checkout_sample  # noqa: F401
from test_health import ASGIClient
from test_payments import attempt, review
from test_payments import sample as payment_sample  # noqa: F401

from app.core.auth import JWTVerifier
from app.core.config import Settings
from app.core.print_render import PrintUnavailable
from app.db.session import Database
from app.main import create_app
from app.workers.printing import run_one


class MemoryStore:
    def __init__(self):
        self.objects = {}
        self.fail = False

    def upload(self, key, data):
        if self.fail:
            raise PrintUnavailable("synthetic_provider_down")
        if key in self.objects:
            assert self.objects[key] == data
        self.objects[key] = data
        return data


@pytest.fixture(scope="module")
def sample(payment_sample, tmp_path_factory):  # noqa: F811
    pg, _, _, app, *_ = payment_sample
    with pg.connect() as c:
        pg.upgrade(c, "0017_print_download_grants")
        c.rollback()
        assert c.execute(
            text("SELECT to_regclass('public.print_download_grants') IS NULL")
        ).scalar_one()
        c.rollback()
        pg.upgrade(c, "0017_print_download_grants")
        c.commit()
        users = {r: uuid4() for r in ("operations", "other")}
        sessions = {r: uuid4() for r in users}
        for role, uid in users.items():
            c.execute(
                text("INSERT INTO auth.users(id,email_confirmed_at) VALUES(:id,now())"),
                {"id": uid},
            )
            c.execute(
                text(
                    "INSERT INTO auth.sessions(id,user_id,aal,not_after) VALUES(:id,:uid,'aal2',now()+interval '1 hour')"
                ),
                {"id": sessions[role], "uid": uid},
            )
            c.execute(
                text(
                    "INSERT INTO public.staff_roles(user_id,role) VALUES(:id,'operations')"
                ),
                {"id": uid},
            )
        c.commit()
    for name, value in bundle(tmp_path_factory.mktemp("print") / "bundle.json").items():
        setattr(app.state.settings, name, value)
    private = ec.generate_private_key(ec.SECP256R1())
    verifier = JWTVerifier(
        Settings(supabase_url=ORIGIN),
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={"keys": [keyset(private)]})
        ),
    )
    opsapp = create_app(app.state.settings, verifier=verifier)
    opsapp.state.database = Database(pg.engine)
    opsapp.state.jwt_verifier = verifier
    opsapp.state.printing_fixture_token = lambda: signed(
        private,
        claims(
            sub=str(users["operations"]),
            session_id=str(sessions["operations"]),
            aal="aal2",
        ),
    )
    opsapp.state.printing_fixture_user = str(users["operations"])
    client = ASGIClient(opsapp)
    store = MemoryStore()

    def provider(req):
        key = req.url.path.split("private-order-print/")[-1]
        if key in store.objects:
            return httpx.Response(
                200,
                content=store.objects[key],
                headers={"content-type": "application/pdf"},
            )
        return httpx.Response(404)

    opsapp.state.print_storage_transport = httpx.MockTransport(provider)

    def call(path, body=None, key=None, role="operations", mfa=True, method="POST"):
        headers = {
            "Authorization": "Bearer "
            + signed(
                private,
                claims(
                    sub=str(users[role]),
                    session_id=str(sessions[role]),
                    aal="aal2" if mfa else "aal1",
                ),
            ),
            "Idempotency-Key": key or str(uuid4()),
        }
        return client.request(method, "/api/v1" + path, json=body, headers=headers)

    yield payment_sample, call, opsapp, store
    verifier.close()


def paid(s):
    base, _, _, _ = s
    oid, aid = attempt(base)
    assert review(base, aid)["state"] == "verified"
    return oid


def enqueue(s, oid=None, key=None):
    oid = oid or paid(s)
    r = s[1](
        f"/admin/orders/{oid}/print-jobs",
        {"reason": "Synthetic production acceptance", "expected_revision": 0},
        key,
    )
    assert r.status_code == 202, r.text
    return oid, r.json()["job_id"]


def durable(s, jid):
    with s[0][0].connect() as c:
        return c.execute(
            text(
                "SELECT id FROM public.durable_jobs WHERE print_job_id=:id AND job_kind='print.render'"
            ),
            {"id": jid},
        ).scalar_one()


def test_enqueue_retry_concurrency_auth_and_encrypted_manifest(sample):
    oid = paid(sample)
    key = str(uuid4())
    path = f"/admin/orders/{oid}/print-jobs"
    body = {"reason": "Synthetic independent acceptance", "expected_revision": 0}
    with ThreadPoolExecutor(2) as p:
        results = list(p.map(lambda _: sample[1](path, body, key), range(2)))
    assert [r.status_code for r in results] == [202, 202], [r.text for r in results]
    assert results[0].json() == results[1].json()
    assert sample[1](path, dict(body, reason="Changed reason"), key).status_code == 409
    assert sample[1](path, body, mfa=False).status_code == 403
    with sample[0][0].connect() as c:
        row = c.execute(
            text("SELECT render_config FROM public.print_jobs WHERE order_id=:id"),
            {"id": oid},
        ).scalar_one()
        assert "public_token" not in json.dumps(row)
        assert (
            c.execute(
                text("SELECT count(*) FROM public.print_jobs WHERE order_id=:id"),
                {"id": oid},
            ).scalar_one()
            == 1
        )


def test_worker_pdf_download_scope_consume_and_qa(sample):
    _oid, jid = enqueue(sample)
    event = durable(sample, jid)
    assert run_one(sample[2].state.database, sample[2].state.settings, sample[3], event)
    assert not run_one(
        sample[2].state.database, sample[2].state.settings, sample[3], event
    )
    status = sample[1](f"/admin/print-jobs/{jid}", method="GET")
    assert status.status_code == 200, status.text
    artifact = status.json()["artifacts"][0]
    path = f"/admin/print-artifacts/{artifact['id']}/download-grants"
    key = str(uuid4())
    grant = sample[1](path, {}, key)
    assert grant.status_code == 201, grant.text
    assert sample[1](path, {}, key).json() == grant.json()
    token = {
        "grant_id": grant.json()["grant_id"],
        "download_token": grant.json()["download_token"],
    }
    assert sample[1]("/admin/print-downloads", token, role="other").status_code == 404
    r = sample[1]("/admin/print-downloads", token)
    assert r.status_code == 200, r.text
    assert r.content.startswith(b"%PDF-") and r.headers["cache-control"] == "no-store"
    assert sample[1]("/admin/print-downloads", token).status_code in (404, 409)
    body = {
        "approved": True,
        "artifact_sha256": artifact["sha256_hex"],
        "observed": [
            {"tag_type": "lost", "symbol_mm": "35", "copies": 3},
            {"tag_type": "ice", "symbol_mm": "35", "copies": 2},
        ],
        "scan_passed": True,
        "logo_quiet_zone_passed": True,
        "bilingual_passed": True,
        "cutting_packaging_passed": True,
        "actual_scale_passed": True,
        "reason": "SYNTHETIC physical observations only",
    }
    assert (
        sample[1](
            f"/admin/print-jobs/{jid}/qa", dict(body, scan_passed=False)
        ).status_code
        == 422
    )
    r = sample[1](f"/admin/print-jobs/{jid}/qa", body)
    assert r.status_code == 200, r.text
    with sample[0][0].connect() as c:
        with pytest.raises(DBAPIError):
            c.execute(
                text(
                    "UPDATE public.print_job_qa SET approved=false WHERE print_job_id=:id"
                ),
                {"id": jid},
            )
        c.rollback()


def test_provider_failure_retry_and_frozen_reprint(sample):
    oid, jid = enqueue(sample)
    event = durable(sample, jid)
    sample[3].fail = True
    try:
        assert not run_one(
            sample[2].state.database, sample[2].state.settings, sample[3], event
        )
    finally:
        sample[3].fail = False
    with sample[0][0].connect() as c:
        assert (
            c.execute(
                text("SELECT status FROM public.durable_jobs WHERE id=:id"),
                {"id": event},
            ).scalar_one()
            == "retry"
        )
        c.execute(
            text(
                "UPDATE public.durable_jobs SET next_attempt_at=now()-interval '1 second' WHERE id=:id"
            ),
            {"id": event},
        )
        c.commit()
    assert run_one(sample[2].state.database, sample[2].state.settings, sample[3], event)
    r = sample[1](
        f"/admin/orders/{oid}/print-jobs",
        {"expected_revision": 1, "reason": "Synthetic damaged-label reprint"},
    )
    assert r.status_code == 202, r.text
    assert r.json()["revision"] == 2
    assert run_one(
        sample[2].state.database,
        sample[2].state.settings,
        sample[3],
        durable(sample, r.json()["job_id"]),
    )


def test_automatic_paid_event_and_unpaid_denial(sample):
    oid, aid = attempt(sample[0])
    assert (
        sample[1](
            f"/admin/orders/{oid}/print-jobs",
            {"expected_revision": 0, "reason": "Synthetic unpaid denial"},
        ).status_code
        == 409
    )
    review(sample[0], aid)
    with sample[0][0].connect() as c:
        event = c.execute(
            text(
                "SELECT id FROM public.durable_jobs WHERE order_id=:id AND job_kind='allocation.finalize'"
            ),
            {"id": oid},
        ).scalar_one()
    assert run_one(sample[2].state.database, sample[2].state.settings, sample[3], event)
    with sample[0][0].connect() as c:
        assert (
            c.execute(
                text("SELECT count(*) FROM public.print_jobs WHERE order_id=:id"),
                {"id": oid},
            ).scalar_one()
            == 1
        )


def test_browser(sample):
    from checkout_browser import run

    oid, jid = enqueue(sample)
    assert run_one(
        sample[2].state.database,
        sample[2].state.settings,
        sample[3],
        durable(sample, jid),
    )
    app = sample[2]
    app.state.checkout_fixture_token = app.state.printing_fixture_token
    app.state.checkout_fixture_user = app.state.printing_fixture_user
    base = sample[0]
    run(
        (base[0], ASGIClient(app), base[2], app, *base[4:]),
        test_files=["tests/printing.spec.ts"],
        extra_env={"PRINT_TEST_ORDER": oid, "PRINT_TEST_JOB": jid},
    )


def test_expired_grant_and_rejected_qa_cannot_release(sample):
    _oid, jid = enqueue(sample)
    assert run_one(
        sample[2].state.database,
        sample[2].state.settings,
        sample[3],
        durable(sample, jid),
    )
    a = sample[1](f"/admin/print-jobs/{jid}", method="GET").json()["artifacts"][0]
    grant = sample[1](f"/admin/print-artifacts/{a['id']}/download-grants", {}).json()
    with sample[0][0].connect() as c:
        c.execute(
            text(
                "UPDATE public.print_download_grants SET expires_at=created_at+interval '1 millisecond' WHERE id=:id"
            ),
            {"id": grant["grant_id"]},
        )
        c.commit()
    assert (
        sample[1](
            "/admin/print-downloads",
            {"grant_id": grant["grant_id"], "download_token": grant["download_token"]},
        ).status_code
        == 404
    )
    body = {
        "approved": False,
        "artifact_sha256": a["sha256_hex"],
        "observed": [{"tag_type": "lost", "symbol_mm": "35", "copies": 3}],
        "scan_passed": False,
        "logo_quiet_zone_passed": False,
        "bilingual_passed": False,
        "cutting_packaging_passed": False,
        "actual_scale_passed": False,
        "reason": "Synthetic physical QA rejection",
    }
    r = sample[1](f"/admin/print-jobs/{jid}/qa", body)
    assert r.status_code == 200, r.text
    assert (
        sample[1](f"/admin/print-artifacts/{a['id']}/download-grants", {}).status_code
        == 409
    )


def test_stale_worker_cannot_publish_and_upload_recovers(sample):
    _, jid = enqueue(sample)
    event = durable(sample, jid)
    memory = sample[3]

    class ExpireAfterUpload:
        def upload(self, key, data):
            memory.upload(key, data)
            with sample[0][0].connect() as c:
                c.execute(
                    text(
                        "UPDATE public.durable_jobs SET lease_until=clock_timestamp()-interval '1 second' WHERE id=:id"
                    ),
                    {"id": event},
                )
                c.commit()

    assert not run_one(
        sample[2].state.database, sample[2].state.settings, ExpireAfterUpload(), event
    )
    with sample[0][0].connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.print_artifacts WHERE print_job_id=:id"
                ),
                {"id": jid},
            ).scalar_one()
            == 0
        )
    assert run_one(sample[2].state.database, sample[2].state.settings, memory, event)


@pytest.mark.skipif(
    __import__("os").environ.get("SAFERETURN_PRINT_LIVE_STORAGE") != "1",
    reason="Explicit synthetic live private-PDF acceptance",
)
def test_live_private_pdf_storage_and_authorized_download(sample):
    from pathlib import Path

    from dotenv import dotenv_values

    from app.integrations.print_storage import PrintStore

    v = dotenv_values(Path(__file__).parents[2] / ".env")
    import hashlib

    from pydantic import SecretStr

    actual = Settings(
        supabase_url=v["SAFERETURN_SUPABASE_URL"],
        supabase_storage_service_key=SecretStr(
            v["SAFERETURN_SUPABASE_STORAGE_SERVICE_KEY"]
        ),
    )
    storage = PrintStore(actual)
    oid, jid = enqueue(sample)
    keys = []
    saved_transport = sample[2].state.print_storage_transport
    saved_url = sample[2].state.settings.supabase_url
    saved_key = sample[2].state.settings.supabase_storage_service_key
    try:

        class TrackingStore:
            def upload(self, key, data):
                keys.append(key)
                return storage.upload(key, data)

        assert run_one(
            sample[2].state.database,
            sample[2].state.settings,
            TrackingStore(),
            durable(sample, jid),
        )
        with sample[0][0].connect() as c:
            row = (
                c.execute(
                    text(
                        "SELECT id,object_key,sha256_hex,size_bytes FROM public.print_artifacts WHERE print_job_id=:id"
                    ),
                    {"id": jid},
                )
                .mappings()
                .one()
            )
        key = row["object_key"]
        if key not in keys:
            keys.append(key)
        data = storage.download(key, row["sha256_hex"], row["size_bytes"])
        assert data.startswith(b"%PDF-")
        assert storage.upload(key, data) == data
        with pytest.raises(PrintUnavailable):
            storage.upload(key, b"%PDF-bad")
        with httpx.Client(timeout=15) as c:
            assert c.get(
                actual.supabase_url
                + "/storage/v1/object/public/private-order-print/"
                + key
            ).status_code in (400, 401, 403, 404)
            assert c.get(
                actual.supabase_url
                + "/storage/v1/object/authenticated/private-order-print/"
                + key,
                headers={"apikey": v["SAFERETURN_SUPABASE_PUBLISHABLE_KEY"]},
            ).status_code in (400, 401, 403, 404)
        sample[2].state.settings.supabase_url = actual.supabase_url
        sample[
            2
        ].state.settings.supabase_storage_service_key = (
            actual.supabase_storage_service_key
        )
        sample[2].state.print_storage_transport = None
        g = sample[1](f"/admin/print-artifacts/{row['id']}/download-grants", {})
        assert g.status_code == 201, g.text
        r = sample[1](
            "/admin/print-downloads",
            {
                "grant_id": g.json()["grant_id"],
                "download_token": g.json()["download_token"],
            },
        )
        assert r.status_code == 200, r.text
        assert hashlib.sha256(r.content).hexdigest() == row["sha256_hex"]
    finally:
        sample[2].state.print_storage_transport = saved_transport
        sample[2].state.settings.supabase_url = saved_url
        sample[2].state.settings.supabase_storage_service_key = saved_key
        if keys:
            assert all(
                k.startswith("order-print/" + oid + "/" + jid + "/") for k in keys
            )
            with storage.client() as c:
                r = c.request(
                    "DELETE", "object/private-order-print", json={"prefixes": keys}
                )
                assert r.status_code in (200, 204), "Synthetic PDF cleanup failed"
                for k in keys:
                    assert c.get(
                        "object/info/private-order-print/" + k
                    ).status_code in (400, 404)


def test_suspended_qr_and_failed_receipt_roll_back(sample, monkeypatch):
    from app.api.v1 import printing
    from app.core.profile_crypto import ProfileCryptoUnavailable

    oid = paid(sample)

    def unavailable(*args, **kwargs):
        raise ProfileCryptoUnavailable()

    with monkeypatch.context() as m:
        m.setattr(printing, "encrypt", unavailable)
        r = sample[1](
            f"/admin/orders/{oid}/print-jobs",
            {"expected_revision": 0, "reason": "Synthetic crypto rollback"},
        )
        assert r.status_code == 503, r.text
    with sample[0][0].connect() as c:
        assert (
            c.execute(
                text("SELECT count(*) FROM public.print_jobs WHERE order_id=:id"),
                {"id": oid},
            ).scalar_one()
            == 0
        )
    _, jid = enqueue(sample, oid)
    event = durable(sample, jid)
    with sample[0][0].connect() as c:
        c.execute(
            text(
                "UPDATE public.qr_codes SET public_status='admin_suspended' WHERE id IN(SELECT u.qr_code_id FROM public.order_item_qr_uses u JOIN public.order_items i ON i.id=u.order_item_id WHERE i.order_id=:id)"
            ),
            {"id": oid},
        )
        c.commit()
    assert not run_one(
        sample[2].state.database, sample[2].state.settings, sample[3], event
    )
    with sample[0][0].connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.print_artifacts WHERE print_job_id=:id"
                ),
                {"id": jid},
            ).scalar_one()
            == 0
        )
        c.execute(
            text(
                "UPDATE public.qr_codes SET public_status='unactivated' WHERE id IN(SELECT u.qr_code_id FROM public.order_item_qr_uses u JOIN public.order_items i ON i.id=u.order_item_id WHERE i.order_id=:id)"
            ),
            {"id": oid},
        )
        c.commit()


def test_concurrent_worker_and_single_use_download(sample):
    _, jid = enqueue(sample)
    event = durable(sample, jid)
    with ThreadPoolExecutor(2) as pool:
        completed = list(
            pool.map(
                lambda _: run_one(
                    sample[2].state.database, sample[2].state.settings, sample[3], event
                ),
                range(2),
            )
        )
    assert sorted(completed) == [False, True]
    a = sample[1](f"/admin/print-jobs/{jid}", method="GET").json()["artifacts"][0]
    g = sample[1](f"/admin/print-artifacts/{a['id']}/download-grants", {}).json()
    payload = {"grant_id": g["grant_id"], "download_token": g["download_token"]}
    with ThreadPoolExecutor(2) as pool:
        responses = list(
            pool.map(lambda _: sample[1]("/admin/print-downloads", payload), range(2))
        )
    codes = [r.status_code for r in responses]
    assert codes.count(200) == 1 and all(code in (200, 404, 409) for code in codes), (
        codes
    )


def test_expiry_at_completion_rolls_back_artifact_then_recovers(sample, monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError

    from app.workers import printing as worker

    _, jid = enqueue(sample)
    event = durable(sample, jid)
    original = worker.complete
    seen = []

    def late_expiry(db, lease):
        seen.append("completion_hook")
        try:
            db.execute(
                text(
                    "UPDATE public.durable_jobs SET lease_until=clock_timestamp()-interval '1 second' WHERE id=:id"
                ),
                {"id": lease["id"]},
            )
            seen.append("lease_shortened")
            original(db, lease)
        except worker.LeaseLost:
            seen.append("completion_fenced")
            raise
        except SQLAlchemyError as error:
            seen.append(str(getattr(getattr(error, "orig", None), "sqlstate", None)))
            raise

    with monkeypatch.context() as m:
        m.setattr(worker, "complete", late_expiry)
        assert not run_one(
            sample[2].state.database, sample[2].state.settings, sample[3], event
        )
    with sample[0][0].connect() as c:
        state = c.execute(
            text("SELECT status,failure_code FROM public.print_jobs WHERE id=:id"),
            {"id": jid},
        ).one()
        assert seen, (state, seen)
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.print_artifacts WHERE print_job_id=:id"
                ),
                {"id": jid},
            ).scalar_one()
            == 0
        )
        assert state.status in ("rendering", "failed"), (state, seen)
        status = c.execute(
            text("SELECT status FROM public.durable_jobs WHERE id=:id"), {"id": event}
        ).scalar_one()
        if status == "leased":
            c.execute(
                text(
                    "UPDATE public.durable_jobs SET lease_until=clock_timestamp()-interval '1 second' WHERE id=:id"
                ),
                {"id": event},
            )
        else:
            c.execute(
                text(
                    "UPDATE public.durable_jobs SET next_attempt_at=clock_timestamp()-interval '1 second' WHERE id=:id"
                ),
                {"id": event},
            )
        c.commit()
    assert run_one(
        sample[2].state.database, sample[2].state.settings, sample[3], event
    ), seen
    with sample[0][0].connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.print_artifacts WHERE print_job_id=:id"
                ),
                {"id": jid},
            ).scalar_one()
            == 1
        )
        assert (
            c.execute(
                text("SELECT status FROM public.durable_jobs WHERE id=:id"),
                {"id": event},
            ).scalar_one()
            == "completed"
        )
