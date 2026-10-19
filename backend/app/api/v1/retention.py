"""Finance Sheet sync and policy-bound private artifact retention controls."""

import base64
import json
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import Authenticated, require_staff

router = APIRouter(tags=["retention"])


class RetentionHoldRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    reason_code: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,80}$")


def _insert_hold(context, parameters):
    try:
        with context.session.begin_nested():
            context.session.execute(
                text("""INSERT INTO public.retention_holds
                (id,resource_type,resource_id,reason_code,placed_by)
                VALUES (:id,:type,:resource,:reason,:actor)"""),
                parameters,
            )
    except SQLAlchemyError as error:
        if getattr(getattr(error, "orig", None), "sqlstate", None) == "23514":
            raise HTTPException(
                status_code=409,
                detail="Hold resource unavailable or deletion already authorized",
            ) from None
        raise


def _audit(context, action: str, target_type: str, target_id: UUID, details: dict):
    context.session.execute(
        text(
            """
            INSERT INTO public.audit_events
              (actor_user_id, actor_kind, action, target_type, target_id, safe_details)
            VALUES (:actor, 'staff', :action, :target_type, :target_id,
                    CAST(:details AS jsonb))
            """
        ),
        {
            "actor": context.principal.user_id,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "details": json.dumps(details, separators=(",", ":")),
        },
    )


def _parse_cursor(cursor: str | None) -> tuple[datetime | None, UUID | None]:
    if not cursor:
        return None, None
    try:
        rem = len(cursor) % 4
        padded = cursor + "=" * (4 - rem) if rem else cursor
        raw = base64.urlsafe_b64decode(padded.encode()).decode()
        ts_str, id_str = json.loads(raw)
        return datetime.fromisoformat(ts_str), UUID(id_str)
    except (ValueError, TypeError, KeyError):
        try:
            return datetime.fromisoformat(cursor), None
        except ValueError:
            return None, None


def _encode_cursor(ts: datetime, ident: UUID) -> str:
    return (
        base64.urlsafe_b64encode(json.dumps([ts.isoformat(), str(ident)]).encode())
        .decode()
        .rstrip("=")
    )


@router.get("/admin/finance/sheet-sync", operation_id="API-238")
def list_sheet_sync(
    context: Authenticated,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
):
    require_staff(context, "finance", "security_admin", "superadmin")
    cursor_ts, cursor_id = _parse_cursor(cursor)
    fetch_limit = limit + 1
    rows = list(
        context.session.execute(
            text(
                """
                SELECT s.id, s.order_id, s.sheet_row_key, s.last_export_version,
                       CASE WHEN EXISTS(SELECT 1 FROM public.durable_jobs d
                         WHERE d.order_id=s.order_id AND d.job_kind='finance.sync' AND d.status='dead')
                         AND NOT EXISTS(SELECT 1 FROM public.durable_jobs d
                         WHERE d.order_id=s.order_id AND d.job_kind='finance.sync' AND d.status IN ('pending','retry','leased'))
                         AND s.status<>'synced' THEN 'failed' ELSE s.status END AS status,
                       s.attempt_count, s.last_error_code, s.last_synced_at, s.updated_at,
                       o.payment_status, o.fulfillment_status, o.currency_code, o.total_pkr
                FROM public.finance_sheet_sync s
                JOIN public.orders o ON o.id=s.order_id
                WHERE (CAST(:cursor_ts AS timestamptz) IS NULL OR (s.updated_at < CAST(:cursor_ts AS timestamptz) OR (s.updated_at = CAST(:cursor_ts AS timestamptz) AND s.id < CAST(:cursor_id AS uuid))))
                ORDER BY s.updated_at DESC, s.id DESC
                LIMIT :fetch_limit
                """
            ),
            {
                "cursor_ts": cursor_ts,
                "cursor_id": cursor_id,
                "fetch_limit": fetch_limit,
            },
        ).mappings()
    )
    has_more = len(rows) > limit
    page_rows = rows[:limit]
    items = [
        {
            "id": row["id"],
            "order_id": row["order_id"],
            "sheet_row_key": row["sheet_row_key"],
            "last_export_version": row["last_export_version"],
            "status": row["status"],
            "attempt_count": row["attempt_count"],
            "last_error_code": row["last_error_code"],
            "last_synced_at": row["last_synced_at"],
            "updated_at": row["updated_at"],
            "payment_status": row["payment_status"],
            "fulfillment_status": row["fulfillment_status"],
            "currency_code": row["currency_code"],
            "total_pkr": str(row["total_pkr"]),
        }
        for row in page_rows
    ]
    next_cursor = None
    if has_more and page_rows:
        last = page_rows[-1]
        next_cursor = _encode_cursor(last["updated_at"], last["id"])
    return {"items": items, "next_cursor": next_cursor}


