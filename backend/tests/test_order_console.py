"""Task5.7E canonical080 predicates in SQLite :memory:, not PG/MVCC proof."""

import json
import sqlite3
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.api.auth import AccessError
from app.api.v1.fulfillment_queries import orders


class Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def mappings(self):
        return self

    def all(self):
        return self.value


class Memory:
    def __init__(self, roles):
        self.roles = set(roles)
        self.sql = sqlite3.connect(":memory:")
        self.sql.row_factory = sqlite3.Row
        self.sql.execute("ATTACH DATABASE ':memory:' AS public")
        self.sql.executescript("""
        CREATE TABLE public.orders(id TEXT,order_number TEXT,order_status TEXT,
         payment_status TEXT,fulfillment_status TEXT,currency_code TEXT,total_pkr TEXT,
         created_at TEXT,placed_at TEXT);
        CREATE TABLE public.shipments(id TEXT,order_id TEXT,status TEXT,carrier TEXT,
         tracking_reference TEXT,created_at TEXT,packed_at TEXT,dispatched_at TEXT,
         delivered_at TEXT);
        """)
        self.sql.create_function("sr_is_staff", 1, lambda r: r in self.roles)
        self.sql.create_function("sr_fulfillment_eligible", 1, lambda _: False)
        self.sql.create_function(
            "jsonb_build_object",
            -1,
            lambda *args: json.dumps(dict(zip(args[::2], args[1::2], strict=True))),
        )
        for i in range(1, 6):
            self.sql.execute(
                "INSERT INTO public.orders VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    str(UUID(int=i)),
                    f"SYNTHETIC-{i}",
                    "cancelled" if i == 5 else "placed",
                    "verified" if i == 4 else "under_review",
                    "allocated" if i == 4 else "unallocated",
                    "PKR",
                    "100.00",
                    "2026-10-20T00:00:00+00:00",
                    "2026-10-20T00:00:00+00:00",
                ),
            )

    def execute(self, statement, params):
        sql = str(statement)
        if "FROM public.staff_roles" in sql:
            return Result(
                1
                if self.roles.intersection(params.get("roles", ["operations"]))
                else None
            )
        # Only PostgreSQL syntax/driver values are adapted; production predicates,
        # LIMIT+1, projections, direction and composite paging remain unchanged.
        sql = sql.replace("public.sr_is_staff(ARRAY[:role])", "sr_is_staff(:role)")
        sql = sql.replace("public.sr_fulfillment_eligible", "sr_fulfillment_eligible")
        sql = sql.replace(" AS timestamptz", " AS TEXT")
        bound = {
            k: v.isoformat()
            if isinstance(v, datetime)
            else str(v)
            if isinstance(v, UUID)
            else v
            for k, v in params.items()
        }
        rows = [dict(r) for r in self.sql.execute(sql, bound)]
        for r in rows:
            if isinstance(r.get("latest_shipment"), str):
                r["latest_shipment"] = json.loads(r["latest_shipment"])
        return Result(rows)


def context(roles, mfa=True):
    return SimpleNamespace(
        session=Memory(roles),
        principal=SimpleNamespace(user_id=UUID(int=100)),
        email_verified=True,
        mfa_verified=mfa,
    )


@pytest.mark.parametrize(
    "roles", [("operations",), ("finance",), ("operations", "finance")]
)
@pytest.mark.parametrize("sort", ["newest", "oldest"])
def test_production_predicates_direction_ties_and_no_filtered_count(roles, sort):
    ctx = context(roles)
    seen, cursor = [], None
    for _ in range(3):
        page = orders(ctx, limit=2, sort=sort, cursor=cursor)
        assert set(page) == {"items", "next_cursor"}
        seen.extend(page["items"])
        cursor = page["next_cursor"]
    assert cursor is None
    assert len(seen) == len({r.order_id for r in seen}) == 5
    assert [r.order_id.int for r in seen] == sorted(
        range(1, 6), reverse=sort == "newest"
    )
    assert all(
        r.projection == ("operations" if "operations" in roles else "finance")
        for r in seen
    )


def test_exact_search_half_open_time_and_independent_states():
    ctx = context(["finance"])
    assert len(orders(ctx, order_number="SYNTHETIC-4")["items"]) == 1
    assert orders(ctx, order_number="SYNTHETIC")["items"] == []
    assert len(orders(ctx, payment_status="verified")["items"]) == 1
    assert len(orders(ctx, order_status="cancelled")["items"]) == 1
    assert len(orders(ctx, fulfillment_status="unallocated")["items"]) == 4
    stamp = datetime(2026, 10, 20, tzinfo=UTC)
    assert len(orders(ctx, created_from=stamp)["items"]) == 5
    assert orders(ctx, created_before=stamp)["items"] == []


@pytest.mark.parametrize("roles", [[], ["superadmin"], ["security_admin"], ["support"]])
def test_no_inherited_role(roles):
    with pytest.raises(AccessError):
        orders(context(roles))


def test_mfa_and_invalid_bounds_dates_cursor():
    with pytest.raises(AccessError):
        orders(context(["finance"], mfa=False))
    for args in [{"limit": 0}, {"limit": 101}, {"cursor": "../x"}]:
        with pytest.raises(HTTPException):
            orders(context(["finance"]), **args)
    with pytest.raises(HTTPException):
        orders(context(["finance"]), created_from=datetime(2026, 1, 1))
