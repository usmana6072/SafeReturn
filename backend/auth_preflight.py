"""Read-only development Auth/JWKS metadata; never print credentials or users."""

import os

import httpx
from sqlalchemy import create_engine, text

from app.db.session import database_url

url = database_url(os.environ["SAFERETURN_TEST_DATABASE_URL"])
engine = create_engine(url, hide_parameters=True)
try:
    with engine.connect() as c:
        print(
            "Installed revision:",
            c.execute(
                text("SELECT version_num FROM public.alembic_version")
            ).scalar_one(),
        )
        for table in ("users", "sessions"):
            columns = c.execute(
                text(
                    "SELECT column_name,data_type FROM information_schema.columns WHERE table_schema='auth' AND table_name=:table ORDER BY ordinal_position"
                ),
                {"table": table},
            ).all()
            print("Auth", table, "column metadata:", columns)
        print(
            "Existing guard:",
            c.execute(
                text(
                    "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname='sr_account_session_state'"
                )
            ).scalar_one(),
        )
    project = url.username.split(".")[-1]
    assert project.isalnum() and len(project) == 20
    origin = f"https://{project}.supabase.co"
    response = httpx.get(origin + "/auth/v1/.well-known/jwks.json", timeout=10)
    response.raise_for_status()
    print(
        "Development JWKS key algorithms:",
        [key.get("alg") for key in response.json()["keys"]],
    )
finally:
    engine.dispose()
