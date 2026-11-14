"""Bounded support observations using existing RLS; no context enrichment."""

import base64
import json
import re
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import text

from app.api.auth import AccessError, authorize, require_staff
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt, encrypt

CaseType = Literal[
    "activation", "lost_tag", "payment", "privacy", "ownership_dispute", "other"
]
Status = Literal["open", "investigating", "resolved", "closed"]
Priority = Literal["low", "normal", "high", "urgent"]


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)

    @field_validator("created_at", "as_of", check_fields=False)
    @classmethod
    def timestamp_utc(cls, value):
        if value.utcoffset() is None:
            raise ValueError("Timezone required")
        return value.astimezone(UTC)


class CaseMetadata(Closed):
    case_id: UUID
    case_type: CaseType
    status: Status
    priority: Priority
    case_revision: int = Field(ge=1, le=2147483647)
    created_at: datetime
    assignment: Literal["mine", "unassigned"]
    assigned_to_me: bool


class Detail(CaseMetadata):
    content_available: Literal[False] = False


class Page(Closed):
    as_of: datetime
    items: list[CaseMetadata] = Field(max_length=100)
    next_cursor: str | None = Field(max_length=2000)


class Event(Closed):
    event_id: UUID
    case_revision: int = Field(ge=1, le=2147483647)
    event_type: Literal["created", "claimed", "updated"]
    from_status: Status | None
    to_status: Status
    priority: Priority
    created_at: datetime


class History(Closed):
    case_id: UUID
    case_revision: int = Field(ge=1, le=2147483647)
    items: list[Event] = Field(max_length=100)
    next_cursor: str | None = Field(max_length=2000)


def invalid(code="VALIDATION_ERROR", status=422):
    raise HTTPException(status, detail={"code": code})


def ident(value):
    if not re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", value):
        invalid()
    return UUID(value)


def query(request, allowed):
    if len(request.url.query) > 4096:
        invalid("INVALID_QUERY", 400)
    params = request.query_params
    if any(k not in allowed or len(params.getlist(k)) != 1 for k in params):
        invalid("INVALID_QUERY", 400)
    if request.headers.get("content-length", "0") != "0" or request.headers.get(
        "transfer-encoding"
    ):
        invalid("INVALID_QUERY", 400)
    return dict(params)


def limit(params):
    value = params.get("limit", "20")
    if not re.fullmatch(r"[1-9][0-9]{0,2}", value) or int(value) > 100:
        invalid()
    return int(value)


def guard(context):
    require_staff(context, "support")
    # Unlike legacy optional discovery, absence never bypasses retained policy.
    if (
        context.session.execute(
            text(
                "SELECT to_regprocedure('public.sr_abuse_case_readable(uuid)') IS NOT NULL"
            )
        ).scalar_one()
        is not True
    ):
        raise AccessError(503)


def reauthorize(context):
    require_staff(authorize(context.session, context.principal), "support")


def cursor_read(settings, actor, token, binding):
    if token is None:
        return None
    try:
        if not re.fullmatch(r"[A-Za-z0-9_-]{40,2000}", token):
            raise ValueError()
        raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
        payload = json.loads(
            decrypt(
                settings,
                actor,
                "support_metadata_cursor:v1",
                raw[2:],
                int.from_bytes(raw[:2], "big"),
            )
        )
        if (
            not isinstance(payload, dict)
            or set(payload) != {"binding", "position"}
            or payload["binding"] != binding
        ):
            raise ValueError()
        return payload["position"]
    except (ValueError, TypeError, KeyError, UnicodeError, ProfileCryptoUnavailable):
        invalid("INVALID_CURSOR")


