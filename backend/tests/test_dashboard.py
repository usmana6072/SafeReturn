"""Synthetic HTTP/crypto and adapted production count SELECTs in SQLite memory.

This is not PostgreSQL helper, RLS, planner, timeout or MVCC acceptance.
"""

import importlib.util
import io
import re
import sqlite3
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.exc import OperationalError
from test_auth import claims, signed
from test_auth import verifier as _verifier
from test_critical_workflow_boundaries import MemoryDatabase, Result
from test_health import ASGIClient

from app.api.v1.dashboard import METRICS, ROLES, count
from app.core.config import Settings
from app.main import create_app

verifier = _verifier
FILE = Path(__file__).parents[1] / "alembic/versions/0028_dashboard_reads.sql"
SQL = FILE.read_text(encoding="utf-8")
PARTS = re.findall(r"\(SELECT count\(\*\) FROM \((.*?)\) c\)", SQL, re.DOTALL)
assert len(PARTS) == 10
CANARY = "PRIVATE_DASHBOARD_CANARY"
ROOT = "/api/v1/admin/dashboard/"


class Rows(Result):
    def scalars(self):
        return iter(self.value)


class Store(MemoryDatabase):
    def __init__(self, actor):
        super().__init__(actor, uuid4())
        self.sql = sqlite3.connect(":memory:", check_same_thread=False)
        self.eligible_orders = set()
        self.sql.create_function(
            "sr_fulfillment_eligible", 1, lambda oid: oid in self.eligible_orders
        )
        self.sql.create_function("sr_actor_id", 0, lambda: str(actor))
        self.sql.executescript("""
        CREATE TABLE products(id TEXT,lifecycle_status TEXT);
        CREATE TABLE product_variants(id TEXT,product_id TEXT,is_active BOOL);
        CREATE TABLE orders(id TEXT,fulfillment_status TEXT,placed_at TEXT);
        CREATE TABLE order_shipping_snapshots(order_id TEXT PRIMARY KEY);
        CREATE TABLE shipments(id TEXT,order_id TEXT,status TEXT,dispatched_at TEXT);
        CREATE TABLE notification_outbox(id TEXT,status TEXT,created_at TEXT);
        CREATE TABLE support_cases(id TEXT,status TEXT,assigned_staff_id TEXT);
        CREATE TABLE finance_sheet_sync(id TEXT,status TEXT);
        CREATE TABLE frozen_history(value TEXT);
        INSERT INTO frozen_history VALUES('immutable synthetic original purchase/QR/payment/custody history');
        """)
        self.fail_groups = set()
        self.bad_projection = False
        self.hook = None
        self.queries = []
        self.timeout = "5s"
        self.depth = 0

    @contextmanager
    def begin_nested(self):
        previous = self.timeout
        self.depth += 1
        try:
            yield self
        except BaseException:
            self.timeout = previous
            raise
        finally:
            self.depth -= 1

    def number(self, index, **args):
        query = PARTS[index].replace("public.", "")
        query = re.sub(r"\bstate\b", ":state", query)
        query = query.replace("day+interval '24 hours'", ":next")
        query = re.sub(r"\bday\b", ":day", query)
        return self.sql.execute(
            "SELECT count(*) FROM (" + query + ")", args
        ).fetchone()[0]

    def aggregate(self, group):
        if group == "catalog":
            return {
                "catalog.products": self.number(0),
                "catalog.variants": self.number(1),
            }
        if group == "fulfillment":
            return {
                "fulfillment.ready_orders": self.number(2),
                "fulfillment.requires_review": self.number(3),
                **{
                    "shipments." + state: self.number(4, state=state)
                    for state in (
                        "preparing",
                        "packed",
                        "dispatched",
                        "delivered",
                        "exception",
                        "returned",
                    )
                },
            }
        if group == "notifications":
            return {
                "notifications." + state: self.number(5, state=state)
                for state in ("pending", "leased", "retry", "sent", "dead")
            }
        if group == "support":
            return {
                "support." + state: self.number(6, state=state)
                for state in ("open", "investigating")
            }
        if group == "finance_mirror":
            return {"finance_mirror.records": self.number(7)}
        raise AssertionError("Unsupported aggregate")

    def execute(self, statement, params=None):
        query, p = str(statement), params or {}
        if query == "SHOW statement_timeout":
            return Rows(self.timeout)
        if "set_config('statement_timeout'" in query:
            self.timeout = p["timeout"]
            assert self.depth
            return Rows(None)
        if query.startswith("SELECT role FROM public.staff_roles"):
            return Rows(sorted(self.roles))
        if "sr_dashboard" in query:
            assert self.depth == 1 and self.timeout.endswith("ms")
            assert 0 < int(self.timeout[:-2]) <= 3000
            ident = p.get("group", p.get("series"))
            self.queries.append(ident)
            if ident in self.fail_groups:
                raise OperationalError("SELECT", {}, Exception(CANARY))
            if "sr_dashboard_summary" in query:
                value = self.aggregate(ident)
                if self.bad_projection:
                    value["private"] = CANARY
            else:
                value = []
                for i in range(30):
                    start = p["end"] - timedelta(days=30 - i)
                    end = start + timedelta(days=1)
                    value.append(
                        {
                            "start": start,
                            "end": end,
                            "n": self.number(
                                8 if ident == "shipments_dispatched" else 9,
                                day=start.isoformat(),
                                next=end.isoformat(),
                            ),
                        }
                    )
            if self.hook:
                self.hook(self, ident)
            return Rows(value)
        return super().execute(statement, params)


