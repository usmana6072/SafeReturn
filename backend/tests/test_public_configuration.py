"""Synthetic API005 ASGI/metadata checks; no lifespan, network or database."""

import json
from typing import get_args

import pytest
from pydantic import SecretStr, ValidationError
from test_health import ASGIClient

from app.api.v1.profiles import ContactEdit, ICEEdit, PreferenceEdit
from app.api.v1.public_actions import FinderLocation, FinderMessageRequest
from app.core import public_configuration as public
from app.core.abuse_intake import Report
from app.core.config import Settings
from app.main import create_app

URL = "/api/v1/public/config"
CANARY = "SECRET-CANARY-44D"


@pytest.fixture
def client():
    app = create_app(Settings())

    class Forbidden:
        def __getattr__(self, name):
            raise AssertionError("Private dependency accessed")

    app.state.database = Forbidden()
    app.state.jwt_verifier = Forbidden()
    app.state.settings = Forbidden()
    return ASGIClient(app)


def record(*, approved=True, en=True, ur=False):
    return public.ReviewedPolicy(
        version="synthetic-v1",
        approved=approved,
        en=public.ReviewedLink(url="https://example.invalid/en", approved=en),
        ur=public.ReviewedLink(url="https://example.invalid/ur", approved=ur),
    )


def metadata(policy=None, support=None):
    return public.ReviewedMetadata(privacy=policy, terms=policy, support=support)


def cache(response):
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-content-type-options"] == "nosniff"
    for key in ("etag", "last-modified", "set-cookie", "cdn-cache-control"):
        assert key not in response.headers


def test_public_empty_config(client):
    response = client.get(URL)
    assert response.status_code == 200
    cache(response)
    body = response.json()
    public.PublicConfiguration.model_validate_json(response.content)
    assert body["supported_locales"] == ["en", "ur"]
    assert body["privacy_policy_version"] is None
    assert body["policies"]["privacy"] == {
        "status": "unavailable",
        "version": None,
        "url": None,
        "locale": None,
    }
    assert body["support"] == {"status": "unavailable", "url": None}
    assert body["policy_publication_ready"] is False
    assert not any(body["public_features"].values())


@pytest.mark.parametrize(
    "suffix",
    [
        "?unknown=SECRET-CANARY-44D",
        "?lang=en&lang=ur",
        "?lang=fr",
        "?lang=",
        "?lang=EN",
        "?lang=en&extra=1",
        "?lang=en&lang=en",
    ],
)
def test_closed_query(client, suffix):
    response = client.get(URL + suffix)
    assert response.status_code == 422
    cache(response)
    assert response.json() == {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Invalid request.",
            "details": {},
        }
    }
    assert CANARY not in response.text


@pytest.mark.parametrize("body", [b"{}", b" ", CANARY.encode(), b"x" * 10000])
def test_no_request_body(client, body):
    response = client.request("GET", URL, content=body)
    assert response.status_code == 422
    cache(response)
    assert CANARY not in response.text


def test_no_personalization_or_conditional_cache(client):
    original = client.get(URL)
    response = client.get(
        URL,
        headers={
            "Authorization": "Bearer " + CANARY,
            "Cookie": "locale=ur; secret=" + CANARY,
            "Accept-Language": "ur",
            "If-None-Match": "*",
            "If-Modified-Since": "Wed, 21 Oct 2026 00:00:00 GMT",
        },
    )
    assert response.status_code == 200
    assert response.json() == original.json()
    cache(response)


@pytest.mark.parametrize(
    "approved,en,ur,locale,selected",
    [
        (False, True, True, "ur", None),
        (True, False, False, "en", None),
        (True, True, False, "ur", "en"),
        (True, True, True, "ur", "ur"),
        (True, False, True, "en", None),
        (True, True, True, "en", "en"),
    ],
)
def test_reviewed_locales(client, monkeypatch, approved, en, ur, locale, selected):
    monkeypatch.setattr(
        public,
        "REVIEWED_METADATA",
        metadata(
            record(approved=approved, en=en, ur=ur),
            public.ReviewedLink(url="https://example.invalid/support", approved=True),
        ),
    )
    response = client.get(URL + "?lang=" + locale)
    assert response.status_code == 200
    body = response.json()
    assert body["locale"] == locale
    assert body["policies"]["privacy"]["locale"] == selected
    assert body["privacy_policy_version"] == ("synthetic-v1" if selected else None)
    assert body["policy_publication_ready"] == bool(selected)
    assert not any(body["public_features"].values())
    cache(response)


@pytest.mark.parametrize("approved", [False, True])
def test_support_requires_approval(client, monkeypatch, approved):
    monkeypatch.setattr(
        public,
        "REVIEWED_METADATA",
        metadata(
            record(),
            public.ReviewedLink(url="https://example.invalid/help", approved=approved),
        ),
    )
    body = client.get(URL).json()
    assert body["policy_publication_ready"] == approved
    assert (body["support"]["url"] is not None) == approved


@pytest.mark.parametrize(
    "url",
    [
        "http://example.invalid",
        "https://user:pass@example.invalid",
        "https://example.invalid/?secret=x",
        "https://example.invalid/#x",
        "https:///path",
        "https://example.invalid:bad",
        "https://example.invalid/\nsecret",
        "https://example.invalid\\secret",
        "https://example.invalid/?",
        "https://example.invalid/#",
    ],
)
def test_invalid_public_urls(url):
    with pytest.raises(ValueError):
        public.ReviewedLink(url=url, approved=True)


