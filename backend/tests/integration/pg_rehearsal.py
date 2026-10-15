"""Isolated real-PostgreSQL rehearsal of the *actual* Alembic chain.

Only namespace identifiers are translated at the driver boundary. Constraints,
triggers, policies, grants, and revision control flow are unchanged. No installed
domain or Auth rows are used. Temporary roles cannot authenticate (NOLOGIN).
Cleanup is confined to fresh UUID namespaces and roles created by this fixture.
"""

import os
import re
import uuid
from contextlib import contextmanager
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, event, text

from alembic import command
from app.db.session import database_url


def metadata(c, expected_revision=None):
    """Read target metadata before any setup; never disclose the URL."""
    revision = c.execute(
        text("SELECT version_num FROM public.alembic_version")
    ).scalar_one()
    assert revision == (
        expected_revision
        or ScriptDirectory.from_config(
            Config(str(Path(__file__).parents[2] / "alembic.ini"))
        ).get_current_head()
    ), "Inspect/reconcile unexpected development head"
    tables = c.execute(
        text(
            "SELECT relname,relrowsecurity FROM pg_class JOIN pg_namespace n ON n.oid=relnamespace WHERE n.nspname='public' AND relkind='r' AND relname<>'alembic_version' ORDER BY relname"
        )
    ).all()
    roles = c.execute(
        text(
            "SELECT rolname,rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname LIKE 'safereturn_%' ORDER BY rolname"
        )
    ).all()
    assert len(tables) == 40 and all(row[1] for row in tables)
    runtime = [
        row
        for row in roles
        if row[0]
        in {
            "safereturn_api",
            "safereturn_worker",
            "safereturn_api_login",
            "safereturn_worker_login",
        }
    ]
    assert len(runtime) == 4 and all(not any(row[1:]) for row in runtime)
    counts = {
        name: c.execute(text(f'SELECT count(*) FROM public."{name}"')).scalar_one()
        for name, _ in tables
    }
    return revision, tables, roles, counts


def catalog(c):
    """Structural definitions, independent of OIDs/owners and namespace names."""
    queries = {
        "constraints": "SELECT r.relname,k.conname,pg_get_constraintdef(k.oid) FROM pg_constraint k JOIN pg_class r ON r.oid=k.conrelid JOIN pg_namespace n ON n.oid=r.relnamespace WHERE n.nspname='public'",
        "indexes": "SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname='public'",
        "triggers": "SELECT r.relname,t.tgname,pg_get_triggerdef(t.oid) FROM pg_trigger t JOIN pg_class r ON r.oid=t.tgrelid JOIN pg_namespace n ON n.oid=r.relnamespace WHERE n.nspname='public' AND NOT t.tgisinternal",
        "policies": "SELECT tablename,policyname,roles::text,cmd,qual,with_check FROM pg_policies WHERE schemaname='public'",
        "columns": "SELECT table_name,column_name,data_type,is_nullable,column_default FROM information_schema.columns WHERE table_schema='public'",
        "functions": "SELECT p.proname,pg_get_functiondef(p.oid) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname LIKE 'sr_%'",
    }
    return {
        key: sorted([tuple(row) for row in c.execute(text(query)).all()])
        for key, query in queries.items()
    }


class Rehearsal:
    def __init__(self, engine, schema, auth, roles, installed_catalog):
        self.engine, self.schema, self.auth, self.roles = engine, schema, auth, roles
        self.installed_catalog = installed_catalog

    def assert_catalog(self, c):
        actual = catalog(c)
        replacements = {
            self.schema: "public",
            self.auth: "auth",
            **{new: old for old, new in self.roles.items()},
        }

        def normalize(value):
            if value is None:
                return value
            for old, new in replacements.items():
                value = re.sub(r"\b" + old + r"\b", new, value)
            return value

        for kind, rows in actual.items():
            assert (
                sorted([tuple(normalize(value) for value in row) for row in rows])
                == self.installed_catalog[kind]
            ), kind

    @contextmanager
    def connect(self):
        with self.engine.connect() as c:
            c.execute(text(f"SET search_path TO {self.schema},pg_catalog"))
            c.commit()
            try:
                yield c
            finally:
                c.rollback()

    def upgrade(self, c, revision="head"):
        if not c.in_transaction():
            c.begin()  # Caller owns COMMIT/ROLLBACK, including transactional DDL.
        cfg = Config(str(Path(__file__).parents[2] / "alembic.ini"))
        cfg.attributes["connection"] = c
        command.upgrade(cfg, revision)


