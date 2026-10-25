"""Opt-in real PostgreSQL generation races in UUID-isolated rehearsal namespaces.

Not run automatically: the owner must identify a disposable rehearsal target and
explicitly enable SAFERETURN_TYPED_INVENTORY_REHEARSAL=1. The shared harness checks
the installed baseline before setup and preserves it after cleanup. No production
schema is upgraded. Current default baseline is the historical 0021 handoff.
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from pg_rehearsal import rehearsal
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.inventory_secrets import new_public_token

pytestmark = pytest.mark.skipif(
    os.environ.get("SAFERETURN_TYPED_INVENTORY_REHEARSAL") != "1",
    reason="Explicit isolated PostgreSQL rehearsal authorization is required",
)


@pytest.fixture(scope="module")
def typed_pg():
    with rehearsal(
        expected_revision=os.environ.get(
            "SAFERETURN_TYPED_BASE_REVISION", "0021_support_case_console"
        )
    ) as pg:
        actor, sid, legacy_batch, legacy_pair = (uuid4() for _ in range(4))
        with pg.connect() as c:
            pg.upgrade(c, "0037_independent_qr_foundation")
            c.execute(
                text("INSERT INTO auth.users(id,email_confirmed_at) VALUES(:id,now())"),
                {"id": actor},
            )
            c.execute(
                text(
                    "INSERT INTO auth.sessions(id,user_id,aal,not_after) VALUES(:id,:uid,'aal2',now()+interval '1 hour')"
                ),
                {"id": sid, "uid": actor},
            )
            c.execute(
                text(
                    "INSERT INTO public.staff_roles(user_id,role) VALUES(:id,'operations')"
                ),
                {"id": actor},
            )
            c.execute(
                text(
                    "INSERT INTO public.qr_batches(id,batch_code,ecc_level) VALUES(:id,:code,'Q')"
                ),
                {"id": legacy_batch, "code": "LEGACY-" + uuid4().hex},
            )
            c.execute(
                text(
                    "INSERT INTO public.tag_pairs(id,pair_reference,batch_id) VALUES(:id,:ref,:batch)"
                ),
                {
                    "id": legacy_pair,
                    "ref": "PAIR-" + uuid4().hex,
                    "batch": legacy_batch,
                },
            )
            for kind in ("lost", "ice"):
                c.execute(
                    text(
                        "INSERT INTO public.qr_codes(pair_id,tag_type,serial_number,public_token,ecc_level) VALUES(:pair,:kind,:serial,:token,'Q')"
                    ),
                    {
                        "pair": legacy_pair,
                        "kind": kind,
                        "serial": uuid4().hex,
                        "token": new_public_token(),
                    },
                )
            c.commit()
            before = c.execute(
                text(
                    "SELECT id,public_token,tag_type FROM public.qr_codes WHERE pair_id=:id ORDER BY tag_type"
                ),
                {"id": legacy_pair},
            ).all()
            pg.upgrade(c, "0038_typed_inventory")
            c.commit()
            assert (
                c.execute(
                    text(
                        "SELECT id,public_token,tag_type FROM public.qr_codes WHERE pair_id=:id ORDER BY tag_type"
                    ),
                    {"id": legacy_pair},
                ).all()
                == before
            )
        yield pg, actor, sid, legacy_pair, before


def admit(c, actor):
    c.execute(text("SET LOCAL ROLE safereturn_api"))
    c.execute(
        text(
            "SELECT set_config('safereturn.actor_id',:actor,true),set_config('safereturn.mfa_verified','true',true)"
        ),
        {"actor": str(actor)},
    )


def generate(pg, actor, sid, label, key, kind="lost", quantity=3, barrier=None):
    with pg.connect() as c:
        admit(c, actor)
        if barrier:
            barrier.wait(timeout=15)
        result = c.execute(
            text(
                "SELECT public.sr_typed_inventory_generate(:sid,:label,:kind,:quantity,'Q',:key,CAST(:tokens AS jsonb))"
            ),
            {
                "sid": sid,
                "label": label,
                "kind": kind,
                "quantity": quantity,
                "key": key,
                "tokens": json.dumps([new_public_token() for _ in range(quantity)]),
            },
        ).scalar_one()
        c.commit()  # Exercises deferred state/quantity checks, not just statements.
        return result


def test_concurrent_same_key_has_one_batch_and_one_audit(typed_pg):
    pg, actor, sid, _, _ = typed_pg
    label, key = "RACE-" + uuid4().hex, uuid4().hex
    barrier = Barrier(2)
    with ThreadPoolExecutor(2) as pool:
        results = list(
            pool.map(
                lambda _: generate(pg, actor, sid, label, key, barrier=barrier),
                range(2),
            )
        )
    assert results[0] == results[1]
    bid = results[0]["batch_id"]
    with pg.connect() as c:
        assert c.execute(
            text(
                "SELECT count(*),count(DISTINCT public_token) FROM public.qr_codes WHERE batch_id=:id"
            ),
            {"id": bid},
        ).one() == (3, 3)
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.audit_events WHERE action='inventory.typed_batch.generated' AND target_id=:id"
                ),
                {"id": bid},
            ).scalar_one()
            == 1
        )
        assert (
            c.execute(
                text("SELECT count(*) FROM public.tag_pairs WHERE batch_id=:id"),
                {"id": bid},
            ).scalar_one()
            == 0
        )


def test_label_race_and_changed_body_do_not_mint_extra_stock(typed_pg):
    pg, actor, sid, _, _ = typed_pg
    label = "LABEL-" + uuid4().hex
    keys = [uuid4().hex, uuid4().hex]
    barrier = Barrier(2)
    with ThreadPoolExecutor(2) as pool:
        results = list(
            pool.map(
                lambda key: generate(pg, actor, sid, label, key, barrier=barrier), keys
            )
        )
    assert sum("batch_id" in result for result in results) == 1
    assert [r["error"] for r in results if "error" in r] == ["BATCH_LABEL_CONFLICT"]
    winner = next(i for i, result in enumerate(results) if "batch_id" in result)
    assert generate(pg, actor, sid, label, keys[winner], quantity=4) == {
        "error": "IDEMPOTENCY_KEY_REUSED"
    }


def test_cross_type_filters_no_tokens_and_no_legacy_rows(typed_pg):
    pg, actor, sid, _, legacy = typed_pg
    result = generate(
        pg, actor, sid, "ICE-" + uuid4().hex, uuid4().hex, kind="ice", quantity=2
    )
    with pg.connect() as c:
        tokens = (
            c.execute(
                text("SELECT public_token FROM public.qr_codes WHERE batch_id=:id"),
                {"id": result["batch_id"]},
            )
            .scalars()
            .all()
        )
        admit(c, actor)
        value = c.execute(
            text(
                "SELECT public.sr_typed_inventory_read(:sid,'codes',CAST(:filters AS jsonb))"
            ),
            {
                "sid": sid,
                "filters": json.dumps(
                    {"qr_type": "ice", "batch_id": result["batch_id"]}
                ),
            },
        ).scalar_one()
        assert len(value["items"]) == 2 and all(
            row["qr_type"] == "ice" for row in value["items"]
        )
        assert all(token not in json.dumps(value) for token in tokens)
        assert not {row["qr_id"] for row in value["items"]} & {
            str(row[0]) for row in legacy
        }
        hidden = c.execute(
            text("SELECT public.sr_public_qr_projection(:token)"), {"token": tokens[0]}
        ).scalar_one()
        assert hidden is None
        wrong_type = c.execute(
            text(
                "SELECT public.sr_typed_inventory_read(:sid,'codes',CAST(:filters AS jsonb))"
            ),
            {
                "sid": sid,
                "filters": json.dumps(
                    {"qr_type": "lost", "batch_id": result["batch_id"]}
                ),
            },
        ).scalar_one()
        assert wrong_type["items"] == []


def test_api_has_no_direct_state_or_receipt_write_grants(typed_pg):
    pg, actor, _, _, _ = typed_pg
    for table in ("standalone_qr_states", "typed_inventory_receipts"):
        with pg.connect() as c:
            admit(c, actor)
            with pytest.raises(DBAPIError):
                c.execute(text(f"SELECT * FROM public.{table}"))
            c.rollback()


def test_audit_failure_rolls_back_batch_codes_state_and_receipt(typed_pg):
    pg, actor, sid, _, _ = typed_pg
    label, key = "ROLLBACK-" + uuid4().hex[:24], uuid4().hex
    with pg.connect() as c:
        c.execute(
            text("""CREATE FUNCTION public.sr_typed_test_audit_failure() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN IF NEW.action='inventory.typed_batch.generated' THEN RAISE EXCEPTION 'synthetic audit failure'; END IF; RETURN NEW; END $$""")
        )
        c.execute(
            text(
                "CREATE TRIGGER sr_typed_test_audit_failure BEFORE INSERT ON public.audit_events FOR EACH ROW EXECUTE FUNCTION public.sr_typed_test_audit_failure()"
            )
        )
        c.commit()
    try:
        with pytest.raises(DBAPIError):
            generate(pg, actor, sid, label, key)
        with pg.connect() as c:
            assert (
                c.execute(
                    text(
                        "SELECT count(*) FROM public.qr_batches WHERE batch_code=:label"
                    ),
                    {"label": label},
                ).scalar_one()
                == 0
            )
            assert (
                c.execute(
                    text(
                        "SELECT count(*) FROM public.typed_inventory_receipts WHERE actor_user_id=:actor AND idempotency_key=:key"
                    ),
                    {"actor": actor, "key": key},
                ).scalar_one()
                == 0
            )
    finally:
        with pg.connect() as c:
            c.execute(
                text("DROP TRIGGER sr_typed_test_audit_failure ON public.audit_events")
            )
            c.execute(text("DROP FUNCTION public.sr_typed_test_audit_failure()"))
            c.commit()
    assert generate(pg, actor, sid, label, key)["generated_quantity"] == 3


@pytest.mark.parametrize("role", ["finance", "support", "security_admin", "superadmin"])
def test_other_roles_do_not_inherit_operations_authority(typed_pg, role):
    pg, _, _, _, _ = typed_pg
    actor, sid = uuid4(), uuid4()
    with pg.connect() as c:
        c.execute(
            text("INSERT INTO auth.users(id,email_confirmed_at) VALUES(:id,now())"),
            {"id": actor},
        )
        c.execute(
            text(
                "INSERT INTO auth.sessions(id,user_id,aal,not_after) VALUES(:id,:actor,'aal2',now()+interval '1 hour')"
            ),
            {"id": sid, "actor": actor},
        )
        c.execute(
            text("INSERT INTO public.staff_roles(user_id,role) VALUES(:actor,:role)"),
            {"actor": actor, "role": role},
        )
        c.commit()
    assert generate(pg, actor, sid, "DENIED-" + uuid4().hex, uuid4().hex) == {
        "error": "FORBIDDEN"
    }


def test_live_session_and_mfa_rechecked_in_database(typed_pg):
    pg, actor, sid, _, _ = typed_pg
    with pg.connect() as c:
        admit(c, actor)
        c.execute(text("SELECT set_config('safereturn.mfa_verified','false',true)"))
        assert c.execute(
            text("SELECT public.sr_typed_inventory_read(:sid,'summary','{}'::jsonb)"),
            {"sid": sid},
        ).scalar_one() == {"error": "FORBIDDEN"}
        c.rollback()
    assert generate(pg, actor, uuid4(), "DENIED-" + uuid4().hex, uuid4().hex) == {
        "error": "FORBIDDEN"
    }


def test_incomplete_batch_fails_at_commit_and_preserves_legacy_tokens(typed_pg):
    pg, _, _, pair, before = typed_pg
    bid = uuid4()
    with pg.connect() as c:
        c.execute(
            text(
                "INSERT INTO public.qr_batches(id,batch_code,ecc_level,status,generation_mode,qr_type,requested_quantity) VALUES(:id,:label,'Q','generated','standalone','lost',2)"
            ),
            {"id": bid, "label": "INCOMPLETE-" + uuid4().hex[:25]},
        )
        qid = uuid4()
        c.execute(
            text(
                "INSERT INTO public.qr_codes(id,batch_id,tag_type,serial_number,public_token,ecc_level) VALUES(:id,:bid,'lost',:serial,:token,'Q')"
            ),
            {"id": qid, "bid": bid, "serial": uuid4().hex, "token": new_public_token()},
        )
        c.execute(
            text("INSERT INTO public.standalone_qr_states(qr_id) VALUES(:id)"),
            {"id": qid},
        )
        with pytest.raises(DBAPIError):
            c.commit()
        c.rollback()
        assert (
            c.execute(
                text("SELECT count(*) FROM public.qr_batches WHERE id=:id"), {"id": bid}
            ).scalar_one()
            == 0
        )
        assert (
            c.execute(
                text(
                    "SELECT id,public_token,tag_type FROM public.qr_codes WHERE pair_id=:id ORDER BY tag_type"
                ),
                {"id": pair},
            ).all()
            == before
        )
