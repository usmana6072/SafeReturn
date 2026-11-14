"""Controlled stdin transport; importing this module performs no network/DB action.

Invocation: python -m app.template_evidence_control
JSON stdin: {operation,authorization,idempotency_key,envelope OR withdrawal}.
No command-line tokens, key enrollment, provider writes or file/URL imports.
"""

import json
import sys
from typing import Literal

from fastapi import HTTPException
from pydantic import Field, ValidationError, model_validator
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import AccessError, authorize
from app.core.auth import AuthRequired, AuthUnavailable, JWTVerifier
from app.core.config import Settings
from app.core.template_content import Closed
from app.core.template_evidence import parse
from app.db.runtime import api_transaction
from app.db.session import Database
from app.services.template_evidence import (
    EvidenceWithdrawal,
    import_evidence,
    revoke_evidence,
)


class ControlRequest(Closed):
    operation: Literal["import", "revoke"]
    authorization: str = Field(min_length=20, max_length=16384)
    idempotency_key: str = Field(pattern=r"^[A-Za-z0-9._:-]{8,160}$")
    envelope: dict | None = None
    withdrawal: EvidenceWithdrawal | None = None

    @model_validator(mode="after")
    def closed_operation(self):
        if (
            self.operation == "import"
            and (self.envelope is None or self.withdrawal is not None)
        ) or (
            self.operation == "revoke"
            and (self.envelope is not None or self.withdrawal is None)
        ):
            raise ValueError("One controlled operation required")
        return self


def run(raw, settings, verifier, database):
    def unique(pairs):
        value = {}
        for k, v in pairs:
            if k in value:
                raise ValueError("Invalid transport")
            value[k] = v
        return value

    if len(raw) > 163840:
        raise ValueError("Invalid transport")
    body = ControlRequest.model_validate(json.loads(raw, object_pairs_hook=unique))
    if database is None:
        raise AccessError(503)
    principal = verifier.verify(body.authorization)
    with api_transaction(database, principal.user_id) as session:
        context = authorize(session, principal)
        if body.operation == "import":
            wire = json.dumps(body.envelope, separators=(",", ":")).encode()
            parse(wire)
            return import_evidence(context, settings, wire, body.idempotency_key)
        return revoke_evidence(context, settings, body.withdrawal, body.idempotency_key)


def main():
    database = None
    verifier = None
    try:
        settings = Settings()
        if not settings.print_template_management_enabled:
            raise AccessError(503)
        # No connection before explicit operator invocation/valid stdin transport.
        raw = sys.stdin.buffer.read(163841)
        database = Database.from_settings(settings)
        verifier = JWTVerifier(settings)
        result = run(raw, settings, verifier, database)
        sys.stdout.write(json.dumps(result) + "\n")
        return 0
    except (
        ValueError,
        RecursionError,
        ValidationError,
        AuthRequired,
        AuthUnavailable,
        AccessError,
        SQLAlchemyError,
        HTTPException,
    ):
        sys.stderr.write("Controlled template operation unavailable or denied.\n")
        return 1
    finally:
        if database is not None:
            database.close()
        if verifier is not None:
            verifier.close()


if __name__ == "__main__":
    raise SystemExit(main())
