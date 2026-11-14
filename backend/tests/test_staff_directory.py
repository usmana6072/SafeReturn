"""Synthetic HTTP/JWT and SQLite-adapted production predicates; not PG acceptance."""

import importlib.util
import io
import re
import sqlite3
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.exc import OperationalError
from test_auth import claims, signed
from test_auth import verifier as _verifier
from test_critical_workflow_boundaries import MemoryDatabase, Result
from test_health import ASGIClient

from app.core.config import Settings
from app.main import create_app

verifier = _verifier
ROOT = "/api/v1/admin/users"
FILE = Path(__file__).parents[1] / "alembic/versions/0029_staff_directory.sql"
SQL = FILE.read_text()
PREDICATE = re.search(r"FROM auth.users u\n(.*?)\n \), bounded", SQL, re.DOTALL)[1]
PREDICATE = re.sub(r"\b(uid|verified|access_filter|observed)\b", r":\1", PREDICATE)
CANARY = "PRIVATE_DIRECTORY_CANARY"


class Store(MemoryDatabase):
    def __init__(self, actor):
        super().__init__(actor, uuid4())
        self.roles = {"security_admin"}
        self.sid = uuid4()
        self.sql = sqlite3.connect(":memory:", check_same_thread=False)
        self.sql.execute(
            "CREATE TABLE users(id TEXT PRIMARY KEY,created_at TEXT,email_confirmed_at TEXT,deleted_at TEXT,is_anonymous BOOL,banned_until TEXT,private TEXT)"
        )
        self.now = datetime.now(UTC).replace(microsecond=0)
        self.timeout = "5s"
        self.depth = 0
        self.hook = None
        self.bad = False
        self.failure = False
        self.verified = True

    def add(self, i, **kw):
        row = {
            "id": str(UUID(int=i)),
            "created_at": self.now.isoformat(),
            "email_confirmed_at": self.now.isoformat(),
            "deleted_at": None,
            "is_anonymous": False,
            "banned_until": None,
            "private": CANARY,
        }
        row.update(kw)
        self.sql.execute(
            "INSERT INTO users VALUES(:id,:created_at,:email_confirmed_at,:deleted_at,:is_anonymous,:banned_until,:private)",
            row,
        )
        return row["id"]

    @contextmanager
    def begin_nested(self):
        old = self.timeout
        self.depth += 1
        try:
            yield self
        except BaseException:
            self.timeout = old
            raise
        finally:
            self.depth -= 1

    def execute(self, statement, params=None):
        q, p = str(statement), params or {}
        if q == "SHOW statement_timeout":
            return Result(self.timeout)
        if "set_config('statement_timeout'" in q:
            assert self.depth == 1
            self.timeout = p.get("timeout", "3000ms")
            return Result(None)
        if "sr_account_session_state" in q:
            return Result(
                SimpleNamespace(email_verified=self.verified, mfa_active=self.mfa)
                if self.active
                and self.actor == str(self.owner)
                and p["sid"] == self.sid
                else None
            )
        if "sr_staff_directory" in q:
            assert self.depth == 1 and self.timeout == "3000ms"
            if self.failure:
                raise OperationalError("SELECT", {}, Exception(CANARY))
            args = {
                "uid": str(p["uid"]) if p["uid"] else None,
                "verified": p["verified"],
                "access_filter": p["access"],
                "observed": self.now.isoformat(),
            }
            query = (
                "SELECT u.id,u.created_at,u.email_confirmed_at,u.banned_until FROM users u\n"
                + PREDICATE
            )
            if p["stamp"]:
                query += " AND (created_at,id)<(:stamp,:ident)"
                args.update(stamp=p["stamp"].isoformat(), ident=str(p["ident"]))
            query += " ORDER BY created_at DESC,id DESC LIMIT :lim"
            args["lim"] = (
                1000
                if p["mode"] == "count"
                else 1
                if p["mode"] == "detail"
                else p["lim"] + 1
            )
            rows = self.sql.execute(query, args).fetchall()
            if p["mode"] == "count":
                value = {
                    "as_of": self.now.isoformat(),
                    "definition": "retained_nonanonymous_auth_registrations_v1",
                    "filters": {
                        "user_id": args["uid"],
                        "email_verified": p["verified"],
                        "provider_access": p["access"],
                    },
                    "count": {"value": len(rows), "is_exact": len(rows) < 1000},
                }
            else:
                value = {
                    "as_of": self.now.isoformat(),
                    "items": [
                        {
                            "user_id": r[0],
                            "registered_at": r[1],
                            "email_verified": r[2] is not None,
                            "provider_access": "banned"
                            if r[3] and r[3] > self.now.isoformat()
                            else "not_banned",
                        }
                        for r in rows
                    ],
                }
            if self.bad:
                value["private"] = CANARY
            if self.hook:
                self.hook(self)
            return Result(value)
        return super().execute(statement, params)


