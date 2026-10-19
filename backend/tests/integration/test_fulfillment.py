"""Isolated real PostgreSQL fulfillment acceptance; no real settlement or shipping."""

import time
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from sqlalchemy import text
from test_auth import ORIGIN, claims, keyset, signed
from test_checkout import sample as checkout_sample  # noqa: F401
from test_health import ASGIClient
from test_payments import sample as payment_sample  # noqa: F401
from test_printing import durable, enqueue
from test_printing import sample as print_sample  # noqa: F401

from app.core.auth import JWTVerifier
from app.core.config import Settings
from app.workers.printing import run_one


@pytest.fixture(scope="module")
def sample(print_sample):  # noqa: F811
    pg = print_sample[0][0]
    app = print_sample[2]
    with pg.connect() as c:
        pg.upgrade(c, "0018_fulfillment_eligibility")
        c.rollback()
        assert c.execute(
            text(
                "SELECT to_regprocedure('public.sr_fulfillment_eligible(uuid)') IS NULL"
            )
        ).scalar_one()
        c.rollback()
        pg.upgrade(c, "0018_fulfillment_eligibility")
        c.commit()
    private = ec.generate_private_key(ec.SECP256R1())
    verifier = JWTVerifier(
        Settings(supabase_url=ORIGIN),
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={"keys": [keyset(private)]})
        ),
    )
    users = {
        "operations": UUID(app.state.printing_fixture_user),
        **print_sample[0][5],
        "finance": print_sample[0][3].state.finance_user,
    }
    with pg.connect() as c:
        c.execute(
            text(
                "INSERT INTO auth.sessions(id,user_id,aal,not_after) VALUES(:sid,:uid,'aal2',now()+interval '1 hour')"
            ),
            {"sid": uuid4(), "uid": users["finance"]},
        )
        c.commit()
        sessions = {
            role: c.execute(
                text("SELECT id FROM auth.sessions WHERE user_id=:id LIMIT 1"),
                {"id": uid},
            ).scalar_one()
            for role, uid in users.items()
        }
        c.rollback()
    old = app.state.jwt_verifier
    app.state.jwt_verifier = verifier
    client = ASGIClient(app)

    def token(role="operations", mfa=True):
        return signed(
            private,
            claims(
                sub=str(users[role]),
                session_id=str(sessions[role]),
                aal="aal2" if mfa else "aal1",
                exp=int(time.time()) + 600,
            ),
        )

    def call(path, body=None, key=None, role="operations", mfa=True, method="POST"):
        return client.request(
            method,
            "/api/v1" + path,
            json=body,
            headers={
                "Authorization": "Bearer " + token(role, mfa),
                "Idempotency-Key": key or str(uuid4()),
            },
        )

    # Existing print helpers sign with the original verifier; swap only around their calls.
    def ready(qa=True):
        app.state.jwt_verifier = old
        try:
            oid, jid = enqueue(print_sample)
            assert run_one(
                app.state.database,
                app.state.settings,
                print_sample[3],
                durable(print_sample, jid),
            )
            if qa:
                a = print_sample[1](f"/admin/print-jobs/{jid}", method="GET").json()[
                    "artifacts"
                ][0]
                body = {
                    "approved": True,
                    "artifact_sha256": a["sha256_hex"],
                    "observed": [
                        {"tag_type": "lost", "symbol_mm": "35", "copies": 3},
                        {"tag_type": "ice", "symbol_mm": "35", "copies": 2},
                    ],
                    **{
                        k: True
                        for k in [
                            "scan_passed",
                            "logo_quiet_zone_passed",
                            "bilingual_passed",
                            "cutting_packaging_passed",
                            "actual_scale_passed",
                        ]
                    },
                    "reason": "Synthetic physical QA fixture only",
                }
                r = print_sample[1](f"/admin/print-jobs/{jid}/qa", body)
                assert r.status_code == 200, r.text
        finally:
            app.state.jwt_verifier = verifier
        with pg.connect() as c:
            pairs = (
                c.execute(
                    text(
                        "SELECT pair_id FROM public.order_pair_units WHERE order_id=:id"
                    ),
                    {"id": oid},
                )
                .scalars()
                .all()
            )
            address = c.execute(
                text(
                    "SELECT source_address_id FROM public.order_shipping_snapshots WHERE order_id=:id"
                ),
                {"id": oid},
            ).scalar_one()
            if qa:
                for pid in pairs:
                    c.execute(
                        text(
                            """INSERT INTO public.pair_print_qa(pair_id,inspected_by,qa_round,lost_scan_passed,ice_scan_passed,pair_match_passed,credential_concealed,bilingual_label_passed,quiet_zone_passed,indoor_size_passed,outdoor_size_passed,packaging_method,tamper_evidence_passed,approved) VALUES(:id,:uid,1,true,true,true,true,true,true,true,true,'sealed_sleeve',true,true)"""
                        ),
                        {"id": pid, "uid": users["operations"]},
                    )
                c.commit()
        return {
            "order_id": oid,
            "shipping_address_id": str(address),
            "pair_ids": list(map(str, pairs)),
            "carrier": "Synthetic carrier",
            "reason": "Synthetic fulfillment verification",
        }, jid

    yield pg, call, ready, app, token, print_sample
    app.state.jwt_verifier = old
    verifier.close()


