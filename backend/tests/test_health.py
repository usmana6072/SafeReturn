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
    assert len(response.headers["x-request-id"]) == 32
    assert response.headers["x-request-id"] != "attacker-controlled"


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
        "/api/v1/me/privacy-consents",
        "/api/v1/me/account-deletion-requests",
        "/api/v1/admin/qr-batches",
        "/api/v1/admin/catalog/categories",
        "/api/v1/admin/catalog/categories/{category_id}",
        "/api/v1/admin/products",
        "/api/v1/admin/products/{product_id}",
        "/api/v1/admin/products/{product_id}/variants",
        "/api/v1/admin/product-variants/{variant_id}",
        "/api/v1/admin/products/{product_id}/images",
        "/api/v1/admin/products/{product_id}/images/{image_id}",
        "/api/v1/public/catalog/categories",
        "/api/v1/public/catalog/featured",
        "/api/v1/public/catalog/products/{product_id}/variants",
        "/api/v1/me/checkout/quotes",
        "/api/v1/me/checkout/quotes/{quote_id}/confirm",
        "/api/v1/me/orders/{order_id}/payment-attempts",
        "/api/v1/me/payment-attempts/{attempt_id}/evidence-uploads",
        "/api/v1/me/payment-attempts/{attempt_id}/evidence-finalize",
        "/api/v1/admin/payment-attempts/{attempt_id}/reviews",
        "/api/v1/admin/orders/{order_id}/payment-attempts",
        "/api/v1/admin/payment-evidence/{evidence_id}",
        "/api/v1/admin/orders/{order_id}/print-jobs",
        "/api/v1/admin/print-jobs/{job_id}",
        "/api/v1/admin/print-jobs/{job_id}/qa",
        "/api/v1/admin/print-downloads",
        "/api/v1/me/orders/{order_id}/print-summary",
        "/api/v1/admin/print-artifacts/{artifact_id}/download-grants",
        "/api/v1/admin/tag-pairs/{pair_id}/print-qa",
        "/api/v1/me/orders",
        "/api/v1/me/orders/{order_id}",
        "/api/v1/me/orders/{order_id}/shipments",
        "/api/v1/admin/orders/ready-to-ship",
        "/api/v1/admin/orders/{order_id}",
        "/api/v1/admin/shipments",
        "/api/v1/admin/shipments/{shipment_id}",
        "/api/v1/admin/finance/sheet-sync",
        "/api/v1/admin/finance/sheet-sync/{sync_id}/retry",
        "/api/v1/admin/storage/artifacts",
        "/api/v1/admin/storage/artifacts/{artifact_id}/retention-holds",
        "/api/v1/admin/storage/artifacts/{artifact_id}/cleanup-retry",
        "/api/v1/me/finder-messages",
        "/api/v1/me/finder-messages/{message_id}",
        "/api/v1/health/live",
        "/api/v1/health/ready",
        "/api/v1/me",
        "/api/v1/public/qr/{token}",
        "/api/v1/public/qr/{token}/activation-context",
        "/api/v1/public/qr/{token}/contact-reveals",
        "/api/v1/public/qr/{token}/finder-messages",
        "/api/v1/public/qr/{token}/messages",
        "/api/v1/public/qr/{token}/whatsapp-link",
        "/api/v1/public/products",
        "/api/v1/public/products/{sku}",
        "/api/v1/me/tag-pairs/activation-intents",
        "/api/v1/me/tag-pairs/activations",
        "/api/v1/me/tag-pairs",
        "/api/v1/me/tag-pairs/{pair_id}",
        "/api/v1/me/qr",
        "/api/v1/me/qr/{qr_id}",
        "/api/v1/me/qr/{qr_id}/lost-profile",
        "/api/v1/me/qr/{qr_id}/ice-profile",
        "/api/v1/me/qr/{qr_id}/ice-contacts",
        "/api/v1/me/qr/{qr_id}/ice-contacts/{contact_id}",
        "/api/v1/me/qr/{qr_id}/contact-preferences",
    }
    inventory = schema["paths"]["/api/v1/admin/qr-batches"]["post"]
    for path, operation in (
        ("/public/qr/{token}", "API-010"),
        ("/public/products", "API-003"),
        ("/public/products/{sku}", "API-004"),
        ("/me/tag-pairs", "API-030"),
        ("/me/tag-pairs/{pair_id}", "API-031"),
        ("/me/qr", "API-205"),
        ("/me/qr/{qr_id}", "API-206"),
    ):
        route = schema["paths"]["/api/v1" + path]["get"]
        assert route["operationId"] == operation
        if path in {"/public/qr/{token}", "/public/products", "/public/products/{sku}"}:
            assert "security" not in route
            continue
        assert route["security"] == [{"SupabaseAccessToken": []}]
        assert (
            "$ref" in route["responses"]["200"]["content"]["application/json"]["schema"]
        )
    assert (
        schema["paths"]["/api/v1/me/checkout/quotes"]["post"]["operationId"]
        == "API-203"
    )
    assert (
        schema["paths"]["/api/v1/me/checkout/quotes/{quote_id}/confirm"]["post"][
            "operationId"
        ]
        == "API-204"
    )
    assert (
        schema["paths"]["/api/v1/me/orders/{order_id}/payment-attempts"]["get"][
            "operationId"
        ]
        == "API-209"
    )
    assert (
        schema["paths"]["/api/v1/me/payment-attempts/{attempt_id}/evidence-uploads"][
            "post"
        ]["operationId"]
        == "API-211"
    )
    assert (
        schema["paths"]["/api/v1/me/payment-attempts/{attempt_id}/evidence-finalize"][
            "post"
        ]["operationId"]
        == "API-212"
    )
    assert (
        schema["paths"]["/api/v1/admin/payment-attempts/{attempt_id}/reviews"]["post"][
            "operationId"
        ]
        == "API-241"
    )
    assert (
        schema["paths"]["/api/v1/admin/orders/{order_id}/print-jobs"]["post"][
            "operationId"
        ]
        == "API-234"
    )
    assert (
        schema["paths"]["/api/v1/admin/print-jobs/{job_id}"]["get"]["operationId"]
        == "API-235"
    )
    assert (
        schema["paths"]["/api/v1/admin/print-artifacts/{artifact_id}/download-grants"][
            "post"
        ]["operationId"]
        == "API-236"
    )
    assert (
        schema["paths"]["/api/v1/admin/tag-pairs/{pair_id}/print-qa"]["post"][
            "operationId"
        ]
        == "API-094"
    )
    assert schema["paths"]["/api/v1/me/orders"]["get"]["operationId"] == "API-061"
    assert (
        schema["paths"]["/api/v1/me/orders/{order_id}"]["get"]["operationId"]
        == "API-062"
    )
    assert (
        schema["paths"]["/api/v1/me/orders/{order_id}/shipments"]["get"]["operationId"]
        == "API-066"
    )
    assert (
        schema["paths"]["/api/v1/admin/orders/{order_id}"]["get"]["operationId"]
        == "API-081"
    )
    assert (
        schema["paths"]["/api/v1/admin/orders/ready-to-ship"]["get"]["operationId"]
        == "API-232"
    )
    assert (
        schema["paths"]["/api/v1/admin/shipments"]["post"]["operationId"] == "API-095"
    )
    assert (
        schema["paths"]["/api/v1/admin/shipments/{shipment_id}"]["patch"]["operationId"]
        == "API-096"
    )
    assert (
        schema["paths"]["/api/v1/admin/finance/sheet-sync"]["get"]["operationId"]
        == "API-238"
    )
    assert (
        schema["paths"]["/api/v1/admin/finance/sheet-sync/{sync_id}/retry"]["post"][
            "operationId"
        ]
        == "API-239"
    )
    assert (
        schema["paths"]["/api/v1/admin/storage/artifacts"]["get"]["operationId"]
        == "API-242"
    )
    assert (
        schema["paths"][
            "/api/v1/admin/storage/artifacts/{artifact_id}/retention-holds"
        ]["post"]["operationId"]
        == "API-243"
    )
    assert (
        schema["paths"][
            "/api/v1/admin/storage/artifacts/{artifact_id}/retention-holds"
        ]["delete"]["operationId"]
        == "API-244"
    )
    assert (
        schema["paths"]["/api/v1/admin/storage/artifacts/{artifact_id}/cleanup-retry"][
            "post"
        ]["operationId"]
        == "API-245"
    )
    assert (
        schema["paths"]["/api/v1/me/finder-messages"]["get"]["operationId"] == "API-050"
    )
    assert (
        schema["paths"]["/api/v1/me/finder-messages/{message_id}"]["get"]["operationId"]
        == "API-051"
    )
    assert (
        schema["paths"]["/api/v1/me/finder-messages/{message_id}"]["patch"][
            "operationId"
        ]
        == "API-052"
    )
    assert (
        schema["paths"]["/api/v1/me/finder-messages/{message_id}"]["delete"][
            "operationId"
        ]
        == "API-053"
    )
    assert inventory["operationId"] == "API-090"
    assert inventory["security"] == [{"SupabaseAccessToken": []}]
    assert "201" in inventory["responses"]
    assert schema["paths"]["/api/v1/health/live"]["get"]["operationId"] == "API-001"
    public_qr = schema["paths"]["/api/v1/public/qr/{token}"]["get"]
    assert public_qr["operationId"] == "API-010"
    assert "security" not in public_qr
    assert (
        schema["paths"]["/api/v1/public/qr/{token}/contact-reveals"]["post"][
            "operationId"
        ]
        == "API-012"
    )
    assert (
        schema["paths"]["/api/v1/public/qr/{token}/whatsapp-link"]["post"][
            "operationId"
        ]
        == "API-013"
    )
    assert (
        schema["paths"]["/api/v1/public/qr/{token}/finder-messages"]["post"][
            "operationId"
        ]
        == "API-015"
    )
    ready = schema["paths"]["/api/v1/health/ready"]["get"]
    assert ready["operationId"] == "API-002"
    assert ready["security"] == [{"InternalReadinessProbe": []}]
    assert {"200", "401", "404", "503"} <= set(ready["responses"])
    assert probe.post("/api/v1/health/live").status_code == 405
    assert probe.get("/api/v1/public/products").status_code == 503


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


def test_account_privacy_route_contract():
    from app.core.config import Settings
    from app.main import create_app

    paths = create_app(Settings()).openapi()["paths"]
    assert paths["/api/v1/me/privacy-consents"]["get"]["operationId"] == "API-022"
    assert (
        paths["/api/v1/me/account-deletion-requests"]["post"]["operationId"]
        == "API-023"
    )
