"""Real cryptographic JWT verification with controlled public-key transport."""

import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from test_health import ASGIClient

from app.api.auth import Authenticated
from app.core.auth import AuthRequired, AuthUnavailable, JWTVerifier
from app.core.config import Settings
from app.main import create_app

ORIGIN = "https://project.test"


def keyset(private, kid="one", algorithm="ES256"):
    jwk = json.loads(
        jwt.algorithms.get_default_algorithms()[algorithm].to_jwk(private.public_key())
    )
    return {**jwk, "kid": kid, "alg": algorithm, "use": "sig", "key_ops": ["verify"]}


def claims(**overrides):
    return {
        "iss": ORIGIN + "/auth/v1",
        "aud": "authenticated",
        "sub": str(uuid.uuid4()),
        "session_id": str(uuid.uuid4()),
        "role": "authenticated",
        "aal": "aal1",
        "is_anonymous": False,
        "iat": int(time.time()) - 1,
        "exp": int(time.time()) + 300,
        **overrides,
    }


def signed(private, payload=None, *, kid="one", algorithm="ES256", headers=None):
    return jwt.encode(
        payload or claims(),
        private,
        algorithm=algorithm,
        headers={"kid": kid, **(headers or {})},
    )


@pytest.fixture
def verifier():
    private = ec.generate_private_key(ec.SECP256R1())
    calls = []
    state = {"keys": [keyset(private)], "now": 100.0, "status": 200}

    def transport(request):
        calls.append(request)
        assert str(request.url) == ORIGIN + "/auth/v1/.well-known/jwks.json"
        assert "authorization" not in request.headers
        return httpx.Response(state["status"], json={"keys": state["keys"]})

    provider = JWTVerifier(
        Settings(supabase_url=ORIGIN),
        transport=httpx.MockTransport(transport),
        clock=lambda: state["now"],
    )
    try:
        yield provider, private, state, calls
    finally:
        provider.close()


def test_valid_signature_and_untrusted_custom_roles(verifier):
    provider, private, _, _ = verifier
    payload = claims(
        aal="aal2",
        user_metadata={"is_admin": True},
        app_metadata={"roles": ["superadmin"]},
    )
    principal = provider.verify(signed(private, payload))
    assert principal.user_id == uuid.UUID(payload["sub"])
    assert principal.session_id == uuid.UUID(payload["session_id"])
    assert principal.mfa_claim
    assert not hasattr(principal, "roles") and not hasattr(principal, "token")


@pytest.mark.parametrize(
    "override",
    [
        {"iss": "https://attacker.test/auth/v1"},
        {"aud": "anon"},
        {"aud": ["authenticated", "other"]},
        lambda: {"exp": int(time.time()) - 5},
        lambda: {"nbf": int(time.time()) + 100},
        lambda: {"iat": int(time.time()) + 100},
        {"exp": "9999999999"},
        {"iat": True},
        {"sub": "not-uuid"},
        {"session_id": None},
        {"role": "service_role"},
        {"role": "anon"},
        {"aal": "aal3"},
        {"is_anonymous": True},
        {"is_anonymous": "false"},
        {"token_type": "refresh"},
        {"type": "refresh"},
    ],
)
def test_invalid_access_claims_rejected(verifier, override):
    provider, private, _, _ = verifier
    if callable(override):
        override = override()
    with pytest.raises(AuthRequired):
        provider.verify(signed(private, claims(**override)))


@pytest.mark.parametrize(
    "missing", ["iss", "aud", "sub", "exp", "iat", "session_id", "role", "aal"]
)
def test_required_claims(verifier, missing):
    provider, private, _, _ = verifier
    payload = claims()
    del payload[missing]
    with pytest.raises(AuthRequired):
        provider.verify(signed(private, payload))


@pytest.mark.parametrize(
    "headers",
    [
        {"alg": "none"},
        {"typ": "refresh"},
        {"jku": "https://attacker.test"},
        {"jwk": {}},
        {"crit": ["b64"]},
        {"kid": ""},
    ],
)
def test_untrusted_headers_never_select_remote_key_location(verifier, headers):
    provider, private, _, calls = verifier
    token = (
        signed(private, headers=headers)
        if headers.get("alg") != "none"
        else jwt.encode(claims(), None, algorithm="none", headers={"kid": "one"})
    )
    with pytest.raises(AuthRequired):
        provider.verify(token)
    assert not calls


@pytest.mark.parametrize("token", ["", "refresh-token", "x.y.z", "a" * 8193])
def test_malformed_and_oversize_tokens(verifier, token):
    with pytest.raises(AuthRequired):
        verifier[0].verify(token)


def test_wrong_signature_and_symmetric_confusion(verifier):
    provider, private, _, _ = verifier
    wrong = ec.generate_private_key(ec.SECP256R1())
    with pytest.raises(AuthRequired):
        provider.verify(signed(wrong))
    with pytest.raises(AuthRequired):
        provider.verify(
            signed(
                "a-test-only-symmetric-key-with-sufficient-entropy", algorithm="HS256"
            )
        )
    assert provider.verify(signed(private))


