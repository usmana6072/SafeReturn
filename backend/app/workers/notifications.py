"""Durable at-least-once finder notifications with fenced, short transactions."""

import argparse
import json
import math
import re
import secrets
import sys
import time
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from email.utils import parseaddr
from html import escape
from typing import Protocol
from uuid import UUID, uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt, encrypt
from app.core.public_site import PUBLIC_WEB_ORIGIN
from app.db.runtime import worker_transaction
from app.db.session import Database

SUBJECT = "SafeReturn: someone sent you a finder message"
HTML = (
    "<h1>Someone found your item</h1>"
    "<p>A finder sent the following information through your SafeReturn QR code.</p>"
)
DELIVERY_FROM_EMAIL = "SafeReturn <services@safereturnqr.me>"
DELIVERY_SUBJECT = "SafeReturn: your order has been delivered"


def delivery_email_html(data):
    values = [
        ("Order", data["order_number"]),
        ("Courier", data.get("carrier") or "Not provided"),
        ("Tracking number", data.get("tracking_reference") or "Not provided"),
        ("Delivered at", data["delivered_at"]),
    ]
    if data.get("received_by"):
        values.append(("Received by", data["received_by"]))
    rows = "".join(
        f'<tr><th align="left" style="padding:8px">{escape(label)}</th><td style="padding:8px">{escape(str(value))}</td></tr>'
        for label, value in values
    )
    items = "".join(
        f"<li>{escape(item['product_name_snapshot'])} × {item['quantity']}</li>"
        for item in data["items"]
    )
    return (
        '<!doctype html><html><body style="font-family:Arial,sans-serif;max-width:640px;margin:auto;padding:24px;color:#173c3a">'
        "<h1>Your SafeReturn order has been delivered</h1><p>Thank you for choosing SafeReturn. Your order has been marked as delivered.</p>"
        f"<table>{rows}</table><h2>Your items</h2><ul>{items}</ul>"
        f'<p><a href="{PUBLIC_WEB_ORIGIN}/orders/{data["order_id"]}">View your order</a></p>'
        "<p>Need help with your delivery? Contact services@safereturnqr.me.</p></body></html>"
    )


def finder_email_html(settings, claimed, row):
    """Escape every finder value; use immutable message fields for safe retries."""

    def decode(field, ciphertext, version):
        return (
            decrypt(settings, row["qr_id"], field, ciphertext, version)
            if ciphertext
            else None
        )

    email = decode(
        "finder_email",
        row["finder_email_ciphertext"],
        row["finder_contact_key_version"],
    )
    phone = decode(
        "finder_phone",
        row["finder_phone_ciphertext"],
        row["finder_contact_key_version"],
    )
    message = decode(
        "finder_message", row["message_text_ciphertext"], row["message_key_version"]
    )
    values = [
        ("QR reference", str(row["qr_id"])),
        (
            "Received (UTC)",
            row["submitted_at"].astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        ),
        ("Finder name", row["finder_name"] or "Not provided"),
        ("Email", email or "Not provided"),
        ("Phone", phone or "Not provided"),
        ("Preferred contact", row["preferred_contact"] or "No preference"),
    ]
    rows = "".join(
        f'<tr><th align="left" style="padding:8px">{escape(label)}</th><td style="padding:8px">{escape(value)}</td></tr>'
        for label, value in values
    )
    location = ""
    if row["latitude_ciphertext"] and row["longitude_ciphertext"]:
        try:
            lat = float(
                decode(
                    "finder_latitude",
                    row["latitude_ciphertext"],
                    row["location_key_version"],
                )
            )
            lon = float(
                decode(
                    "finder_longitude",
                    row["longitude_ciphertext"],
                    row["location_key_version"],
                )
            )
        except (ValueError, TypeError):
            raise NotificationProviderError(
                "invalid_finder_location", transient=False
            ) from None
        if not (
            math.isfinite(lat)
            and math.isfinite(lon)
            and -90 <= lat <= 90
            and -180 <= lon <= 180
        ):
            raise NotificationProviderError("invalid_finder_location", transient=False)
        accuracy = (
            f" (accuracy: {escape(str(row['accuracy_m']))} m)"
            if row["accuracy_m"] is not None
            else ""
        )
        location = f'<h2>Shared location</h2><p>{lat}, {lon}{accuracy}</p><p><a href="https://www.google.com/maps?q={lat},{lon}">View location on Google Maps</a></p>'
    link = f"{PUBLIC_WEB_ORIGIN}/inbox/{claimed.aggregate_id}"
    return (
        '<!doctype html><html><body style="font-family:Arial,sans-serif;color:#173c3a;max-width:640px;margin:auto;padding:24px">'
        + HTML
        + f'<table style="border-collapse:collapse;width:100%">{rows}</table>'
        + f'<h2>Finder message</h2><p style="white-space:pre-wrap;overflow-wrap:anywhere" dir="auto">{escape(message or "")}</p>'
        + location
        + f'<p><a href="{link}">View message in your SafeReturn inbox</a></p>'
        + "<p>Contact the finder using the details above to arrange a return. This message does not confirm that the item has been returned.</p></body></html>"
    )


