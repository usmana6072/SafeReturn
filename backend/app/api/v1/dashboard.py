"""Approved role-scoped dashboard projections. No provider or business writers."""

from datetime import UTC, datetime, timedelta
from time import monotonic
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import Field, ValidationError, field_validator, model_validator
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import (
    AccessError,
    AuthContext,
    Authenticated,
    authorize,
    require_staff,
)
from app.api.v1.catalog import Closed, fail
from app.api.v1.shipping_addresses import PrivateRoute

router = APIRouter(tags=["staff dashboard"], route_class=PrivateRoute)
ROLES = {
    "catalog": {"operations", "security_admin", "superadmin"},
    "inventory": {"operations"},
    "fulfillment": {"operations"},
    "printing": {"operations"},
    "finance": {"finance"},
    "notifications": {"operations", "security_admin"},
    "support": {"support"},
    "finance_mirror": {"finance", "security_admin", "superadmin"},
}
# Fixed existing pages only. No invented filter on a console that ignores it.
METRICS = {
    "catalog": {
        "catalog.products": ("product", "/admin/products"),
        "catalog.variants": ("variant", "/admin/products"),
    },
    "fulfillment": {
        "fulfillment.ready_orders": ("order", "/admin/ready-to-ship"),
        "fulfillment.requires_review": (
            "shipment",
            "/admin/shipments?requires_review=true",
        ),
        **{
            f"shipments.{s}": ("shipment", f"/admin/shipments?status={s}")
            for s in (
                "preparing",
                "packed",
                "dispatched",
                "delivered",
                "exception",
                "returned",
            )
        },
    },
    "notifications": {
        f"notifications.{s}": ("outbox_event", f"/admin/notifications?status={s}")
        for s in ("pending", "leased", "retry", "sent", "dead")
    },
    "support": {
        f"support.{s}": ("case", f"/admin/support?status={s}")
        for s in ("open", "investigating")
    },
    "finance_mirror": {
        "finance_mirror.records": ("sync_record", "/admin/finance/sheet-sync")
    },
}
SERIES = {
    "orders_placed": ({"operations", "finance"}, "order"),
    "shipments_dispatched": ({"operations"}, "shipment"),
    "notifications_created": ({"operations", "security_admin"}, "outbox_event"),
}
Reason = Literal[
    "QUERY_UNAVAILABLE",
    "DRILLDOWN_UNAVAILABLE",
    "FEATURE_DISABLED",
    "LOW_STOCK_UNCONFIGURED",
    "REQUEST_BUDGET_EXHAUSTED",
]
GroupId = Literal[
    "catalog",
    "inventory",
    "fulfillment",
    "printing",
    "finance",
    "notifications",
    "support",
    "finance_mirror",
]
Unit = Literal[
    "product",
    "variant",
    "pair",
    "qr_identity",
    "order",
    "attempt",
    "job",
    "shipment",
    "outbox_event",
    "case",
    "sync_record",
]


class Count(Closed):
    value: int = Field(ge=0, le=1000, strict=True)
    is_exact: bool = Field(strict=True)

    @model_validator(mode="after")
    def exact(self):
        if self.is_exact != (self.value < 1000):
            raise ValueError("Invalid count")
        return self


class Metric(Closed):
    metric_id: str
    unit: Unit
    count: Count
    drilldown: str


class Group(Closed):
    group: GroupId
    status: Literal["ready", "unavailable"]
    as_of: datetime | None
    metrics: list[Metric] = Field(max_length=8)
    reason_code: Reason | None


class Summary(Closed):
    as_of: datetime
    groups: list[Group] = Field(max_length=8)


class Bucket(Closed):
    start: datetime
    end: datetime
    count: Count

    @field_validator("start", "end")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("Timezone required")
        return value.astimezone(UTC)


class Series(Closed):
    series_id: Literal["orders_placed", "shipments_dispatched", "notifications_created"]
    unit: Unit
    status: Literal["ready", "unavailable"]
    reason_code: Reason | None
    buckets: list[Bucket] = Field(max_length=30)


class Trends(Closed):
    as_of: datetime
    range_start: datetime
    range_end: datetime
    bucket_timezone: Literal["UTC"] = "UTC"
    display_timezone: Literal["UTC", "Asia/Karachi"]
    series: list[Series] = Field(max_length=3)


def roles(context: AuthContext) -> set[str]:
    return set(
        context.session.execute(
            text(
                "SELECT role FROM public.staff_roles WHERE user_id=:uid AND revoked_at IS NULL ORDER BY role"
            ),
            {"uid": context.principal.user_id},
        ).scalars()
    )


def guard(context: AuthContext, request: Request, allowed: set[str]) -> set[str]:
    require_staff(
        context, "operations", "finance", "support", "security_admin", "superadmin"
    )
    if not request.app.state.settings.dashboard_enabled:
        raise AccessError(503)
    if any(
        k not in allowed or len(request.query_params.getlist(k)) != 1
        for k in request.query_params
    ):
        fail(422, "INVALID_QUERY")
    return roles(context)


def count(value: int) -> Count:
    if type(value) is not int or not 0 <= value <= 1000:
        raise ValueError("Invalid aggregate")
    return Count(value=value, is_exact=value < 1000)


