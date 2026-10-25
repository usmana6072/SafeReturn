"""API-100 restricted metadata search. No details/reason or contextual delegation."""

from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel
from sqlalchemy import text

from app.api.auth import Authenticated, require_staff
from app.api.v1.catalog import CatalogRoute, fail
from app.api.v1.fulfillment import bounds, page_cursor, paged
from app.api.v1.privacy_exports import recent

router = APIRouter(tags=["restricted audit"], route_class=CatalogRoute)
# Historical action strings are not trusted as labels. Unknown strings remain
# findable by time/actor/target but never expose free text or guessed semantics.
ACTIONS = frozenset(
    {
        "account.profile.update",
        "account.deletion.requested",
        "profile.updated",
        "support_case.created",
        "support_case.changed",
        "support_case.read",
        "privacy.export.requested",
        "privacy.export.decided",
        "privacy.export.granted",
        "privacy.export.consumed",
        "privacy.export.ready",
        "privacy.export.generation_failed",
        "storage.retention_hold_placed",
        "storage.retention_hold_released",
        "storage.cleanup_retry",
        "storage.deletion_authorized",
        "storage.artifact_deleted",
        "finance.sheet_sync_retry",
        "payment.evidence.read",
        "payment.finance.read",
        "shipment.created",
        "shipment.updated",
        "audit.search",
    }
)
Target = Literal[
    "user_profile",
    "qr",
    "tag_pair",
    "order",
    "shipment",
    "payment_attempt",
    "payment_evidence",
    "print_artifact",
    "print_job",
    "support_case",
    "privacy_export",
    "finance_sheet_sync",
    "audit_search",
]
TARGETS = set(Target.__args__)


class Event(BaseModel):
    id: UUID
    occurred_at: datetime
    actor_kind: Literal["customer", "staff", "system", "anonymous"]
    actor_user_id: UUID | None
    action: str
    target_type: str
    target_id: UUID | None


class Page(BaseModel):
    items: list[Event]
    next_cursor: str | None
    scope: Literal["security_metadata"] = "security_metadata"


@router.get("/admin/audit-events", operation_id="API-100", response_model=Page)
def search(
    context: Authenticated,
    request: Request,
    response: Response,
    actor_id: UUID | None = None,
    target_id: UUID | None = None,
    target_type: Target | None = None,
    action: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    cursor: str | None = None,
    limit: int = 20,
):
    require_staff(context, "security_admin")
    recent(context)
    allowed = {
        "actor_id",
        "target_id",
        "target_type",
        "action",
        "start",
        "end",
        "cursor",
        "limit",
    }
    if any(
        k not in allowed or len(request.query_params.getlist(k)) != 1
        for k in request.query_params
    ):
        fail(422, "INVALID_QUERY")
    bounds(limit)
    if action is not None and action not in ACTIONS:
        fail(422, "INVALID_ACTION")
    now = datetime.now(UTC)
    end = end or now
    start = start or end - timedelta(days=7)
    if (
        start.tzinfo is None
        or end.tzinfo is None
        or not timedelta(0) < end - start <= timedelta(days=31)
    ):
        fail(422, "INVALID_TIME_RANGE")
    stamp, ident = page_cursor(cursor)
    # Existing indexes cover actor/target lookup; broad time searches must also
    # fail within a small budget rather than sorting an unlimited history.
    context.session.execute(text("SET LOCAL statement_timeout='3000ms'"))
    # Cursor is navigation, never authority: all filters and role checks reapply.
    rows = (
        context.session.execute(
            text("""SELECT id,occurred_at,actor_kind,actor_user_id,action,target_type,target_id
      FROM public.audit_events WHERE occurred_at>=:start AND occurred_at<:end
      AND (CAST(:actor AS uuid) IS NULL OR actor_user_id=:actor)
      AND (CAST(:target AS uuid) IS NULL OR target_id=:target)
      AND (CAST(:kind AS text) IS NULL OR target_type=:kind)
      AND (CAST(:action AS text) IS NULL OR action=:action)
      AND (CAST(:stamp AS timestamptz) IS NULL OR (occurred_at,id)<(:stamp,:ident))
      ORDER BY occurred_at DESC,id DESC LIMIT :lim"""),
            {
                "start": start,
                "end": end,
                "actor": actor_id,
                "target": target_id,
                "kind": target_type,
                "action": action,
                "stamp": stamp,
                "ident": ident,
                "lim": limit + 1,
            },
        )
        .mappings()
        .all()
    )
    items = [dict(r, created_at=r["occurred_at"]) for r in rows]
    page = paged(items, limit)
    for row in page["items"]:
        row.pop("created_at")
        row["action"] = (
            row["action"] if row["action"] in ACTIONS else "restricted_event"
        )
        row["target_type"] = (
            row["target_type"] if row["target_type"] in TARGETS else "restricted"
        )
    # No filters/private strings enter the read audit. Append-only source intact.
    context.session.execute(
        text("""INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type)
      VALUES(:uid,'staff','audit.search','audit_search')"""),
        {"uid": context.principal.user_id},
    )
    response.headers["Cache-Control"] = "private, no-store"
    return page