@pytest.fixture
def env(verifier):
    provider, private, _, _ = verifier
    actor = uuid4()
    db = Store(actor)
    settings = Settings(dashboard_enabled=True)
    app = create_app(settings)
    app.state.database, app.state.jwt_verifier = db, provider

    def headers(**override):
        return {
            "Authorization": "Bearer "
            + signed(private, claims(**{"sub": str(actor), "aal": "aal2", **override}))
        }

    yield ASGIClient(app), db, headers, settings, app
    db.sql.close()


def read(env, suffix="summary", **kwargs):
    return env[0].get(ROOT + suffix, headers=kwargs.pop("headers", env[2]()), **kwargs)


def groups(response):
    return {g["group"]: g for g in response.json()["groups"]}


def counts(response):
    return {
        m["metric_id"]: m["count"]
        for g in response.json()["groups"]
        for m in g["metrics"]
    }


def test_actual_count_predicates_cardinalities_fanout_and_immutable_history(
    env, caplog
):
    caplog.set_level("INFO")
    _, db, _, _, _ = env
    db.roles = set().union(*ROLES.values())
    db.sql.executemany(
        "INSERT INTO products VALUES(?,?)", [("p1", "draft"), ("p2", "archived")]
    )
    db.sql.executemany(
        "INSERT INTO product_variants VALUES(?,?,?)",
        [(str(i), "p1", True) for i in range(5)],
    )
    db.sql.executemany(
        "INSERT INTO orders VALUES(?,?,NULL)",
        [("o1", "allocated"), ("o2", "packed"), ("o3", "packed"), ("o4", "allocated")],
    )
    db.sql.executemany(
        "INSERT INTO order_shipping_snapshots VALUES(?)", [("o1",), ("o2",), ("o3",)]
    )
    db.eligible_orders = {"o1", "o2", "o3", "o4"}
    db.sql.executemany(
        "INSERT INTO shipments VALUES(?,?,?,NULL)",
        [
            ("s1", "o2", "preparing"),
            ("s2", "o3", "returned"),
            ("s3", "missing", "dispatched"),
        ],
    )
    db.sql.executemany(
        "INSERT INTO notification_outbox VALUES(?,?,NULL)",
        [("n1", "retry"), ("n2", "dead"), ("n3", "sent")],
    )
    # A shipment with no matching parent is impossible under PostgreSQL FK and
    # must not inflate canonical eligibility-review (which joins its order).
    db.sql.executemany(
        "INSERT INTO support_cases VALUES(?,?,?)",
        [
            ("c1", "open", None),
            ("c2", "open", str(db.owner)),
            ("c3", "open", str(uuid4())),
            ("c4", "closed", None),
        ],
    )
    db.sql.executemany(
        "INSERT INTO finance_sheet_sync VALUES(?,?)",
        [("m1", "pending"), ("m2", "failed")],
    )
    before = list(db.sql.iterdump())
    response = read(env)
    assert response.status_code == 200
    values = counts(response)
    assert (
        values["catalog.products"]["value"] == 2
        and values["catalog.variants"]["value"] == 5
    )
    assert (
        values["fulfillment.ready_orders"]["value"] == 2
    )  # missing snapshot and returned shipment excluded
    assert (
        values["shipments.returned"]["value"] == 1
        and values["shipments.exception"]["value"] == 0
    )
    assert (
        values["support.open"]["value"] == 2
        and values["support.investigating"]["value"] == 0
    )
    assert (
        values["notifications.retry"]["value"] == 1
        and values["finance_mirror.records"]["value"] == 2
    )
    assert set(response.json()) == {"as_of", "groups"}
    assert set(groups(response)["notifications"]) == {
        "group",
        "status",
        "as_of",
        "metrics",
        "reason_code",
    }
    assert CANARY not in response.text + caplog.text
    assert list(db.sql.iterdump()) == before and db.timeout == "5s"


