"""Server-controlled contexts: use only after validating identity/MFA/session.

These roles are unavailable to browser clients. Context values are local to the
transaction; they are not a JWT verifier or a substitute for API authorization.
"""

import re
from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import Database


@contextmanager
def api_transaction(
    database: Database,
    actor_user_id: UUID | None = None,
    *,
    mfa_verified: bool = False,
    submission_id: UUID | None = None,
    scan_binding_digest: str | None = None,
) -> Iterator[Session]:
    if any(
        value is not None and not isinstance(value, UUID)
        for value in (actor_user_id, submission_id)
    ):
        raise ValueError("Runtime identity must be UUID")
    if not isinstance(mfa_verified, bool):
        raise TypeError("MFA context must be verified boolean")
    if scan_binding_digest is not None and not re.fullmatch(
        r"[0-9a-f]{64}", scan_binding_digest
    ):
        raise ValueError("Invalid scan binding digest")
    with database.transaction() as session:
        session.execute(text("SET LOCAL ROLE safereturn_api"))
        session.execute(
            text("""
SELECT set_config('safereturn.actor_id',:actor,true),
       set_config('safereturn.mfa_verified',:mfa,true),
       set_config('safereturn.submission_id',:submission,true),
       set_config('safereturn.scan_binding',:binding,true),
       set_config('safereturn.worker_id','',true)
"""),
            {
                "actor": str(actor_user_id) if actor_user_id else "",
                "mfa": "true" if mfa_verified else "false",
                "submission": str(submission_id) if submission_id else "",
                "binding": scan_binding_digest or "",
            },
        )
        yield session


@contextmanager
def worker_transaction(database: Database, worker_id: str) -> Iterator[Session]:
    if not isinstance(worker_id, str) or not re.fullmatch(
        r"[A-Za-z0-9_.:-]{1,100}", worker_id
    ):
        raise ValueError("Invalid worker instance ID")
    with database.transaction() as session:
        session.execute(text("SET LOCAL ROLE safereturn_worker"))
        session.execute(
            text("""
SELECT set_config('safereturn.worker_id',:worker,true),
       set_config('safereturn.actor_id','',true),
       set_config('safereturn.mfa_verified','false',true),
       set_config('safereturn.submission_id','',true),
       set_config('safereturn.scan_binding','',true)
"""),
            {"worker": worker_id},
        )
        yield session
