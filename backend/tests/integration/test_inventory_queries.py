"""Task 3.5A: bounded operations metadata on existing UUID-isolated fixtures."""

import json
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from test_auth_guards import change
from test_commerce_schema import pay, place
from test_inventory_generation import batch_request, inventory_context

pytest_plugins = ["test_auth_guards"]
BASE = "/api/v1/admin"


@pytest.fixture(scope="module")
def sample(guarded):
    pg, wf, commerce, sessions, headers, client = guarded
    inventory_context.__wrapped__(guarded)
    payload = {**batch_request(), "pair_count": 8}
    response = client.post(
        BASE + "/qr-batches",
        json=payload,
        headers={
            **headers(wf["operations"]),
            "Idempotency-Key": "inventory-read-" + uuid4().hex,
        },
    )
    assert response.status_code == 201
    bid = UUID(response.json()["batch_id"])
    empty = uuid4()
    with pg.connect() as c:
        pids = list(
            c.execute(
                text(
                    "SELECT id FROM public.tag_pairs WHERE batch_id=:id ORDER BY pair_reference"
                ),
                {"id": bid},
            ).scalars()
        )
        c.execute(
            text(
                "UPDATE public.tag_pairs SET inventory_status='qa_passed',created_at='2026-01-01T00:00:00Z' WHERE batch_id=:id"
            ),
            {"id": bid},
        )
        c.execute(
            text(
                "UPDATE public.tag_pairs SET inventory_status='generated' WHERE id=:id"
            ),
            {"id": pids[2]},
        )
        c.execute(
            text(
                "UPDATE public.qr_codes SET public_status='admin_suspended' WHERE pair_id=:id AND tag_type='lost'"
            ),
            {"id": pids[1]},
        )
        c.execute(
            text(
                "UPDATE public.pair_activation_credentials SET status='locked' WHERE pair_id=:id"
            ),
            {"id": pids[3]},
        )
        c.execute(
            text(
                "UPDATE public.tag_pairs SET owner_user_id=:owner,ownership_status='active',activated_at=now() WHERE id=:id"
            ),
            {"id": pids[6], "owner": wf["a"]},
        )
        order = c.execute(
            text(
                "INSERT INTO public.orders(order_number,customer_user_id,subtotal_pkr,total_pkr) VALUES(:ref,:uid,1,1) RETURNING id"
            ),
            {"ref": "read-" + uuid4().hex, "uid": wf["a"]},
        ).scalar_one()
        c.execute(
            text(
                "INSERT INTO public.order_pair_units(order_id,pair_id,reserved_until) VALUES(:order,:pair,now()-interval '1 day')"
            ),
            {"order": order, "pair": pids[4]},
        )
        for round_number, approved in [(1, False), (2, True)]:
            c.execute(
                text("""INSERT INTO public.pair_print_qa(pair_id,qa_round,lost_scan_passed,ice_scan_passed,pair_match_passed,credential_concealed,bilingual_label_passed,quiet_zone_passed,indoor_size_passed,outdoor_size_passed,packaging_method,tamper_evidence_passed,approved,inspected_by,notes)
            VALUES(:pair,:round,true,true,true,true,true,true,true,true,'sealed_sleeve',true,:approved,:uid,'PRIVATE-QA-CANARY')"""),
                {
                    "pair": pids[0],
                    "round": round_number,
                    "approved": approved,
                    "uid": wf["operations"],
                },
            )
        for _ in range(2):
            old = c.execute(
                text(
                    "SELECT id FROM public.qr_codes WHERE pair_id=:id AND tag_type='lost' AND is_current"
                ),
                {"id": pids[7]},
            ).scalar_one()
            c.execute(
                text(
                    "UPDATE public.qr_codes SET is_current=false,public_status='revoked',revoked_at=now() WHERE id=:id"
                ),
                {"id": old},
            )
            c.execute(
                text("""INSERT INTO public.qr_codes(pair_id,tag_type,serial_number,public_token,ecc_level,replaces_qr_id)
              VALUES(:pair,'lost',:serial,:token,'Q',:old)"""),
                {
                    "pair": pids[7],
                    "serial": "replacement-" + uuid4().hex,
                    "token": "opaque-" + uuid4().hex,
                    "old": old,
                },
            )
        c.execute(
            text(
                "INSERT INTO public.qr_batches(id,batch_code,ecc_level,created_at) SELECT :id,:label,'Q',created_at FROM public.qr_batches WHERE id=:batch"
            ),
            {"id": empty, "label": "empty-" + uuid4().hex, "batch": bid},
        )
        c.execute(
            text(
                "INSERT INTO public.staff_roles(user_id,role,reason) VALUES(:id,'superadmin','synthetic read denial')"
            ),
            {"id": wf["b"]},
        )
        c.commit()
    return pg, wf, commerce, sessions, headers, client, bid, pids, empty


