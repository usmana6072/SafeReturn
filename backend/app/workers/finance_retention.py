"""Durable finance Sheet projection and policy-bound private-artifact cleanup primitives."""

import argparse
import json
import logging
import re
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

import httpx
import jwt
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import AccessError
from app.core.config import Settings
from app.core.print_render import PrintUnavailable
from app.db.runtime import worker_transaction
from app.db.session import Database
from app.integrations.payment_storage import PaymentStorage
from app.integrations.print_storage import PrintStore

logger = logging.getLogger(__name__)
SHEET_COLUMNS = [
    "order_id",
    "order_number",
    "payment_status",
    "fulfillment_status",
    "currency",
    "amount",
    "payment_method",
    "sender_account",
    "evidence",
    "export_version",
    "reconciliation_time",
]


class SheetProvider(Protocol):
    def upsert(self, *, row_key: str, values: dict[str, str]) -> None: ...


class SheetProviderError(Exception):
    """The provider could not accept a projection; the durable state remains authoritative."""

    def __init__(self, code: str, *, transient: bool = True):
        self.code = (
            code if re.fullmatch(r"[a-z0-9_.-]{1,80}", code) else "provider_failure"
        )
        self.transient = transient
        super().__init__(code)


class LeaseLost(Exception):
    """The worker lost its lease fence; execution must abort without writing results."""


class PrivateObjectStore(Protocol):
    def delete(self, *, bucket: str, object_key: str) -> bool: ...


@contextmanager
def finance_serialization(database):
    """Serialize mirror writers across processes without holding business row locks.

    Session advisory lock is released explicitly before returning to the pool;
    connection loss also releases it. Contention yields to a later bounded run.
    """
    with database.engine.connect() as connection:
        acquired = connection.execute(
            text("SELECT pg_try_advisory_lock(560056, 1)")
        ).scalar_one()
        connection.commit()
        try:
            yield acquired
        finally:
            if acquired:
                try:
                    connection.execute(text("SELECT pg_advisory_unlock(560056, 1)"))
                    connection.commit()
                except SQLAlchemyError:
                    connection.invalidate()
                    raise


@dataclass(frozen=True)
class SheetProjection:
    row_key: str
    values: dict[str, str]


def build_masked_sheet_projection(row: dict) -> SheetProjection:
    """Build a strictly masked and allowlisted reporting view for Google Sheets.

    Never contains: full bank accounts, IBANs, customer delivery address, phone,
    ICE profile notes, QR activation secrets, or private storage signed URLs.
    """
    order_id = str(row["order_id"])
    return SheetProjection(
        row_key=order_id,
        values={
            "order_id": order_id,
            "order_number": str(row.get("order_number") or order_id[:8]),
            "payment_status": str(row["payment_status"]),
            "fulfillment_status": str(row.get("fulfillment_status") or "unallocated"),
            "currency": str(row["currency_code"]),
            "amount": str(row["total_pkr"]),
            "payment_method": str(row.get("payment_method") or "manual_bank"),
            "sender_account": "masked",
            "evidence": "private",
            "export_version": str(int(row.get("last_export_version") or 0) + 1),
            "reconciliation_time": datetime.now(UTC).isoformat(),
        },
    )


