"""Provision only new development login credentials; never rotate existing ones.

Run explicitly: python -m app.db.provision_runtime --env-file .env
Private URLs stay in the ignored file. No credential values reach stdout/errors.
"""

import argparse
import secrets
import subprocess
from pathlib import Path

from dotenv import dotenv_values, set_key
from pydantic import SecretStr
from sqlalchemy import text

from app.core.config import Settings
from app.db.session import Database, database_url


def provision(path: Path):
    if subprocess.run(
        ["git", "check-ignore", "--quiet", str(path)], check=False
    ).returncode:
        raise ValueError("Runtime credentials require a Git-ignored environment file")
    values = dotenv_values(path)
    migration = values.get("SAFERETURN_MIGRATION_DATABASE_URL") or values.get(
        "SAFERETURN_DATABASE_URL"
    )
    if not migration:
        raise ValueError("Development migration configuration required")
    source = database_url(migration)
    db = Database.from_settings(Settings(database_url=SecretStr(migration)))
    try:
        with db.engine.connect() as c:
            if c.execute(
                text("SELECT version_num FROM public.alembic_version")
            ).scalar_one() not in {"0003_workflows_security", "0004_runtime_privacy"}:
                raise ValueError("Verified workflow revision required")
        keys = {
            "safereturn_api_login": "SAFERETURN_API_DATABASE_URL",
            "safereturn_worker_login": "SAFERETURN_WORKER_DATABASE_URL",
        }
        if any(values.get(key) for key in keys.values()):
            if not all(values.get(key) for key in keys.values()):
                raise ValueError(
                    "Partial provisioning requires manual recovery; no credential rotation"
                )
            urls = {role: database_url(values[key]) for role, key in keys.items()}
        else:
            urls = {}
            for role, key in keys.items():
                # Shared Supabase pooler requires role.project_ref; direct hosts
                # use the role alone. Preserve the inspected host, TLS and DB.
                username = role
                if source.host.endswith(".pooler.supabase.com"):
                    _, sep, project_ref = source.username.partition(".")
                    if not sep or not project_ref:
                        raise ValueError("Invalid shared-pooler configuration")
                    username += "." + project_ref
                urls[role] = source.set(
                    username=username, password=secrets.token_urlsafe(40)
                )
            # Save before assigning passwords: a interrupted run never silently
            # invents replacement credentials. Existing primary URL stays live.
            set_key(str(path), "SAFERETURN_MIGRATION_DATABASE_URL", migration)
            for role, key in keys.items():
                set_key(
                    str(path), key, urls[role].render_as_string(hide_password=False)
                )
            with db.engine.begin() as c:
                for role, url in urls.items():
                    c.execute(
                        text(
                            "SELECT set_config('safereturn.provision_password',:password,true)"
                        ),
                        {"password": url.password},
                    )
                    # Role names are a closed local allowlist; password is quoted
                    # by PostgreSQL format(%L), never interpolated into shell/SQL.
                    statement = (
                        "DO $$ BEGIN EXECUTE pg_catalog.format('ALTER ROLE "
                        + role
                        + " PASSWORD %L',pg_catalog.current_setting('safereturn.provision_password')); END $$;"
                    )
                    c.execute(text(statement))
        for role, url in urls.items():
            runtime = Database.from_settings(
                Settings(
                    database_url=SecretStr(url.render_as_string(hide_password=False))
                )
            )
            try:
                with runtime.engine.connect() as c:
                    flags = c.execute(
                        text(
                            "SELECT rolname,rolsuper,rolbypassrls,rolcreaterole,rolcreatedb FROM pg_roles WHERE rolname=session_user"
                        )
                    ).one()
                    if flags != (role, False, False, False, False):
                        raise ValueError(
                            "Runtime login must have restricted role attributes"
                        )
                    if c.execute(
                        text(
                            "SELECT has_schema_privilege(session_user,'public','CREATE')"
                        )
                    ).scalar_one():
                        raise ValueError("Runtime login must not create public objects")
                    expected = (
                        "safereturn_api"
                        if role.endswith("api_login")
                        else "safereturn_worker"
                    )
                    other = (
                        "safereturn_worker"
                        if expected == "safereturn_api"
                        else "safereturn_api"
                    )
                    if c.execute(
                        text("SELECT pg_has_role(session_user,:other,'MEMBER')"),
                        {"other": other},
                    ).scalar_one():
                        raise ValueError("Runtime logins must remain separated")
                    c.execute(text("SET LOCAL ROLE " + expected))
                    assert (
                        c.execute(text("SELECT current_user")).scalar_one() == expected
                    )
            finally:
                runtime.close()
        set_key(
            str(path),
            "SAFERETURN_DATABASE_URL",
            urls["safereturn_api_login"].render_as_string(hide_password=False),
        )
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    args = parser.parse_args()
    try:
        provision(args.env_file)
    except Exception as error:  # noqa: BLE001 -- terminal secrecy boundary
        print(
            "Runtime provisioning failed:",
            type(error).__name__,
            "(credentials suppressed)",
        )
        raise SystemExit(1) from None
    print(
        "Restricted API/worker logins verified; ignored development configuration updated"
    )


if __name__ == "__main__":
    main()
