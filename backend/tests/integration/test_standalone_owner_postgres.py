"""Opt-in Phase 7 ownership races on a separately approved disposable target."""

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_typed_print_fulfillment_postgres import print_fixture
from test_verified_qr_allocation_postgres import (  # noqa: F401
    actor,
    make_order,
    pg_case,
    settle,
    stock,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("SAFERETURN_STANDALONE_OWNER_REHEARSAL") != "1",
    reason="Explicit isolated PostgreSQL owner rehearsal authorization required",
)


@pytest.fixture
def owner_case(pg_case):  # noqa: F811
    sid = uuid4()
    with pg_case[0].connect() as c:
        pg_case[0].upgrade(c, "0043_standalone_activation")
        assert (
            c.execute(text("SELECT public.sr_standalone_owner_enabled()")).scalar_one()
            is False
        )
        c.execute(
            text("UPDATE public.standalone_owner_release SET enabled=true")
        )  # Only the disposable fixture.
        c.execute(
            text(
                "INSERT INTO auth.sessions(id,user_id,aal,not_after) VALUES(:id,:uid,'aal1',now()+interval '1 hour')"
            ),
            {"id": sid, "uid": pg_case[2]},
        )
        c.commit()
    return pg_case, sid


def delivered(case, kinds=("lost",)):
    order = make_order(case, kinds=kinds)
    for kind in set(kinds):
        stock(case, kind=kind, quantity=kinds.count(kind))
    assert settle(case, order)["allocation"]["state"] == "allocated"
    jid, ids = print_fixture(case, order)
    sid = uuid4()
    with case[0].connect() as c:
        actor(c, case[1])
        c.execute(
            text(
                "INSERT INTO public.shipments(id,order_id,shipping_address_id,carrier) SELECT :sid,order_id,source_address_id,'Synthetic' FROM public.order_shipping_snapshots WHERE order_id=:oid"
            ),
            {"sid": sid, "oid": order[0]},
        )
        for iid in ids:
            c.execute(
                text(
                    "INSERT INTO public.shipment_items(shipment_id,logical_item_id,print_job_id,packed_qa_confirmed,packed_by,packed_at) VALUES(:sid,:iid,:jid,true,:uid,now())"
                ),
                {"sid": sid, "iid": iid, "jid": jid, "uid": case[1]},
            )
        for state, stamp in (
            ("packed", "packed_at"),
            ("dispatched", "dispatched_at"),
            ("delivered", "delivered_at"),
        ):
            c.execute(
                text(
                    f"UPDATE public.shipments SET status=:state,{stamp}=now(),tracking_reference='SYNTHETIC' WHERE id=:id"
                ),
                {"state": state, "id": sid},
            )
            c.execute(
                text("UPDATE public.orders SET fulfillment_status=:state WHERE id=:id"),
                {"state": state, "id": order[0]},
            )
        c.commit()
    return order, ids


def begin(owner_case, iid):
    case, sid = owner_case
    with case[0].connect() as c:
        actor(c, case[2])
        c.execute(text("SET LOCAL ROLE safereturn_api"))
        result = c.execute(
            text("SELECT public.sr_standalone_begin(:sid,:iid)"),
            {"sid": sid, "iid": iid},
        ).scalar_one()
        c.commit()
        return result


def confirm(owner_case, intent, key=None, barrier=None):
    case, sid = owner_case
    with case[0].connect() as c:
        actor(c, case[2])
        c.execute(text("SET LOCAL ROLE safereturn_api"))
        if barrier:
            barrier.wait(timeout=20)
        result = c.execute(
            text("SELECT public.sr_standalone_confirm(:sid,:intent,:kh,:rh)"),
            {
                "sid": sid,
                "intent": intent,
                "kh": hashlib.sha256((key or uuid4().hex).encode()).hexdigest(),
                "rh": hashlib.sha256(str(intent).encode()).hexdigest(),
            },
        ).scalar_one()
        c.commit()
        return result


def test_paid_allocation_without_delivery_cannot_begin(owner_case):
    case, _ = owner_case
    order = make_order(case)
    stock(case)
    settle(case, order)
    with case[0].connect() as c:
        iid = c.execute(
            text("SELECT id FROM public.order_logical_items WHERE order_id=:id"),
            {"id": order[0]},
        ).scalar_one()
    assert begin(owner_case, iid)["error"] == "NOT_ELIGIBLE"


def test_independent_types_do_not_activate_siblings_and_defaults_are_private(
    owner_case,
):
    case, _ = owner_case
    _, ids = delivered(case, ("lost", "ice"))
    intent = begin(owner_case, ids[0])
    result = confirm(owner_case, intent["intent_id"], "synthetic-key")
    assert result["status"] == "active"
    assert confirm(owner_case, intent["intent_id"], "synthetic-key") == result
    with case[0].connect() as c:
        rows = (
            c.execute(
                text(
                    "SELECT s.ownership_status FROM public.standalone_qr_states s JOIN public.order_item_qr_allocations a ON a.qr_id=s.qr_id WHERE a.logical_item_id IN (:a,:b) ORDER BY s.ownership_status"
                ),
                {"a": ids[0], "b": ids[1]},
            )
            .scalars()
            .all()
        )
        assert rows == ["active", "unclaimed"]
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.standalone_owner_events WHERE event_type='activated'"
                )
            ).scalar_one()
            == 1
        )
        assert (
            c.execute(
                text(
                    "SELECT coalesce(l.published,i.published) FROM public.qr_codes q LEFT JOIN public.lost_item_profiles l ON l.qr_id=q.id LEFT JOIN public.ice_profiles i ON i.qr_id=q.id WHERE q.id=:id"
                ),
                {"id": result["qr_id"]},
            ).scalar_one()
            is False
        )


