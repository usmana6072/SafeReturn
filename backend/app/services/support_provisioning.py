"""One-subject development command. No cloud call is made by packet validation.

Trust configuration is operator-owned, pinned out of band, never packet input.
The database credential belongs to the trusted command host, not the subject.
"""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import text

from app.core.profile_crypto import decrypt, encrypt
from app.db.session import database_url

PROJECT = "fhuxryfkfrvycsojkzvq"
EMAIL = "usmana6072@gmail.com"
AMENDMENT = "BTR-01-DEV-SUPPORT-20261024"
CHANGE = "SR-SUPPORT-DEV-84bcdd96-522d-4953-8f6c-a899dde084ba"
HOST = "aws-0-ap-northeast-2.pooler.supabase.com"
SUNSET = datetime(2026, 11, 7, 18, 59, 59, tzinfo=UTC)
SCOPE = "metadata:mine,unassigned;history:mine"


class ProvisioningDenied(ValueError):
    """Only a fixed, non-sensitive category may cross the CLI boundary."""


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class Approval(Closed):
    amendment: Literal[AMENDMENT]
    version: Literal["1.1"]
    change_id: Literal[CHANGE]
    approval_id: UUID
    action: Literal["grant", "revoke"]
    project: Literal[PROJECT]
    environment: Literal["development"]
    email: Literal[EMAIL]
    subject_id: UUID
    executor_id: UUID
    role: Literal["support"]
    scope: Literal[SCOPE]
    decision: Literal["APPROVE"]
    owner_authorization_reference: str = Field(min_length=1, max_length=200)
    owner_self_grant_exception: Literal[True]
    amendment_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    implementation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    email_evidence_reference: str = Field(min_length=1, max_length=200)
    mfa_evidence_reference: str = Field(min_length=1, max_length=200)
    authorized_at: datetime
    approval_expires_at: datetime
    grant_expires_at: datetime

    @field_validator("owner_self_grant_exception", mode="before")
    @classmethod
    def exact_confirmation(cls, value):
        if value is not True:
            raise ValueError("Explicit confirmation required")
        return value

    @field_validator("authorized_at", "approval_expires_at", "grant_expires_at")
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timezone required")
        return value.astimezone(UTC)


class Trust(Closed):
    project: Literal[PROJECT]
    subject_id: UUID
    executor_id: UUID
    owner_human_reference: str = Field(min_length=1, max_length=200)
    owner_authorization_reference: str = Field(min_length=1, max_length=200)
    amendment_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    implementation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    valid_until: datetime
    revoked_approvals: list[UUID] = Field(max_length=1000)