class NotificationProvider(Protocol):
    def send(
        self,
        *,
        to: str,
        subject: str,
        html: str,
        idempotency_key: str,
        from_email: str | None = None,
    ) -> str:
        """Return provider acceptance ID, without claiming inbox delivery."""


class NotificationProviderError(Exception):
    def __init__(self, code: str, *, transient: bool, retry_after: int = 0):
        self.code = (
            code if re.fullmatch(r"[a-z0-9_]{1,80}", code) else "provider_failure"
        )
        self.transient = transient
        self.retry_after = max(0, min(3600, retry_after))
        super().__init__(self.code)


class LeaseLost(Exception):
    pass


def _valid_recipient(value):
    return (
        isinstance(value, str)
        and len(value) <= 254
        and bool(
            re.fullmatch(
                r"[^@\s<>\x00-\x1f]+@[^@\s<>\x00-\x1f]+\.[^@\s<>\x00-\x1f]+", value
            )
        )
    )


class BrevoProvider:
    def __init__(self, settings: Settings):
        if (
            settings.email_provider != "brevo"
            or not settings.brevo_api_key
            or not settings.brevo_api_key.get_secret_value().strip()
            or not settings.notification_from_email
            or any(c in settings.notification_from_email for c in "\r\n")
        ):
            raise NotificationProviderError("provider_not_configured", transient=False)
        self.api_key = settings.brevo_api_key.get_secret_value()
        self.from_email = settings.notification_from_email
        self.from_name, self.from_address = parseaddr(self.from_email)
        if not _valid_recipient(self.from_address):
            raise NotificationProviderError("provider_not_configured", transient=False)
        self.timeout = settings.notification_http_timeout_seconds

    def _sender(self, override: str | None) -> dict[str, str]:
        name, address = parseaddr(override or self.from_email)
        if not _valid_recipient(address):
            raise NotificationProviderError("provider_not_configured", transient=False)
        return {"email": address, **({"name": name} if name else {})}

    def send(
        self,
        *,
        to: str,
        subject: str,
        html: str,
        idempotency_key: str,
        from_email: str | None = None,
    ) -> str:
        if not _valid_recipient(to):
            raise NotificationProviderError("invalid_recipient", transient=False)
        try:
            response = httpx.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": self.api_key,
                    "Idempotency-Key": idempotency_key,
                },
                json={
                    "sender": self._sender(from_email),
                    "to": [{"email": to}],
                    "subject": subject,
                    "html": html,
                },
                timeout=self.timeout,
                follow_redirects=False,
            )
        except httpx.HTTPError:
            raise NotificationProviderError(
                "provider_network", transient=True
            ) from None
        if 200 <= response.status_code < 300:
            try:
                provider_id = response.json()["messageId"]
                if not isinstance(provider_id, str) or not re.fullmatch(
                    r"[A-Za-z0-9_@.<>-]{1,254}", provider_id
                ):
                    raise ValueError()
                return provider_id
            except (TypeError, KeyError, ValueError):
                raise NotificationProviderError(
                    "provider_invalid_response", transient=True
                ) from None
        concurrent = False
        if response.status_code == 409:
            try:
                concurrent = (
                    response.json().get("name") == "concurrent_idempotent_requests"
                )
            except (ValueError, AttributeError):
                pass
        try:
            retry_after = int(response.headers.get("Retry-After", "0"))
        except ValueError:
            retry_after = 0
        raise NotificationProviderError(
            f"provider_http_{response.status_code}",
            transient=concurrent
            or response.status_code in (408, 429)
            or response.status_code >= 500,
            retry_after=retry_after,
        )


