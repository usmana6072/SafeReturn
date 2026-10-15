"""Explicit live login/refresh/API/session-revocation check for a dedicated test user.

Load ignored .env explicitly with python-dotenv CLI. Never logs tokens, email,
passwords or provider response bodies. Does not create users or domain data.
"""

import os
import sys

import httpx
from pydantic import SecretStr
from sqlalchemy import text

from app.core.auth import JWTVerifier
from app.core.config import Settings
from app.db.session import Database
from app.main import create_app


def main():
    # Test helper import only: ASGIClient executes the actual FastAPI routes.
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent / "tests"))
    from test_health import ASGIClient

    email = os.environ.get("SAFERETURN_AUTH_TEST_EMAIL")
    password = os.environ.get("SAFERETURN_AUTH_TEST_PASSWORD")
    key = os.environ.get("SAFERETURN_SUPABASE_PUBLISHABLE_KEY")
    if not email or not password or not key:
        raise RuntimeError(
            "Configure the dedicated confirmed Auth test account in ignored .env"
        )
    settings = Settings()
    if not settings.supabase_url:
        raise RuntimeError("Configure the development Supabase origin")
    # Inspect the existing database before any managed provider test session setup.
    inspection = Database.from_settings(
        Settings(database_url=SecretStr(os.environ["SAFERETURN_TEST_DATABASE_URL"]))
    )
    try:
        with inspection.engine.connect() as connection:
            if (
                connection.execute(
                    text("SELECT version_num FROM public.alembic_version")
                ).scalar_one()
                != "0005_account_session_guard"
            ):
                raise RuntimeError(
                    "Reconcile installed migration head before live verification"
                )
    finally:
        inspection.close()
    database = Database.from_settings(
        settings
    )  # restricted API URL, never test/admin role
    verifier = JWTVerifier(settings)
    application = create_app(settings, verifier=verifier)
    application.state.database, application.state.jwt_verifier = database, verifier
    client = ASGIClient(application)
    access = None
    with httpx.Client(
        timeout=10, follow_redirects=False, trust_env=False, headers={"apikey": key}
    ) as provider:
        base = settings.supabase_url.rstrip("/") + "/auth/v1"
        try:
            result = provider.post(
                base + "/token?grant_type=password",
                json={"email": email, "password": password},
            )
            if result.status_code != 200:
                raise RuntimeError(
                    "Test login failed; check confirmed dedicated account/configuration"
                )
            session = result.json()
            access = session["access_token"]
            actor = verifier.verify(access)
            response = client.get(
                "/api/v1/me", headers={"Authorization": "Bearer " + access}
            )
            if (
                response.status_code != 200
                or response.json()["user_id"] != str(actor.user_id)
                or not response.json()["email_verified"]
            ):
                raise RuntimeError(
                    "Restricted account API did not verify the live test identity"
                )
            refreshed = provider.post(
                base + "/token?grant_type=refresh_token",
                json={"refresh_token": session["refresh_token"]},
            )
            if refreshed.status_code != 200:
                raise RuntimeError("Live session refresh failed")
            access = refreshed.json()["access_token"]
            renewed = verifier.verify(access)
            if (
                renewed.user_id != actor.user_id
                or renewed.session_id != actor.session_id
            ):
                raise RuntimeError("Unexpected refreshed identity/session")
            if (
                client.get(
                    "/api/v1/me", headers={"Authorization": "Bearer " + access}
                ).status_code
                != 200
            ):
                raise RuntimeError("Refreshed account API verification failed")
            revoked = provider.post(
                base + "/logout?scope=local",
                headers={"Authorization": "Bearer " + access},
            )
            if revoked.status_code not in (200, 204):
                raise RuntimeError("Local test-session logout failed")
            if (
                client.get(
                    "/api/v1/me", headers={"Authorization": "Bearer " + access}
                ).status_code
                != 401
            ):
                raise RuntimeError("Revoked live session remained authorized")
            print(
                "PASS: live login, signed identity, restricted account API, refresh and local-session revocation. No domain writes."
            )
        finally:
            try:
                if access:
                    cleanup = provider.post(
                        base + "/logout?scope=local",
                        headers={"Authorization": "Bearer " + access},
                    )
                    if cleanup.status_code not in (200, 204, 401, 403, 404):
                        raise RuntimeError("Test-session cleanup requires retry")
            finally:
                verifier.close()
                if database:
                    database.close()


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 -- CLI boundary must never expose provider credentials
        raise SystemExit(
            "Live Auth check did not pass. Check dedicated account/configuration; no credentials or provider details displayed."
        ) from None
