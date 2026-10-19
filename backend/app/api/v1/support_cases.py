"""Canonical case-scoped support intake; no payment, ownership or erasure commands."""

import hashlib
import json
import re
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from pydantic import Field, model_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api.auth import AccessError, Authenticated, require_staff
from app.api.v1.catalog import CatalogRoute, Closed, fail
from app.api.v1.fulfillment import bounds, page_cursor, paged
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt, encrypt

router = APIRouter(tags=["support cases"], route_class=CatalogRoute)
CaseType = Literal[
    "activation", "lost_tag", "payment", "privacy", "ownership_dispute", "other"
]
CaseStatus = Literal["open", "investigating", "resolved", "closed"]
Priority = Literal["low", "normal", "high", "urgent"]


class Intake(Closed):
    case_type: CaseType
    priority: Priority = "normal"
    pair_id: UUID | None = None
    order_id: UUID | None = None
    description: str = Field(min_length=4, max_length=2000)


class Change(Closed):
    expected_revision: int = Field(ge=1, le=2147483647, strict=True)
    action: Literal["claim", "update"]
    status: CaseStatus | None = None
    priority: Priority | None = None
    note: str | None = Field(default=None, min_length=4, max_length=2000)
    confirmed: bool = Field(strict=True)

    @model_validator(mode="after")
    def meaningful_change(self):
        if not self.confirmed:
            raise ValueError("Explicit confirmation required")
        values = (self.status, self.priority, self.note)
        if self.action == "claim" and any(v is not None for v in values):
            raise ValueError("Claim assigns only the current agent")
        if self.action == "update" and all(v is None for v in values):
            raise ValueError("Update must contain a change")
        return self


def command(context, request, operation, body, work, response_status):
    actor = context.principal.user_id
    key = request.headers.get("idempotency-key", "")
    if not re.fullmatch(r"[A-Za-z0-9._:-]{8,160}", key):
        fail(400, "IDEMPOTENCY_KEY_REQUIRED")
    digest = hashlib.sha256(body.model_dump_json().encode()).hexdigest()
    ref = hashlib.sha256(f"{actor}:{operation}:{key}".encode()).hexdigest()
    db = context.session
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:ref,0))"), {"ref": ref}
    )
    args = {"scope": str(actor), "actor": actor, "op": operation, "key": key}
    old = (
        db.execute(
            text(
                "SELECT request_hash,response_body_ciphertext,response_key_version FROM public.idempotency_records WHERE actor_scope=:scope AND operation=:op AND idempotency_key=:key FOR UPDATE"
            ),
            args,
        )
        .mappings()
        .one_or_none()
    )
    settings = request.app.state.settings
    try:
        if old:
            if old["request_hash"] != digest:
                fail(409, "IDEMPOTENCY_KEY_REUSED")
            return json.loads(
                decrypt(
                    settings,
                    actor,
                    "support:" + ref,
                    old["response_body_ciphertext"],
                    old["response_key_version"],
                )
            )
        with db.begin_nested():
            result = work(settings)
            if "error" in result:
                fail(
                    {"NOT_FOUND": 404, "STALE_CASE": 412, "INVALID_REQUEST": 422}.get(
                        result["error"], 409
                    ),
                    result["error"],
                )
            cipher, version = encrypt(
                settings, actor, "support:" + ref, json.dumps(result)
            )
            db.execute(
                text("""INSERT INTO public.idempotency_records(actor_scope,actor_user_id,operation,idempotency_key,request_hash,state,response_status,response_body_ciphertext,response_key_version,expires_at)
            VALUES(:scope,:actor,:op,:key,:hash,'completed',:status,:cipher,:version,now()+interval '1 day')"""),
                {
                    **args,
                    "hash": digest,
                    "status": response_status,
                    "cipher": cipher,
                    "version": version,
                },
            )
            return result
    except ProfileCryptoUnavailable:
        raise AccessError(503) from None
    except IntegrityError:
        fail(409, "CASE_CONFLICT")


FIELDS = "id,case_type,status,priority,case_revision,created_at,assigned_staff_id,description_format"


