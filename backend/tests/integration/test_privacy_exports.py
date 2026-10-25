"""Task 5.7J: isolated PostgreSQL/Auth and memory-only export storage."""

import base64
import json
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from pg_rehearsal import rehearsal
from pydantic import SecretStr
from sqlalchemy import text
from test_auth import ORIGIN, claims, keyset, signed
from test_health import ASGIClient
from test_workflow_schema import workflow_sample

from app.core.auth import JWTVerifier
from app.core.config import Settings
from app.db.session import Database
from app.main import create_app

BASE = "/api/v1/me/privacy/exports"


@pytest.fixture(scope="module")
def cases():
    with rehearsal(expected_revision="0021_support_case_console") as pg:
        with pg.connect() as c:
            pg.upgrade(c, "0021_support_case_console")
            c.commit()
            pg.assert_catalog(c)
            c.rollback()
            pg.upgrade(c, "0022_privacy_exports")
            assert c.execute(
                text("""SELECT bool_and(NOT has_table_privilege(role, 'public.privacy_export_authorities','SELECT,INSERT,UPDATE,DELETE'))
             FROM (VALUES('anon'),('authenticated'),('safereturn_api'),('safereturn_worker')) roles(role)""")
            ).scalar_one()
            assert c.execute(
                text("""SELECT bool_and(NOT has_table_privilege(role, 'public.privacy_exports','INSERT,DELETE'))
             FROM (VALUES('anon'),('authenticated'),('safereturn_api'),('safereturn_worker')) roles(role)""")
            ).scalar_one()
            c.rollback()
            assert c.execute(
                text("SELECT to_regclass('public.privacy_exports') IS NULL")
            ).scalar_one()
            pg.assert_catalog(c)
            c.rollback()
            pg.upgrade(c, "0022_privacy_exports")
            assert c.execute(
                text("""SELECT bool_and(has_function_privilege(r.role,p.oid,'EXECUTE')=(r.role='safereturn_api' AND p.proname<>'sr_support_finder_hold_lock'))
            FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
            CROSS JOIN (VALUES('anon'),('authenticated'),('safereturn_api'),('safereturn_worker')) r(role)
            WHERE n.nspname=current_schema() AND p.proname LIKE 'sr_support_%'""")
            ).scalar_one()
            ids = workflow_sample.__wrapped__(c)
            ids["superadmin"] = uuid4()
            c.execute(
                text("INSERT INTO auth.users(id) VALUES(:id)"),
                {"id": ids["superadmin"]},
            )
            c.execute(
                text(
                    "INSERT INTO public.staff_roles(user_id,role) VALUES(:id,'superadmin'),(:other,'support')"
                ),
                {"id": ids["superadmin"], "other": ids["b"]},
            )
            users = {
                k: ids[k]
                for k in [
                    "a",
                    "b",
                    "support",
                    "operations",
                    "finance",
                    "security_admin",
                    "superadmin",
                ]
            }
            sessions = {k: uuid4() for k in users}
            for role, uid in users.items():
                c.execute(
                    text(
                        "UPDATE auth.users SET email=:email,email_confirmed_at=now() WHERE id=:id"
                    ),
                    {"id": uid, "email": role + "@synthetic.invalid"},
                )
                c.execute(
                    text(
                        "INSERT INTO auth.sessions(id,user_id,aal,not_after) VALUES(:sid,:id,'aal2',now()+interval '1 hour')"
                    ),
                    {"id": uid, "sid": sessions[role]},
                )
            c.commit()
        settings = Settings(
            supabase_url=ORIGIN,
            privacy_export_web_origin="http://127.0.0.1:3100",
            profile_data_keys=SecretStr(
                json.dumps({"1": base64.urlsafe_b64encode(b"S" * 32).decode()})
            ),
        )
        private = ec.generate_private_key(ec.SECP256R1())
        verifier = JWTVerifier(
            settings,
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, json={"keys": [keyset(private)]})
            ),
        )
        app = create_app(settings, verifier=verifier)
        app.state.database = Database(pg.engine)
        app.state.jwt_verifier = verifier
        client = ASGIClient(app)

        def headers(role="a", aal="aal2", key=None, age=0, session=None):
            return {
                "Authorization": "Bearer "
                + signed(
                    private,
                    claims(
                        sub=str(users[role]),
                        session_id=str(session or sessions[role]),
                        aal=aal,
                        amr=[
                            {"method": "password", "timestamp": int(time.time()) - age}
                        ],
                    ),
                ),
                "Idempotency-Key": key or str(uuid4()),
                "Origin": "http://127.0.0.1:3100",
            }

        yield pg, app, client, headers, users, sessions, settings, ids
        verifier.close()