@pytest.mark.parametrize(
    "role,expected",
    [
        (
            "operations",
            {"catalog", "inventory", "fulfillment", "printing", "notifications"},
        ),
        ("finance", {"finance", "finance_mirror"}),
        ("support", {"support"}),
        ("security_admin", {"catalog", "notifications", "finance_mirror"}),
        ("superadmin", {"catalog", "finance_mirror"}),
    ],
)
def test_role_scopes_no_implicit_inheritance(env, role, expected):
    db = env[1]
    db.roles = {role}
    response = read(env)
    assert response.status_code == 200 and set(groups(response)) == expected
    for g in groups(response).values():
        assert ROLES[g["group"]].intersection({role})
    assert not any(k in response.text for k in ["registered_users", "revenue", CANARY])


def test_multi_role_union_and_disabled_dependency_not_queried(env):
    db = env[1]
    db.roles = {"operations", "finance"}
    r = read(env)
    assert set(groups(r)) == set(ROLES) - {"support"}
    assert groups(r)["finance"]["reason_code"] == "FEATURE_DISABLED"
    assert groups(r)["inventory"]["reason_code"] == "LOW_STOCK_UNCONFIGURED"
    assert not {"finance", "inventory", "printing"}.intersection(db.queries)
    env[3].finance_reconciliation_enabled = True
    env[3].inventory_low_stock_threshold = 10
    r = read(env)
    assert groups(r)["finance"]["reason_code"] == "DRILLDOWN_UNAVAILABLE"
    assert groups(r)["inventory"]["reason_code"] == "DRILLDOWN_UNAVAILABLE"
    assert not {"finance", "inventory", "printing"}.intersection(db.queries)


@pytest.mark.parametrize("suffix", ["summary", "trends"])
@pytest.mark.parametrize(
    "fault",
    ["anonymous", "expired", "session", "role", "aal1", "provider_mfa", "disabled"],
)
def test_live_guards_before_queries(env, suffix, fault):
    _, db, h, settings, _ = env
    headers, status = h(), 403
    if fault == "anonymous":
        headers, status = {}, 401
    elif fault == "expired":
        headers, status = h(exp=int(time.time()) - 100), 401
    elif fault == "session":
        db.active, status = False, 401
    elif fault == "role":
        db.roles = {"customer"}
    elif fault == "aal1":
        headers = h(aal="aal1")
    elif fault == "provider_mfa":
        db.mfa = False
    elif fault == "disabled":
        settings.dashboard_enabled, status = False, 503
    response = read(env, suffix, headers=headers)
    assert response.status_code == status and not db.queries
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize(
    "suffix",
    [
        "summary?path=/admin/users",
        "summary?group=finance",
        "trends?display_timezone=UTC&display_timezone=UTC",
        "trends?display_timezone=Europe/London",
        "trends?from=2020-01-01",
    ],
)
def test_closed_queries(env, suffix):
    assert read(env, suffix).status_code == 422 and not env[1].queries


def test_partial_failure_unknown_vs_zero_and_timeout_restore(env, caplog):
    db = env[1]
    db.fail_groups = {"catalog"}
    before = list(db.sql.iterdump())
    r = read(env)
    assert r.status_code == 200
    assert groups(r)["catalog"] == {
        "group": "catalog",
        "status": "unavailable",
        "as_of": None,
        "metrics": [],
        "reason_code": "QUERY_UNAVAILABLE",
    }
    assert counts(r)["shipments.exception"] == {"value": 0, "is_exact": True}
    assert db.timeout == "5s" and not db.depth and list(db.sql.iterdump()) == before
    assert CANARY not in r.text + caplog.text


