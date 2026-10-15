"""Task 2.3: request-level authorization attacks against real isolated PostgreSQL.

Uses signed fixtures, not provider delivery evidence. Rehearsal inspects installed
metadata before setup and checks unchanged metadata/rows after exact cleanup.
"""

import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from sqlalchemy import text
from test_auth import claims, signed
from test_auth_guards import change, guarded  # noqa: F401


@pytest.mark.parametrize(
    "attack",
    [
        "missing",
        "basic",
        "malformed",
        "unsigned",
        "foreign-signature",
        "issuer",
        "audience",
        "expired",
        "future",
        "service-role",
        "anonymous",
        "refresh",
        "missing-session",
        "wrong-session",
    ],
)
def test_account_attack_denies_read_and_write_without_profile_or_audit(guarded, attack):  # noqa: F811
    pg, wf, _, sessions, headers, client = guarded
    uid = wf["a"]
    overrides = {
        "issuer": {"iss": "https://attacker.invalid/auth/v1"},
        "audience": {"aud": "anon"},
        "expired": {"exp": int(time.time()) - 60},
        "future": {"iat": int(time.time()) + 120},
        "service-role": {"role": "service_role"},
        "anonymous": {"is_anonymous": True},
        "refresh": {"token_type": "refresh"},
        "missing-session": {"session_id": str(uuid.uuid4())},
        "wrong-session": {"session_id": str(sessions[wf["b"]])},
    }
    request_headers = headers(uid, **overrides.get(attack, {}))
    if attack in {"missing", "basic", "malformed"}:
        request_headers = {
            "Authorization": {
                "basic": "Basic fixture",
                "malformed": "Bearer invalid",
            }.get(attack, "")
        }
    elif attack == "unsigned":
        request_headers = {
            "Authorization": "Bearer "
            + jwt.encode(claims(sub=str(uid)), "", algorithm="none")
        }
    elif attack == "foreign-signature":
        request_headers = {
            "Authorization": "Bearer "
            + signed(ec.generate_private_key(ec.SECP256R1()), claims(sub=str(uid)))
        }

    def snapshot():
        with pg.connect() as c:
            return tuple(
                c.execute(text(query)).all()
                for query in (
                    "SELECT * FROM public.user_profiles ORDER BY user_id",
                    "SELECT * FROM public.audit_events ORDER BY id",
                )
            )

    before = snapshot()
    for method in ("GET", "PATCH"):
        response = client.request(
            method,
            "/api/v1/me",
            headers={
                **request_headers,
                "If-Match": '"0"',
                "X-Request-ID": "attacker-controlled",
            },
            **(
                {"json": {"display_name": "unauthorized-marker"}}
                if method == "PATCH"
                else {}
            ),
        )
        assert response.status_code == 401
        error = response.json()["error"]
        assert error["code"] == "AUTH_REQUIRED" and error["message_ur"]
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["www-authenticate"] == "Bearer"
        assert (
            error["request_id"]
            == response.headers["x-request-id"]
            != "attacker-controlled"
        )
        assert (
            str(uid) not in response.text and "unauthorized-marker" not in response.text
        )
    assert snapshot() == before
    assert client.get("/api/v1/me", headers=headers(uid)).status_code == 200


def test_rebound_session_denies_existing_signed_token_and_pool_recovers(guarded):  # noqa: F811
    pg, wf, _, sessions, headers, client = guarded
    token = headers(wf["a"])
    # Alter only the isolated session binding, then restore it; no managed Auth writes.
    with change(pg, "auth.sessions", sessions[wf["a"]], {"user_id": wf["b"]}):
        assert client.get("/api/v1/me", headers=token).status_code == 401
        assert (
            client.request(
                "PATCH",
                "/api/v1/me",
                headers={**token, "If-Match": '"0"'},
                json={"display_name": "denied"},
            ).status_code
            == 401
        )
    assert client.get("/api/v1/me", headers=token).status_code == 200