def create(s, body=None, key=None):
    body = body or s[2]()[0]
    r = s[1]("/admin/shipments", body, key)
    assert r.status_code == 201, r.text
    return body, r.json()["shipment_id"]


def move(s, sid, old, new, **extra):
    return s[1](
        f"/admin/shipments/{sid}",
        {
            "expected_status": old,
            "status": new,
            "reason": "Synthetic trusted manual confirmation",
            **extra,
        },
        method="PATCH",
    )


def test_owner_history_copies_snapshot_and_isolation(sample):
    body, _ = sample[2]()
    oid = body["order_id"]
    r = sample[1](f"/me/orders/{oid}", role="owner", method="GET")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["pair_count"] == 1 and len(data["qr_uses"]) == 2
    assert [u["copies"] for u in data["qr_uses"]] == [3, 2]
    assert data["shipping_snapshot"]["city"] == "Lahore"
    assert data["shipping_snapshot"]["recipient_name"] == "Synthetic recipient"
    assert data["print_status"] == "qa_passed"
    assert "object_key" not in r.text and "secret_verifier" not in r.text
    assert sample[1](f"/me/orders/{oid}", role="other", method="GET").status_code == 404
    assert (
        sample[1](f"/me/orders/{oid}/shipments", role="other", method="GET").status_code
        == 404
    )


def test_queue_requires_latest_physical_qa_and_role_mfa(sample):
    body, _jid = sample[2](qa=False)
    oid = body["order_id"]
    assert (
        sample[1]("/admin/orders/ready-to-ship", method="GET", role="owner").status_code
        == 403
    )
    assert (
        sample[1]("/admin/orders/ready-to-ship", method="GET", mfa=False).status_code
        == 403
    )
    r = sample[1]("/admin/orders/ready-to-ship", method="GET")
    assert r.status_code == 200, r.text
    assert oid not in [x["id"] for x in r.json()["items"]]
    assert sample[1]("/admin/shipments", body).status_code == 409


