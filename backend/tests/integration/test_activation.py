"""Task 3.2 real PostgreSQL request, rollback, entitlement and race checks."""

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_commerce_schema import pay, place
from test_inventory_generation import batch_request, open_insert
from test_inventory_generation import inventory_context as _inventory_context

from app.db.runtime import api_transaction
from app.db.session import Database

pytest_plugins = ["test_auth_guards"]
inventory_context = _inventory_context

INTENTS = "/api/v1/me/tag-pairs/activation-intents"
ACTIVATE = "/api/v1/me/tag-pairs/activations"


@pytest.fixture
def activation(inventory_context, guarded):
    pg, wf, headers, client, private, _ = inventory_context
    wf = dict(wf)
    with pg.connect() as c:
        for name in ("a", "b"):
            uid, sid = uuid.uuid4(), uuid.uuid4()
            c.execute(
                text("INSERT INTO auth.users(id,email_confirmed_at) VALUES(:id,now())"),
                {"id": uid},
            )
            c.execute(
                text(
                    "INSERT INTO auth.sessions(id,user_id,aal,not_after) VALUES(:sid,:uid,'aal2',now()+interval '1 hour')"
                ),
                {"sid": sid, "uid": uid},
            )
            guarded[3][uid] = sid
            wf[name] = uid
        c.commit()
    batch = client.post(
        "/api/v1/admin/qr-batches",
        json={**batch_request(), "pair_count": 1},
        headers={**headers(wf["operations"]), "Idempotency-Key": uuid.uuid4().hex},
    )
    assert batch.status_code == 201, batch.text
    manifest = open_insert(
        private, batch.json()["sealed_insert"], batch.json()["batch_id"]
    )
    item = manifest["pairs"][0]
    with pg.connect() as c:
        pid = c.execute(
            text(
                "UPDATE tag_pairs SET inventory_status='qa_passed' WHERE batch_id=:id RETURNING id"
            ),
            {"id": batch.json()["batch_id"]},
        ).scalar_one()
        c.commit()
    return pg, wf, headers, client, pid, item


def intent(a, actor="a", secret=True, token=None):
    _, wf, headers, client, _, item = a
    return client.post(
        INTENTS,
        json={
            "scanned_token": token or item["tags"][0]["public_token"],
            "activation_secret": item["activation_secret"]
            if secret is True
            else (None if secret is False else secret),
        },
        headers=headers(wf[actor]),
    )


def confirm(a, iid, actor="a", key=None, **extra):
    _, wf, headers, client, _, _ = a
    return client.post(
        ACTIVATE,
        json={"intent_id": iid, "confirm": True, **extra},
        headers={**headers(wf[actor]), "Idempotency-Key": key or uuid.uuid4().hex},
    )


def test_public_context_minimal_both_tokens_and_unknown(activation):
    _, _, _, client, _, item = activation
    for tag in item["tags"]:
        response = client.get(
            f"/api/v1/public/qr/{tag['public_token']}/activation-context"
        )
        assert response.status_code == 200
        assert response.json() == {
            "status": "not_activated",
            "can_begin": True,
            "tag_type": tag["tag_type"],
            "context_ttl_seconds": 900,
        }
        assert response.headers["cache-control"] == "no-store"
    assert client.get("/api/v1/public/qr/unknown/activation-context").status_code == 404


def test_token_is_not_entitlement_and_no_owner_disclosure(activation):
    a = intent(activation, secret=False)
    b = intent(activation, secret=False, token="unknown-token")
    assert a.status_code == b.status_code == 409
    assert a.json()["error"]["message"] == b.json()["error"]["message"]
    assert str(activation[4]) not in a.text