@dataclass(frozen=True)
class ClaimedNotification:
    id: UUID
    aggregate_id: UUID
    recipient_ciphertext: bytes | None
    recipient_key_version: int | None
    idempotency_key: str
    attempt: int
    first_attempt_at: datetime
    lease_until: datetime
    event_type: str = "finder_message.created"
    payload_ciphertext: bytes | None = None
    payload_key_version: int | None = None


def _claim_one(session, worker_id: str, lease_seconds: int):
    row = (
        session.execute(
            text("""
            WITH candidate AS (
                SELECT id FROM public.notification_outbox
                WHERE ((event_type='finder_message.created' AND aggregate_type='finder_message')
                    OR (event_type='shipment.delivered' AND aggregate_type='shipment')) AND payload_version=1
                  AND ((status IN ('pending','retry') AND next_attempt_at<=clock_timestamp())
                    OR (status='leased' AND lease_until<=clock_timestamp()))
                ORDER BY next_attempt_at,created_at,id
                FOR UPDATE SKIP LOCKED LIMIT 1
            )
            UPDATE public.notification_outbox o
            SET status='leased',lease_owner=:worker,
                lease_until=clock_timestamp()+(:lease_seconds * interval '1 second'),
                attempt_count=o.attempt_count+1
            FROM candidate WHERE o.id=candidate.id
            RETURNING o.id,o.aggregate_id,o.event_type,o.payload_ciphertext,o.payload_key_version,o.recipient_email_snapshot_ciphertext,
                o.recipient_email_key_version,o.idempotency_key,o.attempt_count,o.lease_until,
                COALESCE((SELECT min(a.attempted_at) FROM public.notification_attempts a
                          WHERE a.outbox_id=o.id),clock_timestamp()) AS first_attempt_at
        """),
            {"worker": worker_id, "lease_seconds": lease_seconds},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        return None
    session.execute(
        text(
            "INSERT INTO public.notification_attempts(outbox_id,attempt_number,outcome) VALUES(:id,:attempt,'unknown')"
        ),
        {"id": row["id"], "attempt": row["attempt_count"]},
    )
    return ClaimedNotification(
        id=row["id"],
        aggregate_id=row["aggregate_id"],
        recipient_ciphertext=row["recipient_email_snapshot_ciphertext"],
        recipient_key_version=row["recipient_email_key_version"],
        idempotency_key=row["idempotency_key"],
        attempt=row["attempt_count"],
        first_attempt_at=row["first_attempt_at"],
        lease_until=row["lease_until"],
        event_type=row["event_type"],
        payload_ciphertext=row["payload_ciphertext"],
        payload_key_version=row["payload_key_version"],
    )


def _prepare_recipient(session, claimed, settings):
    args = {
        "id": claimed.id,
        "attempt": claimed.attempt,
        "snapshot": None,
        "version": None,
    }
    function = (
        "sr_shipment_notification_recipient"
        if claimed.event_type == "shipment.delivered"
        else "sr_notification_recipient"
    )
    query = text(
        f"SELECT public.{function}(:id,:attempt,:snapshot,CAST(:version AS smallint))"
    )
    recipient = session.execute(query, args).scalar_one()
    if recipient is None:
        raise NotificationProviderError("recipient_unavailable", transient=False)
    if claimed.recipient_ciphertext is None:
        if not _valid_recipient(recipient):
            raise NotificationProviderError("invalid_recipient", transient=False)
        ciphertext, version = encrypt(
            settings, claimed.aggregate_id, "owner_email", recipient
        )
        saved = session.execute(
            query, {**args, "snapshot": ciphertext, "version": version}
        ).scalar_one()
        if saved is None:
            raise LeaseLost()
        claimed = replace(
            claimed, recipient_ciphertext=ciphertext, recipient_key_version=version
        )
    return claimed


def _finish(
    database,
    worker,
    claimed,
    *,
    status,
    error=None,
    provider_id=None,
    next_attempt=None,
):
    try:
        with worker_transaction(database, worker) as session:
            # Attempt number fences an expired claim even when a process reuses its worker ID.
            current = session.execute(
                text("""
                    SELECT id FROM public.notification_outbox
                    WHERE id=:id AND status='leased' AND lease_owner=:worker
                      AND attempt_count=:attempt AND lease_until>clock_timestamp()
                    FOR UPDATE
                """),
                {"id": claimed.id, "worker": worker, "attempt": claimed.attempt},
            ).scalar_one_or_none()
            if current is None:
                return False
            outcome = (
                "success"
                if status == "sent"
                else (
                    "transient_failure"
                    if error and error.transient
                    else "permanent_failure"
                )
            )
            session.execute(
                text("""
                    UPDATE public.notification_attempts SET outcome=:outcome,
                        finished_at=clock_timestamp(),provider_message_id=:provider,error_code=:error
                    WHERE outbox_id=:id AND attempt_number=:attempt
                """),
                {
                    "outcome": outcome,
                    "provider": provider_id,
                    "error": error.code if error else None,
                    "id": claimed.id,
                    "attempt": claimed.attempt,
                },
            )
            result = session.execute(
                text("""
                    UPDATE public.notification_outbox SET status=CAST(:status AS varchar),
                        provider_message_id=:provider,last_error_code=:error,
                        next_attempt_at=COALESCE(CAST(:next_attempt AS timestamptz),next_attempt_at),
                        sent_at=CASE WHEN CAST(:status AS varchar)='sent' THEN clock_timestamp() ELSE sent_at END,
                        lease_owner=NULL,lease_until=NULL
                    WHERE id=:id AND status='leased' AND lease_owner=:worker
                      AND attempt_count=:attempt AND lease_until>clock_timestamp()
                """),
                {
                    "status": status,
                    "provider": provider_id,
                    "error": error.code if error else None,
                    "next_attempt": next_attempt,
                    "id": claimed.id,
                    "worker": worker,
                    "attempt": claimed.attempt,
                },
            )
            if result.rowcount != 1:
                raise LeaseLost()
        return True
    except LeaseLost:
        return False


def process_one(
    database: Database,
    settings: Settings,
    provider: NotificationProvider,
    *,
    worker_id: str | None = None,
) -> bool:
    if (
        settings.notification_lease_seconds
        <= settings.notification_http_timeout_seconds + 5
    ):
        raise NotificationProviderError("lease_timeout_configuration", transient=False)
    worker = worker_id or settings.notification_worker_id
    error = None
    html = None
    # The lease, attempt and encrypted recipient are durable before any provider call.
    with worker_transaction(database, worker) as session:
        claimed = _claim_one(session, worker, settings.notification_lease_seconds)
        if claimed is None:
            return False
        try:
            if claimed.attempt > settings.notification_max_attempts:
                raise NotificationProviderError("attempts_exhausted", transient=False)
            if claimed.attempt > 1 and datetime.now(
                UTC
            ) - claimed.first_attempt_at >= timedelta(hours=23):
                raise NotificationProviderError(
                    "idempotency_window_expired", transient=False
                )
            claimed = _prepare_recipient(session, claimed, settings)
            if claimed.event_type == "shipment.delivered":
                html = delivery_email_html(
                    json.loads(
                        decrypt(
                            settings,
                            claimed.aggregate_id,
                            "shipment_delivery",
                            claimed.payload_ciphertext,
                            claimed.payload_key_version,
                        )
                    )
                )
            else:
                html = _finder_html(session, settings, claimed)
        except ProfileCryptoUnavailable:
            error = NotificationProviderError(
                "recipient_decryption_failed", transient=False
            )
        except (ValueError, KeyError, TypeError):
            error = NotificationProviderError(
                "notification_payload_invalid", transient=False
            )
        except NotificationProviderError as preparation_error:
            error = preparation_error
        except LeaseLost:
            return True
    provider_id = None
    if error is None:
        try:
            if claimed.lease_until <= datetime.now(UTC):
                return True
            recipient = decrypt(
                settings,
                claimed.aggregate_id,
                "owner_email",
                claimed.recipient_ciphertext,
                claimed.recipient_key_version,
            )
            if not _valid_recipient(recipient):
                raise NotificationProviderError("invalid_recipient", transient=False)
            options = (
                {"from_email": DELIVERY_FROM_EMAIL}
                if claimed.event_type == "shipment.delivered"
                else {}
            )
            provider_id = provider.send(
                to=recipient,
                subject=DELIVERY_SUBJECT if options else SUBJECT,
                html=html,
                idempotency_key=claimed.idempotency_key,
                **options,
            )
            if not isinstance(provider_id, str) or not re.fullmatch(
                r"[A-Za-z0-9_@.<>-]{1,254}", provider_id
            ):
                raise NotificationProviderError(
                    "provider_invalid_response", transient=True
                )
        except ProfileCryptoUnavailable:
            error = NotificationProviderError(
                "recipient_decryption_failed", transient=False
            )
        except NotificationProviderError as provider_error:
            error = provider_error
    if error is None:
        _finish(database, worker, claimed, status="sent", provider_id=provider_id)
    elif error.transient and claimed.attempt < settings.notification_max_attempts:
        base = min(3600, 5 * 2 ** min(claimed.attempt - 1, 10))
        delay = min(
            3600, max(base + secrets.randbelow(base // 4 + 1), error.retry_after)
        )
        _finish(
            database,
            worker,
            claimed,
            status="retry",
            error=error,
            next_attempt=datetime.now(UTC) + timedelta(seconds=delay),
        )
    else:
        _finish(database, worker, claimed, status="dead", error=error)
    return True


def _finder_html(session, settings, claimed):
    row = (
        session.execute(
            text("SELECT * FROM public.sr_notification_finder_details(:id,:attempt)"),
            {"id": claimed.id, "attempt": claimed.attempt},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise NotificationProviderError("finder_message_unavailable", transient=False)
    return finder_email_html(settings, claimed, row)


def main():
    parser = argparse.ArgumentParser(
        description="SafeReturn finder notification worker"
    )
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--env-file")
    parser.add_argument("--poll-seconds", type=int, default=5, choices=range(1, 61))
    args = parser.parse_args()
    if args.env_file:
        from dotenv import load_dotenv

        load_dotenv(args.env_file)
    settings = Settings()
    settings = settings.model_copy(
        update={
            "database_url": settings.worker_database_url,
            "notification_worker_id": f"{settings.notification_worker_id[:60]}:{uuid4().hex}",
        }
    )
    database = Database.from_settings(settings)
    if database is None:
        print("Worker database is not configured.", file=sys.stderr)
        return 1
    try:
        provider = BrevoProvider(settings)
        while True:
            try:
                processed = process_one(database, settings, provider)
            except SQLAlchemyError:
                print(
                    "Notification database operation failed; lease recovery remains enabled.",
                    file=sys.stderr,
                )
                if args.once:
                    return 1
                processed = False
            if args.once:
                return 0
            if not processed:
                time.sleep(args.poll_seconds)
    except NotificationProviderError as error:
        print(error.code, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())
