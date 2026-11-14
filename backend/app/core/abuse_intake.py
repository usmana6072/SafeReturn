"""Closed anonymous allegations and explicit, unseeded processing policy."""

import base64
import hashlib
import hmac
import json
import re
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class Unavailable(ValueError):
    pass


Positive = Annotated[int, Field(ge=1, le=2147483647, strict=True)]
Reference = Annotated[str, Field(pattern=r"^[A-Za-z0-9._:-]{1,160}$")]


class Report(Closed):
    qr_token: SecretStr = Field(min_length=20, max_length=80)
    message_id: UUID | None = None
    category: Literal["spam", "fraud", "unsafe_content", "other"]
    message: str | None = Field(default=None, min_length=1, max_length=500)
    consent_accepted: Literal[True]
    consent_version: Literal["abuse-report-v1"]
    turnstile_token: SecretStr | None = Field(
        default=None, min_length=1, max_length=2048
    )

    @field_validator("message_id", mode="before")
    @classmethod
    def wire_uuid(cls, value):
        return UUID(value) if isinstance(value, str) else value

    @field_validator("qr_token")
    @classmethod
    def token(cls, value):
        if not re.fullmatch(r"[A-Za-z0-9_-]{20,80}", value.get_secret_value()):
            raise ValueError("Invalid token syntax")
        return value

    @field_validator("consent_accepted", mode="before")
    @classmethod
    def consent(cls, value):
        if value is not True:
            raise ValueError("Explicit consent required")
        return value

    @field_validator("message")
    @classmethod
    def plain(cls, value):
        if value is not None and (
            not value.strip() or re.search(r"[\x00-\x08\x0b-\x1f\x7f-\x9f<>]", value)
        ):
            raise ValueError("Plain text required")
        return value

    def semantic(self):
        return {
            "qr_token": self.qr_token.get_secret_value(),
            "message_id": str(self.message_id) if self.message_id else None,
            "category": self.category,
            "message": self.message,
            "consent_accepted": True,
            "consent_version": self.consent_version,
        }


class Receipt(Closed):
    status: Literal["accepted"]


class Rule(Closed):
    duration_seconds: Positive
    anchor: Literal["created_at", "case_closed_at"]


class Retention(Closed):
    report: Rule
    case: Rule
    budget: Rule
    proof: Rule
    receipt: Rule
    audit: Rule

    @model_validator(mode="after")
    def processing_windows(self):
        if any(
            getattr(self, k).anchor != "created_at"
            for k in ("budget", "proof", "receipt")
        ):
            raise ValueError("Processing records require an explicit creation anchor")
        if self.budget.duration_seconds < 900 or self.proof.duration_seconds < 330:
            raise ValueError("Policy cannot erase a live security window")
        return self


class Policy(Closed):
    schema_version: Annotated[int, Field(ge=1, le=1, strict=True)]
    approval_reference: Reference
    notice_reference: Reference
    consent_version: Literal["abuse-report-v1"]
    intake_enabled: bool
    triage_enabled: bool
    hmac_key_version: Positive
    hmac_key_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    retention: Retention


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def policy(row, *, intake=False, settings=None):
    try:
        value = Policy.model_validate(row["body"])
        now = datetime.now(UTC)
        start = datetime.fromisoformat(row["effective_at"])
        end = datetime.fromisoformat(row["expires_at"])
        if (
            row["revoked"]
            or not start <= now < end
            or hashlib.sha256(canonical(row["body"]).encode()).hexdigest()
            != row["sha256"]
            or not (value.intake_enabled if intake else value.triage_enabled)
        ):
            raise Unavailable()
        if intake and (
            str(settings.abuse_report_policy_id) != row["policy_id"]
            or settings.abuse_report_policy_version != row["version"]
            or settings.abuse_report_hmac_key_version != value.hmac_key_version
            or hashlib.sha256(index_key(settings)).hexdigest() != value.hmac_key_sha256
        ):
            raise Unavailable()
        return value
    except (ValueError, KeyError, TypeError, AttributeError):
        raise Unavailable() from None


def index_key(settings):
    try:
        value = base64.b64decode(
            settings.abuse_report_hmac_key.get_secret_value(), validate=True
        )
        if len(value) != 32:
            raise ValueError()
        return value
    except (ValueError, TypeError, AttributeError):
        raise Unavailable() from None


def fingerprint(key, purpose, value):
    return hmac.new(
        key,
        ("SafeReturn:abuse:v1:" + purpose + ":" + canonical(value)).encode(),
        hashlib.sha256,
    ).hexdigest()


def unique_json(raw):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError("Duplicate JSON field")
            result[k] = v
        return result

    return json.loads(
        raw,
        object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Invalid JSON")),
    )