def test_private_or_malformed_provider_projection_is_not_forwarded(env):
    db = env[1]
    db.bad_projection = True
    r = read(env)
    assert r.status_code == 200 and CANARY not in r.text
    assert not counts(r)


@pytest.mark.parametrize("n", [999, 1000, 1001])
def test_production_count_cap_not_inferred_exact(env, n):
    db = env[1]
    db.sql.executemany(
        "INSERT INTO products VALUES(?,'draft')", [(str(i),) for i in range(n)]
    )
    assert counts(read(env))["catalog.products"] == {
        "value": min(n, 1000),
        "is_exact": n < 1000,
    }


@pytest.mark.parametrize("value", [-1, 1001, 1.5, True, "0"])
def test_strict_count_contract(value):
    with pytest.raises(ValueError):
        count(value)


def test_real_daily_predicates_utc_half_open_returns_and_late_observations(env):
    db = env[1]
    end = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=30)
    db.sql.executemany(
        "INSERT INTO shipments VALUES(?,?,?,?)",
        [
            ("before", "o", "returned", (start - timedelta(seconds=1)).isoformat()),
            ("first", "o", "delivered", start.isoformat()),
            ("second", "o", "returned", (start + timedelta(days=1)).isoformat()),
            ("excluded", "o", "dispatched", end.isoformat()),
        ],
    )
    r = read(env, "trends?display_timezone=Asia/Karachi")
    assert r.status_code == 200
    data = r.json()
    assert (
        data["display_timezone"] == "Asia/Karachi" and data["bucket_timezone"] == "UTC"
    )
    series = {s["series_id"]: s for s in data["series"]}
    assert series["orders_placed"]["status"] == "unavailable"
    dispatch = series["shipments_dispatched"]["buckets"]
    assert len(dispatch) == 30 and [b["count"]["value"] for b in dispatch[:3]] == [
        1,
        1,
        0,
    ]
    assert sum(b["count"]["value"] for b in dispatch) == 2
    db.sql.execute(
        "INSERT INTO shipments VALUES('late','o','returned',?)", (start.isoformat(),)
    )
    second = read(env, "trends").json()
    assert second["series"][1]["buckets"][0]["count"]["value"] == 2
    assert (
        second["range_start"] == data["range_start"]
        and second["range_end"] == data["range_end"]
    )


@pytest.mark.parametrize("fault", ["role", "session", "mfa"])
def test_revoke_during_read_denies_final_projection(env, fault):
    db = env[1]

    def hook(db, ident):
        if fault == "role":
            db.roles = set()
        elif fault == "session":
            db.active = False
        else:
            db.mfa = False

    db.hook = hook
    r = read(env)
    assert r.status_code == (401 if fault == "session" else 403)
    assert "groups" not in r.json()


def test_budget_prevents_query_admission(env, monkeypatch):
    ticks = iter([0, 9, 10, 11, 12, 13])
    monkeypatch.setattr("app.api.v1.dashboard.monotonic", lambda: next(ticks))
    r = read(env)
    assert r.status_code == 200 and not env[1].queries
    assert groups(r)["catalog"]["reason_code"] == "REQUEST_BUDGET_EXHAUSTED"


def test_trend_partial_failure_and_no_global_series_for_support(env):
    db = env[1]
    db.fail_groups = {"shipments_dispatched"}
    r = read(env, "trends")
    series = {s["series_id"]: s for s in r.json()["series"]}
    assert series["shipments_dispatched"]["buckets"] == []
    assert series["notifications_created"]["status"] == "ready"
    db.roles = {"support"}
    assert read(env, "trends").json()["series"] == []


def test_outer_commit_failure_safe_and_immutable(env, caplog):
    db = env[1]
    before = list(db.sql.iterdump())
    db.fail_commit = True
    r = read(env)
    assert r.status_code == 503 and CANARY not in r.text + caplog.text
    assert list(db.sql.iterdump()) == before


