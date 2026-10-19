"""Own account summary and conditional display-name/locale edits (API-020/021)."""

import re
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Header, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text

from app.api.auth import (
    STAFF_ROLES,
    AccessError,
    Authenticated,
    require_verified_account,
)
from app.core.profile_crypto import ProfileCryptoUnavailable, encrypt

router = APIRouter()


class StaffSecurity(BaseModel):
    roles: list[str]
    mfa_verified: bool
    capabilities: list[str]


# Navigation/page capabilities mirror existing endpoint role lists; they never
# replace require_staff on the actual privileged reads and mutations.
STAFF_CAPABILITIES = {
    "catalog.manage": frozenset({"operations", "security_admin", "superadmin"}),
    "payments.review": frozenset({"finance"}),
    "fulfillment.manage": frozenset({"operations"}),
    "support.manage": frozenset({"support"}),
    "notifications.manage": frozenset({"operations", "security_admin"}),
    "printing.manage": frozenset({"operations"}),
}


@router.get(
    "/me/staff-security", operation_id="staffSecurity", response_model=StaffSecurity
)
def staff_security(context: Authenticated):
    # AAL1 bootstrap only. Privileged operations retain their require_staff guards.
    require_verified_account(context)
    roles = list(
        context.session.execute(
            text(
                "SELECT role FROM public.staff_roles WHERE user_id=:uid AND revoked_at IS NULL ORDER BY role"
            ),
            {"uid": context.principal.user_id},
        ).scalars()
    )
    roles = [role for role in roles if role in STAFF_ROLES]
    if not roles:
        raise AccessError(403)
    capabilities = sorted(
        capability
        for capability, allowed_roles in STAFF_CAPABILITIES.items()
        if context.mfa_verified and allowed_roles.intersection(roles)
    )
    return StaffSecurity(
        roles=roles, mfa_verified=context.mfa_verified, capabilities=capabilities
    )


class MaskedContact(BaseModel):
    phone: str | None


class AccountSummary(BaseModel):
    user_id: str
    display_name: str | None
    preferred_locale: Literal["en", "ur"]
    email_verified: bool
    masked_contact: MaskedContact
    version: str


class ProfileEdit(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    display_name: str | None = Field(default=None, max_length=120)
    preferred_locale: Literal["en", "ur"] | None = None

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value):
        if value is not None:
            value = value.strip()
            if not value or any(ord(c) < 32 or ord(c) == 127 for c in value):
                raise ValueError("Invalid name")
        return value


def failure(status, code, message):
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "message_ur": "درخواست مکمل نہیں ہو سکی۔",
                "request_id": uuid4().hex,
                "details": {},
            }
        },
        headers={"Cache-Control": "no-store"},
    )


def summary(context):
    row = (
        context.session.execute(
            text("""
        SELECT display_name,preferred_locale,phone_ciphertext IS NOT NULL AS has_phone,
               extract(epoch FROM updated_at)::text AS version
        FROM public.user_profiles WHERE user_id=:uid
    """),
            {"uid": context.principal.user_id},
        )
        .mappings()
        .one_or_none()
    )
    return {
        "user_id": str(context.principal.user_id),
        "display_name": row["display_name"] if row else None,
        "preferred_locale": row["preferred_locale"] if row else "en",
        "email_verified": context.email_verified,
        # No decryption or new phone collection before the approved key lifecycle.
        "masked_contact": {"phone": "••••" if row and row["has_phone"] else None},
        "version": row["version"] if row else "0",
    }


@router.get("/me", operation_id="API-020", response_model=AccountSummary)
def get_me(context: Authenticated, response: Response):
    data = summary(context)
    response.headers["ETag"] = '"' + data["version"] + '"'
    return data


@router.patch(
    "/me",
    operation_id="API-021",
    response_model=AccountSummary,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {"schema": ProfileEdit.model_json_schema()}
            },
        }
    },
)
async def edit_me(
    request: Request,
    context: Authenticated,
    response: Response,
    if_match: str | None = Header(default=None),
):
    # Parse here so error responses never echo submitted personal data/tokens.
    if request.headers.get("content-type", "").split(";")[0] != "application/json":
        return failure(415, "UNSUPPORTED_MEDIA_TYPE", "JSON required.")
    if not if_match or not re.fullmatch(r'"(?:0|[0-9]{1,12}\.[0-9]{1,6})"', if_match):
        return failure(
            400, "VALIDATION_ERROR", "A current If-Match version is required."
        )
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 2048:
            return failure(400, "VALIDATION_ERROR", "Invalid profile update.")
    try:
        edit = ProfileEdit.model_validate_json(raw)
        fields = edit.model_fields_set
        if not fields or (
            "preferred_locale" in fields and edit.preferred_locale is None
        ):
            raise ValueError()
    except ValueError:
        return failure(400, "VALIDATION_ERROR", "Invalid profile update.")
    uid = context.principal.user_id
    version = if_match[1:-1]
    if version == "0":
        changed = context.session.execute(
            text("""
            INSERT INTO public.user_profiles(user_id,display_name,preferred_locale)
            VALUES(:uid,:name,:locale) ON CONFLICT(user_id) DO NOTHING RETURNING user_id
        """),
            {
                "uid": uid,
                "name": edit.display_name,
                "locale": edit.preferred_locale or "en",
            },
        ).scalar_one_or_none()
    else:
        changed = context.session.execute(
            text("""
            UPDATE public.user_profiles SET
              display_name=CASE WHEN :name_set THEN :name ELSE display_name END,
              preferred_locale=CASE WHEN :locale_set THEN :locale ELSE preferred_locale END,
              updated_at=greatest(clock_timestamp(),updated_at+interval '1 microsecond')
            WHERE user_id=:uid AND extract(epoch FROM updated_at)::text=:version
            RETURNING user_id
        """),
            {
                "uid": uid,
                "version": version,
                "name_set": "display_name" in fields,
                "name": edit.display_name,
                "locale_set": "preferred_locale" in fields,
                "locale": edit.preferred_locale,
            },
        ).scalar_one_or_none()
    if changed is None:
        return failure(
            412, "VERSION_MISMATCH", "Account changed. Reload and try again."
        )
    data = summary(context)
    context.session.execute(
        text("""
            INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,safe_details)
            VALUES(:uid,'customer','account.profile.update','user_profile',:uid,
                   jsonb_build_object('version',CAST(:version AS text)))
        """),
        {"uid": uid, "version": data["version"]},
    )
    response.headers["ETag"] = '"' + data["version"] + '"'
    return data


class DeletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    confirm: Literal[True]
    reason: str | None = Field(default=None, max_length=1000)

    @field_validator("confirm", mode="before")
    @classmethod
    def explicit_confirmation(cls, value):
        if type(value) is not bool or value is not True:
            raise ValueError("Explicit confirmation required")
        return value


@router.get("/me/privacy-consents", operation_id="API-022")
def privacy_consents(context: Authenticated):
    # Audit rows are immutable historical evidence, scoped to the actor. Do not
    # infer former owners' consents from the currently owned QR profiles.
    rows = (
        context.session.execute(
            text("""
        SELECT id,target_id,action,occurred_at,safe_details->>'reason_code' AS consent_version,
               safe_details->>'to_status' AS active_state
        FROM public.audit_events WHERE actor_user_id=:uid AND target_type='qr'
          AND action IN ('profile.ice.updated','profile.ice_contact.updated','profile.ice_contact.removed','profile.whatsapp.updated')
        ORDER BY occurred_at DESC,id DESC LIMIT 101
    """),
            {"uid": context.principal.user_id},
        )
        .mappings()
        .all()
    )
    return {
        "items": [
            {
                "id": r["id"],
                "qr_id": r["target_id"],
                "purpose": r["action"],
                "version": r["consent_version"],
                "timestamp": r["occurred_at"],
                "state_scope": "recorded_event",
                "active": r["active_state"]
                in ("published", "medical_published", "enabled"),
            }
            for r in rows[:100]
        ],
        "has_more": len(rows) > 100,
    }


@router.post(
    "/me/account-deletion-requests",
    operation_id="API-023",
    status_code=202,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {"schema": DeletionRequest.model_json_schema()}
            },
        }
    },
)
async def request_account_deletion(request: Request, context: Authenticated):
    if request.headers.get("content-type", "").split(";")[0] != "application/json":
        return failure(415, "UNSUPPORTED_MEDIA_TYPE", "JSON required.")
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 8192:
            return failure(400, "VALIDATION_ERROR", "Invalid deletion request.")
    try:
        body = DeletionRequest.model_validate_json(raw)
    except ValueError:
        return failure(400, "VALIDATION_ERROR", "Invalid deletion request.")
    authenticated = context.principal.authentication_time
    if (
        authenticated is None
        or not 0 <= datetime.now(UTC).timestamp() - authenticated <= 300
    ):
        return failure(
            403,
            "REAUTH_REQUIRED",
            "Please sign in again before requesting account deletion.",
        )
    if not context.email_verified:
        return failure(
            403,
            "EMAIL_VERIFICATION_REQUIRED",
            "Confirm your email before requesting account deletion.",
        )
    uid = context.principal.user_id
    # Serialize retries per actor; reference an immutable audit marker rather
    # than co-opting an unrelated privacy support case.
    context.session.execute(
        text(
            "SELECT pg_advisory_xact_lock(hashtextextended(CAST(:uid AS text),570023))"
        ),
        {"uid": uid},
    )
    existing = (
        context.session.execute(
            text("""
        SELECT c.id,c.status FROM public.support_cases c JOIN public.audit_events a
          ON a.target_id=c.id AND a.target_type='support_case'
        WHERE a.actor_user_id=:uid AND a.action='account.deletion.requested'
          AND c.opened_by_user_id=:uid AND c.status IN ('open','investigating')
        ORDER BY c.created_at DESC LIMIT 1
    """),
            {"uid": uid},
        )
        .mappings()
        .one_or_none()
    )
    if existing:
        return {"request_id": existing["id"], "status": existing["status"]}
    cipher = version = None
    if body.reason:
        try:
            cipher, version = encrypt(
                context.session.info["settings"],
                uid,
                "account_deletion_reason",
                body.reason,
            )
        except ProfileCryptoUnavailable:
            return failure(
                503,
                "PROVIDER_UNAVAILABLE",
                "Your request could not be stored securely. Please try again.",
            )
    request_id = context.session.execute(
        text("""
        INSERT INTO public.support_cases(opened_by_user_id,case_type,description_ciphertext,description_key_version)
        VALUES(:uid,'privacy',:cipher,:version) RETURNING id
    """),
        {"uid": uid, "cipher": cipher, "version": version},
    ).scalar_one()
    context.session.execute(
        text("""
        INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id)
        VALUES(:uid,'customer','account.deletion.requested','support_case',:id)
    """),
        {"uid": uid, "id": request_id},
    )
    return {"request_id": request_id, "status": "open"}