def test_rsa_signature():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with httpx.MockTransport(
        lambda request: httpx.Response(
            200, json={"keys": [keyset(private, algorithm="RS256")]}
        )
    ) as transport:
        provider = JWTVerifier(Settings(supabase_url=ORIGIN), transport=transport)
        try:
            assert provider.verify(signed(private, algorithm="RS256"))
        finally:
            provider.close()


def test_rotation_cache_revocation_and_unknown_key_refresh_bound(verifier):
    provider, private, state, calls = verifier
    token = signed(private)
    provider.verify(token)
    provider.verify(token)
    assert len(calls) == 1
    replacement = ec.generate_private_key(ec.SECP256R1())
    state["keys"] = [keyset(replacement, "two")]
    state["now"] += 5
    assert provider.verify(signed(replacement, kid="two"))
    assert len(calls) == 2
    for _ in range(10):
        with pytest.raises(AuthRequired):
            provider.verify(signed(private, kid="unknown"))
    assert len(calls) == 2
    with pytest.raises(AuthRequired):
        provider.verify(token)
    state["status"], state["now"] = 503, state["now"] + 61
    with pytest.raises(AuthUnavailable):
        provider.verify(signed(replacement, kid="two"))


def test_fetch_failure_and_invalid_key_sets_fail_closed(verifier):
    provider, private, state, _ = verifier
    state["status"] = 503
    with pytest.raises(AuthUnavailable):
        provider.verify(signed(private))
    state["status"], state["now"], state["keys"] = 200, state["now"] + 5, []
    with pytest.raises(AuthUnavailable):
        provider.verify(signed(private))


def test_concurrent_verification_coalesces_fetch(verifier):
    provider, private, _, calls = verifier
    token = signed(private)
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert len(list(pool.map(provider.verify, [token] * 8))) == 8
    assert len(calls) == 1


@pytest.mark.parametrize(
    "authorization", [None, "Basic irrelevant", "Bearer refresh-token"]
)
def test_protected_dependency_safe_errors_and_health_independent(
    verifier, authorization
):
    provider, _, _, _ = verifier
    app = create_app(Settings(supabase_url=ORIGIN), verifier=provider)

    @app.get("/test-protected")
    def protected(context: Authenticated):
        return {"ok": True}

    app.state.jwt_verifier = provider
    client = ASGIClient(app)
    response = client.get(
        "/test-protected",
        headers={"Authorization": authorization} if authorization else {},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]
    assert client.get("/api/v1/health/live").status_code == 200


def test_unconfigured_auth_fails_closed():
    provider = JWTVerifier(Settings(supabase_url=None))
    try:
        private = ec.generate_private_key(ec.SECP256R1())
        with pytest.raises(AuthUnavailable):
            provider.verify(signed(private))
    finally:
        provider.close()


@pytest.mark.parametrize(
    "mode", ["redirect", "timeout", "duplicate", "private", "oversize", "malformed"]
)
def test_jwks_transport_and_key_injection_fail_closed(mode):
    private = ec.generate_private_key(ec.SECP256R1())
    public = keyset(private)

    def transport(request):
        if mode == "timeout":
            raise httpx.ReadTimeout("test timeout", request=request)
        if mode == "redirect":
            return httpx.Response(
                302, headers={"location": "https://attacker.test/keys"}
            )
        if mode == "oversize":
            return httpx.Response(200, content=b" " * 65537)
        if mode == "malformed":
            return httpx.Response(200, json={"keys": [None]})
        entries = (
            [public, public]
            if mode == "duplicate"
            else [{**public, "d": "untrusted-private-key"}]
        )
        return httpx.Response(200, json={"keys": entries})

    provider = JWTVerifier(
        Settings(supabase_url=ORIGIN), transport=httpx.MockTransport(transport)
    )
    try:
        with pytest.raises(AuthUnavailable):
            provider.verify(signed(private))
    finally:
        provider.close()


@pytest.mark.parametrize(
    "origin",
    [
        "http://project.test",
        "https://user:password@project.test",
        "https://project.test/auth/v1",
        "https://project.test?key=value",
        "https://project.test#fragment",
    ],
)
def test_auth_origin_rejects_credentials_and_unapproved_paths(origin):
    with pytest.raises(ValueError):
        Settings(supabase_url=origin)


def test_duplicate_authorization_headers_rejected_before_verification(verifier):
    provider, private, _, calls = verifier
    app = create_app(Settings(supabase_url=ORIGIN), verifier=provider)
    app.state.jwt_verifier = provider

    @app.get("/test-protected")
    def protected(context: Authenticated):
        return {"ok": True}

    token = signed(private)
    response = ASGIClient(app).get(
        "/test-protected",
        headers=[
            ("Authorization", "Bearer " + token),
            ("Authorization", "Bearer " + token),
        ],
    )
    assert response.status_code == 401
    assert not calls
