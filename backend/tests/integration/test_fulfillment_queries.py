"""Task 5.5A: real guards/RLS, isolated metadata only; no carrier or object writes."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from test_auth_guards import change
from test_commerce_schema import pay, place, qa

pytest_plugins = ["test_auth_guards"]
BASE = "/api/v1/admin"
STAMP = "2026-01-01T00:00:00Z"


@pytest.fixture(scope="module")
def sample(guarded):
    pg, wf, ids, _, _, _ = guarded
    with pg.connect() as c:
        c.execute(
            text("UPDATE public.orders SET created_at=:stamp WHERE id=:id"),
            {"id": ids["purchase"], "stamp": STAMP},
        )
        place(c, ids)
        pay(c, ids)
        qa(c, ids)
        c.execute(
            text(
                "SELECT set_config('safereturn.actor_id',:uid,true),set_config('safereturn.mfa_verified','true',true)"
            ),
            {"uid": str(wf["operations"])},
        )
        c.execute(
            text(
                "UPDATE public.orders SET fulfillment_status='allocated' WHERE id=:id"
            ),
            {"id": ids["purchase"], "stamp": STAMP},
        )
        job = c.execute(
            text(
                "INSERT INTO public.print_jobs(order_id,job_revision,status,template_fingerprint,render_config) VALUES(:id,1,'qa_passed','synthetic-query-fixture','{}') RETURNING id"
            ),
            {"id": ids["purchase"]},
        ).scalar_one()
        c.execute(
            text(
                "INSERT INTO public.print_artifacts(print_job_id,object_key,format,sha256_hex,size_bytes) VALUES(:job,:key,'pdf',:sha,1)"
            ),
            {"job": job, "key": "PRIVATE-OBJECT-" + uuid4().hex, "sha": "a" * 64},
        )
        c.execute(
            text(
                "INSERT INTO public.print_job_qa(print_job_id,inspected_by,approved,artifact_sha256,observations,reason) VALUES(:job,:uid,true,:sha,'{}','Synthetic metadata only, no physical acceptance claim')"
            ),
            {"job": job, "uid": wf["operations"], "sha": "a" * 64},
        )
        packages = {}
        for status in ("preparing", "exception", "returned"):
            packages[status] = c.execute(
                text(
                    "INSERT INTO public.shipments(order_id,shipping_address_id,status,carrier,tracking_reference,created_at) VALUES(:order,:address,:status,'Synthetic Carrier','synthetic-tracking',:stamp) RETURNING id"
                ),
                {
                    "order": ids["purchase"],
                    "address": ids["address"],
                    "status": status,
                    "stamp": STAMP,
                },
            ).scalar_one()
        c.execute(
            text(
                "INSERT INTO public.shipment_pairs(shipment_id,pair_id,packed_qa_confirmed,packed_by,packed_at) VALUES(:shipment,:pair,true,:uid,now())"
            ),
            {
                "shipment": packages["preparing"],
                "pair": ids["pair"],
                "uid": wf["operations"],
            },
        )
        other = c.execute(
            text(
                "INSERT INTO public.orders(order_number,customer_user_id,subtotal_pkr,total_pkr,created_at) VALUES(:number,:uid,1.25,1.25,:stamp) RETURNING id"
            ),
            {"number": "query-" + uuid4().hex, "uid": ids["customer"], "stamp": STAMP},
        ).scalar_one()
        c.execute(
            text(
                "INSERT INTO public.staff_roles(user_id,role,granted_by) VALUES(:uid,'superadmin',:uid)"
            ),
            {"uid": wf["b"]},
        )
        c.commit()
    return {"packages": packages, "job": job, "orders": [ids["purchase"], other]}


def snapshot(pg):
    # One round trip; every row in these schemas is a synthetic fixture.
    tables = (
        "orders",
        "shipments",
        "shipment_pairs",
        "order_shipping_snapshots",
        "order_pair_units",
        "print_jobs",
        "audit_events",
        "idempotency_records",
    )
    with pg.connect() as c:
        return c.execute(
            text(
                "SELECT "
                + ",".join(
                    f"(SELECT md5(coalesce(string_agg(to_jsonb(t)::text,',' ORDER BY to_jsonb(t)::text),'')) FROM public.{table} t)"
                    for table in tables
                )
            )
        ).one()


def get(guarded, path, who="operations", **params):
    _, wf, _, _, headers, client = guarded
    response = client.get(BASE + path, params=params, headers=headers(wf[who]))
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    return response.json()


def test_stable_orders_and_role_specific_safe_projections(guarded, sample):
    pg, _, ids, _, _, _ = guarded
    before = snapshot(pg)
    params = {
        "created_from": STAMP,
        "created_before": "2026-01-02T00:00:00Z",
        "limit": 1,
    }
    for sort in ("oldest", "newest"):
        first = get(guarded, "/orders", sort=sort, **params)
        second = get(
            guarded, "/orders", sort=sort, cursor=first["next_cursor"], **params
        )
        assert [row["order_id"] for row in first["items"] + second["items"]] == [
            str(i) for i in sorted(sample["orders"], reverse=sort == "newest")
        ]
        assert second["next_cursor"] is None
    ops = get(
        guarded,
        "/orders",
        payment_status="verified",
        order_status="placed",
        fulfillment_status="allocated",
    )["items"]
    assert len(ops) == 1
    assert ops[0]["order_id"] == str(ids["purchase"])
    assert ops[0]["total_pkr"] == "0.76"
    assert ops[0]["shipment_count"] == 3  # Two order items must not multiply packages.
    assert ops[0]["fulfillment_eligible"] is True
    assert ops[0]["latest_shipment"]["shipment_id"] == str(
        max(sample["packages"].values())
    )
    finance = get(
        guarded, "/orders", who="finance", order_number=ops[0]["order_number"]
    )["items"]
    assert len(finance) == 1
    assert finance[0]["projection"] == "finance"
    assert set(finance[0]) == {
        "projection",
        "order_id",
        "order_number",
        "order_status",
        "payment_status",
        "fulfillment_status",
        "currency_code",
        "total_pkr",
        "created_at",
        "placed_at",
    }
    # Existing finance detail remains usable without address/decryption capability.
    detail = get(guarded, f"/orders/{ids['purchase']}", who="finance")
    assert "shipping_snapshot" not in detail
    assert detail["print_status"] == "restricted"
    assert snapshot(pg) == before


def test_packages_filters_pair_bounds_and_no_private_projection(guarded, sample):
    pg, wf, ids, _, _, _ = guarded
    before = snapshot(pg)
    for sort in ("oldest", "newest"):
        seen, cursor = [], None
        for _ in range(3):
            params = {
                "sort": sort,
                "limit": 1,
                "order_id": str(ids["purchase"]),
                "created_from": STAMP,
                "created_before": "2026-01-02T00:00:00Z",
            }
            if cursor:
                params["cursor"] = cursor
            result = get(guarded, "/shipments", **params)
            seen.extend(row["shipment_id"] for row in result["items"])
            cursor = result["next_cursor"]
        assert seen == [
            str(i)
            for i in sorted(sample["packages"].values(), reverse=sort == "newest")
        ]
        assert cursor is None
    for status, sid in sample["packages"].items():
        rows = get(
            guarded,
            "/shipments",
            status=status,
            carrier="Synthetic Carrier",
            tracking_reference="synthetic-tracking",
        )["items"]
        assert len(rows) == 1 and rows[0]["shipment_id"] == str(sid)
        detail = get(guarded, f"/shipments/{sid}", pair_limit=1)
        assert {k: v for k, v in detail.items() if k != "pairs"} == rows[0]
        assert detail["fulfillment_eligible"] is True
        assert detail["requires_review"] is False
        assert detail["pair_count"] == (1 if status == "preparing" else 0)
        assert len(detail["pairs"]["items"]) == detail["pair_count"]
        assert detail["pairs"]["next_cursor"] is None
        for forbidden in (
            "ciphertext",
            "shipping_address",
            "recipient",
            "phone",
            "Lahore",
            "public_token",
            "object_key",
            "PRIVATE-OBJECT",
            str(ids["customer"]),
            str(wf["operations"]),
            "bank_reference",
        ):
            assert forbidden not in str(detail)
    assert (
        get(
            guarded,
            f"/shipments/{sample['packages']['preparing']}",
            pair_cursor=str(ids["pair"]),
        )["pairs"]["items"]
        == []
    )
    assert get(guarded, "/shipments", carrier="Absent Carrier")["items"] == []
    assert get(guarded, "/shipments", created_before=STAMP)["items"] == []
    assert snapshot(pg) == before


def test_explicit_roles_session_aal_and_invalid_queries(guarded, sample):
    pg, wf, _, sessions, headers, client = guarded
    paths = ("/orders", "/shipments", f"/shipments/{sample['packages']['preparing']}")
    for path in paths:
        assert client.get(BASE + path).status_code == 401
        for who in ("support", "security_admin", "b"):
            assert client.get(BASE + path, headers=headers(wf[who])).status_code == 403
        assert (
            client.get(
                BASE + path, headers=headers(wf["operations"], aal="aal1")
            ).status_code
            == 403
        )
    assert (
        client.get(BASE + "/shipments", headers=headers(wf["finance"])).status_code
        == 403
    )
    with change(pg, "auth.sessions", sessions[wf["operations"]], {"aal": "aal1"}):
        assert (
            client.get(
                BASE + "/shipments", headers=headers(wf["operations"])
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
            client.get(BASE + "/orders", headers=headers(wf["operations"])).status_code
            == 401
        )
    with pg.connect() as c:
        role = c.execute(
            text(
                "SELECT id FROM public.staff_roles WHERE user_id=:uid AND role='operations'"
            ),
            {"uid": wf["operations"]},
        ).scalar_one()
    with change(pg, "public.staff_roles", role, {"revoked_at": datetime.now(UTC)}):
        assert (
            client.get(
                BASE + "/shipments", headers=headers(wf["operations"])
            ).status_code
            == 403
        )
        assert (
            client.get(BASE + "/orders", headers=headers(wf["operations"])).status_code
            == 403
        )
    for params in (
        {"limit": 101},
        {"cursor": "invalid"},
        {"created_from": "2026-01-01"},
        {"created_from": STAMP, "created_before": STAMP},
        {"sort": "injected"},
        {"carrier": "\n"},
        {"status": "lost"},
    ):
        response = client.get(
            BASE + "/shipments", params=params, headers=headers(wf["operations"])
        )
        assert response.status_code == 422
        assert response.headers["cache-control"] == "no-store"
    assert (
        client.get(
            BASE + f"/shipments/{uuid4()}", headers=headers(wf["operations"])
        ).status_code
        == 404
    )
    assert (
        client.get(
            BASE + paths[2], params={"pair_limit": 0}, headers=headers(wf["operations"])
        ).status_code
        == 422
    )


def test_live_eligibility_and_existing_stale_transition_guard(guarded, sample):
    pg, wf, _, _, headers, client = guarded
    sid = sample["packages"]["preparing"]
    with change(pg, "public.print_jobs", sample["job"], {"status": "failed"}):
        before = snapshot(pg)
        row = get(guarded, f"/shipments/{sid}")
        assert row["status"] == "preparing"
        assert row["fulfillment_eligible"] is False and row["requires_review"] is True
        assert [
            i["shipment_id"]
            for i in get(guarded, "/shipments", requires_review="true")["items"]
        ] == [str(sid)]
        orders = get(guarded, "/orders", payment_status="verified")["items"]
        assert orders[0]["fulfillment_eligible"] is False
        for expected, status in (("dispatched", 412), ("preparing", 409)):
            response = client.request(
                "PATCH",
                BASE + f"/shipments/{sid}",
                headers={
                    **headers(wf["operations"]),
                    "Idempotency-Key": "synthetic-query-" + uuid4().hex,
                },
                json={
                    "expected_status": expected,
                    "status": "packed",
                    "packing_confirmed": True,
                    "reason": "Synthetic stale query transition",
                },
            )
            assert response.status_code == status, response.text
        assert snapshot(pg) == before
