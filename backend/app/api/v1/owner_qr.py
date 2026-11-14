"""Read-only owner collections; current identities, never printed-copy duplicates."""

import base64
import json
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import text

from app.api.auth import (
    AccessError,
    Authenticated,
    require_pair_owner,
    require_qr_owner,
)
from app.api.v1.account import failure

router = APIRouter(tags=["owner QR"])


class TagSummary(BaseModel):
    qr_id: UUID
    pair_id: UUID | None
    pair_reference: str | None
    tag_type: Literal["lost", "ice"]
    public_status: str
    profile_label: str | None
    published: bool
    profile_version: int
    preference_version: int
    profile_complete: bool
    editable: bool
    editor_url: str


class PairSummary(BaseModel):
    pair_id: UUID
    pair_reference: str
    ownership_status: str
    inventory_status: str
    activated_at: datetime | None
    tags: list[TagSummary]


class PairPage(BaseModel):
    items: list[PairSummary]
    next_cursor: str | None


class QRPage(BaseModel):
    items: list[TagSummary]
    next_cursor: str | None


class PhysicalProduct(BaseModel):
    product_name_snapshot: str
    variant_name_snapshot: str
    copies: int


class QRDetail(TagSummary):
    physical_products: list[PhysicalProduct]


def decode_cursor(value):
    if value is None:
        return None
    try:
        if len(value) > 220:
            raise ValueError()
        data = json.loads(
            base64.b64decode(
                value + "=" * (-len(value) % 4), altchars=b"-_", validate=True
            )
        )
        if (
            not isinstance(data, dict)
            or set(data) != {"id", "at"}
            or not isinstance(data["id"], str)
            or not isinstance(data["at"], str)
        ):
            raise ValueError()
        identity, timestamp = UUID(data["id"]), datetime.fromisoformat(data["at"])
        if timestamp.tzinfo is None:
            raise ValueError()
        return identity, timestamp.astimezone(UTC)
    except (ValueError, TypeError, KeyError, OverflowError):
        return False


def encode_cursor(value, timestamp):
    return (
        base64.urlsafe_b64encode(
            json.dumps(
                {"id": str(value), "at": timestamp.isoformat()}, separators=(",", ":")
            ).encode()
        )
        .decode()
        .rstrip("=")
    )


TAG_SELECT = """
 SELECT q.id AS qr_id,q.pair_id,p.pair_reference,q.tag_type,q.public_status,
 coalesce(l.updated_at,i.updated_at,q.created_at) AS sort_at,
 CASE WHEN q.tag_type='lost' THEN l.item_label ELSE i.display_name END AS profile_label,
 CASE WHEN q.tag_type='lost' THEN coalesce(l.published,false) ELSE coalesce(i.published,false) END AS published,
 CASE WHEN q.tag_type='lost' THEN coalesce(l.profile_version,0) ELSE coalesce(i.profile_version,0) END AS profile_version,
 coalesce(c.profile_version,0) AS preference_version
 FROM public.qr_codes q LEFT JOIN public.tag_pairs p ON p.id=q.pair_id
 LEFT JOIN public.lost_item_profiles l ON l.qr_id=q.id
 LEFT JOIN public.ice_profiles i ON i.qr_id=q.id
 LEFT JOIN public.tag_contact_preferences c ON c.qr_id=q.id
 WHERE (p.owner_user_id=:uid OR (q.pair_id IS NULL AND public.sr_owns_qr(q.id))) AND q.is_current
"""


def tag(row):
    return {
        "qr_id": str(row["qr_id"]),
        "pair_id": str(row["pair_id"]) if row["pair_id"] is not None else None,
        "pair_reference": row["pair_reference"],
        "tag_type": row["tag_type"],
        "public_status": row["public_status"],
        "profile_label": row["profile_label"],
        "published": row["published"],
        "profile_version": row["profile_version"],
        "preference_version": row["preference_version"],
        "profile_complete": bool(row["profile_label"]),
        "editable": True,
        "editor_url": f"/my-qr/{row['qr_id']}",
    }


def tags(context, clause="", **params):
    return (
        context.session.execute(
            text(TAG_SELECT + clause),
            {"uid": context.principal.user_id, **params},
        )
        .mappings()
        .all()
    )


def pair_summary(row, children):
    return {
        "pair_id": str(row["id"]),
        "pair_reference": row["pair_reference"],
        "ownership_status": row["ownership_status"],
        "inventory_status": row["inventory_status"],
        "activated_at": row["activated_at"],
        "tags": [tag(t) for t in children],
    }