def canonical(approval: Approval) -> bytes:
    return json.dumps(
        approval.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def unique_object(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ProvisioningDenied("INVALID_DOCUMENT")
        result[name] = value
    return result


def read_document(path):
    try:
        data = Path(path).read_bytes()
        if len(data) > 32768:
            raise ValueError()
        return json.loads(data, object_pairs_hook=unique_object)
    except (OSError, ValueError, UnicodeError):
        raise ProvisioningDenied("INVALID_DOCUMENT") from None


def load_trust(settings):
    try:
        path = Path(settings.support_dev_trust_file)
        raw = path.read_bytes()
        if (
            not settings.support_dev_trust_sha256
            or hashlib.sha256(raw).hexdigest() != settings.support_dev_trust_sha256
        ):
            raise ValueError()
        return Trust.model_validate(read_document(path))
    except (TypeError, OSError, ValueError, ValidationError):
        raise ProvisioningDenied("TRUST_NOT_CONFIGURED") from None


def validate_approval(document, trust, now):
    """Verify owner command intent against operator-pinned configuration.

    No MFA claim in a document substitutes for runtime JWT/provider validation.
    """
    try:
        if set(document) != {"approval"}:
            raise ValueError()
        packet = Approval.model_validate(document["approval"])
        if (
            now.tzinfo is None
            or trust.valid_until.tzinfo is None
            or now >= trust.valid_until
            or packet.subject_id != trust.subject_id
            or packet.executor_id != trust.executor_id
            or packet.executor_id != packet.subject_id
            or packet.owner_authorization_reference
            != trust.owner_authorization_reference
            or packet.amendment_sha256 != trust.amendment_sha256
            or packet.implementation_sha256 != trust.implementation_sha256
            or packet.approval_id in trust.revoked_approvals
            or not packet.authorized_at <= now < packet.approval_expires_at
            or packet.approval_expires_at > packet.authorized_at + timedelta(hours=24)
            or (
                packet.action == "grant"
                and (
                    now >= SUNSET
                    or packet.approval_expires_at > SUNSET
                    or not now
                    < packet.grant_expires_at
                    <= min(SUNSET, now + timedelta(hours=24))
                )
            )
        ):
            raise ValueError()
        return packet
    except (ValueError, TypeError, KeyError, ValidationError):
        raise ProvisioningDenied("APPROVAL_INVALID_OR_UNAVAILABLE") from None


def verify_target(settings):
    """Do not open a connection until exact local configuration is pinned."""
    try:
        if settings.supabase_url != f"https://{PROJECT}.supabase.co":
            raise ValueError()
        if not settings.support_dev_enabled or settings.support_dev_subject_id is None:
            raise ValueError()
        url = database_url(settings.support_dev_database_url.get_secret_value())
        ca = Path(url.query["sslrootcert"])
        if (
            url.host != HOST
            or url.port != 5432
            or url.database != "postgres"
            or url.username != "safereturn_support_command." + PROJECT
            or url.query.get("sslmode") != "verify-full"
            or set(url.query) - {"sslmode", "sslrootcert"}
            or not ca.is_file()
            or hashlib.sha256(ca.read_bytes()).hexdigest()
            != "700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7"
        ):
            raise ValueError()
        return url
    except (AttributeError, KeyError, TypeError, OSError, ValueError):
        raise ProvisioningDenied("EXECUTION_CONFIGURATION_UNAVAILABLE") from None


def verify_principal(packet, principal, now):
    if (
        principal.user_id != packet.executor_id
        or not principal.mfa_claim
        or principal.authentication_time is None
        or not 0 <= now.timestamp() - principal.authentication_time <= 300
    ):
        raise ProvisioningDenied("SESSION_OR_RECENT_MFA_REQUIRED")


def execute(database, settings, packet, principal, key, *, now=None):
    """Dedicated server command credential; never a browser/service-role key.

    SQL function rechecks current provider state, locks, one-use grant and audit.
    The reviewed command host is the owner-intent/JWT verification trust boundary.
    """
    now = now or datetime.now(UTC)
    verify_principal(packet, principal, now)
    if settings.support_dev_subject_id != packet.subject_id:
        raise ProvisioningDenied("SUBJECT_CONFIGURATION_MISMATCH")
    if not isinstance(key, UUID):
        raise ProvisioningDenied("IDEMPOTENCY_KEY_REQUIRED")
    payload_hash = hashlib.sha256(canonical(packet)).hexdigest()
    receipt = json.dumps(
        {
            "approval_id": str(packet.approval_id),
            "action": packet.action,
            "packet_sha256": payload_hash,
            "expires_at": packet.grant_expires_at.isoformat(),
        },
        sort_keys=True,
    )
    cipher, version = encrypt(
        settings, packet.subject_id, "support_dev_receipt:v1", receipt
    )
    params = {
        "uid": packet.subject_id,
        "sid": principal.session_id,
        "amr": principal.authentication_time,
        "approval": packet.approval_id,
        "digest": payload_hash,
        "key": key,
        "expires": packet.grant_expires_at,
        "approval_expires": packet.approval_expires_at,
        "signed": packet.authorized_at,
        "cipher": cipher,
        "version": version,
    }
    with database.transaction() as session:
        session.execute(text("SET LOCAL ROLE safereturn_support_provisioner"))
        session.execute(text("SET LOCAL statement_timeout='8s'"))
        session.execute(text("SET LOCAL lock_timeout='2s'"))
        # Only a fixed function name chosen from the validated action, not SQL input.
        function = {"grant": "sr_support_dev_grant", "revoke": "sr_support_dev_revoke"}[
            packet.action
        ]
        row = (
            session.execute(
                text(f"""SELECT * FROM public.{function}(
            :uid,:sid,:amr,:approval,:digest,:key,:expires,:approval_expires,
            :signed,:cipher,:version)"""),
                params,
            )
            .mappings()
            .one()
        )
        original = json.loads(
            decrypt(
                settings,
                packet.subject_id,
                "support_dev_receipt:v1",
                row["cipher"],
                row["key_version"],
            )
        )
        if original != json.loads(receipt):
            raise ProvisioningDenied("RECEIPT_BINDING_MISMATCH")
    return {
        "outcome": "revoked" if packet.action == "revoke" else "granted",
        "grant_id": str(row["grant_id"]),
        "expires_at": row["expires_at"].isoformat(),
    }