@router.post(
    "/admin/finance/sheet-sync/{sync_id}/retry",
    operation_id="API-239",
    status_code=202,
)
def retry_sheet_sync(sync_id: UUID, context: Authenticated):
    require_staff(context, "finance", "security_admin", "superadmin")
    previous_status = context.session.execute(
        text("SELECT status FROM public.finance_sheet_sync WHERE id=:id FOR UPDATE"),
        {"id": sync_id},
    ).scalar_one_or_none()
    updated = (
        context.session.execute(
            text(
                """
            UPDATE public.finance_sheet_sync
            SET status='retry', last_error_code=NULL, updated_at=clock_timestamp()
            WHERE id=:id AND (status IN ('failed','retry') OR (status<>'synced' AND
              EXISTS(SELECT 1 FROM public.durable_jobs d WHERE d.order_id=finance_sheet_sync.order_id
                AND d.job_kind='finance.sync' AND d.status='dead')))
            RETURNING id, order_id, status
            """
            ),
            {"id": sync_id},
        )
        .mappings()
        .one_or_none()
    )
    if updated is None:
        existing = (
            context.session.execute(
                text("SELECT id, status FROM public.finance_sheet_sync WHERE id=:id"),
                {"id": sync_id},
            )
            .mappings()
            .one_or_none()
        )
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Sheet sync in status '{existing['status']}' cannot be retried",
            )
        raise HTTPException(status_code=404, detail="Eligible Sheet sync not found")

    order_id = updated["order_id"]
    context.session.execute(
        text(
            """
            INSERT INTO public.durable_jobs
              (job_kind, aggregate_type, aggregate_id, order_id, status, idempotency_key)
            SELECT 'finance.sync', 'order', :order, :order, 'pending', :key
            WHERE NOT EXISTS (
              SELECT 1 FROM public.durable_jobs WHERE order_id=:order
              AND job_kind='finance.sync' AND status IN ('pending','retry','leased')
            )
            ON CONFLICT (idempotency_key) DO NOTHING
            """
        ),
        {
            "order": order_id,
            "key": f"payment.finance:{order_id}:{uuid4().hex}",
        },
    )
    _audit(
        context,
        "finance.sheet_sync_retry",
        "finance_sheet_sync",
        sync_id,
        {"from_status": previous_status, "to_status": "retry"},
    )
    return dict(updated)