def test_secret_claim_atomic_replay_and_changed_key_conflict(activation):
    pg, wf, _, _, pid, _ = activation
    created = intent(activation)
    assert created.status_code == 201, created.text
    iid = created.json()["intent_id"]
    with pg.connect() as c:
        c.execute(
            text(
                "INSERT INTO lost_item_profiles(qr_id,item_label) VALUES(:id,'Synthetic label')"
            ),
            {"id": created.json()["lost_qr_id"]},
        )
        c.execute(
            text(
                "INSERT INTO ice_profiles(qr_id,display_name) VALUES(:id,'Synthetic ICE')"
            ),
            {"id": created.json()["ice_qr_id"]},
        )
        c.commit()
    key = uuid.uuid4().hex
    first = confirm(activation, iid, key=key)
    assert first.status_code == 201, first.text
    with pg.connect() as c:
        c.execute(
            text(
                "UPDATE tag_pairs SET activated_at=activated_at+interval '1 second' WHERE id=:p"
            ),
            {"p": pid},
        )
        c.commit()
    assert confirm(activation, iid, key=key).json() == first.json()
    assert confirm(activation, str(uuid.uuid4()), key=key).status_code == 409
    assert confirm(activation, iid).status_code == 409
    assert intent(activation).status_code == 409
    with pg.connect() as c:
        assert c.execute(
            text(
                "SELECT published,profile_version FROM lost_item_profiles WHERE qr_id=:id"
            ),
            {"id": created.json()["lost_qr_id"]},
        ).one() == (False, 1)
        assert c.execute(
            text(
                "SELECT published,profile_version,publication_consent_at FROM ice_profiles WHERE qr_id=:id"
            ),
            {"id": created.json()["ice_qr_id"]},
        ).one() == (False, 1, None)
        assert c.execute(
            text("SELECT owner_user_id,ownership_status FROM tag_pairs WHERE id=:p"),
            {"p": pid},
        ).one() == (wf["a"], "active")
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM qr_codes WHERE pair_id=:p AND is_current AND public_status='active'"
                ),
                {"p": pid},
            ).scalar_one()
            == 2
        )
        assert (
            c.execute(
                text("SELECT status FROM pair_activation_credentials WHERE pair_id=:p"),
                {"p": pid},
            ).scalar_one()
            == "consumed"
        )
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM audit_events WHERE target_id=:p AND action='pair.activated'"
                ),
                {"p": pid},
            ).scalar_one()
            == 1
        )
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM notification_outbox WHERE aggregate_id=:p AND event_type='pair.activated'"
                ),
                {"p": pid},
            ).scalar_one()
            == 1
        )


def test_actor_binding_and_confirmation_required(activation):
    iid = intent(activation).json()["intent_id"]
    assert confirm(activation, iid, actor="b").status_code == 409
    assert confirm(activation, iid, confirm=False).status_code == 400
    assert confirm(activation, iid).status_code == 201


def test_lockout_attempts_persist_on_error(activation):
    pg, _, _, _, pid, _ = activation
    for _ in range(5):
        assert intent(activation, secret="wrong-credential-secret").status_code == 409
    assert intent(activation).status_code == 429
    with pg.connect() as c:
        assert c.execute(
            text(
                "SELECT failed_attempts,status,locked_until>now() FROM pair_activation_credentials WHERE pair_id=:p"
            ),
            {"p": pid},
        ).one() == (5, "locked", True)


@pytest.mark.parametrize(
    "mutation", ["expired", "revoked", "suspended", "credential_revoked", "rotated"]
)
def test_confirmation_rechecks_eligibility(activation, mutation):
    pg, _, _, _, pid, _ = activation
    iid = intent(activation).json()["intent_id"]
    with pg.connect() as c:
        if mutation == "expired":
            # Expiry/binding fields cannot be edited. Make a synthetic historical
            # intent in the isolated schema and prove wall-clock expiry is checked.
            iid = str(
                c.execute(
                    text(
                        "INSERT INTO activation_intents(actor_user_id,pair_id,lost_qr_id,ice_qr_id,method,verifier_key_version,created_at,expires_at) SELECT actor_user_id,pair_id,lost_qr_id,ice_qr_id,method,verifier_key_version,now()-interval '16 minutes',now()-interval '1 minute' FROM activation_intents WHERE id=:id RETURNING id"
                    ),
                    {"id": iid},
                ).scalar_one()
            )
        elif mutation == "revoked":
            c.execute(
                text(
                    "UPDATE tag_pairs SET ownership_status='revoked',revoked_at=now() WHERE id=:p"
                ),
                {"p": pid},
            )
        elif mutation == "suspended":
            c.execute(
                text(
                    "UPDATE qr_codes SET public_status='admin_suspended' WHERE pair_id=:p AND tag_type='ice'"
                ),
                {"p": pid},
            )
        else:
            c.execute(
                text(
                    "UPDATE pair_activation_credentials SET status=:status,verifier_key_version=verifier_key_version+:delta WHERE pair_id=:p"
                ),
                {
                    "p": pid,
                    "status": "revoked"
                    if mutation == "credential_revoked"
                    else "unused",
                    "delta": int(mutation == "rotated"),
                },
            )
        c.commit()
    assert confirm(activation, iid).status_code == 409
    with pg.connect() as c:
        assert (
            c.execute(
                text("SELECT owner_user_id FROM tag_pairs WHERE id=:p"), {"p": pid}
            ).scalar_one()
            is None
        )


def test_two_actors_race_has_one_complete_winner(activation):
    first = intent(activation).json()["intent_id"]
    second = intent(activation, actor="b").json()["intent_id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda args: confirm(activation, *args), [(first, "a"), (second, "b")]
            )
        )
    assert sorted(r.status_code for r in results) == [201, 409]