def get(sample, path, **params):
    _, wf, _, _, headers, client, *_ = sample
    response = client.get(BASE + path, headers=headers(wf["operations"]), params=params)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    return response.json()


def snapshot(pg):
    with pg.connect() as c:
        return tuple(
            c.execute(
                text(
                    f"SELECT md5(COALESCE(string_agg(row_to_json(t)::text,'' ORDER BY row_to_json(t)::text),'')) FROM public.{table} t"
                )
            ).scalar_one()
            for table in [
                "qr_batches",
                "tag_pairs",
                "qr_codes",
                "pair_activation_credentials",
                "pair_print_qa",
                "order_pair_units",
                "audit_events",
            ]
        )


def test_lists_detail_projection_and_tied_pagination_are_read_only(sample):
    pg, _, _, _, _, _, bid, pids, empty = sample
    before = snapshot(pg)
    seen = []
    cursor = None
    while True:
        data = get(
            sample,
            "/tag-pairs",
            batch_id=str(bid),
            limit=3,
            **({"cursor": cursor} if cursor else {}),
        )
        seen += [r["pair_id"] for r in data["items"]]
        cursor = data["next_cursor"]
        if not cursor:
            break
    assert seen == [str(p) for p in sorted(pids, reverse=True)]
    assert len(seen) == len(set(seen)) == 8
    detail = get(sample, f"/tag-pairs/{pids[0]}")
    assert len(detail["current_tags"]) == 2
    assert (
        detail["latest_qa"]["qa_round"] == 2 and detail["latest_qa"]["approved"] is True
    )
    assert "owner_user_id" not in detail
    replacement = get(sample, f"/tag-pairs/{pids[7]}", history_limit=1)
    assert len(replacement["historical_tags"]["items"]) == 1
    second = get(
        sample,
        f"/tag-pairs/{pids[7]}",
        history_limit=1,
        history_cursor=replacement["historical_tags"]["next_cursor"],
    )
    assert second["historical_tags"]["next_cursor"] is None
    assert (
        second["historical_tags"]["items"][0]["qr_id"]
        != replacement["historical_tags"]["items"][0]["qr_id"]
    )
    batch = get(sample, f"/qr-batches/{bid}")
    assert (
        batch["pair_count"],
        batch["current_tag_count"],
        batch["historical_tag_count"],
        batch["qa_passed_pair_count"],
    ) == (8, 16, 2, 7)
    assert get(sample, f"/qr-batches/{empty}")["pair_count"] == 0
    reference = detail["pair_reference"]
    assert len(get(sample, "/tag-pairs", pair_reference=reference)["items"]) == 1
    assert get(sample, "/tag-pairs", pair_reference="' OR 1=1 --")["items"] == []
    batches = []
    cursor = None
    while True:
        result = get(
            sample, "/qr-batches", limit=2, **({"cursor": cursor} if cursor else {})
        )
        batches.extend(row["batch_id"] for row in result["items"])
        cursor = result["next_cursor"]
        if not cursor:
            break
    assert (
        len(batches) == len(set(batches))
        and str(bid) in batches
        and str(empty) in batches
    )
    assert (
        len(get(sample, "/qr-batches", batch_label=batch["batch_label"])["items"]) == 1
    )
    with pg.connect() as c:
        tokens = list(
            c.execute(text("SELECT public_token FROM public.qr_codes")).scalars()
        )
    serialized = json.dumps(
        [detail, replacement, second, batch, get(sample, "/inventory/summary")]
    )
    for field in [
        "secret_verifier",
        "sealed_insert",
        "print_manifest_checksum",
        "public_token",
        "medical",
        "PRIVATE-QA-CANARY",
        "ciphertext",
        "owner_user_id",
    ]:
        assert field not in serialized
    assert not any(token in serialized for token in tokens)
    assert snapshot(pg) == before


