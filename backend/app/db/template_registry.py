"""Registry admission and snapshot helpers. Old installed schemas stay compatible."""

import json
import re

from sqlalchemy import text

from app.api.auth import AccessError
from app.api.v1.catalog import fail


def available(session):
    if "template_registry_available" not in session.info:
        session.info["template_registry_available"] = (
            session.execute(
                text(
                    "SELECT to_regprocedure('public.sr_template_registry_gate(boolean)') IS NOT NULL AS template_registry_available"
                )
            ).scalar_one()
            is True
        )
    return session.info["template_registry_available"]


def gate(session, *, exclusive=False):
    if available(session):
        # Never upgrade a shared advisory lock: the operation chooses its mode first.
        mode = session.info.get("template_registry_gate")
        if mode == "shared" and exclusive:
            raise AccessError(503)
        if mode is None:
            session.execute(
                text("SELECT public.sr_template_registry_gate(:exclusive)"),
                {"exclusive": exclusive},
            )
            session.info["template_registry_gate"] = (
                "exclusive" if exclusive else "shared"
            )
        return True
    return False


def result(value):
    if value is None:
        raise AccessError(403)
    if isinstance(value, dict) and "error" in value:
        code = value["error"]
        if code in {'TEMPLATE_VARIANT_MISMATCH', 'TEMPLATE_BINDING_UNAVAILABLE'}:
            fail(422, code)
        if code in {"FORBIDDEN", "NOT_FOUND", "PROVIDER_UNAVAILABLE"}:
            raise AccessError(
                {"FORBIDDEN": 403, "NOT_FOUND": 404, "PROVIDER_UNAVAILABLE": 503}[code]
            )
        fail(
            412 if code == "VERSION_MISMATCH" else 409,
            "VERSION_MISMATCH" if code == "VERSION_MISMATCH" else "CONFLICT",
        )
    return value


class RegistryRepository:
    def __init__(self, context):
        self.context = context

    def call(self, action, payload):
        return result(
            self.context.session.execute(
                text(
                    "SELECT public.sr_template_lifecycle(:sid,:amr,:action,CAST(:payload AS jsonb))"
                ),
                {
                    "sid": self.context.principal.session_id,
                    "amr": self.context.principal.authentication_time,
                    "action": action,
                    "payload": json.dumps(payload),
                },
            ).scalar_one()
        )


def resolve(session, line):
    if not available(session):
        return None
    gate(session)
    raw = session.execute(
        text("SELECT public.sr_template_resolve(:variant,CAST(:uses AS jsonb))"),
        {"variant": line["variant_id"], "uses": json.dumps(line["qr_uses"])},
    ).scalar_one()
    value = None if raw is None else result(raw)
    settings = session.info.get("settings")
    if (
        value is not None
        and settings is not None
        and not settings.print_template_management_enabled
    ):
        raise AccessError(503)
    return value


def catalog_eligibility(session, variant_id, qr_type=None):
    if not available(session):
        return None
    if qr_type is not None:
        return session.execute(text("SELECT public.sr_template_catalog_type_eligible(:id,:kind)"), {"id": variant_id, "kind": qr_type}).scalar_one()
    return session.execute(
        text("SELECT public.sr_template_catalog_eligible(:id)"), {"id": variant_id}
    ).scalar_one()


def attach_quote_specs(session, lines):
    signatures = set()
    registry = False
    legacy = False
    for line in lines:
        value = resolve(session, line)
        if value is None:
            legacy = True
            continue
        registry = True
        line["registry_specs"] = value
        for spec in value:
            signatures.add((spec["asset_set_id"], spec["policy_sha256"]))
    # Cannot prove shared legacy/registry assets: reject before taking money.
    if registry and (legacy or len(signatures) != 1):
        fail(409, "CONFLICT")


def recheck_quote(session, lines):
    for line in lines:
        current = resolve(session, line)
        if current != line.get("registry_specs"):
            fail(409, "CONFLICT")


def freeze_use(session, use_id, spec):
    if spec is not None:
        result(
            session.execute(
                text("SELECT public.sr_template_freeze_use(:id,CAST(:spec AS jsonb))"),
                {"id": use_id, "spec": json.dumps(spec)},
            ).scalar_one()
        )


def order_specs(session, order_id, *, lock=True):
    if not available(session):
        return None
    if lock:
        gate(session)
    raw = session.execute(
        text("SELECT public.sr_template_order_specs(:id)"), {"id": order_id}
    ).scalar_one()
    return None if raw is None else result(raw)


def registry_manifest(specs, rows):
    """Adapter uses purchase-frozen content. Never current variant or latest revision."""
    from app.core.print_render import PrintUnavailable, build_manifest

    by_id = {s["use_id"]: s for s in specs}
    if len(by_id) != len(specs) or set(by_id) != {str(row["use_id"]) for row in rows}:
        raise PrintUnavailable("registry_snapshot_incomplete")
    assets = {(s["asset_set_id"], s["policy_sha256"]) for s in specs}
    if len(assets) != 1:
        raise PrintUnavailable("registry_assets_incompatible")
    templates = []
    seen = set()
    for s in specs:
        identity = (s["key"], s["version"], s["tag_type"], s["content"]["symbol_mm"])
        if identity not in seen:
            from app.core.template_content import Content

            templates.append(
                Content.model_validate(s["content"])
                .renderer_template(s["key"], s["version"], s["tag_type"])
                .model_dump()
            )
            seen.add(identity)
    first = specs[0]
    bundle = {
        "renderer": "safereturn-vector-v1",
        "approval_ref": "registry-published-v1",
        "origin": first["origin"],
        "font": first["assets"]["font"],
        "logo": first["assets"]["logo"],
        "templates": templates,
    }
    adapted = []
    for row in rows:
        s = by_id[str(row["use_id"])]
        if row["tag_type"] != s["tag_type"]:
            raise PrintUnavailable("registry_type_mismatch")
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", row["public_token"]):
            raise PrintUnavailable("registry_token_policy_mismatch")
        adapted.append(dict(row, template_key=s["key"], template_version=s["version"]))
    value = build_manifest(bundle, adapted)
    value["registry_snapshots"] = [
        {
            k: s[k]
            for k in (
                "use_id",
                "revision_id",
                "fingerprint_sha256",
                "approval_id",
                "policy_sha256",
            )
        }
        for s in specs
    ]
    return value