@pytest.fixture
def env(verifier):
    provider, private, _, _ = verifier
    actor = uuid4()
    db = Store(actor)
    settings = Settings(staff_directory_enabled=True)
    app = create_app(settings)
    app.state.database, app.state.jwt_verifier = db, provider

    def headers(**overrides):
        return {
            "Authorization": "Bearer "
            + signed(
                private,
                claims(
                    **{
                        "sub": str(actor),
                        "session_id": str(db.sid),
                        "aal": "aal2",
                        **overrides,
                    }
                ),
            )
        }

    yield ASGIClient(app), db, headers, settings, app
    db.sql.close()


def get(env, suffix="", **kwargs):
    return env[0].get(ROOT + suffix, headers=kwargs.pop("headers", env[2]()), **kwargs)


@pytest.mark.parametrize(
    "roles",
    [
        set(),
        {"operations"},
        {"finance"},
        {"support"},
        {"superadmin"},
        {"operations", "finance"},
        {"security_admin"},
        {"security_admin", "support", "superadmin"},
    ],
)
@pytest.mark.parametrize("suffix", ["", "/count", "/" + str(UUID(int=1))])
def test_roles(env, roles, suffix):
    env[1].add(1)
    env[1].roles = roles
    r = get(env, suffix)
    assert r.status_code == (200 if "security_admin" in roles else 403)
    assert r.headers["cache-control"] == "private, no-store"
    assert r.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize(
    "change,expected",
    [
        ("anonymous", 401),
        ("expired", 401),
        ("revoked_session", 401),
        ("foreign_session", 401),
        ("foreign_subject", 401),
        ("aal1", 403),
        ("provider_aal1", 403),
        ("unverified", 403),
        ("disabled", 503),
    ],
)
def test_authentication(env, change, expected):
    headers = env[2]()
    if change == "anonymous":
        headers = {}
    if change == "expired":
        headers = env[2](exp=int(time.time()) - 60)
    if change == "revoked_session":
        env[1].active = False
    if change == "foreign_session":
        headers = env[2](session_id=str(uuid4()))
    if change == "foreign_subject":
        headers = env[2](sub=str(uuid4()))
    if change == "aal1":
        headers = env[2](aal="aal1")
    if change == "provider_aal1":
        env[1].mfa = False
    if change == "unverified":
        env[1].verified = False
    if change == "disabled":
        env[3].staff_directory_enabled = False
    assert get(env, headers=headers).status_code == expected


@pytest.mark.parametrize(
    "change,expected", [("roles", 403), ("mfa", 403), ("active", 401)]
)
def test_final_assurance_recheck(env, change, expected):
    env[1].add(1)
    env[1].hook = lambda db: setattr(db, change, set() if change == "roles" else False)
    assert get(env).status_code == expected
    assert env[1].rollbacks == 1


@pytest.mark.parametrize(
    "query",
    [
        "email=a@b.test",
        "name=Private",
        "sort=asc",
        "limit=0",
        "limit=101",
        "limit=-1",
        "limit=01",
        "limit=1&limit=2",
        "email_verified=1",
        "provider_access=active",
        "user_id=bad",
        "cursor=bad",
        "cursor=" + "x" * 1025,
        "offset=1",
    ],
)
def test_invalid_search_and_bounds(env, query):
    assert get(env, "?" + query).status_code == 422


def test_population_filters_detail_and_private_canary(env, caplog):
    db = env[1]
    a = db.add(1)
    db.add(2, email_confirmed_at=None)
    db.add(3, banned_until=(db.now + timedelta(days=1)).isoformat())
    db.add(4, banned_until=db.now.isoformat())
    db.add(5, deleted_at=db.now.isoformat())
    db.add(6, is_anonymous=True)
    db.add(7, is_anonymous=None)
    assert get(env, "/count").json()["count"] == {"value": 5, "is_exact": True}
    for query, n in [
        ("email_verified=false", 1),
        ("provider_access=banned", 1),
        ("provider_access=not_banned", 4),
        ("user_id=" + a, 1),
        ("email_verified=false&provider_access=banned", 0),
    ]:
        rows = get(env, "?" + query).json()["items"]
        assert len(rows) == n
        assert get(env, "/count?" + query).json()["count"]["value"] == n
    for i in (5, 6, 99):
        assert get(env, "/" + str(UUID(int=i))).status_code == 404
    detail = get(env, "/" + a)
    assert detail.json()["application_suspension"] == {
        "status": "unavailable",
        "reason_code": "NOT_IMPLEMENTED",
    }
    assert set(detail.json()["user"]) == {
        "user_id",
        "registered_at",
        "email_verified",
        "provider_access",
    }
    assert CANARY not in detail.text + caplog.text
    assert db.profile["display_name"] == "Before" and db.audit == []


