"""Bounded opaque spool verification using existing durable jobs/worker context."""

from collections.abc import Callable, Iterable
from uuid import UUID, uuid4

from sqlalchemy import text

from app.core.config import Settings
from app.core.manufacturing import (
    TransportConflict,
    canonical,
    identity_snapshot,
    read_spool,
    unpack,
)
from app.core.profile_crypto import ProfileCryptoUnavailable
from app.db.runtime import worker_transaction
from app.db.session import Database
from app.workers.printing import LeaseLost


def run_one(
    database: Database,
    settings: Settings,
    batch_id: UUID,
    *,
    spool_reader: Callable[[bytes], Iterable[bytes]] | None = None,
    before_finish: Callable[[], None] | None = None,
) -> bool:
    """One explicitly selected batch. No network/provider writer or release action."""
    if not settings.manufacturing_exports_enabled:
        raise TransportConflict("manufacturing_disabled")
    owner = "manufacturing:" + uuid4().hex
    with worker_transaction(database, owner) as db:
        lease = db.execute(
            text("SELECT public.sr_mfg_claim(:bid)"), {"bid": batch_id}
        ).scalar_one()
    if lease is None:
        return False
    success = False
    try:
        count, identity = identity_snapshot(lease["pairs"])
        if count != lease["pair_count"] or identity != lease["identity_sha256"]:
            raise TransportConflict("batch_identity_changed")
        data = unpack(settings, batch_id, "source", lease["source"])
        reader = spool_reader(data) if spool_reader else (data,)
        read_spool(reader, lease["manifest_sha256"])
        success = True
    except (TransportConflict, ProfileCryptoUnavailable, OSError):
        # Only a fixed error category is persisted, never provider exception text.
        pass
    if before_finish:
        before_finish()
    with worker_transaction(database, owner) as db:
        ok = db.execute(
            text("SELECT public.sr_mfg_finish(:bid,CAST(:body AS jsonb))"),
            {
                "bid": batch_id,
                "body": canonical(
                    {
                        "job_id": lease["job_id"],
                        "owner": owner,
                        "attempt": lease["attempt"],
                        "revision": lease["revision"],
                        "success": success,
                        "pairs": lease["pairs"],
                        "manifest_sha256": lease["manifest_sha256"],
                    }
                ),
            },
        ).scalar_one()
        if not ok:
            raise LeaseLost()
    return success