def test_offline_migration_capture_canonical_openapi_and_no_writer(env):
    file = FILE.with_suffix(".py")
    spec = importlib.util.spec_from_file_location("dashboard_migration", file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = Path(__file__).parents[2] / "output/task57b"
    for operation in ("upgrade", "downgrade"):
        buffer = io.StringIO()
        context = MigrationContext.configure(
            dialect_name="postgresql", opts={"as_sql": True, "output_buffer": buffer}
        )
        with Operations.context(context):
            getattr(module, operation)()
        (output / (operation + ".sql")).write_text(buffer.getvalue(), encoding="utf-8")
    assert module.down_revision == "0027_manufacturing_exports"
    assert (
        "CREATE TABLE" not in SQL
        and "GRANT SELECT" not in SQL
        and "auth.users" not in SQL
    )
    assert "SET search_path=pg_catalog" in SQL
    assert "TO safereturn_api" in SQL and "LIMIT 1000" in SQL
    schema = env[4].openapi()
    assert schema["paths"][ROOT + "summary"]["get"]["operationId"] == "API-344"
    assert schema["paths"][ROOT + "trends"]["get"]["operationId"] == "API-345"
    for suffix in ("summary", "trends"):
        assert env[0].post(ROOT + suffix, headers=env[2](), json={}).status_code == 405
    assert all(
        path.startswith("/admin/") and ".." not in path
        for metrics in METRICS.values()
        for _, path in metrics.values()
    )


def test_database_timezone_is_normalized_and_naive_buckets_fail_closed(env):
    db = env[1]
    original = db.execute
    mode = "offset"

    def execute(statement, params=None):
        value = original(statement, params)
        if "sr_dashboard_trend" in str(statement):
            for row in value.value:
                for field in ("start", "end"):
                    stamp = row[field].astimezone(timezone(timedelta(hours=5)))
                    row[field] = (
                        stamp.isoformat()
                        if mode == "offset"
                        else stamp.replace(tzinfo=None).isoformat()
                    )
        return value

    db.execute = execute
    response = read(env, "trends")
    assert response.status_code == 200
    assert all(
        b["start"].endswith("Z")
        for s in response.json()["series"]
        for b in s["buckets"]
    )
    mode = "naive"
    response = read(env, "trends")
    assert all(s["status"] == "unavailable" for s in response.json()["series"])


def test_daily_count_cap_uses_actual_timestamp_predicate(env):
    db = env[1]
    stamp = (
        datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        - timedelta(hours=1)
    ).isoformat()
    db.sql.executemany(
        "INSERT INTO notification_outbox VALUES(?,'retry',?)",
        [(str(i), stamp) for i in range(1001)],
    )
    response = read(env, "trends")
    series = next(
        s
        for s in response.json()["series"]
        if s["series_id"] == "notifications_created"
    )
    assert series["buckets"][-1]["count"] == {"value": 1000, "is_exact": False}
    assert sum(b["count"]["value"] for b in series["buckets"][:-1]) == 0


def test_final_partial_revocation_omits_old_role_data(env):
    db = env[1]
    db.roles = {"operations", "finance"}

    def hook(db, ident):
        if ident == "notifications":
            db.roles = {"finance"}

    db.hook = hook
    response = read(env)
    assert response.status_code == 200 and set(groups(response)) == {
        "finance",
        "finance_mirror",
    }
    assert "shipments." not in response.text and "catalog.products" not in response.text


def test_predicates_match_existing_scopes_and_no_suppressed_queries(env):
    assert (
        "assigned_staff_id IS NULL OR s.assigned_staff_id=public.sr_actor_id()" in SQL
    )
    assert "public.sr_fulfillment_eligible(o.id)" in PARTS[2]
    assert "'dispatched','delivered','exception','returned'" in PARTS[2]
    assert "s.status IN('preparing','packed','dispatched')" in PARTS[3]
    for pattern in (
        "ARRAY['operations','security_admin','superadmin']",
        "ARRAY['operations','security_admin']",
        "ARRAY['finance','security_admin','superadmin']",
        "ARRAY['support']",
    ):
        assert pattern in SQL
    assert "interval '720 hours'" in SQL and "LIMIT 1000" in PARTS[8]
    db = env[1]
    db.roles = {"finance"}
    assert read(env).status_code == 200
    assert db.queries == ["finance_mirror"]