def test_create_idempotency_concurrency_membership_and_address(sample):
    body, _jid = sample[2]()
    key = str(uuid4())
    for changed in [
        dict(body, shipping_address_id=str(uuid4())),
        dict(body, pair_ids=[str(uuid4())]),
        dict(body, pair_ids=body["pair_ids"] * 2),
    ]:
        assert sample[1]("/admin/shipments", changed).status_code == 409
    with ThreadPoolExecutor(2) as pool:
        rs = list(
            pool.map(lambda _: sample[1]("/admin/shipments", body, key), range(2))
        )
    assert [r.status_code for r in rs] == [201, 201], [r.text for r in rs]
    assert rs[0].json() == rs[1].json()
    assert (
        sample[1](
            "/admin/shipments", dict(body, reason="Changed synthetic reason"), key
        ).status_code
        == 409
    )
    assert sample[1]("/admin/shipments", body).status_code == 409
    with sample[0].connect() as c:
        assert (
            c.execute(
                text("SELECT count(*) FROM public.shipments WHERE order_id=:id"),
                {"id": body["order_id"]},
            ).scalar_one()
            == 1
        )
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.shipment_pairs WHERE shipment_id=:id"
                ),
                {"id": rs[0].json()["shipment_id"]},
            ).scalar_one()
            == 1
        )
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.audit_events WHERE target_id=:id AND action='shipment.create'"
                ),
                {"id": rs[0].json()["shipment_id"]},
            ).scalar_one()
            == 1
        )


def test_ordered_pack_dispatch_delivery_and_retry(sample):
    body, sid = create(sample)
    assert move(sample, sid, "preparing", "delivered").status_code == 409
    assert move(sample, sid, "preparing", "packed").status_code == 422
    r = move(sample, sid, "preparing", "packed", packing_confirmed=True)
    assert r.status_code == 200, r.text
    assert (
        move(sample, sid, "preparing", "packed", packing_confirmed=True).status_code
        == 412
    )
    assert move(sample, sid, "packed", "dispatched").status_code == 422
    r = move(
        sample, sid, "packed", "dispatched", tracking_reference="SYNTHETIC-TRACKING"
    )
    assert r.status_code == 200, r.text
    payload = {
        "expected_status": "dispatched",
        "status": "delivered",
        "reason": "Synthetic carrier delivery checked manually",
    }
    key = str(uuid4())
    path = f"/admin/shipments/{sid}"
    r = sample[1](path, payload, key, method="PATCH")
    assert r.status_code == 200, r.text
    assert sample[1](path, payload, key, method="PATCH").json() == r.json()
    assert move(sample, sid, "delivered", "returned").status_code == 409
    detail = sample[1](
        f"/me/orders/{body['order_id']}", role="owner", method="GET"
    ).json()
    assert detail["fulfillment_status"] == "delivered"
    shipping = sample[1](
        f"/me/orders/{body['order_id']}/shipments", role="owner", method="GET"
    ).json()["items"][0]
    assert (
        shipping["packed_at"] and shipping["dispatched_at"] and shipping["delivered_at"]
    )


def test_concurrent_different_keys_cannot_duplicate_shipment(sample):
    body, _ = sample[2]()
    with ThreadPoolExecutor(2) as pool:
        rs = list(pool.map(lambda _: sample[1]("/admin/shipments", body), range(2)))
    assert sorted(r.status_code for r in rs) == [201, 409], [r.text for r in rs]


def test_exception_path_cannot_bypass_dispatch(sample):
    _body, sid = create(sample)
    assert move(sample, sid, "preparing", "exception").status_code == 200
    assert move(sample, sid, "exception", "delivered").status_code == 409
    assert (
        move(sample, sid, "exception", "packed", packing_confirmed=True).status_code
        == 409
    )
    assert move(sample, sid, "exception", "returned").status_code == 200


def test_write_rollback_if_receipt_encryption_unavailable(sample, monkeypatch):
    body, _ = sample[2]()
    from app.api.v1 import fulfillment
    from app.core.profile_crypto import ProfileCryptoUnavailable

    old = fulfillment.encrypt

    def unavailable(*args, **kwargs):
        raise ProfileCryptoUnavailable()

    monkeypatch.setattr(fulfillment, "encrypt", unavailable)
    try:
        assert sample[1]("/admin/shipments", body).status_code == 503
    finally:
        monkeypatch.setattr(fulfillment, "encrypt", old)
    with sample[0].connect() as c:
        assert (
            c.execute(
                text("SELECT count(*) FROM public.shipments WHERE order_id=:id"),
                {"id": body["order_id"]},
            ).scalar_one()
            == 0
        )
    create(sample, body)


