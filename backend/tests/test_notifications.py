from unittest.mock import MagicMock, patch

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.workers.notifications import (
    NotificationProviderError,
    ResendProvider,
    process_one,
)


def settings():
    return Settings(
        resend_api_key=SecretStr("test-key"),
        notification_from_email="SafeReturn <noreply@example.test>",
    )


@patch("app.workers.notifications.httpx.post")
def test_resend_returns_provider_id(mock_post):
    mock_post.return_value = httpx.Response(200, json={"id": "email-123"})
    provider_id = ResendProvider(settings()).send(
        to="owner@example.test",
        subject="subject",
        html="<p>body</p>",
        idempotency_key="finder-message:123",
    )
    assert provider_id == "email-123"
    request = mock_post.call_args.kwargs
    assert request["headers"]["Idempotency-Key"] == "finder-message:123"
    assert request["json"]["to"] == ["owner@example.test"]
    assert mock_post.call_args.args[0] == "https://api.resend.com/emails"
    assert request["follow_redirects"] is False


@pytest.mark.parametrize("status", [429, 500, 503])
@patch("app.workers.notifications.httpx.post")
def test_resend_retries_provider_rate_and_server_errors(mock_post, status):
    mock_post.return_value = httpx.Response(status)
    with pytest.raises(NotificationProviderError) as error:
        ResendProvider(settings()).send(
            to="owner@example.test",
            subject="subject",
            html="<p>body</p>",
            idempotency_key="finder-message:123",
        )
    assert error.value.transient is True


@patch("app.workers.notifications.httpx.post")
def test_resend_rejects_invalid_recipient_response(mock_post):
    mock_post.return_value = httpx.Response(400)
    with pytest.raises(NotificationProviderError) as error:
        ResendProvider(settings()).send(
            to="owner@example.test",
            subject="subject",
            html="<p>body</p>",
            idempotency_key="finder-message:123",
        )
    assert error.value.code == "provider_http_400"
    assert error.value.transient is False


def test_resend_requires_credentials():
    with pytest.raises(NotificationProviderError) as error:
        ResendProvider(Settings())
    assert error.value.code == "provider_not_configured"


@patch("app.workers.notifications.httpx.post", side_effect=httpx.ConnectTimeout("down"))
def test_resend_network_failure_is_transient(_mock_post):
    with pytest.raises(NotificationProviderError) as error:
        ResendProvider(settings()).send(
            to="owner@example.test",
            subject="subject",
            html="<p>body</p>",
            idempotency_key="finder-message:123",
        )
    assert error.value.code == "provider_network"
    assert error.value.transient is True


@pytest.mark.parametrize(
    "payload",
    [
        {},
        [],
        {"id": None},
        {"id": []},
        {"id": ""},
        {"id": "x" * 151},
        {"id": "private\nvalue"},
    ],
)
@patch("app.workers.notifications.httpx.post")
def test_resend_rejects_malformed_success_without_echoing_data(mock_post, payload):
    mock_post.return_value = httpx.Response(200, json=payload)
    with pytest.raises(NotificationProviderError) as error:
        ResendProvider(settings()).send(
            to="owner@example.test",
            subject="subject",
            html="<p>body</p>",
            idempotency_key="stable-key",
        )
    assert error.value.code == "provider_invalid_response"
    assert error.value.transient
    assert "private" not in str(error.value)


@pytest.mark.parametrize(
    "name,transient",
    [("concurrent_idempotent_requests", True), ("invalid_idempotent_request", False)],
)
@patch("app.workers.notifications.httpx.post")
def test_resend_distinguishes_inflight_idempotency_from_payload_conflict(
    mock_post, name, transient
):
    mock_post.return_value = httpx.Response(
        409, json={"name": name, "message": "PRIVATE PROVIDER DETAILS"}
    )
    with pytest.raises(NotificationProviderError) as error:
        ResendProvider(settings()).send(
            to="owner@example.test",
            subject="subject",
            html="<p>body</p>",
            idempotency_key="stable-key",
        )
    assert error.value.transient is transient
    assert error.value.code == "provider_http_409"
    assert "PRIVATE" not in str(error.value)


@patch("app.workers.notifications.httpx.post")
def test_resend_honors_bounded_retry_after(mock_post):
    mock_post.return_value = httpx.Response(429, headers={"Retry-After": "99999"})
    with pytest.raises(NotificationProviderError) as error:
        ResendProvider(settings()).send(
            to="owner@example.test",
            subject="subject",
            html="<p>body</p>",
            idempotency_key="stable-key",
        )
    assert error.value.retry_after == 3600


@patch("app.workers.notifications.httpx.post")
def test_invalid_recipient_does_not_call_provider(mock_post):
    with pytest.raises(NotificationProviderError):
        ResendProvider(settings()).send(
            to="owner@example.test\nBcc:someone@example.test",
            subject="subject",
            html="<p>body</p>",
            idempotency_key="stable-key",
        )
    mock_post.assert_not_called()


def test_provider_error_never_retains_untrusted_details():
    error = NotificationProviderError("PRIVATE-OWNER@example.test", transient=False)
    assert error.code == str(error) == "provider_failure"


def test_worker_rejects_lease_shorter_than_provider_timeout_before_claim():
    database = MagicMock()
    with pytest.raises(NotificationProviderError) as error:
        process_one(database, Settings(notification_lease_seconds=10), MagicMock())
    assert error.value.code == "lease_timeout_configuration"
    database.transaction.assert_not_called()
