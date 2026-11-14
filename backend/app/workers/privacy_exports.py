"""Bounded, fenced basic_v1 generator. Explicit injected private store only.

No CLI/automatic live provider activation, notifications or object deletion.
Retries upload identical encrypted bytes under the immutable manifest identity.
"""

import hashlib
import json
from uuid import uuid4

from sqlalchemy import text

from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt, encrypt
from app.db.runtime import worker_transaction
from app.integrations.privacy_export_storage import PrivacyExportStorage

CATEGORIES = (
    "independent_qr",
    "independent_history",
    "logical_items",
    "item_sizes",
    "account",
    "pairs",
    "orders",
    "items",
    "occurrences",
    "payments",
    "receipts",
    "privacy_requests",
)
OMISSIONS = {
    "historical_pairs": ("not-supported", "ownership_history_not_recorded"),
    "lost_text": ("omitted", "third_party_review_required"),
    "ice_contacts_medical_guardians": ("omitted", "individual_authorization_required"),
    "finder_bodies_contacts_locations_identifiers": (
        "omitted",
        "original_recipient_metadata_only",
    ),
    "shipping_identity_address": ("omitted", "outside_basic_v1"),
    "auth_secrets_sessions_factors": ("omitted", "security_secrets"),
    "private_notes_legacy_reasons_staff_audit": (
        "omitted",
        "restricted_staff_material",
    ),
    "storage_provider_credentials": ("omitted", "security_secrets"),
}


class LeaseLost(Exception):
    pass


class ScopeExceeded(Exception):
    pass