def test_paging_invalid_cursor_and_tied_timestamps(sample):
    with sample[0].connect() as c:
        for _ in range(3):
            c.execute(
                text(
                    "INSERT INTO public.orders(order_number,customer_user_id,subtotal_pkr,total_pkr) VALUES(:number,:uid,0,0)"
                ),
                {"number": "PAGE-" + uuid4().hex, "uid": sample[5][0][5]["owner"]},
            )
        c.commit()
    r = sample[1]("/me/orders?limit=1", role="owner", method="GET")
    assert r.status_code == 200, r.text
    seen = set()
    while True:
        d = r.json()
        for item in d["items"]:
            assert item["id"] not in seen
            seen.add(item["id"])
        if not d["next_cursor"]:
            break
        r = sample[1](
            "/me/orders?limit=1&cursor=" + d["next_cursor"], role="owner", method="GET"
        )
        assert r.status_code == 200, r.text
    assert len(seen) >= 3
    assert (
        sample[1]("/me/orders?cursor=broken", role="owner", method="GET").status_code
        == 422
    )
    assert (
        sample[1](
            "/admin/orders/ready-to-ship?status=invalid", method="GET"
        ).status_code
        == 422
    )


def test_settlement_and_newer_print_revision_block_outbound(sample):
    body, _jid = sample[2]()
    oid = body["order_id"]
    with sample[0].connect() as c:
        c.execute(
            text("UPDATE public.orders SET payment_status='refunded' WHERE id=:id"),
            {"id": oid},
        )
        c.commit()
    assert sample[1]("/admin/shipments", body).status_code == 409
    with sample[0].connect() as c:
        c.execute(
            text("UPDATE public.orders SET payment_status='verified' WHERE id=:id"),
            {"id": oid},
        )
        c.commit()
    r = sample[1](
        f"/admin/orders/{oid}/print-jobs",
        {
            "expected_revision": 1,
            "reason": "Synthetic newer revision invalidates release",
        },
    )
    assert r.status_code == 202, r.text
    assert sample[1]("/admin/shipments", body).status_code == 409


def test_concurrent_pack_updates_one_transition_and_receipt(sample):
    _body, sid = create(sample)
    with ThreadPoolExecutor(2) as pool:
        rs = list(
            pool.map(
                lambda _: move(
                    sample, sid, "preparing", "packed", packing_confirmed=True
                ),
                range(2),
            )
        )
    assert sorted(r.status_code for r in rs) == [200, 412], [r.text for r in rs]


def test_role_revocation_blocks_receipt_replay(sample):
    body, _ = sample[2]()
    key = str(uuid4())
    r = sample[1]("/admin/shipments", body, key)
    assert r.status_code == 201, r.text
    uid = sample[3].state.printing_fixture_user
    with sample[0].connect() as c:
        c.execute(
            text(
                "UPDATE public.staff_roles SET revoked_at=now() WHERE user_id=:uid AND role='operations' AND revoked_at IS NULL"
            ),
            {"uid": uid},
        )
        c.commit()
    try:
        assert sample[1]("/admin/shipments", body, key).status_code == 403
    finally:
        with sample[0].connect() as c:
            c.execute(
                text(
                    "UPDATE public.staff_roles SET revoked_at=NULL WHERE user_id=:uid AND role='operations'"
                ),
                {"uid": uid},
            )
            c.commit()


