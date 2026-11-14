"""Operations-only inventory metadata. No activation or print credentials leave SQL."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel
from sqlalchemy import text

from app.api.auth import AccessError, Authenticated, require_staff
from app.api.v1.catalog import CatalogRoute, fail
from app.api.v1.owner_qr import decode_cursor, encode_cursor

router = APIRouter(tags=["inventory queries"], route_class=CatalogRoute)
InventoryStatus = Literal[
    "generated",
    "printed",
    "qa_passed",
    "reserved",
    "packed",
    "shipped",
    "delivered",
    "rejected",
]
OwnershipStatus = Literal[
    "unclaimed", "active", "transfer_pending", "disputed", "revoked"
]
BatchStatus = Literal[
    "draft", "generated", "printed", "qa_passed", "rejected", "closed"
]


class TagMetadata(BaseModel):
    qr_id: UUID
    tag_type: Literal["lost", "ice"]
    serial_number: str
    public_status: str
    replaces_qr_id: UUID | None
    created_at: datetime


class TagHistory(BaseModel):
    items: list[TagMetadata]
    next_cursor: str | None


class LatestQA(BaseModel):
    qa_round: int
    approved: bool
    inspected_at: datetime


class PairMetadata(BaseModel):
    pair_id: UUID
    pair_reference: str
    batch_id: UUID
    inventory_status: str
    ownership_status: str
    created_at: datetime
    current_tags: list[TagMetadata]
    latest_qa: LatestQA | None


class PairPage(BaseModel):
    items: list[PairMetadata]
    next_cursor: str | None


class LiveAllocation(BaseModel):
    unit_id: UUID
    order_id: UUID
    status: str
    reserved_until: datetime | None
    allocated_at: datetime | None


class PairDetail(PairMetadata):
    live_allocation: LiveAllocation | None
    historical_tags: TagHistory


class BatchMetadata(BaseModel):
    batch_id: UUID
    batch_label: str
    status: str
    created_at: datetime
    generated_at: datetime
    printed_at: datetime | None
    qa_approved_at: datetime | None
    ecc_level: str
    print_material: str | None
    logo_template_key: str | None
    intended_environment: str | None
    pair_count: int
    current_tag_count: int
    historical_tag_count: int
    qa_passed_pair_count: int


class BatchPage(BaseModel):
    items: list[BatchMetadata]
    next_cursor: str | None


class LastBatch(BaseModel):
    batch_id: UUID
    batch_label: str
    status: str
    generated_at: datetime


class StockSummary(BaseModel):
    as_of: datetime
    pair_count: int
    current_tag_count: int
    historical_tag_count: int
    available_pairs: int
    reserved_pairs: int
    allocated_pairs: int
    qa_held_pairs: int
    active_pairs: int
    low_stock_threshold: int | None
    low_stock: bool | None
    last_batch: LastBatch | None


def cursor(value):
    parsed = decode_cursor(value)
    if parsed is False:
        fail(422, "INVALID_CURSOR")
    return (None, None) if parsed is None else (parsed[1], parsed[0])


def page(data, limit, model, id_field):
    more = len(data) > limit
    items = [model.model_validate(row) for row in data[:limit]]
    last = items[-1] if items else None
    return {
        "items": items,
        "next_cursor": encode_cursor(getattr(last, id_field), last.created_at)
        if more and last
        else None,
    }


def bounds(limit):
    if not 1 <= limit <= 100:
        fail(422, "INVALID_LIMIT")


# These predicates deliberately mirror sr_checkout_reserve, including live
# reservation states regardless of reserved_until. Elapsed time releases nothing.
AVAILABLE = """p.ownership_status='unclaimed' AND p.inventory_status='qa_passed'
 AND NOT EXISTS(SELECT 1 FROM public.order_pair_units u WHERE u.pair_id=p.id AND u.status IN ('reserved','allocated'))
 AND (SELECT count(*) FROM public.qr_codes q WHERE q.pair_id=p.id AND q.is_current AND q.public_status='unactivated')=2
 AND EXISTS(SELECT 1 FROM public.pair_activation_credentials a WHERE a.pair_id=p.id AND a.status='unused')"""
TAG_FIELDS = "'qr_id',q.id,'tag_type',q.tag_type,'serial_number',q.serial_number,'public_status',q.public_status,'replaces_qr_id',q.replaces_qr_id,'created_at',q.created_at"
PAIR_FIELDS = f"""p.id AS pair_id,p.pair_reference,p.batch_id,p.inventory_status,p.ownership_status,p.created_at,
 COALESCE((SELECT jsonb_agg(jsonb_build_object({TAG_FIELDS}) ORDER BY q.tag_type) FROM public.qr_codes q WHERE q.pair_id=p.id AND q.is_current),'[]'::jsonb) AS current_tags,
 (SELECT jsonb_build_object('qa_round',qa.qa_round,'approved',qa.approved,'inspected_at',qa.inspected_at)
  FROM public.pair_print_qa qa WHERE qa.pair_id=p.id ORDER BY qa.qa_round DESC LIMIT 1) AS latest_qa"""
BATCH_FIELDS = """b.id AS batch_id,b.batch_code AS batch_label,b.status,b.created_at,b.generated_at,b.printed_at,b.qa_approved_at,
 b.ecc_level,b.print_material,b.logo_template_key,b.intended_environment,
 (SELECT count(*) FROM public.tag_pairs p WHERE p.batch_id=b.id) AS pair_count,
 (SELECT count(*) FROM public.qr_codes q JOIN public.tag_pairs p ON p.id=q.pair_id WHERE p.batch_id=b.id AND q.is_current) AS current_tag_count,
 (SELECT count(*) FROM public.qr_codes q JOIN public.tag_pairs p ON p.id=q.pair_id WHERE p.batch_id=b.id AND NOT q.is_current) AS historical_tag_count,
 (SELECT count(*) FROM public.tag_pairs p WHERE p.batch_id=b.id AND p.inventory_status='qa_passed') AS qa_passed_pair_count"""


@router.get("/admin/tag-pairs", operation_id="API-084", response_model=PairPage)
def list_pairs(
    context: Authenticated,
    limit: int = 20,
    cursor_value: str | None = Query(default=None, alias="cursor"),
    pair_reference: str | None = None,
    batch_id: UUID | None = None,
    inventory_status: InventoryStatus | None = None,
    ownership_status: OwnershipStatus | None = None,
):
    require_staff(context, "operations")
    bounds(limit)
    if pair_reference is not None and (
        not 1 <= len(pair_reference) <= 40 or any(ord(c) < 32 for c in pair_reference)
    ):
        fail(422, "INVALID_REFERENCE")
    stamp, ident = cursor(cursor_value)
    data = (
        context.session.execute(
            text(f"""WITH selected AS (
      SELECT p.* FROM public.tag_pairs p WHERE
      (CAST(:ref AS text) IS NULL OR p.pair_reference=:ref)
      AND (CAST(:batch AS uuid) IS NULL OR p.batch_id=:batch)
      AND (CAST(:inventory AS text) IS NULL OR p.inventory_status=:inventory)
      AND (CAST(:ownership AS text) IS NULL OR p.ownership_status=:ownership)
      AND (CAST(:stamp AS timestamptz) IS NULL OR (p.created_at,p.id)<(:stamp,:ident))
      ORDER BY p.created_at DESC,p.id DESC LIMIT :lim)
      SELECT {PAIR_FIELDS} FROM selected p ORDER BY p.created_at DESC,p.id DESC"""),
            {
                "ref": pair_reference,
                "batch": batch_id,
                "inventory": inventory_status,
                "ownership": ownership_status,
                "stamp": stamp,
                "ident": ident,
                "lim": limit + 1,
            },
        )
        .mappings()
        .all()
    )
    return page(data, limit, PairMetadata, "pair_id")


@router.get(
    "/admin/tag-pairs/{pair_id}", operation_id="API-085", response_model=PairDetail
)
def pair_detail(
    pair_id: UUID,
    context: Authenticated,
    history_limit: int = 20,
    history_cursor: str | None = None,
):
    require_staff(context, "operations")
    bounds(history_limit)
    stamp, ident = cursor(history_cursor)
    row = (
        context.session.execute(
            text(f"""SELECT {PAIR_FIELDS},
      (SELECT jsonb_build_object('unit_id',u.id,'order_id',u.order_id,'status',u.status,'reserved_until',u.reserved_until,'allocated_at',u.allocated_at)
       FROM public.order_pair_units u WHERE u.pair_id=p.id AND u.status IN ('reserved','allocated') LIMIT 1) AS live_allocation,
      COALESCE((SELECT jsonb_agg(jsonb_build_object({TAG_FIELDS}) ORDER BY q.created_at DESC,q.id DESC)
       FROM (SELECT * FROM public.qr_codes WHERE pair_id=p.id AND NOT is_current
         AND (CAST(:stamp AS timestamptz) IS NULL OR (created_at,id)<(:stamp,:ident)) ORDER BY created_at DESC,id DESC LIMIT :lim) q),'[]'::jsonb) AS history
      FROM public.tag_pairs p WHERE p.id=:id"""),
            {"id": pair_id, "stamp": stamp, "ident": ident, "lim": history_limit + 1},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise AccessError(404)
    result = dict(row)
    result["historical_tags"] = page(
        result.pop("history"), history_limit, TagMetadata, "qr_id"
    )
    return result


@router.get("/admin/qr-batches", operation_id="API-091", response_model=BatchPage)
def list_batches(
    context: Authenticated,
    limit: int = 20,
    cursor_value: str | None = Query(default=None, alias="cursor"),
    batch_label: str | None = None,
    status: BatchStatus | None = None,
):
    require_staff(context, "operations")
    bounds(limit)
    if batch_label is not None and not 1 <= len(batch_label) <= 40:
        fail(422, "INVALID_BATCH_LABEL")
    stamp, ident = cursor(cursor_value)
    data = (
        context.session.execute(
            text(f"""WITH selected AS (
      SELECT b.* FROM public.qr_batches b WHERE to_jsonb(b)->>'generation_mode' IS DISTINCT FROM 'standalone'
      AND (CAST(:label AS text) IS NULL OR b.batch_code=:label)
      AND (CAST(:status AS text) IS NULL OR b.status=:status)
      AND (CAST(:stamp AS timestamptz) IS NULL OR (b.created_at,b.id)<(:stamp,:ident))
      ORDER BY b.created_at DESC,b.id DESC LIMIT :lim)
      SELECT {BATCH_FIELDS} FROM selected b ORDER BY b.created_at DESC,b.id DESC"""),
            {
                "label": batch_label,
                "status": status,
                "stamp": stamp,
                "ident": ident,
                "lim": limit + 1,
            },
        )
        .mappings()
        .all()
    )
    return page(data, limit, BatchMetadata, "batch_id")


@router.get(
    "/admin/qr-batches/{batch_id}", operation_id="API-092", response_model=BatchMetadata
)
def batch_detail(batch_id: UUID, context: Authenticated):
    require_staff(context, "operations")
    row = (
        context.session.execute(
            text(f"SELECT {BATCH_FIELDS} FROM public.qr_batches b WHERE b.id=:id AND to_jsonb(b)->>'generation_mode' IS DISTINCT FROM 'standalone'"),
            {"id": batch_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise AccessError(404)
    return row


@router.get(
    "/admin/inventory/summary", operation_id="API-230", response_model=StockSummary
)
def stock_summary(context: Authenticated, request: Request):
    require_staff(context, "operations")
    row = (
        context.session.execute(
            text(f"""SELECT statement_timestamp() AS as_of,count(*) AS pair_count,
      COALESCE(sum((SELECT count(*) FROM public.qr_codes q WHERE q.pair_id=p.id AND q.is_current)),0)::bigint AS current_tag_count,
      COALESCE(sum((SELECT count(*) FROM public.qr_codes q WHERE q.pair_id=p.id AND NOT q.is_current)),0)::bigint AS historical_tag_count,
      count(*) FILTER(WHERE {AVAILABLE}) AS available_pairs,
      count(*) FILTER(WHERE EXISTS(SELECT 1 FROM public.order_pair_units u WHERE u.pair_id=p.id AND u.status='reserved')) AS reserved_pairs,
      count(*) FILTER(WHERE EXISTS(SELECT 1 FROM public.order_pair_units u WHERE u.pair_id=p.id AND u.status='allocated')) AS allocated_pairs,
      count(*) FILTER(WHERE p.inventory_status IN ('generated','printed','rejected')) AS qa_held_pairs,
      count(*) FILTER(WHERE p.ownership_status='active') AS active_pairs,
      (SELECT jsonb_build_object('batch_id',b.id,'batch_label',b.batch_code,'status',b.status,'generated_at',b.generated_at)
        FROM public.qr_batches b WHERE to_jsonb(b)->>'generation_mode' IS DISTINCT FROM 'standalone' ORDER BY b.created_at DESC,b.id DESC LIMIT 1) AS last_batch
      FROM public.tag_pairs p""")
        )
        .mappings()
        .one()
    )
    threshold = request.app.state.settings.inventory_low_stock_threshold
    return {
        **row,
        "low_stock_threshold": threshold,
        "low_stock": None if threshold is None else row["available_pairs"] < threshold,
    }