class MemoryStore:
    def __init__(self):
        self.objects = {}
        self.fail = False

    def upload(self, key, data):
        if self.fail:
            raise OSError("synthetic unavailable")
        if key in self.objects:
            assert self.objects[key] == data
        self.objects[key] = data

    def read(self, key):
        if self.fail:
            raise OSError("synthetic unavailable")
        return self.objects[key]


def request_export(cases, role="a", **extra):
    response = cases[2].post(
        BASE,
        headers=cases[3](role),
        json={"scope": "basic_v1", "confirmed": True, **extra},
    )
    assert response.status_code == 202, response.text
    return response.json()["request_id"]


def authorize(cases, rid):
    with cases[0].connect() as c:
        cid = c.execute(
            text("SELECT case_id FROM public.privacy_exports WHERE id=:id"), {"id": rid}
        ).scalar_one()
        c.execute(
            text(
                "INSERT INTO public.privacy_export_authorities(case_id,reviewer_id,authorized_by,expires_at) VALUES(:cid,:reviewer,:custodian,now()+interval '2 days') ON CONFLICT DO NOTHING"
            ),
            {
                "cid": cid,
                "reviewer": cases[4]["security_admin"],
                "custodian": cases[4]["operations"],
            },
        )
        c.commit()
    return str(cid)


def decision(cases, rid, cid, role="security_admin", revision=1, key=None, **extra):
    return cases[2].post(
        "/api/v1/admin/privacy/exports/" + rid + "/decisions",
        headers=cases[3](role, key=key),
        json={
            "case_id": cid,
            "expected_revision": revision,
            "scope_version": "basic_v1",
            "decision": "approve",
            "reason_code": "scope_reviewed",
            "confirmed": True,
            **extra,
        },
    )