def test_summary_matches_checkout_and_holds_survive_elapsed_timers(sample):
    pg, wf, commerce, _, _, client, _bid, pids, _ = sample
    data = get(sample, "/inventory/summary")
    assert data["available_pairs"] == 3
    assert data["low_stock_threshold"] is None and data["low_stock"] is None
    assert (
        get(sample, f"/tag-pairs/{pids[4]}")["live_allocation"]["status"] == "reserved"
    )
    with pg.connect() as c:
        c.execute(
            text("SELECT set_config('safereturn.actor_id',:uid,true)"),
            {"uid": str(wf["operations"])},
        )
        assert c.execute(text("SELECT public.sr_checkout_capacity()")).scalar_one() == 3
        expected = c.execute(
            text(
                "SELECT count(*),count(*) FILTER(WHERE ownership_status='active') FROM public.tag_pairs"
            )
        ).one()
        assert (data["pair_count"], data["active_pairs"]) == tuple(expected)
        # Existing settlement helper acts only on the fixture purchase and allocates
        # its existing unit. It does not initiate any provider payment.
        place(c, commerce)
        pay(c, commerce)
        c.commit()
    updated = get(sample, "/inventory/summary")
    assert updated["allocated_pairs"] == data["allocated_pairs"] + 1
    assert updated["reserved_pairs"] == data["reserved_pairs"] - 1
    assert updated["available_pairs"] == 3
    settings = client.application.state.settings
    try:
        settings.inventory_low_stock_threshold = 4
        assert get(sample, "/inventory/summary")["low_stock"] is True
        settings.inventory_low_stock_threshold = 3
        assert get(sample, "/inventory/summary")["low_stock"] is False
        with pg.connect() as c:
            c.execute(
                text(
                    "UPDATE public.pair_activation_credentials SET status='locked' WHERE pair_id=ANY(:ids)"
                ),
                {"ids": [pids[0], pids[5], pids[7]]},
            )
            c.commit()
        assert get(sample, "/inventory/summary")["available_pairs"] == 0
    finally:
        settings.inventory_low_stock_threshold = None
        with pg.connect() as c:
            c.execute(
                text(
                    "UPDATE public.pair_activation_credentials SET status='unused' WHERE pair_id=ANY(:ids)"
                ),
                {"ids": [pids[0], pids[5], pids[7]]},
            )
            c.commit()