def cursor_write(settings, actor, binding, position):
    try:
        cipher, version = encrypt(
            settings,
            actor,
            "support_metadata_cursor:v1",
            json.dumps(
                {"binding": binding, "position": position}, separators=(",", ":")
            ),
        )
        token = (
            base64.urlsafe_b64encode(version.to_bytes(2, "big") + cipher)
            .decode()
            .rstrip("=")
        )
        if len(token) > 2000:
            raise ValueError()
        return token
    except (ValueError, TypeError, ProfileCryptoUnavailable):
        raise AccessError(503) from None


FIELDS = """c.id AS case_id,c.case_type,c.status,c.priority,c.case_revision,c.created_at,
 CASE WHEN c.assigned_staff_id=:actor THEN 'mine' ELSE 'unassigned' END AS assignment,
 COALESCE(c.assigned_staff_id=:actor,false) AS assigned_to_me"""
SCOPE = """(c.assigned_staff_id IS NULL OR c.assigned_staff_id=:actor)
 AND public.sr_abuse_case_readable(c.id)"""


def audit(context, request, action, case_id=None, count=None):
    context.session.execute(
        text("""INSERT INTO public.audit_events
      (actor_user_id,actor_kind,action,target_type,target_id,request_id,reason,safe_details)
      VALUES(:actor,'staff',:action,'support_case',:case_id,:rid,'authorized_metadata_read',CAST(:safe AS jsonb))"""),
        {
            "actor": context.principal.user_id,
            "action": action,
            "case_id": case_id,
            "rid": getattr(request.state, "request_id", None),
            # sr_safe_json permits outcome, but not an arbitrary count key.
            "safe": json.dumps(
                {} if count is None else {"outcome": f"returned_{count}_records"}
            ),
        },
    )


def checked(model, **values):
    try:
        result = model(**values)
        dates = (
            [item.created_at for item in result.items]
            if isinstance(result, (Page, History))
            else [result.created_at]
        )
        if any(d.utcoffset() is None for d in dates):
            raise ValueError()
        return result
    except (ValidationError, ValueError, TypeError):
        raise AccessError(503) from None


def listing(context, request):
    guard(context)
    p = query(
        request,
        {"case_id", "case_type", "status", "priority", "queue", "limit", "cursor"},
    )
    size = limit(p)
    for field, values in [
        (
            "case_type",
            (
                "activation",
                "lost_tag",
                "payment",
                "privacy",
                "ownership_dispute",
                "other",
            ),
        ),
        ("status", ("open", "investigating", "resolved", "closed")),
        ("priority", ("low", "normal", "high", "urgent")),
        ("queue", ("all", "mine", "unassigned")),
    ]:
        if field in p and p[field] not in values:
            invalid()
    case_id = ident(p["case_id"]) if "case_id" in p else None
    filters = {k: p.get(k) for k in ("case_type", "status", "priority")}
    filters.update(
        case_id=str(case_id) if case_id else None, queue=p.get("queue", "all")
    )
    binding = {"kind": "list", "filters": filters}
    pos = cursor_read(
        request.app.state.settings, context.principal.user_id, p.get("cursor"), binding
    )
    before_time = before_id = None
    if pos is not None:
        try:
            if not isinstance(pos, dict) or set(pos) != {"created_at", "case_id"}:
                raise ValueError()
            before_time = datetime.fromisoformat(pos["created_at"])
            if before_time.utcoffset() is None:
                raise ValueError()
            before_id = ident(pos["case_id"])
        except (ValueError, TypeError, KeyError):
            invalid("INVALID_CURSOR")
    as_of = datetime.now(UTC)
    rows = (
        context.session.execute(
            text(f"""SELECT {FIELDS} FROM public.support_cases c
      WHERE {SCOPE}
      AND (CAST(:case_id AS uuid) IS NULL OR c.id=:case_id)
      AND (CAST(:case_type AS text) IS NULL OR c.case_type=:case_type)
      AND (CAST(:status AS text) IS NULL OR c.status=:status)
      AND (CAST(:priority AS text) IS NULL OR c.priority=:priority)
      AND (:queue='all' OR (:queue='mine' AND c.assigned_staff_id=:actor)
           OR (:queue='unassigned' AND c.assigned_staff_id IS NULL))
      AND (CAST(:before_time AS timestamptz) IS NULL OR (c.created_at,c.id)<(:before_time,:before_id))
      ORDER BY c.created_at DESC,c.id DESC LIMIT :lim"""),
            {
                "actor": context.principal.user_id,
                **filters,
                "case_id": case_id,
                "before_time": before_time,
                "before_id": before_id,
                "lim": size + 1,
            },
        )
        .mappings()
        .all()
    )
    page = checked(
        Page, as_of=as_of, items=[dict(r) for r in rows[:size]], next_cursor=None
    )
    if len(rows) > size:
        last = page.items[-1]
        page.next_cursor = cursor_write(
            request.app.state.settings,
            context.principal.user_id,
            binding,
            {"created_at": last.created_at.isoformat(), "case_id": str(last.case_id)},
        )
    audit(context, request, "support.metadata.list", count=len(page.items))
    reauthorize(context)
    return page