def test_contract_and_authority(cases):
    from app.main import create_app

    schema = create_app(Settings()).openapi()
    operations = {
        op.get("operationId")
        for path in schema["paths"].values()
        for op in path.values()
        if isinstance(op, dict)
    }
    assert all("API-" + str(i) in operations for i in range(325, 331))
    assert all("API-" + str(i) not in operations for i in range(331, 336))
    client, h = cases[2:4]
    assert (
        client.post(BASE, json={"scope": "basic_v1", "confirmed": True}).status_code
        == 401
    )
    for age in (301, -100):
        assert (
            client.post(
                BASE, headers=h(age=age), json={"scope": "basic_v1", "confirmed": True}
            ).status_code
            == 403
        )
    assert (
        client.post(
            BASE,
            headers=h(),
            json={"scope": "basic_v1", "confirmed": True, "email": "CANARY"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            BASE,
            headers={k: v for k, v in h().items() if k != "Idempotency-Key"},
            json={"scope": "basic_v1", "confirmed": True},
        ).status_code
        == 400
    )
    key = str(uuid4())
    body = {"scope": "basic_v1", "confirmed": True}
    a = client.post(BASE, headers=h(key=key), json=body)
    assert a.status_code == 202, a.text
    assert client.post(BASE, headers=h(key=key), json=body).json() == a.json()
    rid = a.json()["request_id"]
    assert client.get(BASE + "/" + rid, headers=h("b")).status_code == 404
    with cases[0].connect() as c:
        cid = str(
            c.execute(
                text("SELECT case_id FROM public.privacy_exports WHERE id=:id"),
                {"id": rid},
            ).scalar_one()
        )
    assert (
        client.post(BASE, headers=h("b"), json={**body, "case_id": cid}).status_code
        == 404
    )
    assert (
        client.post(BASE, headers=h(key=key), json={**body, "case_id": cid}).status_code
        == 409
    )
    assert decision(cases, rid, cid).status_code == 404
    for role in ("b", "support", "finance", "operations", "superadmin"):
        assert (
            client.get("/api/v1/admin/privacy/exports", headers=h(role)).status_code
            == 403
        )
        assert decision(cases, rid, cid, role=role).status_code == 403
    assert (
        client.get("/api/v1/admin/privacy/exports", headers=h("security_admin")).json()[
            "items"
        ]
        == []
    )
    authorize(cases, rid)
    assert decision(cases, rid, str(uuid4())).status_code == 404
    assert (
        client.post(
            "/api/v1/admin/privacy/exports/" + rid + "/decisions",
            headers=h("security_admin", age=301),
            json={
                "case_id": cid,
                "expected_revision": 1,
                "scope_version": "basic_v1",
                "decision": "approve",
                "reason_code": "scope_reviewed",
                "confirmed": True,
            },
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/api/v1/admin/privacy/exports", headers=h("security_admin", aal="aal1")
        ).status_code
        == 403
    )
    key = str(uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(
            pool.map(lambda _: decision(cases, rid, cid, key=str(uuid4())), range(2))
        )
    assert sorted(r.status_code for r in replies) == [200, 412]
    assert decision(cases, rid, cid, revision=2).status_code == 409
    safe = client.get(BASE + "/" + rid, headers=h()).text
    assert all(
        word not in safe
        for word in (
            "object_key",
            "ciphertext",
            "description",
            "subject_id",
            "approver_id",
        )
    )


def ready(cases, role="a"):
    from app.workers.privacy_exports import run_one

    rid = request_export(cases, role)
    with cases[0].connect() as c:
        state = c.execute(
            text("SELECT status FROM public.privacy_exports WHERE id=:id"), {"id": rid}
        ).scalar_one()
    if state == "requested":
        cid = authorize(cases, rid)
        assert decision(cases, rid, cid).status_code == 200
    store = MemoryStore()
    cases[1].state.privacy_export_store = store
    assert run_one(cases[1].state.database, cases[6], store, UUID(rid))
    status = cases[2].get(BASE + "/" + rid, headers=cases[3](role)).json()
    assert status["status"] == "ready", status
    return rid, store, status


def test_encrypted_manifest_delivery_redaction_and_grants(cases):
    rid, store, status = ready(cases)
    client, h = cases[2:4]
    path = BASE + "/" + rid
    cipher = next(iter(store.objects.values()))
    assert (
        cipher.startswith(b"SRD1")
        and b"owner-A" not in cipher
        and b"private" not in cipher
    )

    def grant(role="a", idempotency=None, **extra):
        return client.post(
            path + "/download-grants",
            headers=h(role, key=idempotency),
            json={"expected_revision": status["revision"], "confirmed": True, **extra},
        )

    assert grant("b").status_code == 404
    assert (
        client.post(
            path + "/download-grants",
            headers=h(age=301),
            json={"expected_revision": status["revision"], "confirmed": True},
        ).status_code
        == 403
    )
    assert (
        client.post(
            path + "/download-grants",
            headers={**h(), "Origin": "https://bad.invalid"},
            json={"expected_revision": status["revision"], "confirmed": True},
        ).status_code
        == 403
    )
    replay_key = str(uuid4())
    g = grant(idempotency=replay_key)
    assert g.status_code == 200, g.text
    token = g.json()["grant"]
    assert grant(idempotency=replay_key).json() == g.json()
    import hashlib

    from app.core.profile_crypto import decrypt

    with cases[0].connect() as c:
        receipt = c.execute(
            text(
                "SELECT operation,response_body_ciphertext,response_key_version FROM public.idempotency_records WHERE idempotency_key=:key"
            ),
            {"key": replay_key},
        ).one()
    ref = hashlib.sha256(
        f"{cases[4]['a']}:{receipt[0]}:{replay_key}".encode()
    ).hexdigest()
    stored = decrypt(cases[6], cases[4]["a"], "support:" + ref, receipt[1], receipt[2])
    assert token not in stored and '"grant"' not in stored
    assert (
        client.post(
            path + "/download", headers={**h("b"), "X-Privacy-Grant": token}
        ).status_code
        == 404
    )
    assert (
        client.post(
            path + "/download",
            headers={**h(), "Origin": "https://bad.invalid", "X-Privacy-Grant": token},
        ).status_code
        == 403
    )
    with cases[0].connect() as c:
        sid = uuid4()
        c.execute(
            text(
                "INSERT INTO auth.sessions(id,user_id,aal,not_after) VALUES(:sid,:uid,'aal2',now()+interval '1 hour')"
            ),
            {"sid": sid, "uid": cases[4]["a"]},
        )
        c.commit()
    assert (
        client.post(
            path + "/download", headers={**h(session=sid), "X-Privacy-Grant": token}
        ).status_code
        == 410
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                lambda _: client.post(
                    path + "/download", headers={**h(), "X-Privacy-Grant": token}
                ),
                range(2),
            )
        )
    assert sorted(r.status_code for r in responses) == [200, 410]
    response = next(r for r in responses if r.status_code == 200)
    archive = response.json()
    encoded = response.text
    assert archive["manifest"]["complete_legal_account_dump"] is False
    assert archive["data"]["account"][0]["display_name"].startswith("owner-A")
    assert len(archive["data"]["pairs"]) == 1 and len(archive["data"]["receipts"]) == 1
    assert set(archive["data"]["receipts"][0]) == {"status", "received_at"}
    for canary in (
        "private A",
        "private B",
        "private medical",
        "owner-B",
        "public_token",
        "secret_verifier",
        "finder_email",
        "message_text",
        "description_ciphertext",
        "object_key",
    ):
        assert canary not in encoded
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "attachment" in response.headers["content-disposition"]
    g = grant().json()["grant"]
    with cases[0].connect() as c:
        digest = c.execute(
            text(
                "SELECT digest FROM public.privacy_export_grants WHERE request_id=:id"
            ),
            {"id": rid},
        ).scalar_one()
        assert digest != g and len(digest) == 64
        c.execute(
            text(
                "UPDATE public.privacy_export_grants SET expires_at=now()-interval '1 second' WHERE request_id=:id"
            ),
            {"id": rid},
        )
        c.commit()
    assert (
        client.post(
            path + "/download", headers={**h(), "X-Privacy-Grant": g}
        ).status_code
        == 410
    )
    # A provider failure consumes the capability; no receipt can replay bytes.
    g = grant().json()["grant"]
    store.fail = True
    assert (
        client.post(
            path + "/download", headers={**h(), "X-Privacy-Grant": g}
        ).status_code
        == 503
    )
    store.fail = False
    assert (
        client.post(
            path + "/download", headers={**h(), "X-Privacy-Grant": g}
        ).status_code
        == 410
    )
    g = grant().json()["grant"]
    key = next(iter(store.objects))
    saved = store.objects[key]
    store.objects[key] = saved[:-1] + bytes([saved[-1] ^ 1])
    assert (
        client.post(
            path + "/download", headers={**h(), "X-Privacy-Grant": g}
        ).status_code
        == 503
    )
    store.objects[key] = saved
    assert (
        client.post(
            path + "/download", headers={**h(), "X-Privacy-Grant": g}
        ).status_code
        == 410
    )
    with cases[0].connect() as c:
        c.execute(
            text(
                "UPDATE public.privacy_exports SET expires_at=now()-interval '1 second' WHERE id=:id"
            ),
            {"id": rid},
        )
        c.commit()
    assert client.get(path, headers=h()).json()["status"] == "expired"
    assert grant().status_code == 410


def test_worker_recovery_fencing_crypto_and_revocation(cases):
    from app.db.runtime import worker_transaction
    from app.workers.privacy_exports import LeaseLost, claim, fence, run_one

    rid = request_export(cases)
    cid = authorize(cases, rid)
    assert decision(cases, rid, cid).status_code == 200
    db = cases[1].state.database
    store = MemoryStore()
    store.fail = True
    assert run_one(db, cases[6], store, UUID(rid))
    with cases[0].connect() as c:
        old = c.execute(
            text(
                "SELECT snapshot_ciphertext,manifest_id FROM public.privacy_exports WHERE id=:id"
            ),
            {"id": rid},
        ).one()
        assert old[0]
    with ThreadPoolExecutor(max_workers=2) as pool:
        leases = list(pool.map(lambda _: claim(db, UUID(rid)), range(2)))
    leases = [lease for lease in leases if lease is not None]
    assert len(leases) == 1
    lease = leases[0]
    with cases[0].connect() as c:
        c.execute(
            text(
                "UPDATE public.privacy_exports SET lease_until=now()-interval '1 second' WHERE id=:id"
            ),
            {"id": rid},
        )
        c.commit()
    with worker_transaction(db, "synthetic-stale") as session, pytest.raises(LeaseLost):
        fence(session, lease)
    store.fail = False
    assert run_one(db, cases[6], store, UUID(rid))
    assert next(iter(store.objects.values())) == bytes(old[0])
    with cases[0].connect() as c:
        c.execute(
            text(
                "UPDATE public.privacy_export_authorities SET revoked_at=now() WHERE case_id=:cid"
            ),
            {"cid": cid},
        )
        c.commit()
    status = cases[2].get(BASE + "/" + rid, headers=cases[3]()).json()
    assert (
        cases[2]
        .post(
            BASE + "/" + rid + "/download-grants",
            headers=cases[3](),
            json={"expected_revision": status["revision"], "confirmed": True},
        )
        .status_code
        == 410
    )
    # Fail closed with no key before producing/uploading any bytes.
    rid2 = request_export(cases, "b")
    cid2 = authorize(cases, rid2)
    assert decision(cases, rid2, cid2).status_code == 200
    bad = cases[6].model_copy(update={"profile_data_keys": SecretStr("{}")})
    empty = MemoryStore()
    assert run_one(db, bad, empty, UUID(rid2))
    assert empty.objects == {}
    with cases[0].connect() as c:
        assert (
            c.execute(
                text("SELECT status FROM public.privacy_exports WHERE id=:id"),
                {"id": rid2},
            ).scalar_one()
            == "retry"
        )
        c.execute(
            text(
                "UPDATE public.privacy_exports SET status='escalated' WHERE id IN (:a,:b)"
            ),
            {"a": rid, "b": rid2},
        )
        c.commit()


def test_caps_holds_and_original_recipient(cases):
    from app.workers.privacy_exports import run_one

    rid = request_export(cases, "b")
    cid = authorize(cases, rid)
    assert decision(cases, rid, cid).status_code == 200
    with cases[0].connect() as c:
        # Retention holds preserve sources without imposing a blanket access denial.
        c.execute(
            text(
                "INSERT INTO public.retention_holds(resource_type,resource_id,reason_code,placed_by) VALUES('finder_message',:id,'SYNTHETIC_HOLD',:uid)"
            ),
            {"id": cases[7]["mb"], "uid": cases[4]["security_admin"]},
        )
        # Changed current QR owner must not redirect original-recipient receipts.
        c.execute(
            text("UPDATE public.tag_pairs SET owner_user_id=:uid WHERE id=:id"),
            {"uid": cases[4]["a"], "id": cases[7]["pb"]},
        )
        c.commit()
    store = MemoryStore()
    assert run_one(cases[1].state.database, cases[6], store, UUID(rid))
    from app.core.profile_crypto import decrypt

    with cases[0].connect() as c:
        row = c.execute(
            text(
                "SELECT manifest_id,key_version FROM public.privacy_exports WHERE id=:id"
            ),
            {"id": rid},
        ).one()
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.retention_holds WHERE resource_id=:id AND released_at IS NULL"
                ),
                {"id": cases[7]["mb"]},
            ).scalar_one()
            == 1
        )
        assert (
            c.execute(
                text(
                    "SELECT recipient_owner_user_id FROM public.finder_messages WHERE id=:id"
                ),
                {"id": cases[7]["mb"]},
            ).scalar_one()
            == cases[4]["b"]
        )
        c.execute(
            text(
                "UPDATE public.privacy_exports SET status='expired',expires_at=now() WHERE id=:id"
            ),
            {"id": rid},
        )
        c.commit()
    raw = json.loads(
        decrypt(
            cases[6],
            UUID(rid),
            "privacy-export:" + str(row[0]),
            next(iter(store.objects.values())),
            row[1],
        )
    )
    assert len(raw["data"]["receipts"]) == 1 and raw["data"]["pairs"] == []
    rid = request_export(cases, "b")
    cid = authorize(cases, rid)
    assert decision(cases, rid, cid).status_code == 200
    with cases[0].connect() as c:
        c.execute(
            text(
                "INSERT INTO public.support_cases(opened_by_user_id,case_type) SELECT :uid,'privacy' FROM generate_series(1,10001)"
            ),
            {"uid": cases[4]["b"]},
        )
        c.commit()
    store = MemoryStore()
    assert run_one(cases[1].state.database, cases[6], store, UUID(rid))
    assert not store.objects
    assert (
        cases[2].get(BASE + "/" + rid, headers=cases[3]("b")).json()["status"]
        == "escalated"
    )