@contextmanager
def rehearsal():
    url = os.environ.get("SAFERETURN_TEST_DATABASE_URL")
    if not url:
        raise RuntimeError(
            "Explicitly load development backend/.env; real PostgreSQL required"
        )
    engine = create_engine(
        database_url(url),
        hide_parameters=True,
        pool_size=4,
        max_overflow=0,
        connect_args={
            "connect_timeout": 10,
            "keepalives": 1,
            "keepalives_idle": 10,
            "keepalives_interval": 5,
            "keepalives_count": 3,
            "tcp_user_timeout": 30000,
            "options": "-c statement_timeout=20000 -c lock_timeout=8000",
        },
    )
    suffix = uuid.uuid4().hex
    schema, auth = "sr15_" + suffix, "sr15_auth_" + suffix
    original_roles = [
        "safereturn_api",
        "safereturn_worker",
        "safereturn_api_login",
        "safereturn_worker_login",
    ]
    roles = {
        name: "sr15_" + suffix + "_" + name.removeprefix("safereturn_")
        for name in original_roles
    }
    baseline = None
    created = False
    try:
        with engine.begin() as c:
            baseline = metadata(c)
            installed_catalog = catalog(c)
            assert not c.execute(
                text(
                    "SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname=ANY(:names))"
                ),
                {"names": [schema, auth]},
            ).scalar_one()
            assert not c.execute(
                text("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=ANY(:names))"),
                {"names": list(roles.values())},
            ).scalar_one()
            c.execute(text(f"CREATE SCHEMA {schema}"))
            c.execute(text(f"CREATE SCHEMA {auth}"))
            c.execute(
                text(
                    f"CREATE TABLE {auth}.users(id uuid PRIMARY KEY,email_confirmed_at timestamptz,deleted_at timestamptz,banned_until timestamptz,is_anonymous boolean DEFAULT false)"
                )
            )
            c.execute(
                text(
                    f"CREATE TABLE {auth}.sessions(id uuid PRIMARY KEY,user_id uuid REFERENCES {auth}.users(id),aal text,not_after timestamptz)"
                )
            )
        created = True

        def translate(value):
            if isinstance(value, str):
                # Hyphenated consent identifiers (ice-public-v1, wa-public-v1)
                # are domain values, not schema identifiers. Preserve them.
                value = re.sub(r"(?<![\w-])public(?![\w-])", schema, value)
                value = re.sub(r"(?<![\w-])auth(?![\w-])", auth, value)
                for old, new in roles.items():
                    value = re.sub(r"\b" + old + r"\b", new, value)
                # Temporary logins are never provisioned or enabled.
                return re.sub(r"\bLOGIN\b", "NOLOGIN", value)
            if isinstance(value, dict):
                return {key: translate(item) for key, item in value.items()}
            if isinstance(value, (tuple, list)):
                return type(value)(translate(item) for item in value)
            return value

        def rewrite(c, cursor, statement, parameters, context, executemany):
            return translate(statement), translate(parameters)

        event.listen(engine, "before_cursor_execute", rewrite, retval=True)
        try:
            yield Rehearsal(engine, schema, auth, roles, installed_catalog)
        finally:
            event.remove(engine, "before_cursor_execute", rewrite)
    finally:
        try:
            if created:
                # Names are generated internally, checked absent, and never accepted
                # from env/input. Verify ownership before removing only these objects.
                with engine.begin() as c:
                    c.execute(text("SET LOCAL search_path=public,pg_catalog"))
                    for name in (schema, auth):
                        assert c.execute(
                            text(
                                "SELECT nspowner=(SELECT oid FROM pg_roles WHERE rolname=current_user) FROM pg_namespace WHERE nspname=:name"
                            ),
                            {"name": name},
                        ).scalar_one()
                    c.execute(text(f"DROP SCHEMA {schema} CASCADE"))
                    c.execute(text(f"DROP SCHEMA {auth} CASCADE"))
                    for name in roles.values():
                        if c.execute(
                            text(
                                "SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=:name)"
                            ),
                            {"name": name},
                        ).scalar_one():
                            c.execute(text(f"DROP ROLE {name}"))
                with engine.connect() as c:
                    c.execute(text("SET search_path=public,pg_catalog"))
                    assert metadata(c) == baseline, (
                        "Installed metadata/data changed during rehearsal"
                    )
                    assert catalog(c) == installed_catalog
                    assert (
                        c.execute(
                            text(
                                "SELECT count(*) FROM pg_namespace WHERE nspname=ANY(:names)"
                            ),
                            {"names": [schema, auth]},
                        ).scalar_one()
                        == 0
                    )
                    assert (
                        c.execute(
                            text(
                                "SELECT count(*) FROM pg_roles WHERE rolname=ANY(:names)"
                            ),
                            {"names": list(roles.values())},
                        ).scalar_one()
                        == 0
                    )
        finally:
            engine.dispose()


if __name__ == "__main__":
    engine = create_engine(
        database_url(os.environ["SAFERETURN_TEST_DATABASE_URL"]), hide_parameters=True
    )
    try:
        with engine.connect() as c:
            revision, tables, roles, counts = metadata(c)
            print(
                f"Installed head: {revision}; domain tables: {len(tables)}; RLS: {sum(row[1] for row in tables)}; SafeReturn roles: {len(roles)}; domain rows: {sum(counts.values())}"
            )
            print("PostgreSQL:", c.execute(text("SHOW server_version")).scalar_one())
            schemas = c.execute(
                text(
                    "SELECT count(*) FROM pg_namespace WHERE starts_with(nspname,'sr15_')"
                )
            ).scalar_one()
            temporary_roles = c.execute(
                text("SELECT count(*) FROM pg_roles WHERE starts_with(rolname,'sr15_')")
            ).scalar_one()
            print(
                f"Temporary rehearsal schemas: {schemas}; temporary roles: {temporary_roles}"
            )
    finally:
        engine.dispose()
