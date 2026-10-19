"""Durable at-least-once finder notifications with fenced, short transactions."""

import argparse
import re
import secrets
import sys
import time
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt, encrypt
from app.db.runtime import worker_transaction
from app.db.session import Database

SUBJECT = "SafeReturn: someone sent you a finder message"
HTML = (
    "<p>You have a new finder message.</p>"
    "<p>Sign in to SafeReturn to view it securely.</p>"
    "<p>This notification does not confirm that an item has been returned.</p>"
)


class NotificationProvider(Protocol):
    def send(self, *, to: str, subject: str, html: str, idempotency_key: str) -> str:
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


class ResendProvider:
    def __init__(self, settings: Settings):
        if (
            not settings.resend_api_key
            or not settings.resend_api_key.get_secret_value().strip()
            or not settings.notification_from_email
            or any(c in settings.notification_from_email for c in "\r\n")
        ):
            raise NotificationProviderError("provider_not_configured", transient=False)
        self.api_key = settings.resend_api_key.get_secret_value()
        self.from_email = settings.notification_from_email
        self.timeout = settings.notification_http_timeout_seconds

    def send(self, *, to: str, subject: str, html: str, idempotency_key: str) -> str:
        if not _valid_recipient(to):
            raise NotificationProviderError("invalid_recipient", transient=False)
        try:
            response = httpx.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Idempotency-Key": idempotency_key,
                },
                json={
                    "from": self.from_email,
                    "to": [to],
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
                provider_id = response.json()["id"]
                if not isinstance(provider_id, str) or not re.fullmatch(
                    r"[A-Za-z0-9_-]{1,150}", provider_id
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


def _claim_one(session, worker_id: str, lease_seconds: int):
    row = (
        session.execute(
            text("""
            WITH candidate AS (
                SELECT id FROM public.notification_outbox
                WHERE event_type='finder_message.created'
                  AND aggregate_type='finder_message' AND payload_version=1
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
            RETURNING o.id,o.aggregate_id,o.recipient_email_snapshot_ciphertext,
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
    )


def _prepare_recipient(session, claimed, settings):
    args = {
        "id": claimed.id,
        "attempt": claimed.attempt,
        "snapshot": None,
        "version": None,
    }
    query = text(
        "SELECT public.sr_notification_recipient(:id,:attempt,:snapshot,CAST(:version AS smallint))"
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
        except ProfileCryptoUnavailable:
            error = NotificationProviderError(
                "recipient_decryption_failed", transient=False
            )
        except NotificationProviderError as preparation_error:
            error = preparation_error
        except LeaseLost:
            # Commit the claim; an expired lease is recoverable by another attempt.
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
            provider_id = provider.send(
                to=recipient,
                subject=SUBJECT,
                html=HTML,
                idempotency_key=claimed.idempotency_key,
            )
            if not isinstance(provider_id, str) or not re.fullmatch(
                r"[A-Za-z0-9_-]{1,150}", provider_id
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
        provider = ResendProvider(settings)
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