@router.get("/admin/support-cases", operation_id="API-097")
def cases(
    context: Authenticated,
    request: Request,
    limit: int = 20,
    cursor: str | None = None,
    case_id: UUID | None = None,
    case_type: CaseType | None = None,
    status: CaseStatus | None = None,
    priority: Priority | None = None,
    queue: Literal["all", "mine", "unassigned"] = "all",
    event_limit: int = 20,
    before_revision: int | None = None,
):
    require_staff(context, "support")
    bounds(limit)
    bounds(event_limit)
    if before_revision is not None and not 1 <= before_revision <= 2147483647:
        fail(422, "INVALID_EVENT_CURSOR")
    stamp, ident = page_cursor(cursor)
    uid = context.principal.user_id
    rows = (
        context.session.execute(
            text(f"""SELECT {FIELDS} FROM public.support_cases
      WHERE (assigned_staff_id IS NULL OR assigned_staff_id=:uid)
      AND (CAST(:id AS uuid) IS NULL OR id=:id) AND (CAST(:kind AS text) IS NULL OR case_type=:kind)
      AND (CAST(:status AS text) IS NULL OR status=:status) AND (CAST(:priority AS text) IS NULL OR priority=:priority)
      AND (:queue='all' OR (:queue='mine' AND assigned_staff_id=:uid) OR (:queue='unassigned' AND assigned_staff_id IS NULL))
      AND (CAST(:stamp AS timestamptz) IS NULL OR (created_at,id)<(:stamp,:ident))
      ORDER BY created_at DESC,id DESC LIMIT :lim"""),
            {
                "uid": uid,
                "id": case_id,
                "kind": case_type,
                "status": status,
                "priority": priority,
                "queue": queue,
                "stamp": stamp,
                "ident": ident,
                "lim": limit + 1,
            },
        )
        .mappings()
        .all()
    )
    if case_id and not rows:
        raise AccessError(404)
    items = []
    for row in rows:
        item = {
            k: v
            for k, v in row.items()
            if k not in ["assigned_staff_id", "description_format"]
        }
        own = row["assigned_staff_id"] == uid
        item.update(
            assigned_to_me=own,
            can_claim=row["assigned_staff_id"] is None
            and row["status"] in ["open", "investigating"],
            requires_escalation=row["case_type"]
            in ["payment", "privacy", "ownership_dispute"],
        )
        if case_id and own:
            private = (
                context.session.execute(
                    text(
                        "SELECT pair_id,order_id,opened_by_user_id,description_ciphertext,description_key_version FROM public.support_cases WHERE id=:id AND assigned_staff_id=:uid"
                    ),
                    {"id": case_id, "uid": uid},
                )
                .mappings()
                .one_or_none()
            )
            if private is None:
                raise AccessError(404)
            scope = context.session.execute(
                text("SELECT public.sr_support_context(:id)"), {"id": case_id}
            ).scalar_one()
            if scope is None:
                raise AccessError(404)
            item.update(
                {k: private[k] for k in ["pair_id", "order_id", "opened_by_user_id"]}
            )
            item.update(scope)
            item["legacy_description_restricted"] = (
                row["description_format"] == 0
                and private["description_ciphertext"] is not None
            )
            item["description"] = None
            try:
                if (
                    row["description_format"] == 1
                    and private["description_ciphertext"] is not None
                ):
                    item["description"] = decrypt(
                        request.app.state.settings,
                        case_id,
                        "support_description",
                        private["description_ciphertext"],
                        private["description_key_version"],
                    )
                events = (
                    context.session.execute(
                        text("""SELECT id,case_revision,actor_staff_id,event_type,from_status,to_status,priority,created_at,note_ciphertext,note_key_version
                FROM public.support_case_events WHERE case_id=:id AND (CAST(:before AS integer) IS NULL OR case_revision<:before)
                ORDER BY case_revision DESC LIMIT :lim"""),
                        {
                            "id": case_id,
                            "before": before_revision,
                            "lim": event_limit + 1,
                        },
                    )
                    .mappings()
                    .all()
                )
                history = []
                for event in events[:event_limit]:
                    entry = {
                        k: v
                        for k, v in event.items()
                        if k not in ["note_ciphertext", "note_key_version"]
                    }
                    entry["note"] = (
                        decrypt(
                            request.app.state.settings,
                            event["id"],
                            "support_note",
                            event["note_ciphertext"],
                            event["note_key_version"],
                        )
                        if event["note_ciphertext"] is not None
                        else None
                    )
                    history.append(entry)
            except ProfileCryptoUnavailable:
                raise AccessError(503) from None
            item["history"] = {
                "items": history,
                "next_before_revision": history[-1]["case_revision"]
                if len(events) > event_limit
                else None,
            }
            item["historical_creation_recorded"] = row["description_format"] == 1
            context.session.execute(
                text("""INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,request_id,reason,safe_details)
            VALUES(:uid,'staff','support_case.read','support_case',:id,:rid,'assigned_case_review',jsonb_build_object('version',CAST(:rev AS integer)))"""),
                {
                    "uid": uid,
                    "id": case_id,
                    "rid": getattr(request.state, "request_id", None),
                    "rev": row["case_revision"],
                },
            )
        items.append(item)
    return paged(items, limit)


@router.post("/admin/support-cases", operation_id="API-098", status_code=201)
def create_case(body: Intake, context: Authenticated, request: Request):
    require_staff(context, "support")

    def work(settings):
        cid = uuid4()
        event_id = uuid4()
        cipher, version = encrypt(
            settings, cid, "support_description", body.description
        )
        return context.session.execute(
            text(
                "SELECT public.sr_support_create(:id,:kind,:priority,:pair,:order,:cipher,CAST(:version AS smallint),:event,:rid)"
            ),
            {
                "id": cid,
                "kind": body.case_type,
                "priority": body.priority,
                "pair": body.pair_id,
                "order": body.order_id,
                "cipher": cipher,
                "version": version,
                "event": event_id,
                "rid": getattr(request.state, "request_id", None),
            },
        ).scalar_one()

    return command(context, request, "support.case.create", body, work, 201)


@router.patch("/admin/support-cases/{case_id}", operation_id="API-099")
def update_case(case_id: UUID, body: Change, context: Authenticated, request: Request):
    require_staff(context, "support")
    if (
        context.session.execute(
            text(
                "SELECT 1 FROM public.support_cases WHERE id=:id AND (assigned_staff_id IS NULL OR assigned_staff_id=:uid)"
            ),
            {"id": case_id, "uid": context.principal.user_id},
        ).scalar_one_or_none()
        is None
    ):
        raise AccessError(404)

    def work(settings):
        event_id = uuid4()
        cipher = version = None
        if body.note is not None:
            cipher, version = encrypt(settings, event_id, "support_note", body.note)
        return context.session.execute(
            text(
                "SELECT public.sr_support_change(:id,:expected,:action,:status,:priority,:event,:note,CAST(:version AS smallint),:rid)"
            ),
            {
                "id": case_id,
                "expected": body.expected_revision,
                "action": body.action,
                "status": body.status,
                "priority": body.priority,
                "event": event_id,
                "note": cipher,
                "version": version,
                "rid": getattr(request.state, "request_id", None),
            },
        ).scalar_one()

    return command(
        context, request, "support.case.update:" + str(case_id), body, work, 200
    )