def test_browser_operations(sample):
    from checkout_browser import run

    body, _ = sample[2]()
    app = sample[3]
    app.state.checkout_fixture_token = lambda: sample[4]()
    app.state.checkout_fixture_user = app.state.printing_fixture_user
    base = sample[5][0]
    run(
        (base[0], ASGIClient(app), base[2], app, *base[4:]),
        test_files=["tests/fulfillment.spec.ts"],
        extra_env={"FULFILLMENT_ORDER": body["order_id"]},
    )


def test_browser_owner_history(sample):
    from checkout_browser import run

    from app.db.session import Database
    from app.main import create_app

    body, _ = sample[2]()
    app = create_app(sample[3].state.settings, verifier=sample[3].state.jwt_verifier)
    app.state.database = Database(sample[0].engine)
    app.state.jwt_verifier = sample[3].state.jwt_verifier
    app.state.checkout_fixture_token = lambda: sample[4]("owner", False)
    app.state.checkout_fixture_user = str(sample[5][0][5]["owner"])
    base = sample[5][0]
    try:
        run(
            (base[0], ASGIClient(app), base[2], app, *base[4:]),
            test_files=["tests/order-history.spec.ts"],
            extra_env={"FULFILLMENT_ORDER": body["order_id"]},
        )
    finally:
        app.state.database.close()


def test_operations_address_access_and_finance_minimization(sample):
    body, _ = sample[2]()
    oid = body["order_id"]
    assert (
        sample[1](f"/admin/orders/{oid}", role="owner", method="GET").status_code == 403
    )
    assert sample[1](f"/admin/orders/{oid}", mfa=False, method="GET").status_code == 403
    finance = sample[1](f"/admin/orders/{oid}", role="finance", method="GET")
    assert finance.status_code == 200, finance.text
    assert "shipping_snapshot" not in finance.json()
    assert "Synthetic private street" not in finance.text
    assert sample[1]("/admin/shipments", body, role="finance").status_code == 403
    operations = sample[1](f"/admin/orders/{oid}", method="GET")
    assert operations.status_code == 200, operations.text
    assert operations.json()["shipping_snapshot"]["city"] == "Lahore"
    with sample[0].connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.audit_events WHERE target_id=:id AND action='shipment.address.read'"
                ),
                {"id": oid},
            ).scalar_one()
            == 1
        )


def test_database_commit_guard_rejects_missing_current_print_qa(sample):
    from sqlalchemy.exc import DBAPIError

    from app.db.runtime import api_transaction

    body, _ = sample[2](qa=False)
    sid = uuid4()
    with (
        pytest.raises(DBAPIError) as error,
        api_transaction(
            sample[3].state.database,
            UUID(sample[3].state.printing_fixture_user),
            mfa_verified=True,
        ) as session,
    ):
        session.execute(
            text(
                "INSERT INTO public.shipments(id,order_id,shipping_address_id,carrier) VALUES(:id,:oid,:address,'Synthetic DB bypass probe')"
            ),
            {
                "id": sid,
                "oid": body["order_id"],
                "address": body["shipping_address_id"],
            },
        )
        for pair in body["pair_ids"]:
            session.execute(
                text(
                    "INSERT INTO public.shipment_pairs(shipment_id,pair_id) VALUES(:id,:pair)"
                ),
                {"id": sid, "pair": pair},
            )
    assert error.value.orig.sqlstate == "23514"
    assert "Shipment requires complete" in error.value.orig.diag.message_primary
    with sample[0].connect() as c:
        assert (
            c.execute(
                text("SELECT count(*) FROM public.shipments WHERE id=:id"), {"id": sid}
            ).scalar_one()
            == 0
        )


