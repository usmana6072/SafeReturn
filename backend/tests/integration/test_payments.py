"""Real isolated PostgreSQL acceptance; synthetic ledger and storage only."""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import HTTPException
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from starlette.requests import Request
from test_checkout import confirm, quote
from test_checkout import sample as checkout_sample  # noqa: F401

from app.api.auth import AccessError, AuthContext
from app.api.v1 import payments
from app.core.auth import Principal
from app.db.runtime import api_transaction


@pytest.fixture(scope="module")
def sample(checkout_sample):  # noqa: F811
    pg, _, _, app, *_ = checkout_sample
    app.state.settings.payment_reference_key = SecretStr(
        "synthetic-reference-key-32-bytes"
    )
    app.state.settings.supabase_storage_service_key = SecretStr("synthetic-storage-key")
    uid = uuid4()
    with pg.connect() as c:
        c.execute(
            text("INSERT INTO auth.users(id,email_confirmed_at) VALUES(:id,now())"),
            {"id": uid},
        )
        c.execute(
            text("INSERT INTO public.staff_roles(user_id,role) VALUES(:id,'finance')"),
            {"id": uid},
        )
        c.commit()
    app.state.finance_user = uid
    yield checkout_sample


BODY = {"sender_account": "SYNTHETIC1234", "sender_holder_name": "Synthetic holder"}


def order(s):
    r = confirm(s, quote(s))
    assert r.status_code == 201, r.text
    return r.json()["order_id"]


def attempt(s):
    oid = order(s)
    r = s[2](f"/me/orders/{oid}/payment-attempts", BODY)
    assert r.status_code == 201, r.text
    return oid, r.json()["attempt_id"]


def review(s, aid, body=None, key=None, mfa=True):
    app = s[3]
    with api_transaction(app.state.database, app.state.finance_user) as db:
        db.execute(
            text("SELECT set_config('safereturn.mfa_verified',:v,true)"),
            {"v": "true" if mfa else "false"},
        )
        ctx = AuthContext(
            db, Principal(app.state.finance_user, uuid4(), True), True, mfa
        )
        req = Request(
            {
                "type": "http",
                "app": app,
                "headers": [(b"idempotency-key", (key or str(uuid4())).encode())],
            }
        )
        return payments.review_payment(
            UUID(aid), payments.ReviewRequest(**(body or ledger())), ctx, req
        )


def ledger(**kw):
    return {
        "decision": "verify",
        "bank_verified": True,
        "bank_match_reference": str(uuid4()),
        "settled_amount": "11.00",
        "settled_currency": "PKR",
        "reason": "Synthetic independent bank match",
    } | kw


def test_creation_owner_retry_and_concurrency(sample):
    oid = order(sample)
    path = f"/me/orders/{oid}/payment-attempts"
    key = str(uuid4())
    with ThreadPoolExecutor(2) as p:
        results = list(p.map(lambda _: sample[2](path, BODY, key=key), range(2)))
    assert [r.status_code for r in results] == [201, 201], [r.text for r in results]
    assert results[0].json() == results[1].json()
    assert sample[2](path, BODY, role="other").status_code == 404
    assert sample[2](path, BODY).status_code == 409
    assert (
        sample[2](path, BODY | {"sender_account": "OTHER1234"}, key=key).status_code
        == 409
    )
    assert "SYNTHETIC" not in results[0].text


def test_review_concurrent_exactly_once_and_history(sample):
    oid, aid = attempt(sample)
    body = ledger()
    key = str(uuid4())
    with ThreadPoolExecutor(2) as p:
        results = list(p.map(lambda _: review(sample, aid, body, key), range(2)))
    assert results[0] == results[1]
    with sample[0].connect() as c:
        for sql in (
            "SELECT count(*) FROM public.payment_reviews WHERE attempt_id=:id",
        ):
            assert c.execute(text(sql), {"id": aid}).scalar_one() == 1
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.order_pair_units WHERE order_id=:id AND status='allocated'"
                ),
                {"id": oid},
            ).scalar_one()
            == 1
        )
        assert (
            c.execute(
                text("SELECT count(*) FROM public.durable_jobs WHERE order_id=:id"),
                {"id": oid},
            ).scalar_one()
            == 1
        )
        with pytest.raises(DBAPIError):
            c.execute(
                text(
                    "UPDATE public.payment_reviews SET reason='tampered' WHERE attempt_id=:id"
                ),
                {"id": aid},
            )
        c.rollback()
    with pytest.raises(HTTPException):
        review(sample, aid, body)
    _, other = attempt(sample)
    with pytest.raises(HTTPException):
        review(sample, other, body)


