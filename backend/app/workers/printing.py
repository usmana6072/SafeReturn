"""Fenced durable print worker. CPU/provider I/O runs outside critical DB locks."""

import argparse
import json
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.printing import enqueue, occurrences
from app.core.config import Settings
from app.core.print_render import PrintUnavailable, digest, render_pdf
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt
from app.db.runtime import worker_transaction
from app.db.session import Database
from app.integrations.print_storage import PrintStore


class LeaseLost(Exception):
    pass


def claim(database, s, job_id=None):
    owner = s.print_worker_id[:60] + ":" + uuid4().hex
    with worker_transaction(database, owner) as db:
        row = (
            db.execute(
                text(
                    """SELECT * FROM public.durable_jobs WHERE (job_kind='print.render' OR (job_kind='allocation.finalize' AND idempotency_key LIKE 'print.request:%')) AND (CAST(:id AS uuid) IS NULL OR id=:id) AND ((status IN('pending','retry') AND next_attempt_at<=clock_timestamp()) OR (status='leased' AND lease_until<=clock_timestamp())) ORDER BY created_at,id FOR UPDATE SKIP LOCKED LIMIT 1"""
                ),
                {"id": job_id},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        if row["attempt_count"] >= s.print_max_attempts:
            db.execute(
                text(
                    "UPDATE public.durable_jobs SET status='dead',lease_owner=NULL,lease_until=NULL,last_error_code='attempts_exhausted' WHERE id=:id"
                ),
                {"id": row["id"]},
            )
            return None
        db.execute(
            text(
                "UPDATE public.durable_jobs SET status='leased',lease_owner=:owner,lease_until=clock_timestamp()+make_interval(secs=>:seconds),attempt_count=attempt_count+1 WHERE id=:id"
            ),
            {"id": row["id"], "owner": owner, "seconds": s.print_lease_seconds},
        )
        return dict(row, lease_owner=owner, attempt_count=row["attempt_count"] + 1)


def fence(db, lease):
    ok = db.execute(
        text(
            "SELECT id FROM public.durable_jobs WHERE id=:id AND status='leased' AND lease_owner=:owner AND attempt_count=:attempt AND lease_until>clock_timestamp() FOR UPDATE"
        ),
        {
            "id": lease["id"],
            "owner": lease["lease_owner"],
            "attempt": lease["attempt_count"],
        },
    ).first()
    if ok is None:
        raise LeaseLost()


def complete(db, lease):
    completed = db.execute(
        text(
            "UPDATE public.durable_jobs SET status='completed',completed_at=clock_timestamp(),lease_owner=NULL,lease_until=NULL,last_error_code=NULL WHERE id=:id AND status='leased' AND lease_owner=:owner AND attempt_count=:attempt AND lease_until>clock_timestamp() RETURNING id"
        ),
        {
            "id": lease["id"],
            "owner": lease["lease_owner"],
            "attempt": lease["attempt_count"],
        },
    ).scalar_one_or_none()
    if completed is None:
        raise LeaseLost()


def run_one(database, s, storage=None, job_id=None):
    if not s.print_enabled:
        raise PrintUnavailable("print_disabled")
    lease = claim(database, s, job_id)
    if lease is None:
        return False
    try:
        if lease["job_kind"] == "allocation.finalize":
            with worker_transaction(database, lease["lease_owner"]) as db:
                fence(db, lease)
                existing = db.execute(
                    text("SELECT id FROM public.print_jobs WHERE order_id=:id"),
                    {"id": lease["order_id"]},
                ).first()
                if existing is None:
                    enqueue(db, s, lease["order_id"], 0, "automatic paid-order render")
                complete(db, lease)
            return True
        with worker_transaction(database, lease["lease_owner"]) as db:
            fence(db, lease)
            rows = occurrences(db, lease["order_id"])
            manifest = json.loads(
                decrypt(
                    s,
                    lease["order_id"],
                    "print-render",
                    lease["payload_ciphertext"],
                    lease["payload_key_version"],
                )
            )
            if [
                (str(r["qr_id"]), int(r["copies"]), r["public_token"]) for r in rows
            ] != [
                (o["qr_id"], o["copies"], o["url"].rsplit("/", 1)[1])
                for o in manifest["occurrences"]
            ]:
                raise PrintUnavailable("binding_changed")
            job = db.execute(
                text("SELECT template_fingerprint FROM public.print_jobs WHERE id=:id"),
                {"id": lease["print_job_id"]},
            ).scalar_one()
            if job != digest(manifest):
                raise PrintUnavailable("manifest_integrity_failure")
            db.execute(
                text(
                    "UPDATE public.print_jobs SET status='rendering',attempt_count=attempt_count+1,failure_code=NULL WHERE id=:id"
                ),
                {"id": lease["print_job_id"]},
            )
        # No transaction held during shaping, PDF generation or HTTP.
        data, info = render_pdf(manifest)
        key = (
            "order-print/"
            + str(lease["order_id"])
            + "/"
            + str(lease["print_job_id"])
            + "/"
            + digest(manifest)
            + ".pdf"
        )
        (storage or PrintStore(s)).upload(key, data)
        with worker_transaction(database, lease["lease_owner"]) as db:
            rows = occurrences(db, lease["order_id"])
            if not rows:
                raise PrintUnavailable("binding_changed")
            fence(db, lease)
            aid = uuid4()
            db.execute(
                text(
                    "INSERT INTO public.print_artifacts(id,print_job_id,object_key,format,sha256_hex,size_bytes) VALUES(:id,:jid,:key,'pdf',:sha,:size) ON CONFLICT(object_key) DO NOTHING"
                ),
                {
                    "id": aid,
                    "jid": lease["print_job_id"],
                    "key": key,
                    "sha": info["sha256"],
                    "size": len(data),
                },
            )
            stored = db.execute(
                text(
                    "SELECT sha256_hex FROM public.print_artifacts WHERE object_key=:key"
                ),
                {"key": key},
            ).scalar_one()
            if stored != info["sha256"]:
                raise PrintUnavailable("artifact_integrity_failure")
            db.execute(
                text(
                    "UPDATE public.print_jobs SET status='ready',failure_code=NULL WHERE id=:id"
                ),
                {"id": lease["print_job_id"]},
            )
            db.execute(
                text(
                    "INSERT INTO public.audit_events(actor_kind,action,target_type,target_id,reason,safe_details) VALUES('system','print.ready','print_job',:id,'fenced vector render completed','{}'::jsonb)"
                ),
                {"id": lease["print_job_id"]},
            )
            complete(db, lease)
        return True
    except LeaseLost:
        return False
    except (PrintUnavailable, ProfileCryptoUnavailable, SQLAlchemyError) as error:
        code = (
            str(error)
            if isinstance(error, PrintUnavailable)
            else "database_recheck_failed"
            if isinstance(error, SQLAlchemyError)
            else "crypto_unavailable"
        )
        if not code or len(code) > 80:
            code = "print_unavailable"
        try:
            with worker_transaction(database, lease["lease_owner"]) as db:
                fence(db, lease)
                if lease["print_job_id"]:
                    db.execute(
                        text(
                            "UPDATE public.print_jobs SET status='failed',failure_code=:code WHERE id=:id"
                        ),
                        {"id": lease["print_job_id"], "code": code},
                    )
                db.execute(
                    text(
                        "UPDATE public.durable_jobs SET status=:status,lease_owner=NULL,lease_until=NULL,last_error_code=:code,next_attempt_at=clock_timestamp()+make_interval(secs=>:delay) WHERE id=:id"
                    ),
                    {
                        "id": lease["id"],
                        "status": "dead"
                        if lease["attempt_count"] >= s.print_max_attempts
                        else "retry",
                        "code": code,
                        "delay": min(3600, 30 * 2 ** lease["attempt_count"]),
                    },
                )
        except (LeaseLost, SQLAlchemyError):
            pass
        return False


def main():
    p = argparse.ArgumentParser(
        description="One bounded private-print worker iteration; no daemon"
    )
    p.add_argument("--once", action="store_true", required=True)
    p.parse_args()
    s = Settings()
    database = Database.from_settings(
        s.model_copy(update={"database_url": s.worker_database_url})
    )
    if not database or not s.worker_database_url:
        raise SystemExit("Dedicated worker configuration required")
    try:
        run_one(database, s)
    finally:
        database.close()


if __name__ == "__main__":
    main()