def test_financial_projection_snapshot_and_approval_expiry(cases):
    from sqlalchemy.exc import DBAPIError
    from test_commerce_schema import sample as commerce_sample

    from app.core.profile_crypto import decrypt, encrypt
    from app.db.runtime import worker_transaction
    from app.workers.privacy_exports import run_one

    pg, app, client, h, users, sessions, settings, _ = cases
    with pg.connect() as c:
        own = commerce_sample.__wrapped__(c)
        foreign = commerce_sample.__wrapped__(c)
        uid = own["customer"]
        sid = uuid4()
        c.execute(
            text(
                "UPDATE auth.users SET email='financial-subject@synthetic.invalid',email_confirmed_at=now() WHERE id=:id"
            ),
            {"id": uid},
        )
        c.execute(
            text(
                "INSERT INTO auth.sessions(id,user_id,aal,not_after) VALUES(:sid,:uid,'aal2',now()+interval '1 hour')"
            ),
            {"sid": sid, "uid": uid},
        )
        c.execute(
            text(
                "INSERT INTO public.user_profiles(user_id,display_name) VALUES(:uid,'Synthetic financial subject')"
            ),
            {"uid": uid},
        )
        c.execute(
            text(
                "UPDATE public.payment_attempts SET sender_reference_masked='BANK_CANARY',provider_payload_ref='PROVIDER_LOCATOR_CANARY' WHERE id=:id"
            ),
            {"id": own["attempt"]},
        )
        c.execute(
            text(
                "UPDATE public.order_shipping_snapshots SET city='ADDRESS_CANARY' WHERE order_id=:id"
            ),
            {"id": own["purchase"]},
        )
        cid = uuid4()
        eid = uuid4()
        legacy, version = encrypt(
            settings, uid, "account_deletion_reason", "LEGACY_REASON_CANARY"
        )
        note, note_version = encrypt(
            settings, eid, "support_note", "ASSIGNED_AGENT_NOTE_CANARY"
        )
        c.execute(
            text(
                "INSERT INTO public.support_cases(id,case_type,opened_by_user_id,assigned_staff_id,description_ciphertext,description_key_version) VALUES(:id,'privacy',:uid,:staff,:cipher,:version)"
            ),
            {
                "id": cid,
                "uid": uid,
                "staff": users["support"],
                "cipher": legacy,
                "version": version,
            },
        )
        c.execute(
            text(
                "INSERT INTO public.support_case_events(id,case_id,case_revision,actor_staff_id,event_type,to_status,priority,note_ciphertext,note_key_version) VALUES(:id,:cid,1,:staff,'created','open','normal',:note,:version)"
            ),
            {
                "id": eid,
                "cid": cid,
                "staff": users["support"],
                "note": note,
                "version": note_version,
            },
        )
        c.commit()
    users["financial_subject"] = uid
    sessions["financial_subject"] = sid
    rid = request_export(cases, "financial_subject")
    cid = authorize(cases, rid)
    assert decision(cases, rid, cid).status_code == 200
    # The worker cannot alter identity or approval even with a valid worker context.
    with (
        pytest.raises(DBAPIError),
        worker_transaction(app.state.database, "synthetic-boundary") as db,
    ):
        db.execute(
            text("UPDATE public.privacy_exports SET subject_id=:uid WHERE id=:id"),
            {"uid": users["b"], "id": rid},
        )
    store = MemoryStore()
    assert run_one(app.state.database, settings, store, UUID(rid))
    with pg.connect() as c:
        row = c.execute(
            text(
                "SELECT manifest_id,key_version FROM public.privacy_exports WHERE id=:id"
            ),
            {"id": rid},
        ).one()
    raw = decrypt(
        settings,
        UUID(rid),
        "privacy-export:" + str(row[0]),
        next(iter(store.objects.values())),
        row[1],
    )
    archive = json.loads(raw)
    data = archive["data"]
    assert data["orders"] == [
        {
            "order_id": str(own["purchase"]),
            "status": "draft",
            "total": "0.76",
            "currency": "PKR",
            "placed_at": None,
        }
    ]
    assert (
        len(data["items"]) == 2
        and len(data["occurrences"]) == 2
        and len(data["payments"]) == 1
    )
    assert sum(item["copies"] for item in data["occurrences"]) == 5
    assert data["payments"][0]["amount"] == "0.76"
    for canary in [
        "BANK_CANARY",
        "PROVIDER_LOCATOR_CANARY",
        "ADDRESS_CANARY",
        "LEGACY_REASON_CANARY",
        "ASSIGNED_AGENT_NOTE_CANARY",
        str(foreign["purchase"]),
        str(foreign["customer"]),
    ]:
        assert canary not in raw
    markers = {
        c["source_watermark"] for c in archive["manifest"]["categories"].values()
    }
    assert len(markers) == 1 and next(iter(markers)).startswith("pg_snapshot:")
    with pg.connect() as c:
        c.execute(
            text(
                "UPDATE public.privacy_exports SET expires_at=now()-interval '1 second' WHERE id=:id"
            ),
            {"id": rid},
        )
        c.commit()
    old = request_export(cases, "financial_subject")
    cid = authorize(cases, old)
    assert decision(cases, old, cid).status_code == 200
    with pg.connect() as c:
        c.execute(
            text(
                "UPDATE public.privacy_exports SET approved_at=now()-interval '25 hours' WHERE id=:id"
            ),
            {"id": old},
        )
        c.commit()
    assert run_one(app.state.database, settings, store, UUID(old)) is False
    assert (
        client.get(BASE + "/" + old, headers=h("financial_subject")).json()["status"]
        == "escalated"
    )


