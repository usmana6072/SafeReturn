"""Task 5.7 isolated real DB/API checks; no external providers."""

import asyncio
import time
from uuid import uuid4

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from sqlalchemy import text
from test_auth import ORIGIN, claims, keyset, signed
from test_checkout import sample as checkout_sample  # noqa: F401

from app.core.auth import JWTVerifier
from app.core.config import Settings
from app.core.profile_crypto import encrypt


@pytest.fixture(scope="module")
def inbox(checkout_sample):  # noqa: F811
    sample = checkout_sample
    pg, _client, _call, app, _variants, users, inventory, _product = sample
    pid, tags = inventory[0]
    mids = [uuid4() for _ in range(3)]
    settings = app.state.settings
    with pg.connect() as c:
        pg.upgrade(c, "0019_retention_recovery")
        c.commit()
        c.execute(
            text(
                "UPDATE public.tag_pairs SET owner_user_id=:uid,ownership_status='active',activated_at=now() WHERE id=:id"
            ),
            {"uid": users["owner"], "id": pid},
        )
        c.execute(
            text("UPDATE public.qr_codes SET public_status='active' WHERE pair_id=:id"),
            {"id": pid},
        )
        for mid in mids:
            email, v = encrypt(
                settings, tags["lost"], "finder_email", "synthetic@example.invalid"
            )
            message, mv = encrypt(
                settings, tags["lost"], "finder_message", "SYNTHETIC PRIVATE MESSAGE"
            )
            c.execute(
                text(
                    "INSERT INTO public.finder_messages(id,qr_id,recipient_owner_user_id,finder_name,finder_email_ciphertext,finder_contact_key_version,message_text_ciphertext,message_key_version,consent_version,consent_at) VALUES(:id,:qr,:uid,'Synthetic finder',:email,:v,:msg,:mv,'finder-public-v1',now())"
                ),
                {
                    "id": mid,
                    "qr": tags["lost"],
                    "uid": users["owner"],
                    "email": email,
                    "v": v,
                    "msg": message,
                    "mv": mv,
                },
            )
            c.execute(
                text(
                    "INSERT INTO public.notification_outbox(event_type,aggregate_type,aggregate_id,recipient_user_id,idempotency_key) VALUES('finder_message.created','finder_message',:id,:uid,:key)"
                ),
                {"id": mid, "uid": users["owner"], "key": f"inbox:{mid}"},
            )
        lat, v = encrypt(settings, tags["lost"], "finder_latitude", "31.5204")
        lon, _ = encrypt(settings, tags["lost"], "finder_longitude", "74.3587")
        c.execute(
            text(
                "INSERT INTO public.finder_message_locations(finder_message_id,latitude_ciphertext,longitude_ciphertext,accuracy_m,consent_version,consent_at,key_version) VALUES(:id,:lat,:lon,25,'location-v1',now(),:v)"
            ),
            {"id": mids[0], "lat": lat, "lon": lon, "v": v},
        )
        c.commit()

    private = ec.generate_private_key(ec.SECP256R1())
    app.state.jwt_verifier.close()
    app.state.jwt_verifier = JWTVerifier(
        Settings(supabase_url=ORIGIN),
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={"keys": [keyset(private)]})
        ),
    )
    with pg.connect() as c:
        sessions = dict(c.execute(text("SELECT user_id,id FROM auth.sessions")).all())

    def token(role="owner", recent=True):
        return signed(
            private,
            claims(
                sub=str(users[role]),
                session_id=str(sessions[users[role]]),
                amr=[{"method": "password", "timestamp": int(time.time())}]
                if recent
                else [],
            ),
        )

    app.state.checkout_fixture_token = token

    def request(method, path, *, other=False, body=None, recent=True):
        async def send():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                return await client.request(
                    method,
                    "/api/v1" + path,
                    headers={
                        "Authorization": "Bearer "
                        + token("other" if other else "owner", recent)
                    },
                    json=body,
                )

        return asyncio.run(send())

    return sample, mids, request