def test_two_intents_race_once_and_recheck_changed_fulfillment(owner_case):
    case, _ = owner_case
    _order, ids = delivered(case)
    first, second = begin(owner_case, ids[0]), begin(owner_case, ids[0])
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda i: confirm(owner_case, i["intent_id"], barrier=barrier),
                (first, second),
            )
        )
    assert sum(r.get("status") == "active" for r in results) == 1
    # A separately delivered identity cannot activate after fulfillment is held.
    other, other_ids = delivered(case)
    intent = begin(owner_case, other_ids[0])
    with case[0].connect() as c:
        c.execute(
            text(
                "UPDATE public.orders SET fulfillment_status='exception' WHERE id=:id"
            ),
            {"id": other[0]},
        )
        c.commit()
    assert confirm(owner_case, intent["intent_id"])["error"] == "NOT_ELIGIBLE"


def test_runtime_cannot_write_owner_or_read_intents(owner_case):
    case, _ = owner_case
    with case[0].connect() as c:
        actor(c, case[2])
        c.execute(text("SET LOCAL ROLE safereturn_api"))
        with pytest.raises(DBAPIError):
            c.execute(text("SELECT * FROM public.standalone_activation_intents"))


def test_other_account_cannot_begin_or_consume_purchaser_intent(owner_case):
    case, _ = owner_case
    _, ids = delivered(case)
    intent = begin(owner_case, ids[0])
    with case[0].connect() as c:
        actor(
            c, case[1]
        )  # A real different staff account still has no purchaser entitlement.
        c.execute(text("SET LOCAL ROLE safereturn_api"))
        assert (
            c.execute(
                text("SELECT public.sr_standalone_begin(:sid,:iid)"),
                {"sid": case[3], "iid": ids[0]},
            ).scalar_one()
            is None
        )
        assert (
            c.execute(
                text("SELECT public.sr_standalone_confirm(:sid,:iid,:kh,:rh)"),
                {
                    "sid": case[3],
                    "iid": intent["intent_id"],
                    "kh": "a" * 64,
                    "rh": "b" * 64,
                },
            ).scalar_one()
            is None
        )


@pytest.mark.parametrize("table", ["standalone_owner_receipts", "audit_events"])
def test_activation_rolls_back_if_receipt_or_audit_fails(owner_case, table):
    case, _ = owner_case
    _, ids = delivered(case)
    intent = begin(owner_case, ids[0])
    with case[0].connect() as c:
        c.execute(
            text(
                "CREATE FUNCTION public.sr_owner_fixture_failure() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'SYNTHETIC owner transaction failure'; END $$"
            )
        )
        c.execute(
            text(
                f"CREATE TRIGGER sr_owner_fixture_failure BEFORE INSERT ON public.{table} FOR EACH ROW EXECUTE FUNCTION public.sr_owner_fixture_failure()"
            )
        )
        c.commit()
    with pytest.raises(DBAPIError):
        confirm(owner_case, intent["intent_id"])
    with case[0].connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT ownership_status FROM public.standalone_qr_states WHERE qr_id=:id"
                ),
                {"id": intent["qr_id"]},
            ).scalar_one()
            == "unclaimed"
        )
        assert (
            c.execute(
                text(
                    "SELECT consumed_at FROM public.standalone_activation_intents WHERE id=:id"
                ),
                {"id": intent["intent_id"]},
            ).scalar_one()
            is None
        )
        assert (
            c.execute(
                text("SELECT count(*) FROM public.standalone_owner_events")
            ).scalar_one()
            == 0
        )


def test_expired_intent_and_restricted_account_fail_closed(owner_case):
    case, _sid = owner_case
    _, ids = delivered(case)
    intent = begin(owner_case, ids[0])
    with case[0].connect() as c:
        c.execute(
            text(
                "UPDATE public.standalone_activation_intents SET created_at=now()-interval '10 minutes',expires_at=now()-interval '5 minutes' WHERE id=:id"
            ),
            {"id": intent["intent_id"]},
        )
        c.commit()
    assert confirm(owner_case, intent["intent_id"])["error"] == "NOT_ELIGIBLE"
    second = begin(owner_case, ids[0])
    with case[0].connect() as c:
        c.execute(
            text(
                "UPDATE auth.users SET banned_until=now()+interval '1 hour' WHERE id=:id"
            ),
            {"id": case[2]},
        )
        c.commit()
    assert confirm(owner_case, second["intent_id"]) is None


def test_public_projection_hides_restricted_owner_without_rewriting_url(owner_case):
    case, _ = owner_case
    _, ids = delivered(case)
    intent = begin(owner_case, ids[0])
    confirm(owner_case, intent["intent_id"])
    with case[0].connect() as c:
        token = c.execute(
            text("SELECT public_token FROM public.qr_codes WHERE id=:id"),
            {"id": intent["qr_id"]},
        ).scalar_one()
        c.execute(
            text(
                "UPDATE public.lost_item_profiles SET item_label='SYNTHETIC OWN LABEL',published=true,profile_version=profile_version+1 WHERE qr_id=:id"
            ),
            {"id": intent["qr_id"]},
        )
        c.commit()
        result = c.execute(
            text("SELECT public.sr_public_qr_projection(:token)"), {"token": token}
        ).scalar_one()
        assert result["lost_item"]["label"] == "SYNTHETIC OWN LABEL"
        c.commit()
        c.execute(
            text(
                "UPDATE auth.users SET banned_until=now()+interval '1 hour' WHERE id=:id"
            ),
            {"id": case[2]},
        )
        c.commit()
        result = c.execute(
            text("SELECT public.sr_public_qr_projection(:token)"), {"token": token}
        ).scalar_one()
        assert result["status"] == "admin_suspended" and "lost_item" not in result
