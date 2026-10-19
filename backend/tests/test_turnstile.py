import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.core.turnstile import ChallengeRequired, ChallengeUnavailable, verify


@pytest.fixture
def settings():
    return Settings(
        turnstile_secret_key=SecretStr("synthetic-independent-secret"),
        turnstile_expected_hostname="fixture.test",
    )


def result(**extra):
    return {
        "success": True,
        "hostname": "fixture.test",
        "action": "ice_reveal",
        "cdata": "binding",
        "challenge_ts": datetime.now(UTC).isoformat(),
        **extra,
    }


def call(settings, payload):
    return verify(
        settings,
        "proof",
        "ice_reveal",
        "binding",
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload)),
    )


def test_verifies_only_server_response_and_fixed_endpoint(settings):
    def handler(request):
        assert (
            str(request.url)
            == "https://challenges.cloudflare.com/turnstile/v0/siteverify"
        )
        assert json.loads(request.content) == {
            "secret": "synthetic-independent-secret",
            "response": "proof",
        }
        return httpx.Response(200, json=result())

    verify(
        settings,
        "proof",
        "ice_reveal",
        "binding",
        transport=httpx.MockTransport(handler),
    )


@pytest.mark.parametrize(
    "extra",
    [
        {"success": False},
        {"success": "true"},
        {"hostname": "attacker.test"},
        {"action": "whatsapp"},
        {"cdata": "other-contact"},
        {"challenge_ts": (datetime.now(UTC) - timedelta(minutes=6)).isoformat()},
        {"challenge_ts": (datetime.now(UTC) + timedelta(minutes=1)).isoformat()},
    ],
)
def test_rejects_forged_cross_resource_stale_proofs(settings, extra):
    with pytest.raises(ChallengeRequired):
        call(settings, result(**extra))


@pytest.mark.parametrize(
    "payload",
    [
        {},
        [],
        {"success": False, "error-codes": ["internal-error"]},
        result(challenge_ts="not-a-date"),
        result(challenge_ts=None),
    ],
)
def test_provider_malformed_and_configuration_errors_are_unavailable(settings, payload):
    with pytest.raises(ChallengeUnavailable):
        call(settings, payload)


@pytest.mark.parametrize("status", [301, 429, 500])
def test_provider_errors_do_not_bypass(settings, status):
    with pytest.raises(ChallengeUnavailable):
        verify(
            settings,
            "proof",
            "ice_reveal",
            "binding",
            transport=httpx.MockTransport(
                lambda r: httpx.Response(
                    status, headers={"location": "https://attacker.test"}
                )
            ),
        )


def test_timeout_does_not_bypass(settings):
    def timeout(r):
        raise httpx.ReadTimeout("synthetic timeout")

    with pytest.raises(ChallengeUnavailable):
        verify(
            settings,
            "proof",
            "ice_reveal",
            "binding",
            transport=httpx.MockTransport(timeout),
        )


def test_missing_challenge_and_missing_keys_fail_closed(settings):
    with pytest.raises(ChallengeRequired):
        verify(settings, None, "ice_reveal", "binding")
    with pytest.raises(ChallengeUnavailable):
        verify(Settings(), "proof", "ice_reveal", "binding")