def test_tied_paging_and_cursor_binding(env):
    for i in range(1, 8):
        env[1].add(i)
    first = get(env, "?limit=3").json()
    ids = [u["user_id"] for u in first["items"]]
    cursor = first["next_cursor"]
    assert get(env, "?limit=3&email_verified=true&cursor=" + cursor).status_code == 422
    assert get(env, "?cursor=" + cursor + "x").status_code == 422
    while cursor:
        page = get(env, "?limit=3&cursor=" + cursor).json()
        ids += [u["user_id"] for u in page["items"]]
        cursor = page["next_cursor"]
    assert ids == [str(UUID(int=i)) for i in range(7, 0, -1)]
    assert len(get(env, "?limit=100").json()["items"]) == 7


@pytest.mark.parametrize("size", [0, 999, 1000, 1001])
def test_count_cap_and_optional_profile_session_independence(env, size):
    for i in range(1, size + 1):
        env[1].add(i)
    assert get(env, "/count").json()["count"] == {
        "value": min(size, 1000),
        "is_exact": size < 1000,
    }
    assert len(get(env, "?limit=100").json()["items"]) == min(size, 100)


@pytest.mark.parametrize("failure", ["failure", "bad", "fail_commit"])
def test_safe_failure_and_rollback(env, caplog, failure):
    env[1].add(1)
    setattr(env[1], failure, True)
    r = get(env)
    assert r.status_code == 503 and CANARY not in r.text + caplog.text
    assert env[1].rollbacks == 1 and env[1].timeout == "5s" and env[1].audit == []


@pytest.mark.parametrize(
    "suffix",
    [
        "/count?limit=1",
        "/count?user_id=bad",
        "/" + str(UUID(int=1)) + "?email_verified=true",
    ],
)
def test_closed_routes(env, suffix):
    assert get(env, suffix).status_code == 422


def test_database_timezone_normalizes_public_timestamps(env):
    env[1].now = env[1].now.astimezone(timezone(timedelta(hours=5)))
    uid = env[1].add(1)
    listing = get(env).json()
    detail = get(env, "/" + uid).json()
    total = get(env, "/count").json()
    for value in (
        listing["as_of"],
        detail["as_of"],
        total["as_of"],
        listing["items"][0]["registered_at"],
        detail["user"]["registered_at"],
    ):
        assert value.endswith("Z")


def test_offline_upgrade_downgrade_and_route_compatibility(env):
    path = FILE.with_suffix(".py")
    spec = importlib.util.spec_from_file_location("directory_migration", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    output = io.StringIO()
    ctx = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output}
    )
    with Operations.context(ctx):
        mod.upgrade()
        mod.downgrade()
    ddl = output.getvalue()
    assert "CREATE FUNCTION public.sr_staff_directory" in ddl
    assert "DROP FUNCTION public.sr_staff_directory" in ddl
    assert "SET search_path=pg_catalog" in ddl and "SECURITY DEFINER" in ddl
    assert "ARRAY['security_admin']" in ddl and "sr_account_session_state(sid)" in ddl
    assert "GRANT SELECT" not in ddl and "UPDATE auth." not in ddl
    assert "public.user_profiles" not in SQL and "auth.sessions" not in SQL
    target = Path(__file__).parents[2] / "output/task23c"
    target.mkdir(parents=True, exist_ok=True)
    (target / "offline-upgrade-downgrade.sql").write_text(ddl)
    routes = env[4].openapi()["paths"]
    for suffix, op in [
        ("", "API-346"),
        ("/count", "API-348"),
        ("/{user_id}", "API-347"),
    ]:
        assert routes[ROOT + suffix]["get"]["operationId"] == op
    assert routes["/api/v1/admin/dashboard/summary"]["get"]["operationId"] == "API-344"
    assert routes["/api/v1/admin/dashboard/trends"]["get"]["operationId"] == "API-345"
    assert (
        not Settings().staff_directory_enabled
        and not Settings().dashboard_enabled
        and not Settings().manufacturing_exports_enabled
    )