@router.get("/me/tag-pairs", operation_id="API-030", response_model=PairPage)
def list_pairs(
    context: Authenticated,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    status: Literal["unclaimed", "active", "transfer_pending", "disputed", "revoked"]
    | None = None,
):
    after = decode_cursor(cursor)
    if after is False:
        return failure(400, "VALIDATION_ERROR", "Invalid cursor.")
    rows = (
        context.session.execute(
            text(
                "SELECT id,pair_reference,ownership_status,inventory_status,activated_at,coalesce(activated_at,created_at) AS sort_at FROM public.tag_pairs WHERE owner_user_id=:uid "
                "AND (CAST(:after AS uuid) IS NULL OR (coalesce(activated_at,created_at),id)<(CAST(:at AS timestamptz),CAST(:after AS uuid))) "
                "AND (CAST(:status AS text) IS NULL OR ownership_status=:status) ORDER BY sort_at DESC,id DESC LIMIT :limit"
            ),
            {
                "uid": context.principal.user_id,
                "after": after[0] if after else None,
                "at": after[1] if after else None,
                "status": status,
                "limit": limit + 1,
            },
        )
        .mappings()
        .all()
    )
    children = (
        tags(
            context,
            " AND q.pair_id=ANY(CAST(:ids AS uuid[])) ORDER BY q.tag_type DESC",
            ids=[r["id"] for r in rows[:limit]],
        )
        if rows
        else []
    )
    grouped = {r["id"]: [] for r in rows[:limit]}
    for child in children:
        grouped[child["pair_id"]].append(child)
    return {
        "items": [pair_summary(r, grouped[r["id"]]) for r in rows[:limit]],
        "next_cursor": encode_cursor(rows[limit - 1]["id"], rows[limit - 1]["sort_at"])
        if len(rows) > limit
        else None,
    }


@router.get(
    "/me/tag-pairs/{pair_id}", operation_id="API-031", response_model=PairSummary
)
def get_pair(pair_id: UUID, context: Authenticated):
    require_pair_owner(context, pair_id)
    row = (
        context.session.execute(
            text(
                "SELECT id,pair_reference,ownership_status,inventory_status,activated_at FROM public.tag_pairs WHERE id=:pid AND owner_user_id=:uid"
            ),
            {"pid": pair_id, "uid": context.principal.user_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        # Ownership can be revoked between the guard and representation query.
        raise AccessError(404)
    return pair_summary(
        row, tags(context, " AND q.pair_id=:pid ORDER BY q.tag_type DESC", pid=pair_id)
    )


@router.get("/me/qr", operation_id="API-205", response_model=QRPage)
def list_qr(
    context: Authenticated,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    tag_type: Literal["lost", "ice"] | None = None,
    pair_id: UUID | None = None,
    search: str = Query(default="", max_length=120),
    publication: Literal["draft", "published"] | None = None,
    status: Literal[
        "unactivated", "active", "owner_disabled", "admin_suspended", "revoked"
    ]
    | None = None,
):
    after = decode_cursor(cursor)
    if after is False:
        return failure(400, "VALIDATION_ERROR", "Invalid cursor.")
    rows = tags(
        context,
        " AND (CAST(:after AS uuid) IS NULL OR (coalesce(l.updated_at,i.updated_at,q.created_at),q.id)<(CAST(:at AS timestamptz),CAST(:after AS uuid)))"
        " AND (CAST(:kind AS text) IS NULL OR q.tag_type=:kind)"
        " AND (CAST(:pid AS uuid) IS NULL OR q.pair_id=:pid)"
        " AND (CAST(:status AS text) IS NULL OR q.public_status=:status)"
        " AND strpos(lower(coalesce(l.item_label,i.display_name,'')),lower(:search))>0"
        " AND (CAST(:publication AS text) IS NULL OR (CASE WHEN q.tag_type='lost' THEN coalesce(l.published,false) ELSE coalesce(i.published,false) END)=(:publication='published'))"
        " ORDER BY sort_at DESC,q.id DESC LIMIT :limit",
        after=after[0] if after else None,
        at=after[1] if after else None,
        search=search.strip(),
        publication=publication,
        kind=tag_type,
        pid=pair_id,
        status=status,
        limit=limit + 1,
    )
    return {
        "items": [tag(r) for r in rows[:limit]],
        "next_cursor": encode_cursor(
            rows[limit - 1]["qr_id"], rows[limit - 1]["sort_at"]
        )
        if len(rows) > limit
        else None,
    }


@router.get("/me/qr/{qr_id}", operation_id="API-206", response_model=QRDetail)
def get_qr(qr_id: UUID, context: Authenticated):
    require_qr_owner(context, qr_id)
    rows = tags(context, " AND q.id=:qid", qid=qr_id)
    if not rows:
        raise AccessError(404)
    result = tag(rows[0])
    if result["pair_id"] is None:
        result["physical_products"] = context.session.execute(text("SELECT public.sr_standalone_products(:qid)"), {"qid": qr_id}).scalar_one()
        return result
    result["physical_products"] = [
        dict(r)
        for r in context.session.execute(
            text(
                "SELECT oi.product_name_snapshot,oi.variant_name_snapshot,u.copies FROM public.order_item_qr_uses u "
                "JOIN public.order_items oi ON oi.id=u.order_item_id JOIN public.orders o ON o.id=oi.order_id "
                "WHERE u.qr_code_id=:qid AND o.customer_user_id=:uid ORDER BY u.id"
            ),
            {"qid": qr_id, "uid": context.principal.user_id},
        ).mappings()
    ]
    return result
