"""Offline integration boundaries; no database/provider readiness claim."""

import json
import re
import warnings
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from test_health import ASGIClient

from app.api.v1.checkout import legacy_order
from app.core.config import Settings
from app.main import create_app


def test_openapi_operation_ids_and_local_references_are_valid():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        document = create_app(Settings()).openapi()
    operations = [
        operation
        for item in document["paths"].values()
        for method, operation in item.items()
        if method in {"get", "post", "put", "patch", "delete", "options", "head"}
    ]
    identities = [operation["operationId"] for operation in operations]
    assert len(identities) == len(set(identities))
    for reference in re.findall(r'"\$ref":\s*"(#[^"]+)"', json.dumps(document)):
        target = document
        for segment in reference[2:].split("/"):
            target = target[segment.replace("~1", "/").replace("~0", "~")]


def test_legacy_order_contract_documents_quote_required_rejection():
    operation = create_app(Settings()).openapi()["paths"]["/api/v1/me/orders"]["post"]
    assert operation["operationId"] == "API-060"
    assert "409" in operation["responses"]
    assert "200" not in operation["responses"]
    with pytest.raises(HTTPException) as rejected:
        legacy_order(SimpleNamespace(email_verified=True))
    assert rejected.value.status_code == 409
    assert rejected.value.detail == {"code": "QUOTE_REQUIRED"}


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/me",
        "/api/v1/me/orders",
        "/api/v1/me/finder-messages",
        "/api/v1/admin/support-cases",
        "/api/v1/admin/products",
        "/api/v1/admin/inventory/summary",
    ],
)
def test_initial_protected_reads_reject_missing_token_before_database(path):
    response = ASGIClient(create_app(Settings())).get(path)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert "no-store" in response.headers["cache-control"]
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]


def test_public_configuration_does_not_advertise_unapproved_capabilities():
    response = ASGIClient(create_app(Settings())).get("/api/v1/public/config")
    assert response.status_code == 200
    assert "no-store" in response.headers["cache-control"]
    # Default policy/contact metadata must remain unavailable during integration.
    assert "unavailable" in response.text


def test_api_does_not_enable_cross_origin_credentials_implicitly():
    response = ASGIClient(create_app(Settings())).request(
        "OPTIONS",
        "/api/v1/me",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert "access-control-allow-origin" not in response.headers
    assert "access-control-allow-credentials" not in response.headers