def detail(context, request, case_id):
    guard(context)
    query(request, set())
    cid = ident(case_id)
    row = (
        context.session.execute(
            text(
                f"SELECT {FIELDS} FROM public.support_cases c WHERE c.id=:case_id AND {SCOPE}"
            ),
            {"actor": context.principal.user_id, "case_id": cid},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise AccessError(404)
    result = checked(Detail, **dict(row))
    audit(context, request, "support.metadata.read", cid)
    reauthorize(context)
    return result


def history(context, request, case_id):
    guard(context)
    p = query(request, {"limit", "cursor"})
    cid, size = ident(case_id), limit(p)
    binding = {"kind": "history", "case_id": str(cid)}
    pos = cursor_read(
        request.app.state.settings, context.principal.user_id, p.get("cursor"), binding
    )
    if pos is not None and (
        not isinstance(pos, dict)
        or set(pos) != {"revision", "before"}
        or any(
            type(pos[k]) is not int or not 1 <= pos[k] <= 2147483647
            for k in ("revision", "before")
        )
    ):
        invalid("INVALID_CURSOR")
    # Case scope/revision and event projection share one statement snapshot.
    row = (
        context.session.execute(
            text("""SELECT c.id AS case_id,c.case_revision,
      COALESCE((SELECT jsonb_agg(to_jsonb(e) ORDER BY e.case_revision DESC) FROM
       (SELECT h.id AS event_id,h.case_revision,h.event_type,h.from_status,h.to_status,h.priority,h.created_at
        FROM public.support_case_events h WHERE h.case_id=c.id AND h.case_revision<:before
        ORDER BY h.case_revision DESC LIMIT :lim) e),'[]'::jsonb) AS items
      FROM public.support_cases c WHERE c.id=:case_id AND c.assigned_staff_id=:actor
      AND public.sr_abuse_case_readable(c.id)"""),
            {
                "case_id": cid,
                "actor": context.principal.user_id,
                "before": pos["before"] if pos else 2147483648,
                "lim": size + 1,
            },
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise AccessError(404)
    if pos and pos["revision"] != row["case_revision"]:
        invalid("VERSION_MISMATCH", 409)
    try:
        # jsonb encodes timestamps/UUIDs as strings, unlike the direct case SELECT.
        events = [Event.model_validate_json(json.dumps(e)) for e in row["items"][:size]]
    except (ValidationError, ValueError, TypeError):
        raise AccessError(503) from None
    result = checked(
        History,
        case_id=row["case_id"],
        case_revision=row["case_revision"],
        items=events,
        next_cursor=None,
    )
    if len(row["items"]) > size:
        result.next_cursor = cursor_write(
            request.app.state.settings,
            context.principal.user_id,
            binding,
            {"revision": result.case_revision, "before": events[-1].case_revision},
        )
    audit(context, request, "support.metadata.history.read", cid)
    reauthorize(context)
    return result