@router.get("/admin/storage/artifacts", operation_id="API-242")
def list_private_artifacts(
    context: Authenticated,
    order_id: UUID | None = None,
    job_id: UUID | None = None,
    resource_type: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
):
    require_staff(context, "operations", "finance", "security_admin", "superadmin")
    rows = context.session.execute(
        text(
            """
            SELECT a.id, 'print_artifact' AS resource_type, a.print_job_id AS owner_id,
                   a.bucket, a.object_key, a.format, a.sha256_hex, a.size_bytes,
                   a.retention_until, a.deletion_hold_reason, a.deleted_at,
                   (a.deletion_hold_reason IS NOT NULL OR public.sr_retention_held('print_artifact',a.id)) AS on_hold,
                   (SELECT jsonb_build_object('id',d.id,'status',d.status,'attempt_count',d.attempt_count,'last_error_code',d.last_error_code)
                    FROM public.durable_jobs d WHERE d.job_kind='retention.cleanup' AND d.aggregate_type='print_artifact' AND d.aggregate_id=a.id
                    ORDER BY d.created_at DESC,d.id DESC LIMIT 1) AS cleanup_job
            FROM public.print_artifacts a
            JOIN public.print_jobs j ON j.id=a.print_job_id
            WHERE (CAST(:order_id AS uuid) IS NULL OR j.order_id=CAST(:order_id AS uuid))
              AND (CAST(:job_id AS uuid) IS NULL OR j.id=CAST(:job_id AS uuid))
              AND (CAST(:resource_type AS text) IS NULL OR CAST(:resource_type AS text)='print_artifact')
            UNION ALL
            SELECT e.id, 'payment_evidence', e.attempt_id,
                   e.bucket, e.object_key, e.content_type,
                   e.sha256_hex, e.bytes_size, e.retention_until, e.deletion_hold_reason, e.deleted_at,
                   (e.deletion_hold_reason IS NOT NULL OR public.sr_retention_held('payment_evidence',e.id)),
                   (SELECT jsonb_build_object('id',d.id,'status',d.status,'attempt_count',d.attempt_count,'last_error_code',d.last_error_code)
                    FROM public.durable_jobs d WHERE d.job_kind='retention.cleanup' AND d.aggregate_type='payment_evidence' AND d.aggregate_id=e.id
                    ORDER BY d.created_at DESC,d.id DESC LIMIT 1)
            FROM public.payment_evidence e
            JOIN public.payment_attempts p ON p.id=e.attempt_id
            WHERE (CAST(:order_id AS uuid) IS NULL OR p.order_id=CAST(:order_id AS uuid))
              AND (CAST(:job_id AS uuid) IS NULL)
              AND (CAST(:resource_type AS text) IS NULL OR CAST(:resource_type AS text)='payment_evidence')
            ORDER BY deleted_at NULLS FIRST, retention_until NULLS LAST, id DESC
            LIMIT :limit
            """
        ),
        {
            "order_id": order_id,
            "job_id": job_id,
            "resource_type": resource_type,
            "limit": limit,
        },
    ).mappings()
    return {"items": [dict(row) for row in rows]}


@router.post(
    "/admin/storage/artifacts/{artifact_id}/cleanup-retry",
    operation_id="API-245",
    status_code=202,
)
def retry_artifact_cleanup(
    artifact_id: UUID, body: RetentionHoldRequest, context: Authenticated
):
    require_staff(context, "security_admin", "superadmin")
    job_id = context.session.execute(
        text("SELECT public.sr_retention_retry(:id,:reason)"),
        {"id": artifact_id, "reason": body.reason_code},
    ).scalar_one_or_none()
    if job_id is None:
        raise HTTPException(status_code=404, detail="Cleanup job not found")
    return {"job_id": job_id}


