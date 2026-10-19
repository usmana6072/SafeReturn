"""Recipient-scoped finder inbox operations."""

import base64
import binascii
import math
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text

from app.api.auth import Authenticated, require_message_recipient
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt

router = APIRouter(tags=["finder-inbox"])


class MessageUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    status: str = Field(pattern="^(viewed|archived|flagged)$")


def _parse_cursor(value: str | None):
    if value is None:
        return None, None
    try:
        if len(value) > 256:
            raise ValueError
        raw = base64.b64decode(
            value + "=" * (-len(value) % 4), altchars=b"-_", validate=True
        ).decode()
        stamp, identifier = raw.split("|", 1)
        timestamp = datetime.fromisoformat(stamp)
        if timestamp.tzinfo is None:
            raise ValueError
        return timestamp.astimezone(UTC), UUID(identifier)
    except (ValueError, UnicodeError, binascii.Error):
        raise HTTPException(status_code=422, detail="Invalid inbox cursor") from None


def _cursor(row):
    return (
        base64.urlsafe_b64encode(
            f"{row['submitted_at'].isoformat()}|{row['id']}".encode()
        )
        .decode()
        .rstrip("=")
    )


def _message_or_404(context, message_id: UUID):
    row = (
        context.session.execute(
            text(
                """
            SELECT m.id,m.qr_id,m.finder_name,m.finder_email_ciphertext,
                   m.finder_phone_ciphertext,m.finder_contact_key_version,
                   m.message_text_ciphertext,m.message_key_version,m.status,
                   m.submitted_at,q.tag_type
            FROM public.finder_messages m
            JOIN public.qr_codes q ON q.id=m.qr_id
            WHERE m.id=:id AND m.recipient_owner_user_id=:uid AND m.deleted_at IS NULL AND m.status<>'deleted'
            """
            ),
            {"id": message_id, "uid": context.principal.user_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Finder message not found")
    return row


def _decrypt_message(context, row):
    settings = (
        context.session.info.get("settings")
        if hasattr(context.session, "info") and "settings" in context.session.info
        else None
    )
    if settings is None:
        from app.core.config import Settings

        settings = Settings()
    try:
        email = (
            decrypt(
                settings,
                row["qr_id"],
                "finder_email",
                row["finder_email_ciphertext"],
                row["finder_contact_key_version"],
            )
            if row["finder_email_ciphertext"]
            else None
        )
        phone = (
            decrypt(
                settings,
                row["qr_id"],
                "finder_phone",
                row["finder_phone_ciphertext"],
                row["finder_contact_key_version"],
            )
            if row["finder_phone_ciphertext"]
            else None
        )
        message = decrypt(
            settings,
            row["qr_id"],
            "finder_message",
            row["message_text_ciphertext"],
            row["message_key_version"],
        )
    except ProfileCryptoUnavailable:
        raise HTTPException(
            status_code=503, detail="Finder message is temporarily unavailable"
        ) from None
    return email, phone, message


@router.get("/me/finder-messages", operation_id="API-050")
def list_finder_messages(
    context: Authenticated,
    cursor: str | None = Query(default=None, max_length=256),
    limit: int = Query(default=25, ge=1, le=100),
    status: str | None = Query(default=None, pattern="^(new|viewed|archived|flagged)$"),
    qr_id: UUID | None = None,
):
    if status is not None and status not in {"new", "viewed", "archived", "flagged"}:
        raise HTTPException(status_code=422, detail="Invalid message status")
    cursor_ts, cursor_id = _parse_cursor(cursor)
    rows = list(
        context.session.execute(
            text(
                """
                SELECT m.id,m.qr_id,m.finder_name,m.status,m.submitted_at,q.tag_type,
                       lp.item_label AS qr_label,
                       (SELECT o.status FROM public.notification_outbox o
                        WHERE o.aggregate_type='finder_message' AND o.aggregate_id=m.id
                          AND o.event_type='finder_message.created' AND o.recipient_user_id=:uid
                        ORDER BY o.created_at DESC,o.id DESC LIMIT 1) AS notification_status
                FROM public.finder_messages m
                JOIN public.qr_codes q ON q.id=m.qr_id
                LEFT JOIN public.lost_item_profiles lp ON lp.qr_id=m.qr_id
                WHERE m.recipient_owner_user_id=:uid
                  AND m.deleted_at IS NULL AND m.status<>'deleted'
                  AND (CAST(:cursor AS timestamptz) IS NULL OR (m.submitted_at,m.id) < (CAST(:cursor AS timestamptz),CAST(:cursor_id AS uuid)))
                  AND (CAST(:status AS text) IS NULL OR m.status=CAST(:status AS text))
                  AND (CAST(:qr_id AS uuid) IS NULL OR m.qr_id=CAST(:qr_id AS uuid))
                ORDER BY m.submitted_at DESC,m.id DESC
                LIMIT :limit
                """
            ),
            {
                "uid": context.principal.user_id,
                "cursor": cursor_ts,
                "cursor_id": cursor_id,
                "status": status,
                "qr_id": qr_id,
                "limit": limit + 1,
            },
        ).mappings()
    )
    items = [
        {
            "id": row["id"],
            "qr_id": row["qr_id"],
            "tag_type": row["tag_type"],
            "finder_name": row["finder_name"],
            "qr_label": row["qr_label"],
            "notification_status": row["notification_status"],
            "status": row["status"],
            "submitted_at": row["submitted_at"],
        }
        for row in rows[:limit]
    ]
    return {
        "items": items,
        "next_cursor": _cursor(rows[limit - 1]) if len(rows) > limit else None,
    }


@router.get("/me/finder-messages/{message_id}", operation_id="API-051")
def get_finder_message(message_id: UUID, context: Authenticated):
    row = _message_or_404(context, message_id)
    email, phone, message = _decrypt_message(context, row)
    settings = (
        context.session.info.get("settings")
        if hasattr(context.session, "info") and "settings" in context.session.info
        else None
    )
    if settings is None:
        from app.core.config import Settings

        settings = Settings()
    location = (
        context.session.execute(
            text(
                """
            SELECT latitude_ciphertext,longitude_ciphertext,accuracy_m,
                   consent_at,key_version
            FROM public.finder_message_locations
            WHERE finder_message_id=:id
            """
            ),
            {"id": message_id},
        )
        .mappings()
        .one_or_none()
    )
    decoded_location = None
    if location is not None:
        try:
            latitude = decrypt(
                settings,
                row["qr_id"],
                "finder_latitude",
                location["latitude_ciphertext"],
                location["key_version"],
            )
            longitude = decrypt(
                settings,
                row["qr_id"],
                "finder_longitude",
                location["longitude_ciphertext"],
                location["key_version"],
            )
        except ProfileCryptoUnavailable:
            raise HTTPException(
                status_code=503, detail="Finder location is temporarily unavailable"
            ) from None
        try:
            lat, lon = float(latitude), float(longitude)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=503, detail="Finder location is temporarily unavailable"
            ) from None
        if not (
            math.isfinite(lat)
            and math.isfinite(lon)
            and -90 <= lat <= 90
            and -180 <= lon <= 180
        ):
            raise HTTPException(
                status_code=503, detail="Finder location is temporarily unavailable"
            )
        if location["consent_at"] is not None:
            decoded_location = {
                "latitude": lat,
                "longitude": lon,
                "accuracy_m": location["accuracy_m"],
                "maps_url": f"https://www.google.com/maps?q={lat},{lon}",
                "consent_at": location["consent_at"],
            }
    return {
        "id": row["id"],
        "tag_type": row["tag_type"],
        "finder_name": row["finder_name"],
        "finder_email": email,
        "finder_phone": phone,
        "message": message,
        "status": row["status"],
        "submitted_at": row["submitted_at"],
        "location": decoded_location,
    }


@router.patch("/me/finder-messages/{message_id}", operation_id="API-052")
def update_finder_message(
    message_id: UUID, body: MessageUpdate, context: Authenticated
):
    require_message_recipient(context, message_id)
    updated = (
        context.session.execute(
            text(
                """
            UPDATE public.finder_messages
            SET status=:status
            WHERE id=:id AND recipient_owner_user_id=:uid AND deleted_at IS NULL AND status<>'deleted'
            RETURNING id,status
            """
            ),
            {"id": message_id, "uid": context.principal.user_id, "status": body.status},
        )
        .mappings()
        .one_or_none()
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Finder message not found")
    return dict(updated)


@router.delete(
    "/me/finder-messages/{message_id}", operation_id="API-053", status_code=204
)
def delete_finder_message(message_id: UUID, context: Authenticated, response: Response):
    # A customer deletion request hides the message without destroying evidence.
    # Physical erasure remains blocked until an approved retention policy exists;
    # deleted_at is reserved for the actual policy-authorized tombstone.
    require_message_recipient(context, message_id)
    context.session.execute(
        text(
            """
            UPDATE public.finder_messages
            SET status='deleted'
            WHERE id=:id AND recipient_owner_user_id=:uid AND deleted_at IS NULL AND status<>'deleted'
            """
        ),
        {"id": message_id, "uid": context.principal.user_id},
    )
    response.headers["Cache-Control"] = "no-store"