def test_mismatch_mfa_release_and_rollback(sample):
    oid, aid = attempt(sample)
    for b in (
        ledger(settled_amount="10.99"),
        ledger(settled_currency="USD"),
        ledger(bank_verified=False),
    ):
        with pytest.raises(HTTPException):
            review(sample, aid, b)
    with pytest.raises(AccessError):
        review(sample, aid, mfa=False)
    with sample[0].connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.payment_reviews WHERE attempt_id=:id"
                ),
                {"id": aid},
            ).scalar_one()
            == 0
        )
        assert (
            c.execute(
                text("SELECT status FROM public.order_pair_units WHERE order_id=:id"),
                {"id": oid},
            ).scalar_one()
            == "reserved"
        )
        with pytest.raises(DBAPIError):
            c.execute(
                text(
                    "UPDATE public.order_pair_units SET status='released' WHERE order_id=:id"
                ),
                {"id": oid},
            )
        c.rollback()


def test_private_evidence_failures_and_retry(sample):
    _, aid = attempt(sample)
    app = sample[3]
    data = b"\x89PNG\r\n\x1a\nsyntheticIEND\xaeB`\x82"
    state = {"data": data, "public": False, "fail": False}

    def provider(req):
        if state["fail"]:
            return httpx.Response(503)
        if "/bucket/" in req.url.path:
            return httpx.Response(
                200,
                json={
                    "public": state["public"],
                    "file_size_limit": 5000000,
                    "allowed_mime_types": ["image/png"],
                },
            )
        if req.method == "POST":
            return httpx.Response(
                200,
                json={
                    "url": "/object/upload/sign/private-payment-evidence/"
                    + req.url.path.split("private-payment-evidence/")[1]
                    + "?token=synthetic"
                },
            )
        return httpx.Response(
            200, content=state["data"], headers={"content-type": "image/png"}
        )

    app.state.payment_storage_transport = httpx.MockTransport(provider)
    body = {
        "filename": "proof.png",
        "content_type": "image/png",
        "bytes_size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    path = f"/me/payment-attempts/{aid}/evidence-uploads"
    state["public"] = True
    assert sample[2](path, body).status_code == 503
    state["public"] = False
    r = sample[2](path, body)
    assert r.status_code == 200, r.text
    token = {"upload_token": r.json()["upload_token"], "sha256": body["sha256"]}
    path = f"/me/payment-attempts/{aid}/evidence-finalize"
    assert sample[2](path, token, role="other").status_code == 404
    state["data"] = b"fake"
    assert sample[2](path, token).status_code == 422
    state["data"] = data
    key = str(uuid4())
    r = sample[2](path, token, key=key)
    assert r.status_code == 200, r.text
    state["fail"] = True
    assert sample[2](path, token, key=key).json() == r.json()
    with sample[0].connect() as c:
        assert (
            c.execute(
                text("SELECT state FROM public.payment_attempts WHERE id=:id"),
                {"id": aid},
            ).scalar_one()
            == "under_review"
        )
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.payment_evidence WHERE attempt_id=:id"
                ),
                {"id": aid},
            ).scalar_one()
            == 1
        )


def test_browser(sample):
    from checkout_browser import run

    oid = order(sample)
    data = b"\x89PNG\r\n\x1a\nsyntheticIEND\xaeB`\x82"

    def provider(req):
        if "/bucket/" in req.url.path:
            return httpx.Response(
                200,
                json={
                    "public": False,
                    "file_size_limit": 5000000,
                    "allowed_mime_types": ["image/png"],
                },
            )
        if req.method == "POST":
            return httpx.Response(
                200,
                json={
                    "url": "/object/upload/sign/private-payment-evidence/"
                    + req.url.path.split("private-payment-evidence/")[1]
                    + "?token=synthetic"
                },
            )
        return httpx.Response(200, content=data, headers={"content-type": "image/png"})

    sample[3].state.payment_storage_transport = httpx.MockTransport(provider)
    run(
        sample,
        test_files=["tests/payments.spec.ts"],
        extra_env={"PAYMENT_TEST_ORDER": oid},
    )