@router.post(
    "/admin/storage/artifacts/{artifact_id}/retention-holds",
    operation_id="API-243",
    status_code=201,
)
def place_retention_hold(
    artifact_id: UUID, body: RetentionHoldRequest, context: Authenticated
):
    require_staff(context, "security_admin", "superadmin")
    context.session.execute(
        text(
            "SELECT pg_advisory_xact_lock(hashtextextended(CAST(:id AS text),560056))"
        ),
        {"id": artifact_id},
    )
    # Check if resource exists and is active (not deleted)
    resource_info = (
        context.session.execute(
            text(
                """
            SELECT 'print_artifact' AS res_type, deleted_at FROM public.print_artifacts WHERE id=:id
            UNION ALL
            SELECT 'payment_evidence' AS res_type, deleted_at FROM public.payment_evidence WHERE id=:id
            UNION ALL
            SELECT 'order' AS res_type, NULL::timestamptz AS deleted_at FROM public.orders WHERE id=:id
            UNION ALL
            SELECT 'finder_message' AS res_type, deleted_at FROM public.finder_messages WHERE id=:id
            """
            ),
            {"id": artifact_id},
        )
        .mappings()
        .one_or_none()
    )

    if resource_info is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if resource_info["deleted_at"] is not None:
        raise HTTPException(
            status_code=409, detail="Artifact already deleted; cannot place hold"
        )

    resource_type = resource_info["res_type"]

    # Check for existing active hold with the same reason (idempotent)
    existing_hold = context.session.execute(
        text(
            """
            SELECT id FROM public.retention_holds
            WHERE resource_id=:resource AND reason_code=:reason AND released_at IS NULL
            """
        ),
        {"resource": artifact_id, "reason": body.reason_code},
    ).scalar_one_or_none()
    if existing_hold is not None:
        return {
            "hold_id": existing_hold,
            "resource_type": resource_type,
            "resource_id": artifact_id,
            "reason_code": body.reason_code,
        }

    hold_id = uuid4()
    _insert_hold(
        context,
        {
            "id": hold_id,
            "type": resource_type,
            "resource": artifact_id,
            "reason": body.reason_code,
            "actor": context.principal.user_id,
        },
    )
    if resource_type == "print_artifact":
        context.session.execute(
            text(
                "UPDATE public.print_artifacts SET deletion_hold_reason=:reason WHERE id=:id"
            ),
            {"id": artifact_id, "reason": body.reason_code},
        )
    elif resource_type == "payment_evidence":
        context.session.execute(
            text(
                "UPDATE public.payment_evidence SET deletion_hold_reason=:reason WHERE id=:id"
            ),
            {"id": artifact_id, "reason": body.reason_code},
        )
    _audit(
        context,
        "storage.retention_hold_placed",
        resource_type,
        artifact_id,
        {"reason_code": body.reason_code},
    )
    return {
        "hold_id": hold_id,
        "resource_type": resource_type,
        "resource_id": artifact_id,
        "reason_code": body.reason_code,
    }


@router.delete(
    "/admin/storage/artifacts/{artifact_id}/retention-holds",
    operation_id="API-244",
    status_code=204,
)
def release_retention_hold(artifact_id: UUID, context: Authenticated):
    require_staff(context, "security_admin", "superadmin")
    context.session.execute(
        text(
            "SELECT pg_advisory_xact_lock(hashtextextended(CAST(:id AS text),560056))"
        ),
        {"id": artifact_id},
    )
    released_rows = list(
        context.session.execute(
            text(
                """
                UPDATE public.retention_holds
                SET released_by=:actor, released_at=clock_timestamp()
                WHERE resource_id=:resource AND released_at IS NULL
                RETURNING id, resource_type, reason_code
                """
            ),
            {"resource": artifact_id, "actor": context.principal.user_id},
        ).mappings()
    )
    if not released_rows:
        raise HTTPException(status_code=404, detail="Active retention hold not found")
    resource_type = released_rows[0]["resource_type"]

    remaining_hold = context.session.execute(
        text(
            """
            SELECT reason_code FROM public.retention_holds
            WHERE resource_id=:resource AND released_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"resource": artifact_id},
    ).scalar_one_or_none()

    if resource_type == "print_artifact":
        context.session.execute(
            text(
                "UPDATE public.print_artifacts SET deletion_hold_reason=:reason WHERE id=:id"
            ),
            {"id": artifact_id, "reason": remaining_hold},
        )
    elif resource_type == "payment_evidence":
        context.session.execute(
            text(
                "UPDATE public.payment_evidence SET deletion_hold_reason=:reason WHERE id=:id"
            ),
            {"id": artifact_id, "reason": remaining_hold},
        )
    _audit(
        context,
        "storage.retention_hold_released",
        resource_type,
        artifact_id,
        {"reason_code": released_rows[0]["reason_code"]},
    )