def test_same_idempotency_key_concurrent_retries(activation):
    iid = intent(activation).json()["intent_id"]
    key = uuid.uuid4().hex
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: confirm(activation, iid, key=key), range(2)))
    assert [r.status_code for r in results] == [201, 201]
    assert results[0].json() == results[1].json()


def test_runtime_cannot_forge_intent_or_direct_ownership(activation):
    pg, wf, _, _, pid, _ = activation
    with (
        pytest.raises(DBAPIError),
        api_transaction(Database(pg.engine), wf["a"]) as session,
    ):
        session.execute(
            text(
                "INSERT INTO public.activation_intents(actor_user_id,pair_id,lost_qr_id,ice_qr_id,method,verifier_key_version,expires_at) SELECT :a,:p,l.id,i.id,'concealed_credential',3,now()+interval '1 minute' FROM public.qr_codes l,public.qr_codes i WHERE l.pair_id=:p AND i.pair_id=:p AND l.tag_type='lost' AND i.tag_type='ice'"
            ),
            {"a": wf["a"], "p": pid},
        )
    with api_transaction(Database(pg.engine), wf["a"]) as session:
        assert (
            session.execute(
                text(
                    "UPDATE public.tag_pairs SET owner_user_id=:a,ownership_status='active',activated_at=now() WHERE id=:p"
                ),
                {"a": wf["a"], "p": pid},
            ).rowcount
            == 0
        )


def test_paid_order_entitlement_and_refund_recheck(guarded):
    pg, _, commerce, _, headers, client = guarded
    with pg.connect() as c:
        place(c, commerce)
        pay(c, commerce)
        c.execute(
            text("UPDATE tag_pairs SET inventory_status='qa_passed' WHERE id=:pair"),
            commerce,
        )
        c.execute(
            text(
                "INSERT INTO pair_activation_credentials(pair_id,secret_verifier,verifier_key_version) VALUES(:pair,decode(repeat('ab',32),'hex'),1)"
            ),
            commerce,
        )
        token = c.execute(
            text(
                "SELECT public_token FROM qr_codes WHERE pair_id=:pair AND tag_type='ice'"
            ),
            commerce,
        ).scalar_one()
        c.commit()
    response = client.post(
        INTENTS, json={"scanned_token": token}, headers=headers(commerce["customer"])
    )
    assert response.status_code == 201, response.text
    assert response.json()["method"] == "order_entitlement"
    with pg.connect() as c:
        c.execute(
            text("UPDATE orders SET payment_status='refunded' WHERE id=:purchase"),
            commerce,
        )
        c.commit()
    denied_key = uuid.uuid4().hex
    result = client.post(
        ACTIVATE,
        json={"intent_id": response.json()["intent_id"], "confirm": True},
        headers={**headers(commerce["customer"]), "Idempotency-Key": denied_key},
    )
    assert result.status_code == 409, result.text
    # Restore only the synthetic order; the previous ineligible decision stays stable.
    with pg.connect() as c:
        c.execute(
            text("UPDATE orders SET payment_status='verified' WHERE id=:purchase"),
            commerce,
        )
        c.commit()
    payload = {"intent_id": response.json()["intent_id"], "confirm": True}
    assert (
        client.post(
            ACTIVATE,
            json=payload,
            headers={**headers(commerce["customer"]), "Idempotency-Key": denied_key},
        ).status_code
        == 409
    )
    activated = client.post(
        ACTIVATE,
        json=payload,
        headers={**headers(commerce["customer"]), "Idempotency-Key": uuid.uuid4().hex},
    )
    assert activated.status_code == 201, activated.text


def test_validation_never_echoes_secret_and_bounds_body(activation):
    _, wf, headers, client, _, _ = activation
    secret = "sensitive-input-must-never-echo"
    response = client.post(
        INTENTS,
        json={
            "scanned_token": "x",
            "activation_secret": secret,
            "owner_user_id": "forbidden",
        },
        headers=headers(wf["a"]),
    )
    assert response.status_code == 400
    assert secret not in response.text
    response = client.post(
        INTENTS, json={"scanned_token": "x" * 5000}, headers=headers(wf["a"])
    )
    assert response.status_code == 413


