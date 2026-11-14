"""Local operator entry point. Default/template/check modes never open a socket."""

import argparse
import getpass
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import httpx
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

from app.core.auth import AuthRequired, AuthUnavailable, JWTVerifier
from app.core.config import Settings
from app.core.profile_crypto import ProfileCryptoUnavailable
from app.db.session import Database
from app.services.support_provisioning import (
    AMENDMENT,
    CHANGE,
    EMAIL,
    PROJECT,
    SCOPE,
    SUNSET,
    ProvisioningDenied,
    execute,
    load_trust,
    read_document,
    validate_approval,
    verify_target,
)

ROOT = Path(__file__).resolve().parents[2]
IMPLEMENTATION_FILES = (
    "backend/app/support_provisioning_cli.py",
    "backend/app/services/support_provisioning.py",
    "backend/app/services/support_development_access.py",
    "backend/app/api/auth.py",
    "backend/app/api/v1/support_development.py",
    "backend/app/main.py",
    "backend/app/core/config.py",
    "backend/app/core/auth.py",
    "backend/app/core/profile_crypto.py",
    "backend/app/db/session.py",
    "backend/app/db/runtime.py",
    "backend/alembic/versions/0044_support_dev_exception.py",
    "backend/alembic/versions/0044_support_dev_exception.sql",
    "frontend/lib/auth/support-onboarding.ts",
    "frontend/app/dev/support-onboarding/actions.ts",
    "frontend/app/dev/support-onboarding/form.tsx",
    "frontend/app/dev/support-onboarding/page.tsx",
)


def implementation_digest():
    value = hashlib.sha256()
    for name in IMPLEMENTATION_FILES:
        value.update(name.encode() + b"\0")
        value.update(hashlib.sha256((ROOT / name).read_bytes()).digest())
    return value.hexdigest()


def template():
    return {
        "status": "PREPARATION_ONLY_NOT_AUTHORIZED",
        "approval": {
            "amendment": AMENDMENT,
            "version": "1.1",
            "change_id": CHANGE,
            "approval_id": str(uuid4()),
            "action": "grant",
            "project": PROJECT,
            "environment": "development",
            "email": EMAIL,
            "subject_id": None,
            "executor_id": None,
            "role": "support",
            "scope": SCOPE,
            "decision": None,
            "owner_authorization_reference": None,
            "owner_self_grant_exception": True,
            "amendment_sha256": hashlib.sha256(
                (
                    ROOT / "docs/BTR_01_DEVELOPMENT_SUPPORT_EXCEPTION_v1.1.md"
                ).read_bytes()
            ).hexdigest(),
            "implementation_sha256": implementation_digest(),
            "email_evidence_reference": None,
            "mfa_evidence_reference": None,
            "authorized_at": None,
            "approval_expires_at": None,
            "grant_expires_at": None,
        },
        "hard_sunset": SUNSET.isoformat(),
        "instructions": "User completes official Auth email/MFA in their own browser. No secrets in this packet. A separately reviewed exact live operation is required.",
    }


def check(settings, document):
    trust = load_trust(settings)
    packet = validate_approval(document, trust, datetime.now(UTC))
    expected = hashlib.sha256(
        (ROOT / "docs/BTR_01_DEVELOPMENT_SUPPORT_EXCEPTION_v1.1.md").read_bytes()
    ).hexdigest()
    if (
        packet.amendment_sha256 != expected
        or packet.implementation_sha256 != implementation_digest()
    ):
        raise ProvisioningDenied("REVIEWED_IMPLEMENTATION_MISMATCH")
    if settings.support_dev_subject_id != packet.subject_id:
        raise ProvisioningDenied("SUBJECT_CONFIGURATION_MISMATCH")
    return packet


def verify_running_backend(settings, packet, token, *, transport=None):
    origin = urlsplit(settings.support_dev_backend_origin)
    if (
        origin.scheme != "http"
        or origin.hostname != "127.0.0.1"
        or not origin.port
        or origin.username
        or origin.password
        or origin.path
        or origin.query
        or origin.fragment
    ):
        raise ProvisioningDenied("LOOPBACK_BACKEND_REQUIRED")
    try:
        with httpx.Client(
            timeout=5, follow_redirects=False, trust_env=False, transport=transport
        ) as client:
            response = client.get(
                settings.support_dev_backend_origin
                + "/api/v1/me/support-development-readiness",
                headers={"Authorization": "Bearer " + token},
            )
        if response.status_code != 200 or len(response.content) > 2048:
            raise ValueError()
        expected_state = (
            {"unregistered", "active"}
            if packet.action == "grant"
            else {"active", "inactive"}
        )
        body = response.json()
        if (
            body.get("project") != PROJECT
            or body.get("subject_id") != str(packet.subject_id)
            or body.get("implementation_sha256") != packet.implementation_sha256
            or body.get("metadata_only") is not True
            or body.get("state") not in expected_state
        ):
            raise ValueError()
    except (httpx.HTTPError, ValueError, AttributeError):
        raise ProvisioningDenied("RUNNING_BACKEND_FENCE_NOT_VERIFIED") from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm-change")
    parser.add_argument("--idempotency-key", type=UUID)
    args = parser.parse_args(argv)
    if args.packet is None:
        if args.execute:
            print("DENIED: PACKET_REQUIRED")
            return 2
        print(json.dumps(template(), indent=2))
        return 0
    database = verifier = None
    try:
        settings = Settings(_env_file=ROOT / "backend/.env")
        packet = check(settings, read_document(args.packet))
        if not args.execute:
            print("OFFLINE_PACKET_CHECK_PASSED; no connection or grant executed")
            return 0
        if args.confirm_change != CHANGE or args.idempotency_key is None:
            raise ProvisioningDenied("EXACT_EXECUTION_CONFIRMATION_REQUIRED")
        url = verify_target(settings)
        # Local private operator input only; never a CLI argument, log or file.
        # Do not send this credential to an assistant/chat. No password/OTP is requested.
        token = getpass.getpass("Local signed-in access token (hidden, never saved): ")
        verifier = JWTVerifier(settings)
        principal = verifier.verify(token)
        verify_running_backend(settings, packet, token)
        token = None
        database = Database(
            create_engine(
                url,
                echo=False,
                hide_parameters=True,
                pool_size=1,
                max_overflow=0,
                connect_args={"connect_timeout": 5},
            )
        )
        print(
            json.dumps(
                execute(database, settings, packet, principal, args.idempotency_key)
            )
        )
        return 0
    except ProvisioningDenied as error:
        print("DENIED: " + str(error))
    except (
        AuthRequired,
        AuthUnavailable,
        ProfileCryptoUnavailable,
        SQLAlchemyError,
        OSError,
        ValueError,
    ):
        print(
            "DENIED: AUTH_CRYPTO_CONFIGURATION_OR_DATABASE_UNAVAILABLE; reconcile the same key if commit outcome is uncertain"
        )
    finally:
        if database:
            database.close()
        if verifier:
            verifier.close()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