def test_privacy_export_browser(cases):
    import os
    import shutil
    import socket
    import subprocess
    import threading
    import time
    from pathlib import Path

    import uvicorn

    pg, app, _client, headers, users, _sessions, settings, _ids = cases
    root = Path(__file__).parents[3]
    state = {"role": "a"}
    store = MemoryStore()
    app.state.privacy_export_store = store
    user = lambda: {
        "id": str(users[state["role"]]),
        "aud": "authenticated",
        "role": "authenticated",
        "email": state["role"] + "@synthetic.invalid",
        "email_confirmed_at": "2026-01-01T00:00:00Z",
        "user_metadata": {},
        "app_metadata": {},
        "created_at": "2026-01-01T00:00:00Z",
    }

    @app.get("/auth/v1/user")
    def fixture_user():
        return user()

    @app.post("/auth/v1/token")
    def fixture_token():
        return {
            "access_token": headers(state["role"])["Authorization"].removeprefix(
                "Bearer "
            ),
            "refresh_token": "synthetic-refresh",
            "expires_in": 3600,
            "token_type": "bearer",
            "user": user(),
        }

    @app.post("/fixture/support-role/{role}")
    def fixture_role(role: str):
        assert role in users
        state["role"] = role
        return {"ok": True}

    @app.post("/fixture/export-authorize")
    def fixture_authorize():
        with pg.connect() as c:
            rid = str(
                c.execute(
                    text(
                        "SELECT id FROM public.privacy_exports WHERE subject_id=:uid AND status='requested' ORDER BY created_at DESC LIMIT 1"
                    ),
                    {"uid": users["a"]},
                ).scalar_one()
            )
        authorize(cases, rid)
        return {"ok": True}

    @app.post("/fixture/export-build")
    def fixture_build():
        from app.workers.privacy_exports import run_one

        assert run_one(app.state.database, settings, store)
        return {"ok": True}

    for port in (3100, 8115):
        with socket.socket() as probe:
            assert probe.connect_ex(("127.0.0.1", port)) != 0, "Isolated port occupied"
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("SAFERETURN_", "TASK", "QR_TEST_"))
    }
    env.update(
        SAFERETURN_API_ORIGIN="http://127.0.0.1:8115",
        SAFERETURN_WEB_ORIGIN="http://127.0.0.1:3100",
        SAFERETURN_SUPABASE_URL="https://fixture.test",
        SAFERETURN_SUPABASE_PUBLISHABLE_KEY="sb_publishable_fixture",
        SAFERETURN_SESSION_SIGNING_KEY="ab" * 32,
        NEXT_TELEMETRY_DISABLED="1",
        PLAYWRIGHT_EXTERNAL_SERVER="1",
        PLAYWRIGHT_CHANNEL="msedge",
    )
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=8115,
            lifespan="off",
            access_log=False,
            log_level="error",
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    process = None
    try:
        process = subprocess.Popen(
            [
                shutil.which("node"),
                "--require",
                str(root / "frontend/tests/qr-fixture-fetch.cjs"),
                str(root / "frontend/node_modules/next/dist/bin/next"),
                "start",
                "--hostname",
                "127.0.0.1",
                "--port",
                "3100",
            ],
            cwd=root / "tmp/task57j-final-web",
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        for _ in range(50):
            try:
                if (
                    httpx.get("http://127.0.0.1:3100/login", timeout=2).status_code
                    == 200
                ):
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.2)
        else:
            raise AssertionError("Isolated frontend did not start")
        result = subprocess.run(
            [
                shutil.which("npm.cmd" if os.name == "nt" else "npm"),
                "test",
                "--",
                "tests/privacy-exports.spec.ts",
                "--workers=1",
                "--output=../tmp/task57j-playwright-" + uuid4().hex,
            ],
            cwd=root / "frontend",
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
            check=False,
        )
        print(result.stdout.encode("ascii", "backslashreplace").decode("ascii"))
        if result.returncode:
            print(result.stderr.encode("ascii", "backslashreplace").decode("ascii"))
        assert result.returncode == 0, "Synthetic privacy export browser failed"
    finally:
        if process:
            process.terminate()
            process.wait(timeout=15)
        server.should_exit = True
        thread.join(timeout=15)