def test_outbox_failure_rolls_back_entire_activation_and_allows_retry(activation):
    pg, _, _, _, pid, _ = activation
    iid = intent(activation).json()["intent_id"]
    key = uuid.uuid4().hex
    with pg.connect() as c:
        c.execute(
            text(
                "CREATE FUNCTION public.test_activation_outbox_failure() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'injected activation outbox failure' USING ERRCODE='23514'; END $$"
            )
        )
        c.execute(
            text(
                "CREATE TRIGGER test_activation_outbox_failure BEFORE INSERT ON public.notification_outbox FOR EACH ROW WHEN (NEW.event_type='pair.activated') EXECUTE FUNCTION public.test_activation_outbox_failure()"
            )
        )
        c.commit()
    try:
        assert confirm(activation, iid, key=key).status_code == 503
        with pg.connect() as c:
            assert (
                c.execute(
                    text("SELECT owner_user_id FROM tag_pairs WHERE id=:p"), {"p": pid}
                ).scalar_one()
                is None
            )
            assert (
                c.execute(
                    text(
                        "SELECT status FROM pair_activation_credentials WHERE pair_id=:p"
                    ),
                    {"p": pid},
                ).scalar_one()
                == "unused"
            )
            assert (
                c.execute(
                    text("SELECT state FROM activation_intents WHERE id=:id"),
                    {"id": iid},
                ).scalar_one()
                == "pending"
            )
            assert (
                c.execute(
                    text(
                        "SELECT count(*) FROM audit_events WHERE target_id=:p AND action='pair.activated'"
                    ),
                    {"p": pid},
                ).scalar_one()
                == 0
            )
            assert (
                c.execute(
                    text(
                        "SELECT count(*) FROM idempotency_records WHERE idempotency_key=:key"
                    ),
                    {"key": key},
                ).scalar_one()
                == 0
            )
    finally:
        with pg.connect() as c:
            c.execute(
                text(
                    "DROP TRIGGER test_activation_outbox_failure ON public.notification_outbox"
                )
            )
            c.execute(text("DROP FUNCTION public.test_activation_outbox_failure()"))
            c.commit()
    assert confirm(activation, iid, key=key).status_code == 201


def test_unverified_and_anonymous_cannot_create_intent(activation):
    pg, wf, _, client, _, item = activation
    assert (
        client.post(
            INTENTS, json={"scanned_token": item["tags"][0]["public_token"]}
        ).status_code
        == 401
    )
    with pg.connect() as c:
        c.execute(
            text("UPDATE auth.users SET email_confirmed_at=NULL WHERE id=:id"),
            {"id": wf["a"]},
        )
        c.commit()
    assert intent(activation).status_code == 403


@pytest.mark.parametrize("recipient", ["a", "b"])
def test_live_unpaid_allocation_cannot_be_bypassed_with_secret(activation, recipient):
    pg, wf, _, _, pid, _ = activation
    with pg.connect() as c:
        oid = c.execute(
            text(
                "INSERT INTO orders(order_number,customer_user_id,subtotal_pkr,total_pkr) VALUES(:n,:a,0,0) RETURNING id"
            ),
            {"n": uuid.uuid4().hex, "a": wf[recipient]},
        ).scalar_one()
        c.execute(
            text(
                "INSERT INTO order_pair_units(order_id,pair_id,reserved_until) VALUES(:o,:p,now()+interval '1 hour')"
            ),
            {"o": oid, "p": pid},
        )
        c.commit()
    assert intent(activation).status_code == 409


def test_durable_account_and_peer_attempt_limits(activation):
    pg, wf, _, _, _, _ = activation
    with api_transaction(Database(pg.engine), wf["a"]) as session:
        session.execute(
            text(
                "DO $$ BEGIN FOR n IN 1..20 LOOP PERFORM public.sr_begin_activation('unknown',NULL,NULL); END LOOP; END $$"
            )
        )
    assert intent(activation).status_code == 429
    # Independent synthetic peer binding: never spend the test client's own bucket.
    with api_transaction(Database(pg.engine)) as session:
        session.execute(
            text(
                "DO $$ BEGIN FOR n IN 1..100 LOOP PERFORM public.sr_activation_rate(repeat('b',64)); END LOOP; END $$"
            )
        )
    with api_transaction(Database(pg.engine)) as session:
        assert (
            session.execute(
                text("SELECT public.sr_activation_rate(repeat('b',64))")
            ).scalar_one()
            is False
        )


@pytest.mark.parametrize("configuration", ["missing", "historical"])
def test_missing_or_historical_verifier_key_fails_without_guess_penalty(
    activation, configuration
):
    from app.core.config import Settings

    pg, _, _, client, pid, _ = activation
    settings = client.application.state.settings
    client.application.state.settings = (
        Settings(activation_verifier_key=None)
        if configuration == "missing"
        else settings.model_copy(
            update={
                "activation_verifier_key_version": settings.activation_verifier_key_version
                + 1
            }
        )
    )
    assert intent(activation).status_code == 503
    with pg.connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT failed_attempts FROM pair_activation_credentials WHERE pair_id=:p"
                ),
                {"p": pid},
            ).scalar_one()
            == 0
        )
