"""Standalone inventory metadata and generation; no allocation or activation."""

import json
import re
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api.auth import AccessError, Authenticated, require_staff
from app.api.v1.catalog import CatalogRoute, fail
from app.api.v1.inventory_queries import cursor
from app.api.v1.owner_qr import encode_cursor
from app.core.inventory_secrets import new_public_token


class InventoryRoute(CatalogRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handle(request):
            response = await original(request)
            response.headers["Cache-Control"] = "private, no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            return response

        return handle


router = APIRouter(tags=["typed inventory"], route_class=InventoryRoute)
QRType = Literal["lost", "ice"]
InventoryStatus = Literal["available", "allocated", "retired"]
OwnershipStatus = Literal["unclaimed", "active", "revoked"]
BatchStatus = Literal[
    "draft", "generated", "printed", "qa_passed", "rejected", "closed"
]


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GenerateRequest(Closed):
    batch_label: str = Field(
        min_length=3, max_length=40, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]+$"
    )
    qr_type: QRType
    quantity: int = Field(ge=1, le=1000, strict=True)
    ecc_level: Literal["M", "Q"] = "Q"


class GenerationReceipt(Closed):
    batch_id: UUID
    batch_label: str
    qr_type: QRType
    generated_quantity: int = Field(ge=1, le=1000)
    status: Literal["generated"]
    created_at: datetime


class Paging(Closed):
    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = Field(default=None, max_length=220)


class QRFilters(Paging):
    qr_type: QRType | None = None
    batch_id: UUID | None = None
    inventory_status: InventoryStatus | None = None
    ownership_status: OwnershipStatus | None = None


class BatchFilters(Paging):
    qr_type: QRType | None = None
    batch_label: str | None = Field(default=None, min_length=1, max_length=40)
    status: BatchStatus | None = None


class SummaryFilters(Closed):
    qr_type: QRType | None = None


class QRMetadata(Closed):
    qr_id: UUID
    batch_id: UUID
    batch_label: str
    qr_type: QRType
    serial_number: str
    public_status: str
    inventory_status: InventoryStatus
    ownership_status: OwnershipStatus
    row_version: int
    created_at: datetime
    allocatable: bool


class BatchMetadata(Closed):
    batch_id: UUID
    batch_label: str
    qr_type: QRType
    requested_quantity: int
    generated_quantity: int
    status: BatchStatus
    ecc_level: Literal["M", "Q"]
    created_at: datetime


class QRPage(Closed):
    as_of: datetime
    items: list[QRMetadata]
    next_cursor: str | None


class BatchPage(Closed):
    as_of: datetime
    items: list[BatchMetadata]
    next_cursor: str | None


class TypeCount(Closed):
    qr_type: QRType
    total: int
    available: int
    allocated: int
    retired: int
    allocatable: int


class Summary(Closed):
    as_of: datetime
    items: list[TypeCount]


def checked(result):
    if result is None:
        raise AccessError(404)
    if "error" in result:
        code = result["error"]
        if code == "FORBIDDEN":
            raise AccessError(403)
        if code in {"BATCH_LABEL_CONFLICT", "IDEMPOTENCY_KEY_REUSED"}:
            fail(409, code)
        raise AccessError(503)
    return result


def read(context, view, filters):
    require_staff(context, "operations")
    return checked(
        context.session.execute(
            text(
                "SELECT public.sr_typed_inventory_read(:sid,:view,CAST(:filters AS jsonb))"
            ),
            {
                "sid": context.principal.session_id,
                "view": view,
                "filters": json.dumps(filters),
            },
        ).scalar_one()
    )


def paging(filters):
    values = filters.model_dump(mode="json", exclude={"cursor"})
    stamp, identity = cursor(filters.cursor)
    values.update(
        at=stamp.isoformat() if stamp else None,
        after_id=str(identity) if identity else None,
    )
    return values


def page(result, limit, model, id_field):
    items = [model.model_validate(row) for row in result["items"][:limit]]
    last = items[-1] if items else None
    return {
        "as_of": result["as_of"],
        "items": items,
        "next_cursor": encode_cursor(getattr(last, id_field), last.created_at)
        if len(result["items"]) > limit and last
        else None,
    }


@router.post(
    "/admin/qr-inventory/batches",
    status_code=201,
    response_model=GenerationReceipt,
    operation_id="typed-inventory-generate",
)
def generate(body: GenerateRequest, context: Authenticated, request: Request):
    require_staff(context, "operations")
    # Bearer-authenticated backend API. Browser callers use the same-origin relay
    # in Phase 3; no cookie authentication or new browser token transport here.
    keys = request.headers.getlist("idempotency-key")
    if len(keys) != 1 or not re.fullmatch(r"[A-Za-z0-9._:-]{8,160}", keys[0]):
        fail(400, "IDEMPOTENCY_KEY_REQUIRED")
    if request.query_params:
        fail(422, "INVALID_QUERY")
    try:
        with context.session.begin_nested():
            result = context.session.execute(
                text(
                    "SELECT public.sr_typed_inventory_generate(:sid,:label,:kind,:quantity,:ecc,:key,CAST(:tokens AS jsonb))"
                ),
                {
                    "sid": context.principal.session_id,
                    "label": body.batch_label,
                    "kind": body.qr_type,
                    "quantity": body.quantity,
                    "ecc": body.ecc_level,
                    "key": keys[0],
                    "tokens": json.dumps(
                        [new_public_token() for _ in range(body.quantity)]
                    ),
                },
            ).scalar_one()
            return checked(result)
    except IntegrityError:
        fail(409, "GENERATION_CONFLICT")


@router.get(
    "/admin/qr-inventory/batches",
    response_model=BatchPage,
    operation_id="typed-inventory-batches",
)
def batches(context: Authenticated, filters: Annotated[BatchFilters, Query()]):
    return page(
        read(context, "batches", paging(filters)),
        filters.limit,
        BatchMetadata,
        "batch_id",
    )


@router.get(
    "/admin/qr-inventory/batches/{batch_id}",
    response_model=BatchMetadata,
    operation_id="typed-inventory-batch-detail",
)
def batch_detail(batch_id: UUID, context: Authenticated):
    return read(context, "batch", {"batch_id": str(batch_id)})


@router.get(
    "/admin/qr-inventory/summary",
    response_model=Summary,
    operation_id="typed-inventory-summary",
)
def summary(context: Authenticated, filters: Annotated[SummaryFilters, Query()]):
    return read(context, "summary", filters.model_dump(mode="json"))


@router.get(
    "/admin/qr-inventory/codes",
    response_model=QRPage,
    operation_id="typed-inventory-codes",
)
def codes(context: Authenticated, filters: Annotated[QRFilters, Query()]):
    return page(
        read(context, "codes", paging(filters)), filters.limit, QRMetadata, "qr_id"
    )


@router.get(
    "/admin/qr-inventory/codes/{qr_id}",
    response_model=QRMetadata,
    operation_id="typed-inventory-code-detail",
)
def code_detail(qr_id: UUID, context: Authenticated):
    return read(context, "code", {"qr_id": str(qr_id)})
