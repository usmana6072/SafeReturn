"""Initial domain mappings. Auth users are managed exclusively by Supabase."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    Table,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "pk": "pk_%(table_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
        }
    )


# Resolution stub only; excluded from every migration/autogenerate operation.
Table("users", Base.metadata, Column("id", Uuid, primary_key=True), schema="auth")


def auth_fk(delete="RESTRICT"):
    return ForeignKey("auth.users.id", ondelete=delete)


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class Identity:
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )


class UserProfile(Timestamps, Base):
    __tablename__ = "user_profiles"
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, auth_fk("CASCADE"), primary_key=True
    )
    display_name: Mapped[str | None] = mapped_column(String(120))
    preferred_locale: Mapped[str] = mapped_column(String(5), server_default="en")
    phone_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    phone_key_version: Mapped[int | None] = mapped_column(SmallInteger)
    __table_args__ = (
        CheckConstraint("preferred_locale IN ('en','ur')", name="locale"),
        CheckConstraint(
            "(phone_ciphertext IS NULL AND phone_key_version IS NULL) OR (phone_ciphertext IS NOT NULL AND phone_key_version > 0 AND phone_key_version IS NOT NULL)",
            name="phone_key",
        ),
    )


class StaffRole(Identity, Base):
    __tablename__ = "staff_roles"
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, auth_fk())
    role: Mapped[str] = mapped_column(String(40))
    granted_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, auth_fk())
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        CheckConstraint(
            "role IN ('support','operations','finance','security_admin','superadmin')",
            name="role",
        ),
        Index(
            "uq_staff_active_role",
            "user_id",
            "role",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )


class QRBatch(Identity, Timestamps, Base):
    __tablename__ = "qr_batches"
    batch_code: Mapped[str] = mapped_column(String(40), unique=True)
    supplier_name: Mapped[str | None] = mapped_column(String(120))
    print_material: Mapped[str | None] = mapped_column(String(60))
    ecc_level: Mapped[str] = mapped_column(String(1))
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    printed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    qa_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    qa_approved_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, auth_fk())
    print_manifest_checksum: Mapped[str | None] = mapped_column(String(64))
    logo_template_key: Mapped[str | None] = mapped_column(String(80))
    intended_environment: Mapped[str | None] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(24), server_default="draft")
    generation_mode: Mapped[str] = mapped_column(
        String(16), server_default="legacy_pair"
    )
    qr_type: Mapped[str | None] = mapped_column(String(8))
    requested_quantity: Mapped[int | None] = mapped_column(Integer)
    __table_args__ = (
        CheckConstraint(
            "(generation_mode='legacy_pair' AND qr_type IS NULL AND requested_quantity IS NULL) OR "
            "(generation_mode='standalone' AND qr_type IS NOT NULL AND qr_type IN ('lost','ice') "
            "AND requested_quantity IS NOT NULL AND requested_quantity BETWEEN 1 AND 1000)",
            name="generation_shape",
        ),
        CheckConstraint("ecc_level IN ('M','Q')", name="ecc"),
        CheckConstraint(
            "status IN ('draft','generated','printed','qa_passed','rejected','closed')",
            name="status",
        ),
    )


class TagPair(Identity, Timestamps, Base):
    __tablename__ = "tag_pairs"
    pair_reference: Mapped[str] = mapped_column(String(40), unique=True)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("qr_batches.id", ondelete="RESTRICT")
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, auth_fk())
    inventory_status: Mapped[str] = mapped_column(
        String(24), server_default="generated"
    )
    ownership_status: Mapped[str] = mapped_column(
        String(24), server_default="unclaimed"
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    row_version: Mapped[int] = mapped_column(Integer, server_default="1")
    __table_args__ = (
        CheckConstraint(
            "inventory_status IN ('generated','printed','qa_passed','reserved','packed','shipped','delivered','rejected')",
            name="inventory",
        ),
        CheckConstraint(
            "ownership_status IN ('unclaimed','active','transfer_pending','disputed','revoked')",
            name="ownership",
        ),
        CheckConstraint(
            "ownership_status <> 'active' OR (owner_user_id IS NOT NULL AND activated_at IS NOT NULL)",
            name="active_owner",
        ),
        CheckConstraint(
            "ownership_status <> 'unclaimed' OR activated_at IS NULL", name="unclaimed"
        ),
        CheckConstraint(
            "revoked_at IS NULL OR ownership_status = 'revoked'", name="revocation"
        ),
        CheckConstraint("row_version > 0", name="version"),
        Index("ix_pair_owner", "owner_user_id", "ownership_status"),
        Index("ix_pair_batch", "batch_id", "inventory_status"),
    )


class QRCode(Identity, Timestamps, Base):
    __tablename__ = "qr_codes"
    pair_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("tag_pairs.id", ondelete="RESTRICT")
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("qr_batches.id", ondelete="RESTRICT")
    )
    tag_type: Mapped[str] = mapped_column(String(8))
    serial_number: Mapped[str] = mapped_column(String(50), unique=True)
    public_token: Mapped[str] = mapped_column(String(80), unique=True)
    public_status: Mapped[str] = mapped_column(String(24), server_default="unactivated")
    is_current: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    replaces_qr_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("qr_codes.id", ondelete="RESTRICT")
    )
    ecc_level: Mapped[str] = mapped_column(String(1))
    qr_version: Mapped[int | None] = mapped_column(SmallInteger)
    printed_size_mm: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint(
            "(pair_id IS NOT NULL AND batch_id IS NULL) OR "
            "(pair_id IS NULL AND batch_id IS NOT NULL)",
            name="identity_shape",
        ),
        CheckConstraint(
            "pair_id IS NOT NULL OR (replaces_qr_id IS NULL AND is_current)",
            name="standalone_no_replacement",
        ),
        CheckConstraint("tag_type IN ('lost','ice')", name="type"),
        CheckConstraint(
            "public_status IN ('unactivated','active','owner_disabled','admin_suspended','revoked')",
            name="status",
        ),
        CheckConstraint("ecc_level IN ('M','Q')", name="ecc"),
        CheckConstraint(
            "public_status <> 'revoked' OR revoked_at IS NOT NULL", name="revocation"
        ),
        CheckConstraint("replaces_qr_id <> id", name="replacement_self"),
        CheckConstraint("qr_version BETWEEN 1 AND 40", name="qr_version"),
        CheckConstraint("printed_size_mm > 0", name="size"),
        Index(
            "uq_current_pair_tag_type",
            "pair_id",
            "tag_type",
            unique=True,
            postgresql_where=text("is_current"),
        ),
        Index(
            "uq_qr_replacement",
            "replaces_qr_id",
            unique=True,
            postgresql_where=text("replaces_qr_id IS NOT NULL"),
        ),
        Index(
            "ix_standalone_qr_batch_type",
            "batch_id",
            "tag_type",
            "id",
            postgresql_where=text("pair_id IS NULL"),
        ),
    )


class StandaloneQRState(Timestamps, Base):
    """Independent lifecycle; runtime access is closed during Phase 1."""

    __tablename__ = "standalone_qr_states"
    qr_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("qr_codes.id", ondelete="RESTRICT"), primary_key=True
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, auth_fk())
    inventory_status: Mapped[str] = mapped_column(
        String(16), server_default="available"
    )
    ownership_status: Mapped[str] = mapped_column(
        String(16), server_default="unclaimed"
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    row_version: Mapped[int] = mapped_column(Integer, server_default="1")
    __table_args__ = (
        CheckConstraint(
            "inventory_status IN ('available','allocated','retired')", name="inventory"
        ),
        CheckConstraint(
            "ownership_status IN ('unclaimed','active','revoked')", name="ownership"
        ),
        CheckConstraint(
            "ownership_status <> 'unclaimed' OR (owner_user_id IS NULL AND activated_at IS NULL)",
            name="unclaimed",
        ),
        CheckConstraint(
            "ownership_status <> 'active' OR (owner_user_id IS NOT NULL AND activated_at IS NOT NULL "
            "AND inventory_status='allocated')",
            name="active_owner",
        ),
        CheckConstraint(
            "(ownership_status='revoked') = (revoked_at IS NOT NULL)", name="revocation"
        ),
        CheckConstraint("row_version > 0", name="version"),
        Index("ix_standalone_owner", "owner_user_id", "ownership_status"),
        Index("ix_standalone_inventory", "inventory_status", "qr_id"),
    )


class PairActivationCredential(Timestamps, Base):
    __tablename__ = "pair_activation_credentials"
    pair_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tag_pairs.id", ondelete="RESTRICT"), primary_key=True
    )
    secret_verifier: Mapped[bytes] = mapped_column(LargeBinary)
    verifier_key_version: Mapped[int] = mapped_column(SmallInteger)
    status: Mapped[str] = mapped_column(String(20), server_default="unused")
    failed_attempts: Mapped[int] = mapped_column(Integer, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint(
            "status IN ('unused','locked','consumed','revoked')", name="status"
        ),
        CheckConstraint(
            "verifier_key_version > 0 AND octet_length(secret_verifier) > 0",
            name="verifier",
        ),
        CheckConstraint("failed_attempts >= 0", name="attempts"),
        CheckConstraint(
            "status <> 'consumed' OR consumed_at IS NOT NULL", name="consumed"
        ),
    )


class Profile:
    qr_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("qr_codes.id", ondelete="RESTRICT"), primary_key=True
    )
    profile_version: Mapped[int] = mapped_column(Integer, server_default="1")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    published: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))


class LostItemProfile(Profile, Base):
    __tablename__ = "lost_item_profiles"
    item_label: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    reward_text: Mapped[str | None] = mapped_column(String(200))
    return_instructions: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("profile_version > 0", name="version"),)


class ICEProfile(Profile, Base):
    __tablename__ = "ice_profiles"
    display_name: Mapped[str | None] = mapped_column(String(120))
    blood_group: Mapped[str | None] = mapped_column(String(8))
    emergency_instructions: Mapped[str | None] = mapped_column(Text)
    medical_notes_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    medical_notes_key_version: Mapped[int | None] = mapped_column(SmallInteger)
    show_medical_notes: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false")
    )
    publication_consent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    publication_consent_version: Mapped[str | None] = mapped_column(String(30))
    __table_args__ = (
        CheckConstraint("profile_version > 0", name="version"),
        CheckConstraint(
            "blood_group IN ('A+','A-','B+','B-','AB+','AB-','O+','O-')",
            name="blood_group",
        ),
        CheckConstraint(
            "(medical_notes_ciphertext IS NULL AND medical_notes_key_version IS NULL) OR (medical_notes_ciphertext IS NOT NULL AND medical_notes_key_version IS NOT NULL AND medical_notes_key_version > 0)",
            name="medical_key",
        ),
        CheckConstraint(
            "NOT published OR (publication_consent_at IS NOT NULL AND publication_consent_version IS NOT NULL)",
            name="consent",
        ),
        CheckConstraint(
            "NOT show_medical_notes OR (medical_notes_ciphertext IS NOT NULL AND publication_consent_at IS NOT NULL AND publication_consent_version IS NOT NULL)",
            name="medical_consent",
        ),
    )


class ICEContact(Identity, Timestamps, Base):
    __tablename__ = "ice_contacts"
    ice_qr_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("ice_profiles.qr_id", ondelete="RESTRICT")
    )
    relationship_label: Mapped[str] = mapped_column(String(60))
    display_name: Mapped[str | None] = mapped_column(String(120))
    phone_ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    phone_key_version: Mapped[int] = mapped_column(SmallInteger)
    display_order: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    published: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    publication_consent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    publication_consent_version: Mapped[str | None] = mapped_column(String(30))
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint(
            "phone_key_version > 0 AND octet_length(phone_ciphertext) > 0", name="phone"
        ),
        CheckConstraint("display_order >= 0", name="display_order"),
        CheckConstraint(
            "NOT published OR publication_consent_at IS NOT NULL", name="consent"
        ),
        CheckConstraint(
            "removed_at IS NULL OR NOT published", name="removed_unpublished"
        ),
        Index("ix_ice_contact_display", "ice_qr_id", "published", "display_order"),
    )


class TagContactPreference(Base):
    __tablename__ = "tag_contact_preferences"
    qr_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("qr_codes.id", ondelete="RESTRICT"), primary_key=True
    )
    whatsapp_enabled: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false")
    )
    whatsapp_phone_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    whatsapp_phone_key_version: Mapped[int | None] = mapped_column(SmallInteger)
    whatsapp_consent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    whatsapp_consent_version: Mapped[str | None] = mapped_column(String(30))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    profile_version: Mapped[int] = mapped_column(Integer, server_default="1")
    __table_args__ = (
        CheckConstraint("profile_version>0", name="version"),
        CheckConstraint(
            "NOT whatsapp_enabled OR (whatsapp_phone_ciphertext IS NOT NULL AND whatsapp_phone_key_version IS NOT NULL AND whatsapp_phone_key_version > 0 AND whatsapp_consent_at IS NOT NULL AND whatsapp_consent_version IS NOT NULL)",
            name="whatsapp_consent",
        ),
    )
