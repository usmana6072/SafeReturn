"""Durable workflow records. Ciphertext is opaque; encryption is service-owned."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.commerce import Created
from app.db.models import Base, Identity, Timestamps, auth_fk


class FinderMessage(Identity, Base):
    __tablename__ = "finder_messages"
    qr_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("qr_codes.id", ondelete="RESTRICT")
    )
    recipient_owner_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, auth_fk())
    finder_name: Mapped[str | None] = mapped_column(String(80))
    finder_email_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    finder_phone_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    finder_contact_key_version: Mapped[int] = mapped_column(SmallInteger)
    preferred_contact: Mapped[str | None] = mapped_column(String(12))
    message_text_ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    message_key_version: Mapped[int] = mapped_column(SmallInteger)
    status: Mapped[str] = mapped_column(String(24), server_default="new")
    abuse_flag: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    consent_version: Mapped[str] = mapped_column(String(30))
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retention_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint(
            "status IN ('new','viewed','archived','flagged','deleted')", name="status"
        ),
        CheckConstraint(
            "preferred_contact IN ('email','phone')", name="preferred_contact"
        ),
        CheckConstraint(
            "finder_email_ciphertext IS NOT NULL OR finder_phone_ciphertext IS NOT NULL",
            name="contact",
        ),
        CheckConstraint(
            "finder_contact_key_version > 0 AND message_key_version > 0 AND octet_length(message_text_ciphertext) > 0",
            name="encryption",
        ),
        CheckConstraint(
            "finder_email_ciphertext IS NULL OR octet_length(finder_email_ciphertext) > 0",
            name="email",
        ),
        CheckConstraint(
            "finder_phone_ciphertext IS NULL OR octet_length(finder_phone_ciphertext) > 0",
            name="phone",
        ),
        CheckConstraint("length(consent_version) > 0", name="consent"),
        Index(
            "idx_finder_recipient", "recipient_owner_user_id", text("submitted_at DESC")
        ),
        Index("idx_finder_qr", "qr_id", text("submitted_at DESC")),
    )


class FinderMessageLocation(Created, Base):
    __tablename__ = "finder_message_locations"
    finder_message_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("finder_messages.id", ondelete="CASCADE"), primary_key=True
    )
    latitude_ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    longitude_ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    accuracy_m: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    location_source: Mapped[str] = mapped_column(
        String(30), server_default="browser_geolocation"
    )
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consent_version: Mapped[str] = mapped_column(String(30))
    key_version: Mapped[int] = mapped_column(SmallInteger)
    __table_args__ = (
        CheckConstraint("accuracy_m >= 0", name="accuracy"),
        CheckConstraint("location_source = 'browser_geolocation'", name="source"),
        CheckConstraint(
            "key_version > 0 AND octet_length(latitude_ciphertext)>0 AND octet_length(longitude_ciphertext)>0",
            name="encryption",
        ),
        CheckConstraint("length(consent_version)>0", name="consent"),
    )


class EncryptedPayload:
    payload_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    payload_key_version: Mapped[int | None] = mapped_column(SmallInteger)


class Lease:
    attempt_count: Mapped[int] = mapped_column(Integer, server_default="0")
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    lease_owner: Mapped[str | None] = mapped_column(String(100))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(80))


PAYLOAD_CHECK = "(payload_ciphertext IS NULL AND payload_key_version IS NULL) OR (payload_ciphertext IS NOT NULL AND octet_length(payload_ciphertext)>0 AND payload_key_version IS NOT NULL AND payload_key_version>0)"
LEASE_CHECK = "(status='leased' AND lease_owner IS NOT NULL AND lease_until IS NOT NULL) OR (status<>'leased' AND lease_owner IS NULL AND lease_until IS NULL)"


class NotificationOutbox(Identity, Created, EncryptedPayload, Lease, Base):
    __tablename__ = "notification_outbox"
    event_type: Mapped[str] = mapped_column(String(60))
    aggregate_type: Mapped[str] = mapped_column(String(40))
    aggregate_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    recipient_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, auth_fk())
    recipient_email_snapshot_ciphertext: Mapped[bytes | None] = mapped_column(
        LargeBinary
    )
    recipient_email_key_version: Mapped[int | None] = mapped_column(SmallInteger)
    payload_version: Mapped[int] = mapped_column(SmallInteger, server_default="1")
    status: Mapped[str] = mapped_column(String(16), server_default="pending")
    provider_message_id: Mapped[str | None] = mapped_column(String(150))
    idempotency_key: Mapped[str] = mapped_column(String(160), unique=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','leased','retry','sent','dead')", name="status"
        ),
        CheckConstraint("attempt_count>=0 AND payload_version>0", name="versions"),
        CheckConstraint(LEASE_CHECK, name="lease"),
        CheckConstraint(PAYLOAD_CHECK, name="payload_key"),
        CheckConstraint(
            "(recipient_email_snapshot_ciphertext IS NULL AND recipient_email_key_version IS NULL) OR (recipient_email_snapshot_ciphertext IS NOT NULL AND recipient_email_key_version IS NOT NULL AND recipient_email_key_version>0)",
            name="email_key",
        ),
        CheckConstraint("status<>'sent' OR sent_at IS NOT NULL", name="sent"),
        Index(
            "idx_outbox_due",
            "next_attempt_at",
            "created_at",
            postgresql_where=text("status IN ('pending','retry')"),
        ),
        Index(
            "idx_outbox_lease", "lease_until", postgresql_where=text("status='leased'")
        ),
        Index("idx_outbox_aggregate", "aggregate_type", "aggregate_id"),
    )


class NotificationAttempt(Identity, Base):
    __tablename__ = "notification_attempts"
    outbox_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("notification_outbox.id", ondelete="RESTRICT")
    )
    attempt_number: Mapped[int] = mapped_column(Integer)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[str] = mapped_column(String(20), server_default="unknown")
    provider_message_id: Mapped[str | None] = mapped_column(String(150))
    error_code: Mapped[str | None] = mapped_column(String(80))
    __table_args__ = (
        UniqueConstraint("outbox_id", "attempt_number"),
        CheckConstraint("attempt_number>0", name="attempt"),
        CheckConstraint(
            "outcome IN ('success','transient_failure','permanent_failure','unknown')",
            name="outcome",
        ),
    )


class AuditEvent(Identity, Base):
    __tablename__ = "audit_events"
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, auth_fk())
    actor_kind: Mapped[str] = mapped_column(String(20))
    action: Mapped[str] = mapped_column(String(100))
    target_type: Mapped[str] = mapped_column(String(60))
    target_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    request_id: Mapped[str | None] = mapped_column(String(100))
    reason: Mapped[str | None] = mapped_column(Text)
    safe_details: Mapped[dict] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    __table_args__ = (
        CheckConstraint(
            "actor_kind IN ('customer','staff','system','anonymous')", name="actor"
        ),
        CheckConstraint("jsonb_typeof(safe_details)='object'", name="details"),
        Index("idx_audit_target", "target_type", "target_id", text("occurred_at DESC")),
        Index("idx_audit_actor", "actor_user_id", text("occurred_at DESC")),
    )


class IdempotencyRecord(Identity, Created, Base):
    __tablename__ = "idempotency_records"
    actor_scope: Mapped[str] = mapped_column(String(100))
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, auth_fk())
    operation: Mapped[str] = mapped_column(String(80))
    idempotency_key: Mapped[str] = mapped_column(String(160))
    request_hash: Mapped[str] = mapped_column(String(64))
    response_status: Mapped[int | None] = mapped_column(Integer)
    response_body_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    response_key_version: Mapped[int | None] = mapped_column(SmallInteger)
    state: Mapped[str] = mapped_column(String(20), server_default="processing")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("actor_scope", "operation", "idempotency_key"),
        CheckConstraint("request_hash ~ '^[0-9a-f]{64}$'", name="request_hash"),
        CheckConstraint("state IN ('processing','completed','failed')", name="state"),
        CheckConstraint("expires_at>created_at", name="expiry"),
        CheckConstraint("response_status BETWEEN 100 AND 599", name="response_status"),
        CheckConstraint(
            "(response_body_ciphertext IS NULL AND response_key_version IS NULL) OR (response_body_ciphertext IS NOT NULL AND response_key_version IS NOT NULL AND response_key_version>0)",
            name="response_key",
        ),
    )


class ScanContext(Identity, Created, Base):
    __tablename__ = "scan_contexts"
    qr_code_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("qr_codes.id", ondelete="RESTRICT")
    )
    public_token_digest: Mapped[str] = mapped_column(String(64))
    session_binding_digest: Mapped[str] = mapped_column(String(64))
    bound_actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, auth_fk())
    state: Mapped[str] = mapped_column(String(16), server_default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint(
            "public_token_digest ~ '^[0-9a-f]{64}$' AND session_binding_digest ~ '^[0-9a-f]{64}$'",
            name="digests",
        ),
        CheckConstraint(
            "state IN ('pending','consumed','expired','revoked')", name="state"
        ),
        CheckConstraint("expires_at>created_at", name="expiry"),
        CheckConstraint(
            "state<>'consumed' OR (consumed_at IS NOT NULL AND bound_actor_user_id IS NOT NULL)",
            name="consumption",
        ),
        Index(
            "idx_scan_expiry", "expires_at", postgresql_where=text("state='pending'")
        ),
    )


class ActivationIntent(Identity, Created, Base):
    __tablename__ = "activation_intents"
    actor_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, auth_fk())
    pair_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tag_pairs.id", ondelete="RESTRICT")
    )
    lost_qr_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("qr_codes.id", ondelete="RESTRICT")
    )
    ice_qr_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("qr_codes.id", ondelete="RESTRICT")
    )
    scan_context_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("scan_contexts.id", ondelete="RESTRICT")
    )
    method: Mapped[str] = mapped_column(String(24))
    order_pair_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("order_pair_units.id", ondelete="RESTRICT")
    )
    verifier_key_version: Mapped[int | None] = mapped_column(SmallInteger)
    state: Mapped[str] = mapped_column(String(16), server_default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint(
            "method IN ('order_entitlement','concealed_credential')", name="method"
        ),
        CheckConstraint(
            "(method='order_entitlement' AND order_pair_unit_id IS NOT NULL AND verifier_key_version IS NULL) OR (method='concealed_credential' AND order_pair_unit_id IS NULL AND verifier_key_version IS NOT NULL AND verifier_key_version>0)",
            name="entitlement",
        ),
        CheckConstraint(
            "state IN ('pending','consumed','expired','revoked')", name="state"
        ),
        CheckConstraint("lost_qr_id<>ice_qr_id", name="distinct_tags"),
        CheckConstraint("expires_at>created_at", name="expiry"),
        CheckConstraint(
            "state<>'consumed' OR consumed_at IS NOT NULL", name="consumption"
        ),
        Index("idx_activation_actor", "actor_user_id", "created_at"),
        Index(
            "idx_activation_expiry",
            "expires_at",
            postgresql_where=text("state='pending'"),
        ),
    )


class DurableJob(Identity, Created, EncryptedPayload, Lease, Base):
    __tablename__ = "durable_jobs"
    job_kind: Mapped[str] = mapped_column(String(40))
    aggregate_type: Mapped[str] = mapped_column(String(40))
    aggregate_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("orders.id", ondelete="RESTRICT")
    )
    print_job_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("print_jobs.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(16), server_default="pending")
    idempotency_key: Mapped[str] = mapped_column(String(160), unique=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint(
            "job_kind IN ('allocation.finalize','print.render','finance.sync','retention.cleanup')",
            name="kind",
        ),
        CheckConstraint(
            "status IN ('pending','leased','retry','completed','dead')", name="status"
        ),
        CheckConstraint("attempt_count>=0", name="attempts"),
        CheckConstraint(LEASE_CHECK, name="lease"),
        CheckConstraint(PAYLOAD_CHECK, name="payload_key"),
        CheckConstraint(
            "status<>'completed' OR completed_at IS NOT NULL", name="completion"
        ),
        CheckConstraint(
            "job_kind='retention.cleanup' OR order_id IS NOT NULL", name="order"
        ),
        CheckConstraint(
            "job_kind<>'print.render' OR print_job_id IS NOT NULL", name="print_job"
        ),
        Index(
            "idx_jobs_due",
            "next_attempt_at",
            "created_at",
            postgresql_where=text("status IN ('pending','retry')"),
        ),
        Index(
            "idx_jobs_lease", "lease_until", postgresql_where=text("status='leased'")
        ),
    )


class PrintJob(Identity, Timestamps, Base):
    __tablename__ = "print_jobs"
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("orders.id", ondelete="RESTRICT")
    )
    job_revision: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text, server_default="queued")
    template_fingerprint: Mapped[str] = mapped_column(Text)
    render_config: Mapped[dict] = mapped_column(JSONB)
    attempt_count: Mapped[int] = mapped_column(Integer, server_default="0")
    failure_code: Mapped[str | None] = mapped_column(String(80))
    __table_args__ = (
        UniqueConstraint("order_id", "job_revision"),
        CheckConstraint("job_revision>0 AND attempt_count>=0", name="versions"),
        CheckConstraint(
            "status IN ('queued','rendering','ready','downloaded','qa_passed','failed','superseded','deleted')",
            name="status",
        ),
        CheckConstraint("jsonb_typeof(render_config)='object'", name="config"),
        Index("idx_print_jobs_order", "order_id", "created_at"),
    )


class PrintArtifact(Identity, Created, Base):
    __tablename__ = "print_artifacts"
    print_job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("print_jobs.id", ondelete="RESTRICT")
    )
    bucket: Mapped[str] = mapped_column(Text, server_default="private-order-print")
    object_key: Mapped[str] = mapped_column(Text, unique=True)
    format: Mapped[str] = mapped_column(Text)
    sha256_hex: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    retention_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deletion_hold_reason: Mapped[str | None] = mapped_column(Text)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("bucket='private-order-print'", name="bucket"),
        CheckConstraint("format IN ('pdf','svg','other_approved')", name="format"),
        CheckConstraint(
            "sha256_hex ~ '^[0-9a-f]{64}$' AND size_bytes>0", name="integrity"
        ),
        Index(
            "idx_artifacts_cleanup",
            "retention_until",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


class FinanceSheetSync(Identity, Base):
    __tablename__ = "finance_sheet_sync"
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("orders.id", ondelete="RESTRICT"), unique=True
    )
    sheet_row_key: Mapped[str | None] = mapped_column(Text)
    last_export_version: Mapped[int] = mapped_column(Integer, server_default="0")
    status: Mapped[str] = mapped_column(Text, server_default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, server_default="0")
    last_error_code: Mapped[str | None] = mapped_column(String(80))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','synced','retry','failed')", name="status"
        ),
        CheckConstraint("last_export_version>=0 AND attempt_count>=0", name="versions"),
    )


class RetentionHold(Identity, Created, Base):
    __tablename__ = "retention_holds"
    resource_type: Mapped[str] = mapped_column(String(40))
    resource_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    reason_code: Mapped[str] = mapped_column(String(80))
    placed_by: Mapped[uuid.UUID] = mapped_column(Uuid, auth_fk())
    released_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, auth_fk())
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint(
            "resource_type IN ('order','finder_message','print_artifact','payment_evidence')",
            name="resource",
        ),
        CheckConstraint("reason_code ~ '^[a-zA-Z0-9_.-]+$'", name="reason"),
        CheckConstraint(
            "(released_at IS NULL AND released_by IS NULL) OR (released_at IS NOT NULL AND released_by IS NOT NULL)",
            name="release",
        ),
        Index(
            "idx_retention_active",
            "resource_type",
            "resource_id",
            postgresql_where=text("released_at IS NULL"),
        ),
    )


class SupportCase(Identity, Created, Base):
    __tablename__ = "support_cases"
    pair_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("tag_pairs.id", ondelete="RESTRICT")
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("orders.id", ondelete="RESTRICT")
    )
    opened_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, auth_fk())
    case_type: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), server_default="open")
    assigned_staff_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, auth_fk())
    description_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    description_key_version: Mapped[int | None] = mapped_column(SmallInteger)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint(
            "case_type IN ('activation','lost_tag','payment','privacy','ownership_dispute','other')",
            name="type",
        ),
        CheckConstraint(
            "status IN ('open','investigating','resolved','closed')", name="status"
        ),
        CheckConstraint(
            "(description_ciphertext IS NULL AND description_key_version IS NULL) OR (description_ciphertext IS NOT NULL AND description_key_version IS NOT NULL AND description_key_version>0)",
            name="description_key",
        ),
    )
