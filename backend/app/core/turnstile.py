"""Server-verified, action/resource-bound Turnstile; no unapproved outage bypass."""

import hashlib
from datetime import UTC, datetime

import httpx


class ChallengeRequired(Exception):
    pass


class ChallengeUnavailable(Exception):
    pass


def challenge_binding(action, token, contact_id=None):
    return hashlib.sha256(f"{action}:{token}:{contact_id or ''}".encode()).hexdigest()


def verify(settings, token, action, binding, *, transport=None):
    secret = settings.turnstile_secret_key
    hostname = settings.turnstile_expected_hostname
    if not secret or not secret.get_secret_value() or not hostname:
        raise ChallengeUnavailable()
    if not token:
        raise ChallengeRequired()
    try:
        with httpx.Client(
            timeout=settings.turnstile_timeout_seconds,
            follow_redirects=False,
            transport=transport,
        ) as client:
            response = client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                json={"secret": secret.get_secret_value(), "response": token},
            )
            response.raise_for_status()
            result = response.json()
        if not isinstance(result, dict) or "success" not in result:
            raise ChallengeUnavailable()
        if result.get("success") is not True:
            if set(result.get("error-codes", [])) & {
                "internal-error",
                "invalid-input-secret",
                "missing-input-secret",
            }:
                raise ChallengeUnavailable()
            raise ChallengeRequired()
        stamp = datetime.fromisoformat(result["challenge_ts"])
        age = (datetime.now(UTC) - stamp).total_seconds()
        if (
            result.get("hostname") != hostname
            or result.get("action") != action
            or result.get("cdata") != binding
            or not -30 <= age <= 300
        ):
            raise ChallengeRequired()
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError):
        raise ChallengeUnavailable() from None
