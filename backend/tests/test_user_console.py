"""Opt-in5.7C state read: synthetic ASGI/crypto/SQLite, not PostgreSQL acceptance."""

import importlib.util
import io
import re
from pathlib import Path
from uuid import UUID

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.exc import OperationalError
from test_auth import verifier as _verifier
from test_critical_workflow_boundaries import Result as Rows
from test_staff_directory import CANARY, get
from test_staff_directory import FILE as DIRECTORY_FILE
from test_staff_directory import env as _env

verifier = _verifier
env = _env
FILE = DIRECTORY_FILE.parent / "0031_staff_account_state.sql"
SQL = FILE.read_text()


@pytest.fixture
def console(env):
    _client, db, _headers, _settings, _app = env
    db.add(1)
    db.sql.execute(
        "CREATE TABLE account_security_state(user_id TEXT PRIMARY KEY,state TEXT,revision INTEGER)"
    )
    original = db.execute
    db.state_fault = None
    db.state_hook = None
    db.reads = 0

    def execute(statement, params=None):
        if "sr_staff_account_state" not in str(statement):
            return original(statement, params)
        db.reads += 1
        assert db.depth == 1 and db.timeout == "3000ms"
        if db.state_fault == "sql":
            raise OperationalError("SELECT", {}, Exception(CANARY))
        where = (
            re.search(r" FROM auth.users u LEFT JOIN.*?;", SQL, re.DOTALL)[0]
            .replace("public.", "")
            .replace("auth.", "")
            .replace("u.id=uid", "u.id=:uid")
        )
        row = db.sql.execute(
            "SELECT COALESCE(a.state,'active'),COALESCE(a.revision,1)" + where,
            {"uid": str(params["uid"])},
        ).fetchone()
        value = (
            {
                "status": "ready",
                "state": row[0],
                "revision": row[1],
                "as_of": db.now.isoformat(),
            }
            if row
            else None
        )
        if db.state_fault == "bad":
            value["private"] = CANARY
        if db.state_hook:
            db.state_hook(db)
        return Rows(value)

    db.execute = execute
    return env


def detail(env, query="include=account_security"):
    return get(env, "/" + str(UUID(int=1)) + ("?" + query if query else ""))


def test_default_contract_unchanged_and_explicit_state_read(console):
    db = console[1]
    assert detail(console, "").json()["application_suspension"] == {
        "status": "unavailable",
        "reason_code": "NOT_IMPLEMENTED",
    }
    assert db.reads == 0
    result = detail(console).json()["application_suspension"]
    assert result == {
        "status": "ready",
        "state": "active",
        "revision": 1,
        "as_of": console[1].now.isoformat().replace("+00:00", "Z"),
        "commands_available": False,
    }
    assert db.reads == 1 and db.timeout == "5s"


@pytest.mark.parametrize("state,revision", [("active", 4), ("suspended", 8)])
def test_authoritative_state_revision_not_provider_ban(console, state, revision):
    db = console[1]
    db.sql.execute(
        "INSERT INTO account_security_state VALUES(?,?,?)",
        (str(UUID(int=1)), state, revision),
    )
    console[3].account_lifecycle_enabled = True
    console[3].account_lifecycle_web_origin = "https://synthetic.test"
    value = detail(console).json()
    assert (
        value["application_suspension"]["state"] == state
        and value["application_suspension"]["revision"] == revision
    )
    assert value["application_suspension"]["commands_available"] is True
    assert value["user"]["provider_access"] == "not_banned"


@pytest.mark.parametrize("fault", ["sql", "bad"])
def test_missing_or_malformed_state_is_unavailable_not_active(console, fault, caplog):
    db = console[1]
    db.state_fault = fault
    response = detail(console)
    assert response.status_code == 200 and response.json()[
        "application_suspension"
    ] == {"status": "unavailable", "reason_code": "STATE_UNAVAILABLE"}
    assert CANARY not in response.text + caplog.text and db.timeout == "5s"


@pytest.mark.parametrize(
    "query",
    [
        "include=other",
        "include=account_security&include=account_security",
        "include=account_security&field=email",
    ],
)
def test_closed_optin_queries(console, query):
    assert detail(console, query).status_code == 422 and console[1].reads == 0


@pytest.mark.parametrize("role", ["superadmin", "support", "operations", "finance"])
def test_state_read_no_role_inheritance(console, role):
    console[1].roles = {role}
    assert detail(console).status_code == 403 and console[1].reads == 0


@pytest.mark.parametrize(
    "fault,status", [("roles", 403), ("mfa", 403), ("active", 401)]
)
def test_final_live_denial_not_masked_as_state_unavailable(console, fault, status):
    db = console[1]
    db.state_hook = lambda db: setattr(db, fault, set() if fault == "roles" else False)
    response = detail(console)
    assert (
        response.status_code == status and "application_suspension" not in response.text
    )


def test_offline_read_only_upgrade_and_helper_only_downgrade(console):
    spec = importlib.util.spec_from_file_location(
        "state_read_migration", FILE.with_suffix(".py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    out = io.StringIO()
    ctx = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": out}
    )
    with Operations.context(ctx):
        module.upgrade()
        module.downgrade()
    target = Path(__file__).parents[2] / "output/task57c"
    target.mkdir(parents=True, exist_ok=True)
    (target / "offline-upgrade-downgrade.sql").write_text(out.getvalue())
    assert module.down_revision == "0030_account_lifecycle"
    assert "DROP FUNCTION public.sr_staff_account_state(uuid,uuid)" in out.getvalue()
    assert (
        "ARRAY['security_admin']" in SQL
        and "sr_account_session_state(sid)" in SQL
        and "SET search_path=pg_catalog" in SQL
    )
    assert "GRANT SELECT" not in SQL and not re.search(
        r"\b(UPDATE|DELETE|INSERT)\b", SQL
    )
