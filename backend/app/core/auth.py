"""Supabase access-token verification; no token or private claims are retained."""

import json
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import httpx
import jwt

from app.core.config import Settings


class AuthRequired(Exception):
    pass


class AuthUnavailable(Exception):
    pass


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    session_id: UUID
    mfa_claim: bool
    authentication_time: int | None = None


class JWTVerifier:
    """Fixed issuer/algorithms, bounded cache, coalesced rotation refresh.

    Legacy symmetric keys are deliberately unsupported: the inspected project
    uses ES256. Never substitute a publishable/service API key as a JWT secret.
    """

    def __init__(self, settings: Settings, *, transport=None, clock=time.monotonic):
        self.issuer = (
            settings.supabase_url + "/auth/v1" if settings.supabase_url else None
        )
        self.ttl = settings.auth_jwks_cache_seconds
        self.clock = clock
        self.client = httpx.Client(
            timeout=settings.auth_http_timeout_seconds,
            transport=transport,
            follow_redirects=False,
            trust_env=False,
        )
        self.keys = {}
        self.loaded_at = float("-inf")
        self.attempted_at = float("-inf")
        self.lock = threading.Lock()

    def close(self):
        self.client.close()

    def _key(self, kid, algorithm):
        if self.issuer is None:
            raise AuthUnavailable()
        with self.lock:
            now = self.clock()
            fresh = now - self.loaded_at < self.ttl
            if not fresh or kid not in self.keys:
                if now - self.attempted_at >= 5:
                    self.attempted_at = now
                    try:
                        with self.client.stream(
                            "GET", self.issuer + "/.well-known/jwks.json"
                        ) as response:
                            response.raise_for_status()
                            data = bytearray()
                            for chunk in response.iter_bytes():
                                data.extend(chunk)
                                if len(data) > 65536:
                                    raise ValueError("Oversize key set")
                        entries = json.loads(data)["keys"]
                        if not isinstance(entries, list) or not 1 <= len(entries) <= 32:
                            raise ValueError("Invalid key set")
                        keys = {}
                        for entry in entries:
                            alg = entry.get("alg")
                            if alg not in ("ES256", "RS256"):
                                continue
                            if (
                                entry.get("kty") != {"ES256": "EC", "RS256": "RSA"}[alg]
                                or entry.get("use", "sig") != "sig"
                                or entry.get("key_ops", ["verify"]) != ["verify"]
                                or "d" in entry
                            ):
                                raise ValueError("Invalid signing key")
                            key_id = entry["kid"]
                            if (
                                not isinstance(key_id, str)
                                or not 1 <= len(key_id) <= 128
                                or key_id in keys
                            ):
                                raise ValueError("Invalid key identity")
                            key = jwt.PyJWK.from_dict(entry, algorithm=alg)
                            if alg == "ES256" and entry.get("crv") != "P-256":
                                raise ValueError("Invalid curve")
                            if alg == "RS256" and key.key.key_size < 2048:
                                raise ValueError("Invalid RSA strength")
                            keys[key_id] = key
                        self.keys, self.loaded_at = keys, now
                    except (
                        httpx.HTTPError,
                        ValueError,
                        KeyError,
                        TypeError,
                        AttributeError,
                        jwt.PyJWTError,
                    ):
                        raise AuthUnavailable() from None
                elif not fresh:
                    raise AuthUnavailable()
            key = self.keys.get(kid)
            if key is None or key.algorithm_name != algorithm:
                raise AuthRequired()
            return key

    def verify(self, token: str) -> Principal:
        try:
            if not isinstance(token, str) or len(token) > 8192 or token.count(".") != 2:
                raise AuthRequired()
            header = jwt.get_unverified_header(token)
            alg, kid = header.get("alg"), header.get("kid")
            if (
                alg not in ("ES256", "RS256")
                or header.get("typ") != "JWT"
                or not isinstance(kid, str)
                or not 1 <= len(kid) <= 128
                or any(name in header for name in ("jku", "x5u", "jwk", "crit"))
            ):
                raise AuthRequired()
            key = self._key(kid, alg)
            claims = jwt.decode(
                token,
                key.key,
                algorithms=[alg],
                issuer=self.issuer,
                audience="authenticated",
                options={
                    "require": [
                        "iss",
                        "aud",
                        "sub",
                        "exp",
                        "iat",
                        "session_id",
                        "role",
                        "aal",
                    ],
                    "strict_aud": True,
                },
            )
            if (
                claims["role"] != "authenticated"
                or claims["aal"] not in ("aal1", "aal2")
                or claims.get("is_anonymous", False) is not False
                or claims.get("token_type", "access") != "access"
                or claims.get("type", "access") != "access"
            ):
                raise AuthRequired()
            for name in ("exp", "iat", "nbf"):
                if name in claims and (
                    type(claims[name]) is not int or claims[name] < 0
                ):
                    raise AuthRequired()
            if claims["exp"] <= claims["iat"]:
                raise AuthRequired()
            # A refreshed access token's iat is not proof of recent reauthentication.
            # Only signed provider AMR entries represent an authentication event.
            authentication_time = None
            now = datetime.now(UTC).timestamp()
            amr = claims.get("amr", [])
            if isinstance(amr, list):
                valid = [
                    entry["timestamp"]
                    for entry in amr
                    if isinstance(entry, dict)
                    and entry.get("method")
                    in ("password", "otp", "totp", "mfa/totp", "webauthn", "oauth")
                    and type(entry.get("timestamp")) is int
                    and 0 <= entry["timestamp"] <= now
                ]
                authentication_time = max(valid, default=None)
            return Principal(
                UUID(claims["sub"]),
                UUID(claims["session_id"]),
                claims["aal"] == "aal2",
                authentication_time,
            )
        except (jwt.PyJWTError, ValueError, TypeError, KeyError, AttributeError):
            raise AuthRequired() from None