class GoogleSheetsProvider:
    """Production Google Sheets adapter; fails closed when unconfigured."""

    def __init__(
        self, settings: Settings, transport: httpx.BaseTransport | None = None
    ):
        self.spreadsheet_id = settings.google_sheets_spreadsheet_id
        self.sa_json = settings.google_sheets_service_account_json
        self.transport = transport
        self.approved = settings.google_sheets_approved
        self.tab = settings.google_sheets_tab

    def upsert(self, *, row_key: str, values: dict[str, str]) -> None:
        if not self.spreadsheet_id or not self.sa_json:
            raise SheetProviderError("google_sheets_not_configured", transient=False)

        try:
            sa_data = json.loads(self.sa_json.get_secret_value())
            if not isinstance(sa_data, dict):
                raise TypeError("invalid_credentials")
            token_uri = sa_data.get("token_uri", "https://oauth2.googleapis.com/token")
            client_email = sa_data["client_email"]
            private_key = sa_data["private_key"]
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            raise SheetProviderError(
                "google_sheets_invalid_credentials", transient=False
            ) from None

        if not self.approved or not self.tab:
            raise SheetProviderError("google_sheets_not_approved", transient=False)
        if values.get("order_id") != row_key:
            raise SheetProviderError("sheet_row_key_mismatch", transient=False)
        if token_uri != "https://oauth2.googleapis.com/token":
            raise SheetProviderError(
                "google_sheets_invalid_credentials", transient=False
            )

        try:
            now = int(datetime.now(UTC).timestamp())
            payload = {
                "iss": client_email,
                "sub": client_email,
                "aud": token_uri,
                "iat": now,
                "exp": now + 3600,
                "scope": "https://www.googleapis.com/auth/spreadsheets",
            }
            assertion = jwt.encode(payload, private_key, algorithm="RS256")

            with httpx.Client(timeout=10.0, transport=self.transport) as client:
                token_resp = client.post(
                    token_uri,
                    data={
                        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                        "assertion": assertion,
                    },
                )
                if token_resp.status_code != 200:
                    raise SheetProviderError("provider_auth_failure", transient=True)
                access_token = token_resp.json()["access_token"]

                headers = {"Authorization": f"Bearer {access_token}"}
                range_name = self.tab + "!A:K"
                row_data = [
                    values.get("order_id", ""),
                    values.get("order_number", ""),
                    values.get("payment_status", ""),
                    values.get("fulfillment_status", ""),
                    values.get("currency", ""),
                    values.get("amount", ""),
                    values.get("payment_method", ""),
                    values.get("sender_account", "masked"),
                    values.get("evidence", "private"),
                    values.get("export_version", "1"),
                    values.get("reconciliation_time", ""),
                ]
                # The worker must serialize all writes to the approved range.
                base = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}/values/"
                existing = client.get(base + range_name, headers=headers)
                if existing.status_code != 200:
                    raise SheetProviderError("provider_read_failed")
                rows = existing.json().get("values", [])
                if not rows or rows[0] != SHEET_COLUMNS:
                    raise SheetProviderError(
                        "sheet_columns_not_approved", transient=False
                    )
                matches = [
                    (i + 1, row)
                    for i, row in enumerate(rows)
                    if row and row[0] == row_key
                ]
                if len(matches) > 1:
                    raise SheetProviderError("duplicate_sheet_rows", transient=False)
                if matches:
                    position, previous = matches[0]
                    if len(previous) < 10 or int(previous[9]) > int(
                        values["export_version"]
                    ):
                        raise SheetProviderError(
                            "sheet_version_conflict", transient=False
                        )
                    resp = client.put(
                        base
                        + f"{self.tab}!A{position}:K{position}?valueInputOption=RAW",
                        headers=headers,
                        json={"values": [row_data]},
                    )
                    if resp.status_code != 200:
                        raise SheetProviderError("provider_unavailable")
                    return
                # RAW prevents spreadsheet formula evaluation of exported text.
                append_url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}/values/{range_name}:append?valueInputOption=RAW"
                resp = client.post(
                    append_url,
                    headers=headers,
                    json={"values": [row_data]},
                )
                if resp.status_code not in (200, 201):
                    raise SheetProviderError("provider_unavailable", transient=True)
        except SheetProviderError:
            raise
        except (httpx.HTTPError, ValueError, KeyError, TypeError, jwt.PyJWTError):
            raise SheetProviderError("provider_unavailable", transient=True) from None


