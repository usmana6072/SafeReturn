"""Narrow PostgreSQL helpers; no direct runtime template-table DML."""

import json

from sqlalchemy import text

from app.api.auth import AccessError
from app.api.v1.catalog import fail


class TemplateRepository:
    def __init__(self, context):
        self.context = context

    def call(self, action, payload):
        if action in {"publish", "bind", "retire", "bindings"}:
            from app.db.template_registry import RegistryRepository

            return RegistryRepository(self.context).call(action, payload)
        result = self.context.session.execute(
            text(
                "SELECT public.sr_template_service(:sid,:amr,:action,CAST(:payload AS jsonb))"
            ),
            {
                "sid": self.context.principal.session_id,
                "amr": self.context.principal.authentication_time,
                "action": action,
                "payload": json.dumps(payload),
            },
        ).scalar_one()
        if result is None:
            raise AccessError(403)
        if "error" in result:
            code = result["error"]
            if code in {"NOT_FOUND", "PROVIDER_UNAVAILABLE", "FORBIDDEN"}:
                raise AccessError(
                    {"NOT_FOUND": 404, "PROVIDER_UNAVAILABLE": 503, "FORBIDDEN": 403}[
                        code
                    ]
                )
            fail(
                412 if code == "VERSION_MISMATCH" else 409,
                "VERSION_MISMATCH" if code == "VERSION_MISMATCH" else "CONFLICT",
            )
        return result