def test_every_read_requires_explicit_operations_and_genuine_mfa(sample):
    pg, wf, _, sessions, headers, client, bid, pids, _ = sample
    paths = [
        "/tag-pairs",
        f"/tag-pairs/{pids[0]}",
        "/qr-batches",
        f"/qr-batches/{bid}",
        "/inventory/summary",
    ]
    for path in paths:
        assert client.get(BASE + path).status_code == 401
        for role in ["a", "b", "finance", "support", "security_admin"]:
            assert client.get(BASE + path, headers=headers(wf[role])).status_code == 403
        assert (
            client.get(
                BASE + path, headers=headers(wf["operations"], aal="aal1")
            ).status_code
            == 403
        )
    with change(pg, "auth.sessions", sessions[wf["operations"]], {"aal": "aal1"}):
        assert (
            client.get(
                BASE + "/inventory/summary", headers=headers(wf["operations"])
            ).status_code
            == 403
        )
    with pg.connect() as c:
        role_id = c.execute(
            text(
                "SELECT id FROM public.staff_roles WHERE user_id=:id AND role='operations'"
            ),
            {"id": wf["operations"]},
        ).scalar_one()
    from datetime import UTC, datetime

    with change(pg, "staff_roles", role_id, {"revoked_at": datetime.now(UTC)}):
        assert (
            client.get(
                BASE + "/inventory/summary", headers=headers(wf["operations"])
            ).status_code
            == 403
        )
    with change(
        pg,
        "auth.sessions",
        sessions[wf["operations"]],
        {"not_after": datetime(2020, 1, 1, tzinfo=UTC)},
    ):
        assert (
            client.get(
                BASE + "/inventory/summary", headers=headers(wf["operations"])
            ).status_code
            == 401
        )


def test_bad_bounds_filters_cursor_and_missing_detail_are_safe(sample):
    _, wf, _, _, headers, client, _bid, pids, _ = sample
    for path in [
        "/tag-pairs?limit=0",
        "/qr-batches?limit=101",
        "/tag-pairs?cursor=not-a-cursor",
        "/qr-batches?cursor=%5B%5D",
        "/tag-pairs?ownership_status=bogus",
        f"/tag-pairs/{pids[0]}?history_limit=101",
        f"/tag-pairs/{pids[0]}?history_cursor=broken",
        "/qr-batches?batch_label=" + ("x" * 41),
    ]:
        r = client.get(BASE + path, headers=headers(wf["operations"]))
        assert r.status_code == 422
        assert "no-store" in r.headers["cache-control"]
    for path in [f"/tag-pairs/{uuid4()}", f"/qr-batches/{uuid4()}"]:
        assert (
            client.get(BASE + path, headers=headers(wf["operations"])).status_code
            == 404
        )


def test_generation_and_reads_are_atomic_and_query_plans_are_inspected(sample):
    pg, wf, _, _, headers, client, _, _, _ = sample
    payload = {**batch_request(), "pair_count": 4}

    def generate():
        r = client.post(
            BASE + "/qr-batches",
            json=payload,
            headers={
                **headers(wf["operations"]),
                "Idempotency-Key": "read-race-" + uuid4().hex,
            },
        )
        assert r.status_code == 201
        return r.json()

    def read():
        return get(sample, "/qr-batches", batch_label=payload["batch_label"])

    with ThreadPoolExecutor(max_workers=2) as pool:
        future = pool.submit(generate)
        reads = [pool.submit(read) for _ in range(2)]
        created = future.result()
        for f in reads:
            for row in f.result()["items"]:
                assert (row["pair_count"], row["current_tag_count"]) == (4, 8)
    assert get(sample, f"/qr-batches/{created['batch_id']}")["pair_count"] == 4
    with pg.connect() as c:
        indexes = set(
            c.execute(
                text(
                    "SELECT indexname FROM pg_indexes WHERE schemaname=current_schema()"
                )
            ).scalars()
        )
        assert {
            "ix_pair_batch",
            "uq_current_pair_tag_type",
            "uq_pair_one_live_claim",
        }.issubset(indexes)
        plan = c.execute(
            text(
                "EXPLAIN (FORMAT JSON) SELECT p.id FROM public.tag_pairs p WHERE p.batch_id=:id ORDER BY p.created_at DESC,p.id DESC LIMIT 21"
            ),
            {"id": created["batch_id"]},
        ).scalar_one()
        assert plan[0]["Plan"]["Node Type"] == "Limit"