def test_inbox_authorization_paging_location_and_mutation(inbox):
    _sample, mids, request = inbox
    base = "/me/finder-messages"
    response = request("GET", base + "?limit=1")
    assert response.status_code == 200, response.text
    found = []
    while True:
        body = response.json()
        found.extend(x["id"] for x in body["items"])
        assert "SYNTHETIC PRIVATE MESSAGE" not in response.text
        if not body["next_cursor"]:
            break
        response = request("GET", base + "?limit=1&cursor=" + body["next_cursor"])
    assert set(found) == {str(x) for x in mids} and len(found) == 3
    assert request("GET", base + "?cursor=invalid").status_code == 422
    mid = mids[0]
    detail = request("GET", f"{base}/{mid}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["message"] == "SYNTHETIC PRIVATE MESSAGE"
    assert detail.json()["location"]["latitude"] == 31.5204
    assert detail.headers["cache-control"].endswith("no-store")
    assert request("GET", f"{base}/{mids[1]}").json()["location"] is None
    for method in ["GET", "PATCH", "DELETE"]:
        assert (
            request(
                method,
                f"{base}/{mid}",
                other=True,
                body={"status": "viewed"} if method == "PATCH" else None,
            ).status_code
            == 404
        )
    assert request("GET", base, other=True).json()["items"] == []
    assert _sample[1].get("/api/v1" + base).status_code == 401
    settings = _sample[3].state.settings
    _sample[3].state.settings = settings.model_copy(update={"profile_data_keys": None})
    try:
        failed = request("GET", f"{base}/{mid}")
        assert (
            failed.status_code == 503 and "SYNTHETIC PRIVATE MESSAGE" not in failed.text
        )
    finally:
        _sample[3].state.settings = settings
    # Simulate a later ownership change in synthetic data only. Recipient access
    # must follow the immutable message snapshot rather than the current pair.
    with _sample[0].connect() as c:
        c.execute(
            text("UPDATE public.tag_pairs SET owner_user_id=:uid WHERE id=:id"),
            {"uid": _sample[5]["other"], "id": _sample[6][0][0]},
        )
        c.commit()
    try:
        assert request("GET", f"{base}/{mid}").status_code == 200
        assert request("GET", f"{base}/{mid}", other=True).status_code == 404
        assert request("GET", base, other=True).json()["items"] == []
    finally:
        with _sample[0].connect() as c:
            c.execute(
                text("UPDATE public.tag_pairs SET owner_user_id=:uid WHERE id=:id"),
                {"uid": _sample[5]["owner"], "id": _sample[6][0][0]},
            )
            c.commit()
    for status in ["viewed", "flagged", "archived"]:
        r = request("PATCH", f"{base}/{mid}", body={"status": status})
        assert r.status_code == 200, r.text
    assert (
        request("PATCH", f"{base}/{mid}", body={"status": "deleted"}).status_code == 422
    )
    assert (
        request(
            "PATCH", f"{base}/{mid}", body={"status": "viewed", "message": "changed"}
        ).status_code
        == 422
    )


def test_browser_and_retained_deletion(inbox):
    from checkout_browser import run

    sample, mids, request = inbox
    run(
        sample,
        test_files=["tests/inbox.spec.ts"],
        extra_env={"TASK57_MESSAGE": str(mids[0])},
    )
    mid = mids[1]
    # Retention is unapproved and an explicit legal hold must survive hiding.
    with sample[0].connect() as c:
        c.execute(
            text(
                "INSERT INTO public.retention_holds(resource_type,resource_id,reason_code,placed_by) VALUES('finder_message',:id,'synthetic.legal',:uid)"
            ),
            {"id": mid, "uid": sample[5]["owner"]},
        )
        c.commit()
    base = "/me/finder-messages"
    for _ in range(2):
        assert request("DELETE", f"{base}/{mid}").status_code == 204
    assert request("GET", f"{base}/{mid}").status_code == 404
    assert (
        request("PATCH", f"{base}/{mid}", body={"status": "viewed"}).status_code == 404
    )
    assert str(mid) not in [x["id"] for x in request("GET", base).json()["items"]]
    with sample[0].connect() as c:
        row = c.execute(
            text(
                "SELECT status,deleted_at,retention_until,message_text_ciphertext FROM public.finder_messages WHERE id=:id"
            ),
            {"id": mid},
        ).one()
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.retention_holds WHERE resource_id=:id AND released_at IS NULL"
                ),
                {"id": mid},
            ).scalar_one()
            == 1
        )
        assert row[0] == "deleted" and row[1] is None and row[2] is None and row[3]