class StorageStore:
    """Unified adapter for private object store deletion."""

    def __init__(
        self,
        settings: Settings,
        payment_transport: httpx.BaseTransport | None = None,
        print_transport: httpx.BaseTransport | None = None,
    ):
        self.settings = settings
        self.payment_transport = payment_transport
        self.print_transport = print_transport

    def delete(self, *, bucket: str, object_key: str) -> bool:
        if bucket == "private-payment-evidence":
            store = PaymentStorage(self.settings, transport=self.payment_transport)
            return store.delete(object_key)
        elif bucket == "private-order-print":
            store = PrintStore(self.settings, transport=self.print_transport)
            return store.delete(object_key)
        else:
            raise ValueError(f"Unsupported storage bucket: {bucket}")


def claim_finance_job(
    database: Database,
    settings: Settings,
    job_id: UUID | None = None,
) -> dict | None:
    """Claim a due finance.sync job under the worker lease fence."""
    owner = settings.finance_worker_id[:60] + ":" + uuid4().hex
    with worker_transaction(database, owner) as db:
        row = (
            db.execute(
                text(
                    """
                    SELECT * FROM public.durable_jobs
                    WHERE job_kind='finance.sync'
                      AND (CAST(:id AS uuid) IS NULL OR id=:id)
                      AND (
                        (status IN ('pending', 'retry') AND next_attempt_at <= clock_timestamp())
                        OR (status='leased' AND lease_until <= clock_timestamp())
                      )
                    ORDER BY created_at, id
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                    """
                ),
                {"id": job_id},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None

        if row["attempt_count"] >= settings.finance_max_attempts:
            db.execute(
                text(
                    """
                    UPDATE public.durable_jobs
                    SET status='dead', lease_owner=NULL, lease_until=NULL,
                        last_error_code='attempts_exhausted'
                    WHERE id=:id
                    """
                ),
                {"id": row["id"]},
            )
            return None

        db.execute(
            text(
                """
                UPDATE public.durable_jobs
                SET status='leased', lease_owner=:owner,
                    lease_until=clock_timestamp() + make_interval(secs=>:seconds),
                    attempt_count=attempt_count+1
                WHERE id=:id
                """
            ),
            {
                "id": row["id"],
                "owner": owner,
                "seconds": settings.finance_lease_seconds,
            },
        )
        return dict(row, lease_owner=owner, attempt_count=row["attempt_count"] + 1)


def fence_finance_job(db, lease: dict) -> None:
    """Assert active lease ownership and validity under lock."""
    ok = db.execute(
        text(
            """
            SELECT id FROM public.durable_jobs
            WHERE id=:id AND status='leased' AND lease_owner=:owner
              AND attempt_count=:attempt AND lease_until > clock_timestamp()
            FOR UPDATE
            """
        ),
        {
            "id": lease["id"],
            "owner": lease["lease_owner"],
            "attempt": lease["attempt_count"],
        },
    ).first()
    if ok is None:
        raise LeaseLost()


def complete_finance_job(db, lease: dict) -> None:
    """Mark the leased job completed and clear ownership."""
    completed = db.execute(
        text(
            """
            UPDATE public.durable_jobs
            SET status='completed', completed_at=clock_timestamp(),
                lease_owner=NULL, lease_until=NULL, last_error_code=NULL
            WHERE id=:id AND status='leased' AND lease_owner=:owner
              AND attempt_count=:attempt AND lease_until > clock_timestamp()
            RETURNING id
            """
        ),
        {
            "id": lease["id"],
            "owner": lease["lease_owner"],
            "attempt": lease["attempt_count"],
        },
    ).scalar_one_or_none()
    if completed is None:
        raise LeaseLost()


def fail_finance_job(db, lease: dict, error_code: str, max_attempts: int) -> None:
    """Schedule retry or mark dead on exhausted attempts."""
    if lease["attempt_count"] >= max_attempts:
        db.execute(
            text("""UPDATE public.finance_sheet_sync SET status='failed',
            last_error_code=:err,updated_at=clock_timestamp() WHERE order_id=:oid"""),
            {"oid": lease["order_id"], "err": error_code},
        )
        db.execute(
            text(
                """
                UPDATE public.durable_jobs
                SET status='dead', lease_owner=NULL, lease_until=NULL,
                    last_error_code=:err
                WHERE id=:id AND status='leased' AND lease_owner=:owner
                """
            ),
            {"id": lease["id"], "owner": lease["lease_owner"], "err": error_code},
        )
    else:
        db.execute(
            text(
                """
                UPDATE public.durable_jobs
                SET status='retry', lease_owner=NULL, lease_until=NULL,
                    last_error_code=:err,
                    next_attempt_at=clock_timestamp() + make_interval(secs=>LEAST(3600, 10 * power(2, LEAST(attempt_count, 8))::int) + floor(random()*10)::int)
                WHERE id=:id AND status='leased' AND lease_owner=:owner
                """
            ),
            {"id": lease["id"], "owner": lease["lease_owner"], "err": error_code},
        )


def process_sheet_sync(
    database: Database,
    provider: SheetProvider,
    *,
    worker_id: str,
    sync_id: UUID | None = None,
    order_id: UUID | None = None,
    lease: dict | None = None,
) -> bool:
    """Execute finance sheet synchronization.

    Outages never roll back verified payment or allocation state.
    """
    with worker_transaction(database, worker_id) as session:
        if lease is None:
            raise LeaseLost("A durable finance lease is required")
        fence_finance_job(session, lease)
        row = (
            session.execute(
                text(
                    """
                SELECT s.id, s.order_id, s.sheet_row_key, s.last_export_version, s.status,
                       o.order_number, o.total_pkr, o.currency_code, o.payment_status,
                       o.fulfillment_status
                FROM public.finance_sheet_sync s
                JOIN public.orders o ON o.id=s.order_id
                WHERE (CAST(:sync_id AS uuid) IS NULL OR s.id=:sync_id)
                  AND (CAST(:order_id AS uuid) IS NULL OR s.order_id=:order_id)
                  AND s.status IN ('pending', 'retry', 'synced')
                FOR UPDATE OF s
                """
                ),
                {"sync_id": sync_id, "order_id": order_id},
            )
            .mappings()
            .one_or_none()
        )

        if row is None:
            return False
        if row["status"] == "synced":
            return True

        current_sync_id = row["id"]
        projection = build_masked_sheet_projection(dict(row))

    # Outbound call to external Google Sheets provider runs OUTSIDE database locks
    try:
        provider.upsert(row_key=projection.row_key, values=projection.values)
    except SheetProviderError as err:
        lease["failure_code"] = err.code
        lease["permanent_failure"] = not err.transient
        with worker_transaction(database, worker_id) as session:
            fence_finance_job(session, lease)
            session.execute(
                text(
                    """
                    UPDATE public.finance_sheet_sync
                    SET status=:status, attempt_count=attempt_count+1,
                        last_error_code=:err, updated_at=clock_timestamp()
                    WHERE id=:id
                    """
                ),
                {
                    "id": current_sync_id,
                    "err": err.code[:80],
                    "status": "retry" if err.transient else "failed",
                },
            )
            session.execute(
                text(
                    """
                    INSERT INTO public.audit_events
                      (actor_user_id, actor_kind, action, target_type, target_id, safe_details)
                    VALUES (NULL, 'system', 'finance.sheet_sync_failed', 'finance_sheet_sync', :id,
                            CAST(:details AS jsonb))
                    """
                ),
                {
                    "id": current_sync_id,
                    "details": json.dumps(
                        {"reason_code": err.code[:80]}, separators=(",", ":")
                    ),
                },
            )
        return False

    # Provider success: record only under the original lease fence.
    with worker_transaction(database, worker_id) as session:
        fence_finance_job(session, lease)
        updated = session.execute(
            text(
                """
                UPDATE public.finance_sheet_sync
                SET status='synced', sheet_row_key=:row_key,
                    last_export_version=last_export_version+1,
                    last_synced_at=clock_timestamp(), last_error_code=NULL,
                    attempt_count=attempt_count+1, updated_at=clock_timestamp()
                WHERE id=:id
                  AND last_export_version=:version
                  AND EXISTS(SELECT 1 FROM public.orders o WHERE o.id=:oid
                    AND o.payment_status=:payment AND o.fulfillment_status=:fulfillment)
                RETURNING id
                """
            ),
            {
                "id": current_sync_id,
                "row_key": projection.row_key,
                "version": row["last_export_version"],
                "oid": row["order_id"],
                "payment": row["payment_status"],
                "fulfillment": row["fulfillment_status"],
            },
        ).scalar_one_or_none()
        if updated is None:
            return True  # A newer committed event owns the pending projection.
        session.execute(
            text(
                """
                INSERT INTO public.audit_events
                  (actor_user_id, actor_kind, action, target_type, target_id, safe_details)
                VALUES (NULL, 'system', 'finance.sheet_synced', 'finance_sheet_sync', :id,
                        CAST(:details AS jsonb))
                """
            ),
            {
                "id": current_sync_id,
                "details": json.dumps({"outcome": "synced"}, separators=(",", ":")),
            },
        )
    return True


def run_one_finance_sync(
    database: Database,
    settings: Settings,
    provider: SheetProvider | None = None,
    job_id: UUID | None = None,
) -> bool:
    """Durable worker execution slice for finance sync jobs."""
    with finance_serialization(database) as acquired:
        if not acquired:
            return False
        return _run_finance_locked(database, settings, provider, job_id)


def _run_finance_locked(database, settings, provider, job_id):
    lease = claim_finance_job(database, settings, job_id)
    if lease is None:
        return False

    prov = provider or GoogleSheetsProvider(settings)
    order_id = lease["order_id"]

    success = False
    try:
        success = process_sheet_sync(
            database,
            prov,
            worker_id=lease["lease_owner"],
            order_id=order_id,
            lease=lease,
        )
    except LeaseLost:
        return False
    except (SQLAlchemyError, httpx.HTTPError, SheetProviderError, ValueError) as e:
        logger.warning("Unexpected finance sync failure (err=%s)", type(e).__name__)
        success = False

    try:
        with worker_transaction(database, lease["lease_owner"]) as db:
            fence_finance_job(db, lease)
            if success:
                complete_finance_job(db, lease)
            else:
                fail_finance_job(
                    db,
                    lease,
                    lease.get("failure_code", "provider_unavailable"),
                    lease["attempt_count"]
                    if lease.get("permanent_failure")
                    else settings.finance_max_attempts,
                )
    except LeaseLost:
        logger.warning("Finance worker lost lease fence for job %s", lease["id"])
        return False

    return success


def cleanup_private_artifact(
    database: Database,
    store: PrivateObjectStore,
    *,
    worker_id: str,
    artifact_id: UUID,
    resource_type: str = "print_artifact",
    settings: Settings | None = None,
    lease: dict | None = None,
) -> dict:
    """Commit deletion authorization before remote I/O, then fence the tombstone.

    The committed intent serializes hold/job admission and survives ambiguous
    remote responses, a crash, or a failed local commit. Recovery repeats only
    the same immutable object deletion, with authoritative absence verification.
    """
    if resource_type not in {"print_artifact", "payment_evidence"}:
        return {"deleted": False, "reason": "unsupported_resource"}
    cfg = settings or Settings()
    approval = (
        cfg.print_retention_approval
        if resource_type == "print_artifact"
        else cfg.evidence_retention_approval
    )
    if not approval or not approval.strip():
        return {"deleted": False, "reason": "policy_not_approved"}
    if (
        lease is None
        or lease["aggregate_id"] != artifact_id
        or lease["aggregate_type"] != resource_type
    ):
        raise LeaseLost("A matching durable cleanup lease is required")
    with worker_transaction(database, worker_id) as session:
        fence_retention_job(session, lease)
        intent = session.execute(
            text("SELECT public.sr_retention_prepare(:job,:attempt,:approval)"),
            {
                "job": lease["id"],
                "attempt": lease["attempt_count"],
                "approval": approval,
            },
        ).scalar_one()
    if not intent.get("authorized"):
        return intent
    # No database row lock or transaction spans the provider operation.
    with worker_transaction(database, worker_id) as session:
        fence_retention_job(session, lease)
    if (
        store.delete(bucket=intent["bucket"], object_key=intent["object_key"])
        is not True
    ):
        raise OSError("storage_delete_unconfirmed")
    with worker_transaction(database, worker_id) as session:
        fence_retention_job(session, lease)
        session.execute(
            text("SELECT public.sr_retention_finish(:job,:attempt)"),
            {"job": lease["id"], "attempt": lease["attempt_count"]},
        )
        complete_retention_job(session, lease)
    return {
        "deleted": True,
        "artifact_id": str(artifact_id),
        "resource_type": resource_type,
    }


def claim_retention_job(
    database: Database,
    settings: Settings,
    job_id: UUID | None = None,
) -> dict | None:
    """Claim a due retention.cleanup job under worker lease fence."""
    owner = settings.retention_worker_id[:60] + ":" + uuid4().hex
    with worker_transaction(database, owner) as db:
        row = (
            db.execute(
                text(
                    """
                    SELECT * FROM public.durable_jobs
                    WHERE job_kind='retention.cleanup'
                      AND (CAST(:id AS uuid) IS NULL OR id=:id)
                      AND (
                        (status IN ('pending', 'retry') AND next_attempt_at <= clock_timestamp())
                        OR (status='leased' AND lease_until <= clock_timestamp())
                      )
                    ORDER BY created_at, id
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                    """
                ),
                {"id": job_id},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None

        if row["attempt_count"] >= settings.retention_max_attempts:
            db.execute(
                text(
                    """
                    UPDATE public.durable_jobs
                    SET status='dead', lease_owner=NULL, lease_until=NULL,
                        last_error_code='attempts_exhausted'
                    WHERE id=:id
                    """
                ),
                {"id": row["id"]},
            )
            return None

        db.execute(
            text(
                """
                UPDATE public.durable_jobs
                SET status='leased', lease_owner=:owner,
                    lease_until=clock_timestamp() + make_interval(secs=>:seconds),
                    attempt_count=attempt_count+1
                WHERE id=:id
                """
            ),
            {
                "id": row["id"],
                "owner": owner,
                "seconds": settings.retention_lease_seconds,
            },
        )
        return dict(row, lease_owner=owner, attempt_count=row["attempt_count"] + 1)


def fence_retention_job(db, lease: dict) -> None:
    """Assert active retention job lease ownership and validity under lock."""
    ok = db.execute(
        text(
            """
            SELECT id FROM public.durable_jobs
            WHERE id=:id AND status='leased' AND lease_owner=:owner
              AND attempt_count=:attempt AND lease_until > clock_timestamp()
            FOR UPDATE
            """
        ),
        {
            "id": lease["id"],
            "owner": lease["lease_owner"],
            "attempt": lease["attempt_count"],
        },
    ).first()
    if ok is None:
        raise LeaseLost()


def complete_retention_job(db, lease: dict) -> None:
    """Mark the leased retention job completed and clear ownership."""
    completed = db.execute(
        text(
            """
            UPDATE public.durable_jobs
            SET status='completed', completed_at=clock_timestamp(),
                lease_owner=NULL, lease_until=NULL, last_error_code=NULL
            WHERE id=:id AND status='leased' AND lease_owner=:owner
              AND attempt_count=:attempt AND lease_until > clock_timestamp()
            RETURNING id
            """
        ),
        {
            "id": lease["id"],
            "owner": lease["lease_owner"],
            "attempt": lease["attempt_count"],
        },
    ).scalar_one_or_none()
    if completed is None:
        raise LeaseLost()


def fail_retention_job(db, lease: dict, error_code: str, max_attempts: int) -> None:
    """Schedule retry or mark dead for retention cleanup job."""
    if lease["attempt_count"] >= max_attempts:
        db.execute(
            text(
                """
                UPDATE public.durable_jobs
                SET status='dead', lease_owner=NULL, lease_until=NULL,
                    last_error_code=:err
                WHERE id=:id AND status='leased' AND lease_owner=:owner
                """
            ),
            {"id": lease["id"], "owner": lease["lease_owner"], "err": error_code},
        )
    else:
        db.execute(
            text(
                """
                UPDATE public.durable_jobs
                SET status='retry', lease_owner=NULL, lease_until=NULL,
                    last_error_code=:err,
                    next_attempt_at=clock_timestamp() + make_interval(secs=>LEAST(3600, 10 * power(2, LEAST(attempt_count, 8))::int) + floor(random()*10)::int)
                WHERE id=:id AND status='leased' AND lease_owner=:owner
                """
            ),
            {"id": lease["id"], "owner": lease["lease_owner"], "err": error_code},
        )


def run_one_retention_cleanup(
    database: Database,
    settings: Settings,
    store: PrivateObjectStore | None = None,
    job_id: UUID | None = None,
) -> dict:
    """Durable worker execution slice for private artifact retention cleanup jobs."""
    lease = claim_retention_job(database, settings, job_id)
    if lease is None:
        return {"claimed": False}

    st = store or StorageStore(settings)
    resource_type = lease["aggregate_type"]
    artifact_id = lease["aggregate_id"]

    result = {}
    try:
        result = cleanup_private_artifact(
            database,
            st,
            worker_id=lease["lease_owner"],
            artifact_id=artifact_id,
            resource_type=resource_type,
            settings=settings,
            lease=lease,
        )
    except LeaseLost:
        return {"claimed": True, "success": False, "error": "lease_lost"}
    except (
        SQLAlchemyError,
        httpx.HTTPError,
        ValueError,
        OSError,
        AccessError,
        PrintUnavailable,
    ) as e:
        logger.warning("Unexpected retention cleanup error (err=%s)", type(e).__name__)
        result = {"deleted": False, "reason": "worker_exception"}

    if result.get("deleted"):
        return {"claimed": True, "result": result}
    try:
        with worker_transaction(database, lease["lease_owner"]) as db:
            fence_retention_job(db, lease)
            if result.get("deleted") or result.get("reason") in (
                "already_deleted",
                "not_found",
            ):
                complete_retention_job(db, lease)
            else:
                fail_retention_job(
                    db,
                    lease,
                    result.get("reason", "failed")[:80],
                    settings.retention_max_attempts,
                )
    except LeaseLost:
        logger.warning("Retention worker lost lease fence for job %s", lease["id"])
        return {"claimed": True, "success": False, "error": "lease_lost"}

    return {"claimed": True, "result": result}


def main():
    parser = argparse.ArgumentParser(
        description="Finance Sheet sync and retention worker"
    )
    parser.add_argument("--mode", choices=["sync", "cleanup", "all"], default="sync")
    args = parser.parse_args()

    settings = Settings()
    database = Database.from_settings(
        settings.model_copy(update={"database_url": settings.worker_database_url})
    )
    if database is None:
        raise RuntimeError("Worker database login is required")
    try:
        if args.mode in ("sync", "all"):
            claimed = run_one_finance_sync(database, settings)
            print(f"Finance sync job executed: {claimed}")
        if args.mode in ("cleanup", "all"):
            with worker_transaction(database, settings.retention_worker_id) as db:
                for kind, approval in (
                    ("print_artifact", settings.print_retention_approval),
                    ("payment_evidence", settings.evidence_retention_approval),
                ):
                    if approval:
                        db.execute(
                            text("SELECT public.sr_retention_schedule(:kind)"),
                            {"kind": kind},
                        )
            claimed_retention = run_one_retention_cleanup(database, settings)
            print(f"Retention cleanup job executed: {claimed_retention}")
    finally:
        database.close()


if __name__ == "__main__":
    main()