def test_database_completion_rechecks_late_print_failure_and_rolls_back(sample):
    from sqlalchemy.exc import DBAPIError

    body, jid = sample[2]()
    sid = uuid4()
    with sample[0].connect() as c:
        with pytest.raises(DBAPIError) as error, c.begin():
            c.execute(
                text(
                    "SELECT set_config('safereturn.actor_id',:uid,true),set_config('safereturn.mfa_verified','true',true)"
                ),
                {"uid": sample[3].state.printing_fixture_user},
            )
            c.execute(
                text(
                    "INSERT INTO public.shipments(id,order_id,shipping_address_id,carrier) VALUES(:id,:oid,:address,'Synthetic commit fault probe')"
                ),
                {
                    "id": sid,
                    "oid": body["order_id"],
                    "address": body["shipping_address_id"],
                },
            )
            for pair in body["pair_ids"]:
                c.execute(
                    text(
                        "INSERT INTO public.shipment_pairs(shipment_id,pair_id) VALUES(:id,:pair)"
                    ),
                    {"id": sid, "pair": pair},
                )
            c.execute(
                text("UPDATE public.print_jobs SET status='failed' WHERE id=:id"),
                {"id": jid},
            )
        assert error.value.orig.sqlstate == "23514"
        assert (
            c.execute(
                text("SELECT count(*) FROM public.shipments WHERE id=:id"), {"id": sid}
            ).scalar_one()
            == 0
        )
        assert (
            c.execute(
                text("SELECT status FROM public.print_jobs WHERE id=:id"), {"id": jid}
            ).scalar_one()
            == "qa_passed"
        )


def test_database_commit_guard_rejects_removed_membership(sample):
    from sqlalchemy.exc import DBAPIError

    _body, sid = create(sample)
    with sample[0].connect() as c:
        with pytest.raises(DBAPIError) as error, c.begin():
            c.execute(
                text(
                    "SELECT set_config('safereturn.actor_id',:uid,true),set_config('safereturn.mfa_verified','true',true)"
                ),
                {"uid": sample[3].state.printing_fixture_user},
            )
            c.execute(
                text("DELETE FROM public.shipment_pairs WHERE shipment_id=:id"),
                {"id": sid},
            )
        assert error.value.orig.sqlstate == "23514"
        assert "Shipment requires complete" in error.value.orig.diag.message_primary
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.shipment_pairs WHERE shipment_id=:id"
                ),
                {"id": sid},
            ).scalar_one()
            == 1
        )


def test_database_eligibility_does_not_expose_finance_rows(sample):
    from app.db.runtime import api_transaction

    body, _ = sample[2]()
    uid = UUID(sample[3].state.printing_fixture_user)
    with api_transaction(sample[3].state.database, uid, mfa_verified=True) as session:
        assert (
            session.execute(
                text("SELECT count(*) FROM public.payment_attempts WHERE order_id=:id"),
                {"id": body["order_id"]},
            ).scalar_one()
            == 0
        )
        assert (
            session.execute(
                text("SELECT public.sr_fulfillment_eligible(:id)"),
                {"id": body["order_id"]},
            ).scalar_one()
            is True
        )
    with api_transaction(sample[3].state.database, uid, mfa_verified=False) as session:
        assert (
            session.execute(
                text("SELECT public.sr_fulfillment_eligible(:id)"),
                {"id": body["order_id"]},
            ).scalar_one()
            is False
        )


def test_refund_pauses_outbound_and_allows_safe_exception(sample):
    body, sid = create(sample)
    with sample[0].connect() as c:
        c.execute(
            text("UPDATE public.orders SET payment_status='refunded' WHERE id=:id"),
            {"id": body["order_id"]},
        )
        c.commit()
    assert (
        move(sample, sid, "preparing", "packed", packing_confirmed=True).status_code
        == 409
    )
    history = sample[1]("/admin/orders/ready-to-ship?status=exception", method="GET")
    assert history.status_code == 200, history.text
    assert body["order_id"] in [r["id"] for r in history.json()["items"]]
    r = move(sample, sid, "preparing", "exception")
    assert r.status_code == 200, r.text
    assert (
        move(sample, sid, "exception", "packed", packing_confirmed=True).status_code
        == 409
    )
    assert move(sample, sid, "exception", "returned").status_code == 200
