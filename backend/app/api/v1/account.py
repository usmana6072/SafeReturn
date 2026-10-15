"""Own account summary and conditional display-name/locale edits (API-020/021)."""

import re
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Header, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text

from app.api.auth import Authenticated

router = APIRouter()


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