@pytest.mark.parametrize(
    "bad",
    [
        None,
        {},
        CANARY,
        public.ReviewedMetadata.model_construct(
            privacy={"version": CANARY, "approved": True},
            terms=None,
            support=None,
        ),
    ],
)
def test_malformed_metadata_fails_closed(client, monkeypatch, bad, caplog):
    monkeypatch.setattr(public, "REVIEWED_METADATA", bad)
    response = client.get(URL)
    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "PROVIDER_UNAVAILABLE",
            "message": "Service temporarily unavailable.",
            "details": {},
        }
    }
    cache(response)
    assert CANARY not in response.text + caplog.text


def test_closed_output_models(client):
    body = client.get(URL).json()
    for key in ("secret", "internal_origin", "rate_limit", "customer_data"):
        with pytest.raises(ValidationError):
            public.PublicConfiguration.model_validate_json(
                json.dumps({**body, key: CANARY})
            )
    schema = public.PublicConfiguration.model_json_schema()
    for definition in [schema, *schema["$defs"].values()]:
        if definition.get("type") == "object":
            assert definition["additionalProperties"] is False
            assert set(definition["required"]) == set(definition["properties"])
    assert set(body) == {
        "supported_locales",
        "default_locale",
        "locale",
        "public_features",
        "max_finder_message_length",
        "privacy_policy_version",
        "policies",
        "consent_versions",
        "support",
        "policy_publication_ready",
    }
    for field, value in [
        ("privacy_policy_version", "fake-v1"),
        ("policy_publication_ready", True),
    ]:
        with pytest.raises(ValidationError):
            public.PublicConfiguration.model_validate_json(
                json.dumps({**body, field: value})
            )


def test_nested_allowlist_and_immutable_registry():
    with pytest.raises(ValidationError):
        public.ReviewedMetadata(privacy=None, terms=None, support=None, secret=CANARY)
    with pytest.raises(ValidationError):
        public.REVIEWED_METADATA.support = None
    with pytest.raises(ValidationError):
        public.ConfigurationFeatures(
            abuse_reporting_available=True, template_publication_available=False
        )
    with pytest.raises(ValidationError):
        public.PolicyMetadata(status="unavailable", version="v1", url=None, locale=None)


def test_versions_match_working_validators(client):
    versions = client.get(URL).json()["consent_versions"]
    for version in versions["finder_contact"]:
        FinderMessageRequest(
            message="Synthetic found item",
            finder_email="a@example.invalid",
            contact_consent_accepted=True,
            contact_consent_version=version,
        )
    assert set(versions["finder_contact"]) == {"finder-public-v1", "finder-v1"}
    assert (
        FinderMessageRequest.model_json_schema()["properties"]["message"]["maxLength"]
        == 1000
    )
    checks = [
        (FinderLocation, "consent_version", "finder_location"),
        (ICEEdit, "publication_consent_version", "ice_publication"),
        (ContactEdit, "publication_consent_version", "ice_contact"),
        (PreferenceEdit, "consent_version", "whatsapp_publication"),
    ]
    for model, field, key in checks:
        literal = get_args(model.model_fields[field].annotation)[0]
        assert set(get_args(literal)) == set(versions[key])
    assert set(get_args(Report.model_fields["consent_version"].annotation)) == set(
        versions["abuse_report"]
    )


def test_openapi_and_existing_routes_unchanged(client):
    schema = client.get("/openapi.json").json()
    operation = schema["paths"][URL]["get"]
    assert operation["operationId"] == "API-005"
    assert "requestBody" not in operation
    assert operation["parameters"][0]["schema"]["enum"] == ["en", "ur"]
    for path in (
        "/api/v1/public/qr/{token}",
        "/api/v1/public/abuse-reports",
        "/api/v1/admin/support-cases",
        "/api/v1/public/catalog/featured",
    ):
        assert path in schema["paths"]


def test_settings_secrets_flags_and_logs_are_excluded(caplog):
    settings = Settings(
        database_url=SecretStr(CANARY),
        turnstile_secret_key=SecretStr(CANARY),
        supabase_url="https://internal-origin.invalid",
        inventory_low_stock_threshold=987654321,
        abuse_reports_enabled=True,
        print_template_management_enabled=True,
    )
    response = ASGIClient(create_app(settings)).get(URL)
    assert response.status_code == 200
    for private in (
        CANARY,
        "internal-origin.invalid",
        "987654321",
        "supabase",
        "turnstile",
    ):
        assert private not in response.text + caplog.text
    assert not any(response.json()["public_features"].values())


def test_existing_openapi_preserved_against_pre_registration(monkeypatch):
    from fastapi import APIRouter

    from app import main

    current = create_app(Settings()).openapi()
    monkeypatch.setattr(main, "public_config_router", APIRouter())
    previous = create_app(Settings()).openapi()
    assert set(current["paths"]) - set(previous["paths"]) == {URL}
    for path, value in previous["paths"].items():
        assert current["paths"][path] == value
    for name, value in previous["components"]["schemas"].items():
        assert current["components"]["schemas"][name] == value
