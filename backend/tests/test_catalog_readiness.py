"""Task 5.1A synthetic catalog boundary tests; no database/provider mutations."""

import os
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path
from uuid import uuid4

import httpx
import jwt
import pytest
import uvicorn
from fastapi import FastAPI
from test_auth import verifier as _verifier
from test_critical_workflow_boundaries import workflow as _workflow

from app.api.v1 import catalog

verifier = _verifier
workflow = _workflow


@pytest.mark.parametrize(
    "gate,expected",
    [
        ("category", "FUTURE_PRODUCT_DISABLED"),
        ("variants", "PHYSICAL_CATALOG_APPROVAL_REQUIRED"),
        ("template", "PHYSICAL_CATALOG_APPROVAL_REQUIRED"),
        ("image", "VERIFIED_PUBLIC_IMAGE_REQUIRED"),
    ],
)
def test_existing_publication_error_codes_and_guards(
    workflow, monkeypatch, gate, expected
):
    client, db, headers, _, pid = workflow
    app = client.application
    # Test-only approval; no environment or real renderer configuration changes.
    app.state.settings.catalog_approved_templates = ["synthetic-only@1"]
    variant = {
        "id": str(uuid4()),
        "is_active": True,
        "fulfillment_method": "pdf_label",
        "size_mm": 30,
        "currency_code": "PKR",
        "template_key": "synthetic-only",
        "template_version": 1,
    }

    class Query:
        def __init__(self, value):
            self.value = value

        def mappings(self):
            return self

        def one_or_none(self):
            return self.value

        def all(self):
            return self.value

        def scalar_one_or_none(self):
            return self.value

    original = db.execute

    def execute(statement, params=None):
        sql = str(statement)
        if "SELECT slug,is_active" in sql:
            return Query(
                None
                if gate == "category"
                else {"slug": "qr-stickers", "is_active": True}
            )
        if "FROM public.product_variants" in sql:
            return Query(
                []
                if gate == "variants"
                else [{**variant, "template_key": "unapproved"}]
                if gate == "template"
                else [variant]
            )
        if "FROM public.product_images" in sql:
            return Query(None)
        return original(statement, params)

    db.execute = execute
    old = {"id": pid, "lifecycle_status": "draft"}
    monkeypatch.setattr(catalog, "lock", lambda *args: old.copy())
    monkeypatch.setattr(
        catalog,
        "update",
        lambda ctx, table, identifier, values: {"id": identifier, **values},
    )

    def command(context, request, action, body, work):
        catalog.guard(context)
        return work()[0]

    monkeypatch.setattr(catalog, "mutation", command)
    body = {
        "price_per_copy": "100.00",
        "slug": "synthetic-only",
        "name": "Synthetic only",
        "category_id": str(uuid4()),
        "lifecycle_status": "published",
    }
    response = client.request(
        "PATCH", f"/api/v1/admin/products/{pid}", headers=headers(), json=body
    )
    assert response.status_code == 422 and response.json()["error"]["code"] == expected
    assert old["lifecycle_status"] == "draft"
    assert response.headers["cache-control"] == "no-store"
    for role in ("finance", "support"):
        db.roles = {role}
        assert (
            client.request(
                "PATCH", f"/api/v1/admin/products/{pid}", headers=headers(), json=body
            ).status_code
            == 403
        )
    db.roles = {"operations"}
    db.mfa = False
    assert (
        client.request(
            "PATCH", f"/api/v1/admin/products/{pid}", headers=headers(), json=body
        ).status_code
        == 403
    )
    assert (
        client.request("PATCH", f"/api/v1/admin/products/{pid}", json=body).status_code
        == 401
    )
    assert (
        app.openapi()["paths"]["/api/v1/admin/catalog/approved-templates"]["get"][
            "operationId"
        ]
        == "API-339"
    )