def claim(database, request_id=None):
    token = uuid4()
    with worker_transaction(database, "privacy-export:" + token.hex) as db:
        row = (
            db.execute(
                text("""SELECT * FROM public.privacy_exports
          WHERE (CAST(:id AS uuid) IS NULL OR id=:id) AND
          (status IN ('approved','retry') OR (status='building' AND lease_until<=clock_timestamp()))
          ORDER BY created_at,id FOR UPDATE SKIP LOCKED LIMIT 1"""),
                {"id": request_id},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        valid = db.execute(
            text(
                "SELECT public.sr_export_current(r) FROM public.privacy_exports r WHERE id=:id"
            ),
            {"id": row["id"]},
        ).scalar_one()
        if (
            not valid
            or row["attempt"] >= 3
            or (
                row["watermark"] is None
                and db.execute(
                    text("SELECT :stamp < now()-interval '24 hours'"),
                    {"stamp": row["approved_at"]},
                ).scalar_one()
            )
        ):
            db.execute(
                text(
                    "UPDATE public.privacy_exports SET status='escalated',revision=revision+1,failure_code='review_required',lease_token=NULL,lease_until=NULL WHERE id=:id"
                ),
                {"id": row["id"]},
            )
            return None
        new = (
            db.execute(
                text("""UPDATE public.privacy_exports SET status='building',revision=revision+1,attempt=attempt+1,
          lease_token=:token,lease_until=clock_timestamp()+interval '180 seconds',watermark=coalesce(watermark,clock_timestamp())
          WHERE id=:id RETURNING *"""),
                {"id": row["id"], "token": token},
            )
            .mappings()
            .one()
        )
        return dict(new)


def fence(db, lease):
    row = (
        db.execute(
            text("""SELECT * FROM public.privacy_exports r WHERE id=:id AND lease_token=:token
      AND status='building' AND lease_until>clock_timestamp() AND public.sr_export_current(r) FOR UPDATE"""),
            {"id": lease["id"], "token": lease["lease_token"]},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise LeaseLost()
    return row


def audit(db, request_id, action):
    db.execute(
        text("""INSERT INTO public.audit_events(actor_kind,action,target_type,target_id)
      VALUES('system',:action,'privacy_export',:id)"""),
        {"action": action, "id": request_id},
    )


def snapshot(database, lease, settings):
    categories, data = {}, {}
    count, byte_count = 0, 0
    # A single MVCC snapshot across every bounded page; no source mutations.
    with database.transaction() as db:
        db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
        db.execute(text("SET LOCAL ROLE safereturn_worker"))
        db.execute(
            text("SELECT set_config('safereturn.worker_id','privacy-snapshot',true)")
        )
        # Use the exact MVCC visibility watermark, rather than implying that the
        # earlier lease-admission timestamp is a wall-clock completeness cutoff.
        source_watermark = (
            "pg_snapshot:"
            + db.execute(text("SELECT pg_current_snapshot()::text")).scalar_one()
        )
        for category in CATEGORIES:
            after, values = None, []
            while True:
                rows = (
                    db.execute(
                        text(
                            "SELECT * FROM public.sr_export_page(:id,:token,:category,:after)"
                        ),
                        {
                            "id": lease["id"],
                            "token": lease["lease_token"],
                            "category": category,
                            "after": after,
                        },
                    )
                    .mappings()
                    .all()
                )
                for row in rows:
                    count += 1
                    byte_count += len(
                        json.dumps(row["value"], ensure_ascii=False).encode()
                    )
                    if count > 10000 or byte_count > 10 * 1024 * 1024:
                        raise ScopeExceeded()
                    values.append(row["value"])
                if len(rows) < 100:
                    break
                after = rows[-1]["id"]
            data[category] = values
            categories[category] = {
                "disposition": "included",
                "reason_code": "allowlisted_own_records",
                "schema_version": 1,
                "source_count": len(values),
                "source_watermark": source_watermark,
            }
        for name, (disposition, reason) in OMISSIONS.items():
            categories[name] = {
                "disposition": disposition,
                "reason_code": reason,
                "schema_version": 1,
                "source_count": None,
                "source_watermark": source_watermark,
            }
        manifest = {
            "scope": "basic_v1",
            "policy_version": lease["policy_version"],
            "manifest_id": str(lease["manifest_id"]),
            "categories": categories,
            "records": count,
            "snapshot": "generation_mvcc_snapshot; later changes excluded",
            "holds": "records_preserved; no retention hold interpreted as disclosure denial",
            "complete_legal_account_dump": False,
        }
        raw = json.dumps(
            {"manifest": manifest, "data": data},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        if len(raw.encode()) > 10 * 1024 * 1024:
            raise ScopeExceeded()
        cipher, version = encrypt(
            settings, lease["id"], "privacy-export:" + str(lease["manifest_id"]), raw
        )
    return cipher, version, hashlib.sha256(raw.encode()).hexdigest(), categories


def run_one(database, settings, storage: PrivacyExportStorage, request_id=None):
    if storage is None:
        raise ValueError("Explicit private storage adapter required")
    lease = claim(database, request_id)
    if lease is None:
        return False
    try:
        if lease["snapshot_ciphertext"] is None:
            cipher, version, checksum, categories = snapshot(database, lease, settings)
            with worker_transaction(database, "privacy-save") as db:
                fence(db, lease)
                db.execute(
                    text("""UPDATE public.privacy_exports SET snapshot_ciphertext=:cipher,snapshot_key_version=:version,
                checksum=:sha,manifest=CAST(:manifest AS jsonb) WHERE id=:id"""),
                    {
                        "id": lease["id"],
                        "cipher": cipher,
                        "version": version,
                        "sha": checksum,
                        "manifest": json.dumps(categories),
                    },
                )
        else:
            cipher, version, checksum = (
                bytes(lease["snapshot_ciphertext"]),
                lease["snapshot_key_version"],
                lease["checksum"],
            )
            raw = decrypt(
                settings,
                lease["id"],
                "privacy-export:" + str(lease["manifest_id"]),
                cipher,
                version,
            )
            if hashlib.sha256(raw.encode()).hexdigest() != checksum:
                raise ProfileCryptoUnavailable()
        key = "privacy-export/" + str(lease["id"]) + "/" + str(lease["manifest_id"])
        # External I/O outside locks; a stale upload never authorizes retrieval.
        storage.upload(key, cipher)
        with worker_transaction(database, "privacy-complete") as db:
            fence(db, lease)
            db.execute(
                text("""UPDATE public.privacy_exports SET status='ready',revision=revision+1,object_key=:key,key_version=:version,
             ready_at=clock_timestamp(),expires_at=clock_timestamp()+interval '24 hours',lease_token=NULL,lease_until=NULL,failure_code=NULL WHERE id=:id"""),
                {"id": lease["id"], "key": key, "version": version},
            )
            audit(db, lease["id"], "privacy.export.ready")
        return True
    except LeaseLost:
        return False
    except (ProfileCryptoUnavailable, OSError, ScopeExceeded) as error:
        with worker_transaction(database, "privacy-failure") as db:
            # Expired/replaced leases must not change a successor's state.
            changed = db.execute(
                text("""UPDATE public.privacy_exports SET status=:status,revision=revision+1,
             failure_code=:code,lease_token=NULL,lease_until=NULL WHERE id=:id AND lease_token=:token AND lease_until>clock_timestamp() RETURNING id"""),
                {
                    "id": lease["id"],
                    "token": lease["lease_token"],
                    "status": "escalated"
                    if isinstance(error, ScopeExceeded) or lease["attempt"] >= 3
                    else "retry",
                    "code": "generation_unavailable",
                },
            ).scalar_one_or_none()
            if changed is not None:
                audit(db, lease["id"], "privacy.export.generation_failed")
        return changed is not None