def final_roles(context: AuthContext) -> set[str]:
    live = authorize(context.session, context.principal)
    require_staff(
        live, "operations", "finance", "support", "security_admin", "superadmin"
    )
    return roles(live)


class BudgetExpired(Exception):
    pass


def query(context: AuthContext, deadline: float, sql: str, params: dict):
    remaining = int((deadline - monotonic()) * 1000)
    if remaining < 1:
        raise BudgetExpired()
    # SAVEPOINT rolls failed SQL back without discarding independent widgets.
    # SET LOCAL is restored on both success and failure; never alter session defaults.
    with context.session.begin_nested():
        previous = context.session.execute(text("SHOW statement_timeout")).scalar_one()
        context.session.execute(
            text("SELECT set_config('statement_timeout',:timeout,true)"),
            {"timeout": str(min(3000, remaining)) + "ms"},
        )
        result = context.session.execute(text(sql), params).scalar_one()
        context.session.execute(
            text("SELECT set_config('statement_timeout',:timeout,true)"),
            {"timeout": previous},
        )
        if result is None:
            raise AccessError(403)
        return result


@router.get("/admin/dashboard/summary", operation_id="API-344", response_model=Summary)
def summary(request: Request, context: Authenticated):
    permitted = guard(context, request, set())
    settings = request.app.state.settings
    deadline, observed = monotonic() + 8, datetime.now(UTC)
    groups = []
    for group, allowed in ROLES.items():
        if not permitted.intersection(allowed):
            continue
        reason = None
        metrics = []
        stamp = None
        if group not in METRICS:
            reason = "DRILLDOWN_UNAVAILABLE"
            if group == "finance" and not settings.finance_reconciliation_enabled:
                reason = "FEATURE_DISABLED"
            if group == "inventory" and settings.inventory_low_stock_threshold is None:
                reason = "LOW_STOCK_UNCONFIGURED"
        else:
            try:
                stamp = datetime.now(UTC)
                values = query(
                    context,
                    deadline,
                    "SELECT public.sr_dashboard_summary(:group)",
                    {"group": group},
                )
                if not isinstance(values, dict) or set(values) != set(METRICS[group]):
                    raise ValueError("Unexpected projection")
                metrics = [
                    Metric(
                        metric_id=key,
                        unit=unit,
                        count=count(values[key]),
                        drilldown=path,
                    )
                    for key, (unit, path) in METRICS[group].items()
                ]
            except BudgetExpired:
                reason = "REQUEST_BUDGET_EXHAUSTED"
            except (SQLAlchemyError, ValidationError, ValueError, TypeError):
                reason = "QUERY_UNAVAILABLE"
        groups.append(
            Group(
                group=group,
                status="unavailable" if reason else "ready",
                as_of=None if reason else stamp,
                metrics=[] if reason else metrics,
                reason_code=reason,
            )
        )
    # Revocations during independent queries cannot leave now-forbidden groups.
    final = final_roles(context)
    if not final:
        raise AccessError(403)
    return Summary(
        as_of=observed, groups=[g for g in groups if final.intersection(ROLES[g.group])]
    )


@router.get("/admin/dashboard/trends", operation_id="API-345", response_model=Trends)
def trends(
    request: Request,
    context: Authenticated,
    display_timezone: Literal["UTC", "Asia/Karachi"] = "UTC",
):
    permitted = guard(context, request, {"display_timezone"})
    observed = datetime.now(UTC)
    end = observed.replace(hour=0, minute=0, second=0, microsecond=0)
    start, deadline = end - timedelta(days=30), monotonic() + 8
    series = []
    for ident, (allowed, unit) in SERIES.items():
        if not permitted.intersection(allowed):
            continue
        reason, buckets = None, []
        if ident == "orders_placed":
            reason = "DRILLDOWN_UNAVAILABLE"
        else:
            try:
                rows = query(
                    context,
                    deadline,
                    "SELECT public.sr_dashboard_trend(:series,:end)",
                    {"series": ident, "end": end},
                )
                if not isinstance(rows, list) or len(rows) != 30:
                    raise ValueError("Invalid buckets")
                for i, row in enumerate(rows):
                    if set(row) != {"start", "end", "n"}:
                        raise ValueError("Invalid bucket")
                    bucket = Bucket(
                        start=row["start"], end=row["end"], count=count(row["n"])
                    )
                    if bucket.start != start + timedelta(
                        days=i
                    ) or bucket.end != bucket.start + timedelta(days=1):
                        raise ValueError("Invalid range")
                    buckets.append(bucket)
            except BudgetExpired:
                reason = "REQUEST_BUDGET_EXHAUSTED"
            except (SQLAlchemyError, ValidationError, ValueError, TypeError):
                reason = "QUERY_UNAVAILABLE"
        series.append(
            Series(
                series_id=ident,
                unit=unit,
                status="unavailable" if reason else "ready",
                reason_code=reason,
                buckets=[] if reason else buckets,
            )
        )
    final = final_roles(context)
    if not final:
        raise AccessError(403)
    return Trends(
        as_of=observed,
        range_start=start,
        range_end=end,
        display_timezone=display_timezone,
        series=[s for s in series if final.intersection(SERIES[s.series_id][0])],
    )


def install(application):
    application.include_router(router, prefix="/api/v1")

    @application.middleware("http")
    async def private_headers(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/v1/admin/dashboard/"):
            response.headers["Cache-Control"] = "private, no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response