def test_failure_after_allocation_rolls_back(sample, monkeypatch):
    oid, aid = attempt(sample)

    def unavailable(*args, **kwargs):
        raise payments.ProfileCryptoUnavailable()

    with monkeypatch.context() as m:
        m.setattr(payments, "encrypt", unavailable)
        with pytest.raises(AccessError):
            review(sample, aid)
    with sample[0].connect() as c:
        assert (
            c.execute(
                text("SELECT state FROM public.payment_attempts WHERE id=:id"),
                {"id": aid},
            ).scalar_one()
            == "under_review"
        )
        assert (
            c.execute(
                text("SELECT status FROM public.order_pair_units WHERE order_id=:id"),
                {"id": oid},
            ).scalar_one()
            == "reserved"
        )
        assert (
            c.execute(
                text("SELECT count(*) FROM public.durable_jobs WHERE order_id=:id"),
                {"id": oid},
            ).scalar_one()
            == 0
        )
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.payment_reviews WHERE attempt_id=:id"
                ),
                {"id": aid},
            ).scalar_one()
            == 0
        )
    assert review(sample, aid)["state"] == "verified"


def test_reject_more_info_and_new_attempt(sample):
    oid, aid = attempt(sample)
    assert (
        review(
            sample,
            aid,
            {
                "decision": "request_more_info",
                "reason": "Synthetic clarification needed",
            },
        )["state"]
        == "under_review"
    )
    assert (
        review(
            sample,
            aid,
            {"decision": "reject", "reason": "Synthetic bank receipt absent"},
        )["state"]
        == "rejected"
    )
    r = sample[2](f"/me/orders/{oid}/payment-attempts", BODY)
    assert r.status_code == 201, r.text
    assert r.json()["attempt_id"] != aid


def test_signed_finance_http_and_evidence_denial(sample):
    from cryptography.hazmat.primitives.asymmetric import ec
    from test_auth import ORIGIN, claims, keyset, signed
    from test_health import ASGIClient

    from app.core.auth import JWTVerifier
    from app.core.config import Settings
    from app.main import create_app

    private = ec.generate_private_key(ec.SECP256R1())
    verifier = JWTVerifier(
        Settings(supabase_url=ORIGIN),
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={"keys": [keyset(private)]})
        ),
    )
    app = create_app(sample[3].state.settings, verifier=verifier)
    app.state.jwt_verifier = verifier
    app.state.database = sample[3].state.database
    app.state.payment_storage_transport = sample[3].state.payment_storage_transport
    uid = sample[3].state.finance_user
    sid = uuid4()
    with sample[0].connect() as c:
        c.execute(
            text(
                "INSERT INTO auth.sessions(id,user_id,aal,not_after) VALUES(:sid,:uid,'aal2',now()+interval '1 hour')"
            ),
            {"sid": sid, "uid": uid},
        )
        c.commit()
    client = ASGIClient(app)
    _, aid = attempt(sample)
    body = ledger()
    headers = {
        "Authorization": "Bearer "
        + signed(private, claims(sub=str(uid), session_id=str(sid), aal="aal2")),
        "Idempotency-Key": str(uuid4()),
    }
    path = f"/api/v1/admin/payment-attempts/{aid}/reviews"
    try:
        low = dict(
            headers,
            Authorization="Bearer "
            + signed(private, claims(sub=str(uid), session_id=str(sid), aal="aal1")),
        )
        assert client.post(path, json=body, headers=low).status_code == 403
        r = client.post(path, json=body, headers=headers)
        assert r.status_code == 200, r.text
        assert client.post(path, json=body, headers=headers).json() == r.json()
        oid = r.json()["order_id"]
        details = client.get(
            f"/api/v1/admin/orders/{oid}/payment-attempts", headers=headers
        )
        assert details.status_code == 200, details.text
        assert details.json()["items"][0]["sender_account"] == "SYNTHETIC1234"
        with sample[0].connect() as c:
            eid = c.execute(
                text("SELECT id FROM public.payment_evidence LIMIT 1")
            ).scalar_one()
        evidence = client.get(
            "/api/v1/admin/payment-evidence/" + str(eid), headers=headers
        )
        assert evidence.status_code == 200, evidence.text
        assert evidence.headers["cache-control"] == "no-store"
        assert "attachment" in evidence.headers["content-disposition"]
        assert (
            client.post(
                path,
                json=body | {"reason": "Changed synthetic reason"},
                headers=headers,
            ).status_code
            == 409
        )
        assert (
            client.get(
                "/api/v1/admin/payment-evidence/" + str(uuid4()), headers=headers
            ).status_code
            == 404
        )
    finally:
        verifier.close()


