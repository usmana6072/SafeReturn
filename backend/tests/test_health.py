import asyncio
from unittest.mock import MagicMock

import httpx
from pydantic import SecretStr

from app.core.config import Settings
from app.db.session import Database, get_database
from app.main import create_app


class ASGIClient:
    def __init__(self, application):
        self.application = application

    def request(self, method, path, **kwargs):
        async def send():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=self.application),
                base_url="http://test",
            ) as session:
                return await session.request(method, path, **kwargs)

        return asyncio.run(send())

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)


def client(token=None):
    return ASGIClient(create_app(Settings(readiness_token=token)))


def test_liveness_is_public_and_minimal():
    response = client().get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_disabled_without_configured_token():
    assert client().get("/api/v1/health/ready").status_code == 404
    assert client(SecretStr("")).get("/api/v1/health/ready").status_code == 404


def test_readiness_rejects_unauthenticated_and_wrong_token():
    probe = client(SecretStr("synthetic-probe-token"))
    for headers in (
        {},
        {"Authorization": "Bearer wrong"},
        {"Authorization": "Basic x"},
    ):
        response = probe.get("/api/v1/health/ready", headers=headers)
        assert response.status_code == 401
        assert "synthetic-probe-token" not in response.text


def test_authorized_readiness_reports_unavailable_database():
    response = client(SecretStr("synthetic-probe-token")).get(
        "/api/v1/health/ready",
        headers={"Authorization": "Bearer synthetic-probe-token"},
    )
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "database": "unavailable"}


def test_contract_and_unimplemented_routes():
    probe = client()
    schema = probe.get("/openapi.json").json()
    assert set(schema["paths"]) == {
        "/api/v1/admin/qr-batches",
        "/api/v1/health/live",
        "/api/v1/health/ready",
        "/api/v1/me",
        "/api/v1/public/qr/{token}/activation-context",
        "/api/v1/me/tag-pairs/activation-intents",
        "/api/v1/me/tag-pairs/activations",
        "/api/v1/me/qr/{qr_id}/lost-profile",
        "/api/v1/me/qr/{qr_id}/ice-profile",
        "/api/v1/me/qr/{qr_id}/ice-contacts",
        "/api/v1/me/qr/{qr_id}/ice-contacts/{contact_id}",
        "/api/v1/me/qr/{qr_id}/contact-preferences",
    }
    inventory = schema["paths"]["/api/v1/admin/qr-batches"]["post"]
    assert inventory["operationId"] == "API-090"
    assert inventory["security"] == [{"SupabaseAccessToken": []}]
    assert "201" in inventory["responses"]
    assert schema["paths"]["/api/v1/health/live"]["get"]["operationId"] == "API-001"
    ready = schema["paths"]["/api/v1/health/ready"]["get"]
    assert ready["operationId"] == "API-002"
    assert ready["security"] == [{"InternalReadinessProbe": []}]
    assert {"200", "401", "404", "503"} <= set(ready["responses"])
    assert probe.post("/api/v1/health/live").status_code == 405
    assert probe.get("/api/v1/public/products").status_code == 404


def test_authorized_readiness_uses_database_and_never_probes_for_wrong_token():
    database = MagicMock(spec=Database)
    database.is_available.return_value = True
    app = create_app(Settings(readiness_token=SecretStr("synthetic-probe-token")))
    app.dependency_overrides[get_database] = lambda: database
    probe = ASGIClient(app)
    assert probe.get("/api/v1/health/ready").status_code == 401
    database.is_available.assert_not_called()
    response = probe.get(
        "/api/v1/health/ready",
        headers={"Authorization": "Bearer synthetic-probe-token"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}
    assert response.headers["cache-control"] == "no-store"
    database.is_available.return_value = False
    response = probe.get(
        "/api/v1/health/ready",
        headers={"Authorization": "Bearer synthetic-probe-token"},
    )
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "database": "unavailable"}