def test_catalog_browser():
    root = Path(__file__).parents[2]
    app = FastAPI()
    uid = str(uuid4())
    token = jwt.encode(
        {"sub": uid, "aud": "authenticated", "exp": int(time.time()) + 3600},
        "synthetic-test-key-000000000000000000",
        algorithm="HS256",
    )
    user = {
        "id": uid,
        "aud": "authenticated",
        "role": "authenticated",
        "email": "catalog@synthetic.invalid",
        "email_confirmed_at": "2026-01-01T00:00:00Z",
        "created_at": "2026-01-01T00:00:00Z",
        "user_metadata": {},
        "app_metadata": {},
    }

    @app.get("/auth/v1/user")
    def fixture_user():
        return user

    @app.post("/auth/v1/token")
    def fixture_token():
        return {
            "access_token": token,
            "refresh_token": "synthetic-refresh",
            "expires_in": 3600,
            "token_type": "bearer",
            "user": user,
        }

    @app.get("/api/v1/me/staff-security")
    def staff():
        return {
            "roles": ["operations"],
            "mfa_verified": True,
            "capabilities": ["catalog.manage"],
        }

    @app.get("/api/v1/me")
    def account():
        return {
            "user_id": uid,
            "display_name": "Synthetic",
            "preferred_locale": "en",
            "email_verified": True,
            "masked_contact": {"phone": None},
            "version": "0",
        }

    for port in (3100, 8115):
        with socket.socket() as probe:
            assert probe.connect_ex(("127.0.0.1", port)) != 0, "Isolated port occupied"
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("SAFERETURN_", "QR_TEST_", "TASK"))
    }
    env.update(
        SAFERETURN_API_ORIGIN="http://127.0.0.1:8115",
        SAFERETURN_WEB_ORIGIN="http://127.0.0.1:3100",
        SAFERETURN_SUPABASE_URL="https://fixture.test",
        SAFERETURN_SUPABASE_PUBLISHABLE_KEY="sb_publishable_fixture",
        SAFERETURN_SESSION_SIGNING_KEY="ab" * 32,
        NEXT_TELEMETRY_DISABLED="1",
        PLAYWRIGHT_EXTERNAL_SERVER="1",
        PLAYWRIGHT_CHANNEL="msedge",
    )
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=8115,
            lifespan="off",
            access_log=False,
            log_level="error",
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    process = None
    try:
        with (
            root
            / os.environ.get("TASK51A_OUT", "output/task51a")
            / "frontend-browser.log"
        ).open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                [
                    shutil.which("node"),
                    "--require",
                    str(root / "frontend/tests/qr-fixture-fetch.cjs"),
                    str(root / "frontend/node_modules/next/dist/bin/next"),
                    "start",
                    "--hostname",
                    "127.0.0.1",
                    "--port",
                    "3100",
                ],
                cwd=root / os.environ.get("TASK51A_WEB", "tmp/task51a-web"),
                env=env,
                stdout=log,
                stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            for _ in range(50):
                try:
                    if (
                        httpx.get("http://127.0.0.1:3100/login", timeout=2).status_code
                        == 200
                    ):
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.2)
            else:
                raise AssertionError("Isolated frontend unavailable")
            result = subprocess.run(
                [
                    shutil.which("npm.cmd" if os.name == "nt" else "npm"),
                    "test",
                    "--",
                    os.environ.get("TASK51A_SPEC", "tests/catalog-readiness.spec.ts"),
                    "--workers=1",
                    "--output=../tmp/task51a-discovery-playwright-" + uuid4().hex,
                ],
                cwd=root / "frontend",
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=180,
                check=False,
            )
            print(result.stdout.encode("ascii", "backslashreplace").decode("ascii"))
            if result.returncode:
                print(result.stderr.encode("ascii", "backslashreplace").decode("ascii"))
            assert result.returncode == 0
    finally:
        if process:
            process.terminate()
            process.wait(timeout=15)
        server.should_exit = True
        thread.join(timeout=15)