@pytest.mark.skipif(
    __import__("os").environ.get("SAFERETURN_PAYMENT_LIVE_STORAGE") != "1",
    reason="Explicit synthetic live-storage acceptance only",
)
def test_live_private_storage_acceptance(sample):
    import base64
    from pathlib import Path
    from urllib.parse import unquote, urlsplit

    from dotenv import dotenv_values

    v = dotenv_values(Path(__file__).parents[2] / ".env")
    app = sample[3]
    app.state.settings.supabase_url = v["SAFERETURN_SUPABASE_URL"]
    app.state.settings.supabase_storage_service_key = SecretStr(
        v["SAFERETURN_SUPABASE_STORAGE_SERVICE_KEY"]
    )
    app.state.payment_storage_transport = None
    data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aDTsAAAAASUVORK5CYII="
    )
    _, aid = attempt(sample)
    body = {
        "filename": "synthetic-acceptance.png",
        "content_type": "image/png",
        "bytes_size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    bucket = "private-payment-evidence"
    keys = []
    origin = v["SAFERETURN_SUPABASE_URL"]
    secret = v["SAFERETURN_SUPABASE_STORAGE_SERVICE_KEY"]
    with httpx.Client(timeout=20, follow_redirects=False) as c:
        try:
            r = sample[2](f"/me/payment-attempts/{aid}/evidence-uploads", body)
            assert r.status_code == 200, r.text
            grant = r.json()
            key = unquote(urlsplit(grant["upload_url"]).path.split(bucket + "/")[1])
            keys.append(key)
            assert key.startswith("payment-evidence/" + aid + "/")
            uploaded = c.put(
                grant["upload_url"], content=data, headers={"Content-Type": "image/png"}
            )
            assert uploaded.status_code in (200, 201), uploaded.status_code
            assert c.put(
                grant["upload_url"], content=data, headers={"Content-Type": "image/png"}
            ).status_code in (400, 409)
            assert c.get(
                origin + "/storage/v1/object/public/" + bucket + "/" + key
            ).status_code in (400, 401, 403, 404)
            assert c.get(
                origin + "/storage/v1/object/authenticated/" + bucket + "/" + key,
                headers={"apikey": v["SAFERETURN_SUPABASE_PUBLISHABLE_KEY"]},
            ).status_code in (400, 401, 403, 404)
            finalized = sample[2](
                f"/me/payment-attempts/{aid}/evidence-finalize",
                {"upload_token": grant["upload_token"], "sha256": body["sha256"]},
            )
            assert finalized.status_code == 200, finalized.text
            assert finalized.json()["payment_state"] == "under_review"
            # Real provider rejects an oversized body before metadata can be finalized.
            second = sample[2](f"/me/payment-attempts/{aid}/evidence-uploads", body)
            assert second.status_code == 200, second.text
            secondkey = unquote(
                urlsplit(second.json()["upload_url"]).path.split(bucket + "/")[1]
            )
            keys.append(secondkey)
            assert c.put(
                second.json()["upload_url"],
                content=b"x" * 5000001,
                headers={"Content-Type": "image/png"},
            ).status_code in (400, 413)
            assert c.put(
                second.json()["upload_url"],
                content=b"<html>synthetic</html>",
                headers={"Content-Type": "text/html"},
            ).status_code in (400, 415)
            from app.integrations.payment_storage import PaymentStorage

            assert (
                PaymentStorage(app.state.settings).verify(
                    {
                        "object_key": key,
                        "bytes_size": len(data),
                        "content_type": "image/png",
                        "sha256": body["sha256"],
                    }
                )
                == data
            )
        finally:
            assert all(k.startswith("payment-evidence/" + aid + "/") for k in keys)
            if keys:
                deleted = c.request(
                    "DELETE",
                    origin + "/storage/v1/object/" + bucket,
                    headers={"Authorization": "Bearer " + secret, "apikey": secret},
                    json={"prefixes": keys},
                )
                assert deleted.status_code in (200, 204), (
                    "Synthetic evidence cleanup failed"
                )
                for k in keys:
                    assert c.get(
                        origin + "/storage/v1/object/authenticated/" + bucket + "/" + k,
                        headers={"Authorization": "Bearer " + secret, "apikey": secret},
                    ).status_code in (400, 404), "Synthetic evidence still present"
    print(
        "Live synthetic Storage: upload, no-overwrite, public/anonymous denial, finalize, exact content, size/MIME denial and exact-key cleanup PASS"
    )