def test_hold_delete_race_and_no_resurrection(inbox):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    s, mids, request = inbox
    mid = mids[2]
    barrier = Barrier(2)

    def hold():
        with s[0].connect() as c:
            barrier.wait(timeout=10)
            c.execute(
                text(
                    "INSERT INTO public.retention_holds(resource_type,resource_id,reason_code,placed_by) VALUES('finder_message',:id,'synthetic.race',:uid)"
                ),
                {"id": mid, "uid": s[5]["owner"]},
            )
            c.commit()

    def hide():
        barrier.wait(timeout=10)
        assert request("DELETE", f"/me/finder-messages/{mid}").status_code == 204

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(hold), pool.submit(hide)]
        for result in futures:
            result.result(timeout=40)
    assert (
        request(
            "PATCH", f"/me/finder-messages/{mid}", body={"status": "viewed"}
        ).status_code
        == 404
    )
    with s[0].connect() as c:
        row = c.execute(
            text(
                "SELECT status,deleted_at,message_text_ciphertext FROM public.finder_messages WHERE id=:id"
            ),
            {"id": mid},
        ).one()
        assert row[0] == "deleted" and row[1] is None and row[2]
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.finder_message_locations WHERE finder_message_id=:id"
                ),
                {"id": mids[0]},
            ).scalar_one()
            == 1
        )
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.retention_holds WHERE resource_id=:id AND released_at IS NULL"
                ),
                {"id": mid},
            ).scalar_one()
            == 1
        )


def test_account_privacy_requests_and_concurrency(inbox):
    from concurrent.futures import ThreadPoolExecutor

    from app.core.profile_crypto import decrypt

    s, _mids, request = inbox
    uid = s[5]["other"]
    with s[0].connect() as c:
        for actor in s[5].values():
            c.execute(
                text(
                    "INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,safe_details) VALUES(:uid,'customer','profile.whatsapp.updated','qr',:qr,'{\"reason_code\":\"wa-public-v1\",\"to_status\":\"enabled\"}')"
                ),
                {"uid": actor, "qr": s[6][0][1]["lost"]},
            )
        c.commit()
    own = request("GET", "/me/privacy-consents")
    assert own.status_code == 200, own.text
    assert len(own.json()["items"]) == 1 and own.json()["items"][0]["active"] is True
    other = request("GET", "/me/privacy-consents", other=True)
    assert other.json()["items"][0]["id"] != own.json()["items"][0]["id"]
    path = "/me/account-deletion-requests"
    body = {"confirm": True, "reason": "SYNTHETIC PRIVATE DELETION REASON"}
    assert request("POST", path, body=body, recent=False).status_code == 403
    bad = request("POST", path, body={"confirm": False, "reason": "DO NOT ECHO"})
    assert bad.status_code == 400 and "DO NOT ECHO" not in bad.text
    settings = s[3].state.settings
    s[3].state.settings = settings.model_copy(update={"profile_data_keys": None})
    try:
        assert request("POST", path, body=body, other=True).status_code == 503
    finally:
        s[3].state.settings = settings
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(lambda _: request("POST", path, body=body, other=True), range(2))
        )
    assert all(r.status_code == 202 for r in responses), [r.text for r in responses]
    identifier = responses[0].json()["request_id"]
    assert responses[1].json()["request_id"] == identifier
    assert all("SYNTHETIC PRIVATE" not in r.text for r in responses)
    with s[0].connect() as c:
        row = c.execute(
            text(
                "SELECT description_ciphertext,description_key_version FROM public.support_cases WHERE id=CAST(:id AS uuid) AND opened_by_user_id=:uid"
            ),
            {"id": identifier, "uid": uid},
        ).one()
        assert (
            decrypt(settings, uid, "account_deletion_reason", row[0], row[1])
            == body["reason"]
        )
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.audit_events WHERE action='account.deletion.requested' AND actor_user_id=:uid"
                ),
                {"uid": uid},
            ).scalar_one()
            == 1
        )
        assert (
            c.execute(
                text("SELECT count(*) FROM auth.users WHERE id=:uid"), {"uid": uid}
            ).scalar_one()
            == 1
        )
        assert (
            c.execute(
                text("SELECT count(*) FROM public.tag_pairs WHERE owner_user_id=:uid"),
                {"uid": s[5]["owner"]},
            ).scalar_one()
            == 1
        )
