"""Catalog, immutable purchase records, settlement and fulfillment mappings."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
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

from app.db.models import Base, Identity, Timestamps, auth_fk


class Created:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class ProductCategory(Identity, Base):
    __tablename__ = "product_categories"
    slug: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")


class Product(Identity, Timestamps, Base):
    __tablename__ = "products"
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("product_categories.id", ondelete="RESTRICT")
    )
    slug: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    lifecycle_status: Mapped[str] = mapped_column(Text, server_default="draft")
    # NULL is retained only for legacy products awaiting an explicit admin price.
    price_per_copy: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    max_order_copies: Mapped[int] = mapped_column(Integer, server_default="100")
    # Required for new-model publication in Phase 3; legacy products are not inferred.
    qr_type: Mapped[str | None] = mapped_column(String(8))
    commerce_model: Mapped[str] = mapped_column(String(16), server_default="legacy_pair")
    is_featured: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    featured_sort_order: Mapped[int] = mapped_column(Integer, server_default="0")
    allows_new_pair: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    allows_existing_qr: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false")
    )
    __table_args__ = (
        CheckConstraint("price_per_copy BETWEEN 0 AND 9999999999.99", name="price_per_copy"),
        CheckConstraint("max_order_copies BETWEEN 1 AND 100", name="max_order_copies"),
        CheckConstraint("qr_type IN ('lost','ice')", name="qr_type"),
        CheckConstraint("commerce_model IN ('legacy_pair','single_qr') AND (commerce_model<>'single_qr' OR qr_type IS NOT NULL)", name="commerce_model"),
        CheckConstraint(
            "lifecycle_status IN ('draft','published','archived')", name="lifecycle"
        ),
        Index(
            "idx_products_featured",
            "featured_sort_order",
            "id",
            postgresql_where=text("lifecycle_status='published' AND is_featured"),
        ),
    )


class ProductVariant(Identity, Timestamps, Base):
    __tablename__ = "product_variants"
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="RESTRICT")
    )
    sku: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    size_mm: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    material: Mapped[str | None] = mapped_column(Text)
    color: Mapped[str | None] = mapped_column(Text)
    currency_code: Mapped[str] = mapped_column(String(3), server_default="PKR")
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    fulfillment_method: Mapped[str] = mapped_column(Text)
    template_key: Mapped[str | None] = mapped_column(Text)
    template_version: Mapped[int] = mapped_column(Integer, server_default="1")
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")
    __table_args__ = (
        CheckConstraint("size_mm > 0", name="size"),
        CheckConstraint("unit_price >= 0", name="price"),
        CheckConstraint("currency_code ~ '^[A-Z]{3}$'", name="currency"),
        CheckConstraint(
            "fulfillment_method IN ('pdf_label','manufacturer_artwork','manual')",
            name="method",
        ),
        CheckConstraint("template_version > 0", name="template_version"),
        Index(
            "idx_product_variants_live",
            "product_id",
            "sort_order",
            postgresql_where=text("is_active"),
        ),
    )


class ProductImage(Identity, Created, Base):
    __tablename__ = "product_images"
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="RESTRICT")
    )
    cloudinary_public_id: Mapped[str] = mapped_column(Text)
    alt_text: Mapped[str] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")
    is_primary: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    __table_args__ = (UniqueConstraint("product_id", "cloudinary_public_id"),)


class Order(Identity, Timestamps, Base):
    __tablename__ = "orders"
    commerce_model: Mapped[str] = mapped_column(String(16), server_default="legacy_pair")
    payment_instructions_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    revision: Mapped[int] = mapped_column(Integer, server_default="1")
    order_number: Mapped[str] = mapped_column(String(40), unique=True)
    customer_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, auth_fk())
    order_status: Mapped[str] = mapped_column(String(24), server_default="draft")
    payment_status: Mapped[str] = mapped_column(
        String(24), server_default="awaiting_transfer"
    )
    fulfillment_status: Mapped[str] = mapped_column(
        String(24), server_default="unallocated"
    )
    currency_code: Mapped[str] = mapped_column(String(3), server_default="PKR")
    subtotal_pkr: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    shipping_pkr: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    tax_pkr: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    discount_pkr: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    total_pkr: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    placed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("commerce_model IN ('legacy_pair','single_qr')", name="commerce_model"),
        CheckConstraint("revision > 0", name="revision"),
        CheckConstraint(
            "order_status IN ('draft','placed','processing','fulfilled','cancelled')",
            name="status",
        ),
        CheckConstraint(
            "payment_status IN ('awaiting_transfer','proof_submitted','under_review','verified','rejected','refunded')",
            name="payment",
        ),
        CheckConstraint(
            "fulfillment_status IN ('unallocated','allocated','packed','dispatched','delivered','exception')",
            name="fulfillment",
        ),
        CheckConstraint("currency_code ~ '^[A-Z]{3}$'", name="currency"),
        CheckConstraint(
            "subtotal_pkr >= 0 AND shipping_pkr >= 0 AND tax_pkr >= 0 AND discount_pkr >= 0 AND total_pkr >= 0",
            name="amounts",
        ),
        CheckConstraint(
            "total_pkr = subtotal_pkr + shipping_pkr + tax_pkr - discount_pkr",
            name="total",
        ),
        CheckConstraint(
            "order_status IN ('draft','cancelled') OR placed_at IS NOT NULL",
            name="placement",
        ),
        CheckConstraint(
            "placed_at IS NULL OR order_status <> 'draft'", name="no_unplace"
        ),
        Index("idx_orders_customer", "customer_user_id", "created_at"),
    )


class OrderLogicalItem(Identity, Created, Base):
    __tablename__ = "order_logical_items"
    order_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("orders.id", ondelete="RESTRICT"))
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("products.id", ondelete="RESTRICT"))
    identity_group: Mapped[str | None] = mapped_column(String(80))
    product_name_snapshot: Mapped[str] = mapped_column(Text)
    qr_type_snapshot: Mapped[str] = mapped_column(String(8))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    max_copies_snapshot: Mapped[int] = mapped_column(Integer)
    product_version_snapshot: Mapped[int] = mapped_column(Integer)
    currency_code: Mapped[str] = mapped_column(String(3), server_default="PKR")
    __table_args__ = (
        CheckConstraint("qr_type_snapshot IN ('lost','ice')", name="type"),
        CheckConstraint("quantity BETWEEN 1 AND max_copies_snapshot AND max_copies_snapshot BETWEEN 1 AND 100", name="copies"),
        CheckConstraint("unit_price_snapshot>=0 AND line_total=quantity*unit_price_snapshot AND currency_code='PKR' AND product_version_snapshot>0", name="pricing"),
        Index("uq_logical_item_identity", "order_id", "product_id", text("coalesce(identity_group,'')"), unique=True),
        CheckConstraint("identity_group IS NULL OR identity_group ~ '^[A-Za-z0-9_-]{1,80}$'", name="group"),
    )


class OrderItemSize(Identity, Created, Base):
    __tablename__ = "order_item_sizes"
    logical_item_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("order_logical_items.id", ondelete="RESTRICT"))
    variant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("product_variants.id", ondelete="RESTRICT"))
    variant_name_snapshot: Mapped[str] = mapped_column(Text)
    sku_snapshot: Mapped[str] = mapped_column(Text)
    size_mm_snapshot: Mapped[Decimal] = mapped_column(Numeric(7, 2))
    material_snapshot: Mapped[str | None] = mapped_column(Text)
    copies: Mapped[int] = mapped_column(Integer)
    variant_version_snapshot: Mapped[int] = mapped_column(Integer)
    print_spec_snapshot: Mapped[dict] = mapped_column(JSONB)
    # Registry tables are SQL-managed; migration 0040 adds their RESTRICT FKs.
    revision_id: Mapped[uuid.UUID] = mapped_column(Uuid, Computed("(print_spec_snapshot->>'revision_id')::uuid", persisted=True))
    approval_id: Mapped[uuid.UUID] = mapped_column(Uuid, Computed("(print_spec_snapshot->>'approval_id')::uuid", persisted=True))
    __table_args__ = (
        UniqueConstraint("logical_item_id", "variant_id"),
        UniqueConstraint("logical_item_id", "size_mm_snapshot"),
        CheckConstraint("copies BETWEEN 1 AND 100 AND size_mm_snapshot BETWEEN 30 AND 100 AND variant_version_snapshot>0", name="shape"),
    )


class TypedOrderSettlement(Base):
    __tablename__ = "typed_order_settlements"
    order_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("orders.id", ondelete="RESTRICT"), primary_key=True)
    attempt_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("payment_attempts.id", ondelete="RESTRICT"), unique=True)
    state: Mapped[str] = mapped_column(Text)
    reason_code: Mapped[str | None] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(Integer, server_default="1")
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("clock_timestamp()"))
    allocated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("state IN ('reconciliation_pending','allocated')", name="state"),
        CheckConstraint("reason_code IN ('stock_shortage','financial_review','cancellation_review','template_review')", name="reason"),
        CheckConstraint("revision>0", name="revision"),
        CheckConstraint("(state='allocated' AND allocated_at IS NOT NULL AND reason_code IS NULL) OR (state='reconciliation_pending' AND allocated_at IS NULL AND reason_code IS NOT NULL)", name="allocation"),
    )


class OrderItemQRAllocation(Base):
    __tablename__ = "order_item_qr_allocations"
    logical_item_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("order_logical_items.id", ondelete="RESTRICT"), primary_key=True)
    qr_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("qr_codes.id", ondelete="RESTRICT"), unique=True)
    order_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("typed_order_settlements.order_id", ondelete="RESTRICT"))
    purchaser_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, auth_fk())
    allocated_by: Mapped[uuid.UUID] = mapped_column(Uuid, auth_fk())
    allocated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("clock_timestamp()"))
    __table_args__ = (Index("ix_typed_allocations_order", "order_id", "logical_item_id"),)


class TypedAllocationEvent(Identity, Created, Base):
    __tablename__ = "typed_allocation_events"
    order_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("typed_order_settlements.order_id", ondelete="RESTRICT"))
    settlement_revision: Mapped[int] = mapped_column(Integer)
    event_kind: Mapped[str] = mapped_column(Text)
    __table_args__ = (
        UniqueConstraint("order_id", "settlement_revision"),
        CheckConstraint("settlement_revision>0", name="revision"),
        CheckConstraint("event_kind IN ('allocation.ready','allocation.reconciliation')", name="kind"),
    )


class OrderItem(Identity, Created, Base):
    __tablename__ = "order_items"
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("orders.id", ondelete="RESTRICT")
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="RESTRICT")
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("product_variants.id", ondelete="RESTRICT")
    )
    product_name_snapshot: Mapped[str] = mapped_column(Text)
    variant_name_snapshot: Mapped[str] = mapped_column(Text)
    sku_snapshot: Mapped[str] = mapped_column(Text)
    size_mm_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    material_snapshot: Mapped[str | None] = mapped_column(Text)
    fulfillment_method_snapshot: Mapped[str] = mapped_column(Text)
    template_key_snapshot: Mapped[str | None] = mapped_column(Text)
    template_version_snapshot: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tax_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    discount_snapshot: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), server_default="0"
    )
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency_code: Mapped[str] = mapped_column(String(3), server_default="PKR")
    __table_args__ = (
        CheckConstraint(
            "quantity > 0 AND template_version_snapshot > 0", name="quantities"
        ),
        CheckConstraint("size_mm_snapshot > 0", name="size"),
        CheckConstraint(
            "unit_price_snapshot >= 0 AND tax_snapshot >= 0 AND discount_snapshot >= 0 AND line_total >= 0",
            name="amounts",
        ),
        CheckConstraint(
            "line_total = quantity * unit_price_snapshot + tax_snapshot - discount_snapshot",
            name="line_total",
        ),
        CheckConstraint(
            "fulfillment_method_snapshot IN ('pdf_label','manufacturer_artwork','manual')",
            name="method",
        ),
        CheckConstraint("currency_code ~ '^[A-Z]{3}$'", name="currency"),
        Index("idx_order_items_order", "order_id", "id"),
    )


class OrderPairUnit(Identity, Created, Base):
    __tablename__ = "order_pair_units"
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("orders.id", ondelete="RESTRICT")
    )
    pair_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tag_pairs.id", ondelete="RESTRICT")
    )
    kind: Mapped[str] = mapped_column(Text, server_default="new_pair")
    status: Mapped[str] = mapped_column(Text, server_default="reserved")
    reserved_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    allocated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    allocated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, auth_fk())
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("kind = 'new_pair'", name="kind"),
        CheckConstraint(
            "status IN ('reserved','allocated','released','cancelled')", name="status"
        ),
        CheckConstraint(
            "status <> 'reserved' OR reserved_until IS NOT NULL", name="reservation"
        ),
        CheckConstraint(
            "status <> 'allocated' OR allocated_at IS NOT NULL", name="allocation"
        ),
        CheckConstraint(
            "status NOT IN ('released','cancelled') OR released_at IS NOT NULL",
            name="release",
        ),
        Index(
            "uq_pair_one_live_claim",
            "pair_id",
            unique=True,
            postgresql_where=text("status IN ('reserved','allocated')"),
        ),
        Index("idx_pair_units_order", "order_id"),
        Index(
            "idx_pair_units_expiry",
            "reserved_until",
            postgresql_where=text("status='reserved'"),
        ),
    )


class OrderItemQRUse(Identity, Created, Base):
    __tablename__ = "order_item_qr_uses"
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("order_items.id", ondelete="RESTRICT")
    )
    qr_code_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("qr_codes.id", ondelete="RESTRICT")
    )
    pair_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("order_pair_units.id", ondelete="RESTRICT")
    )
    use_kind: Mapped[str] = mapped_column(Text)
    tag_type_snapshot: Mapped[str] = mapped_column(Text)
    copies: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        CheckConstraint("use_kind IN ('new_pair','existing_owned')", name="kind"),
        CheckConstraint("tag_type_snapshot IN ('lost','ice')", name="type"),
        CheckConstraint("copies > 0", name="copies"),
        CheckConstraint(
            "(use_kind='new_pair' AND pair_unit_id IS NOT NULL) OR (use_kind='existing_owned' AND pair_unit_id IS NULL)",
            name="pair_unit",
        ),
        UniqueConstraint("order_item_id", "qr_code_id", "use_kind"),
        Index("idx_order_qr_uses_qr", "qr_code_id"),
        Index("idx_order_qr_uses_unit", "pair_unit_id"),
    )


class PaymentAttempt(Identity, Timestamps, Base):
    __tablename__ = "payment_attempts"
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("orders.id", ondelete="RESTRICT")
    )
    provider_key: Mapped[str] = mapped_column(Text)
    provider_external_id: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency_code: Mapped[str] = mapped_column(String(3), server_default="PKR")
    state: Mapped[str] = mapped_column(Text, server_default="initiated")
    sender_reference_masked: Mapped[str | None] = mapped_column(Text)
    sender_holder_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    sender_account_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    sender_key_version: Mapped[int | None] = mapped_column(SmallInteger)
    provider_payload_ref: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, auth_fk())
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint(
            "state IN ('initiated','submitted','under_review','verified','rejected','expired','refunded','disputed')",
            name="state",
        ),
        CheckConstraint("amount >= 0", name="amount"),
        CheckConstraint("currency_code ~ '^[A-Z]{3}$'", name="currency"),
        CheckConstraint(
            "state <> 'verified' OR verified_at IS NOT NULL", name="verification"
        ),
        CheckConstraint(
            "(sender_holder_ciphertext IS NULL AND sender_account_ciphertext IS NULL AND sender_key_version IS NULL) OR ((sender_holder_ciphertext IS NOT NULL OR sender_account_ciphertext IS NOT NULL) AND sender_key_version IS NOT NULL AND sender_key_version > 0)",
            name="sender_key",
        ),
        UniqueConstraint("provider_key", "idempotency_key"),
        Index(
            "uq_payment_provider_external",
            "provider_key",
            "provider_external_id",
            unique=True,
            postgresql_where=text("provider_external_id IS NOT NULL"),
        ),
        Index("idx_payments_order", "order_id", "created_at"),
    )


class PaymentEvidence(Identity, Created, Base):
    __tablename__ = "payment_evidence"
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("payment_attempts.id", ondelete="RESTRICT")
    )
    bucket: Mapped[str] = mapped_column(Text, server_default="private-payment-evidence")
    object_key: Mapped[str] = mapped_column(Text, unique=True)
    sha256_hex: Mapped[str] = mapped_column(String(64))
    content_type: Mapped[str] = mapped_column(Text)
    bytes_size: Mapped[int] = mapped_column(BigInteger)
    retention_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deletion_hold_reason: Mapped[str | None] = mapped_column(Text)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("bytes_size > 0", name="size"),
        CheckConstraint("sha256_hex ~ '^[0-9a-f]{64}$'", name="hash"),
        CheckConstraint("bucket = 'private-payment-evidence'", name="private_bucket"),
        CheckConstraint(
            "content_type IN ('image/jpeg','image/png','application/pdf')",
            name="content_type",
        ),
        Index("idx_evidence_attempt", "attempt_id"),
    )


class PaymentReview(Identity, Base):
    __tablename__ = "payment_reviews"
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("payment_attempts.id", ondelete="RESTRICT")
    )
    reviewed_by: Mapped[uuid.UUID] = mapped_column(Uuid, auth_fk())
    decision: Mapped[str] = mapped_column(String(24))
    bank_verified: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    bank_reference_fingerprint: Mapped[bytes | None] = mapped_column(LargeBinary)
    bank_reference_key_version: Mapped[int | None] = mapped_column(SmallInteger)
    reason: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    __table_args__ = (
        CheckConstraint(
            "decision IN ('verify','reject','request_more_info')", name="decision"
        ),
        CheckConstraint(
            "decision <> 'verify' OR (bank_verified AND bank_reference_fingerprint IS NOT NULL AND bank_reference_key_version IS NOT NULL AND bank_reference_key_version > 0)",
            name="bank_confirmation",
        ),
        Index(
            "uq_review_settlement",
            "bank_reference_fingerprint",
            unique=True,
            postgresql_where=text("decision='verify'"),
        ),
        Index("idx_review_attempt", "attempt_id"),
    )


class AddressFields:
    recipient_name_ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    phone_ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    address_ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    city: Mapped[str] = mapped_column(String(100))
    province: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    key_version: Mapped[int] = mapped_column(SmallInteger)


class ShippingAddress(Identity, Created, AddressFields, Base):
    __tablename__ = "shipping_addresses"
    customer_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, auth_fk())
    is_saved: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    __table_args__ = (
        CheckConstraint(
            "key_version > 0 AND octet_length(recipient_name_ciphertext) > 0 AND octet_length(phone_ciphertext) > 0 AND octet_length(address_ciphertext) > 0",
            name="encryption",
        ),
        Index("idx_addresses_customer", "customer_user_id"),
        UniqueConstraint("customer_user_id", "id", name="uq_shipping_address_owner"),
        CheckConstraint("version > 0", name="version"),
    )


class ShippingAddressBook(Base):
    __tablename__ = "shipping_address_books"
    customer_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, auth_fk(), primary_key=True
    )
    version: Mapped[int] = mapped_column(Integer)
    default_address_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    __table_args__ = (
        ForeignKeyConstraint(
            ["customer_user_id", "default_address_id"],
            ["shipping_addresses.customer_user_id", "shipping_addresses.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("version > 0", name="version"),
    )


class OrderShippingSnapshot(Created, AddressFields, Base):
    __tablename__ = "order_shipping_snapshots"
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("orders.id", ondelete="RESTRICT"), primary_key=True
    )
    source_address_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("shipping_addresses.id", ondelete="RESTRICT")
    )
    __table_args__ = (
        CheckConstraint(
            "key_version > 0 AND octet_length(recipient_name_ciphertext) > 0 AND octet_length(phone_ciphertext) > 0 AND octet_length(address_ciphertext) > 0",
            name="encryption",
        ),
    )


class Shipment(Identity, Created, Base):
    __tablename__ = "shipments"
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("orders.id", ondelete="RESTRICT")
    )
    shipping_address_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("shipping_addresses.id", ondelete="RESTRICT")
    )
    carrier: Mapped[str | None] = mapped_column(String(80))
    tracking_reference: Mapped[str | None] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(24), server_default="preparing")
    packed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint(
            "status IN ('preparing','packed','dispatched','delivered','exception','returned')",
            name="status",
        ),
        CheckConstraint("status <> 'packed' OR packed_at IS NOT NULL", name="packed"),
        CheckConstraint(
            "status <> 'dispatched' OR dispatched_at IS NOT NULL", name="dispatch"
        ),
        CheckConstraint(
            "status <> 'delivered' OR delivered_at IS NOT NULL", name="delivery"
        ),
        Index("idx_shipments_order", "order_id"),
    )


class ShipmentPair(Base):
    __tablename__ = "shipment_pairs"
    shipment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("shipments.id", ondelete="RESTRICT"), primary_key=True
    )
    pair_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tag_pairs.id", ondelete="RESTRICT"),
        primary_key=True,
        unique=True,
    )
    packed_qa_confirmed: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false")
    )
    packed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, auth_fk())
    packed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint(
            "NOT packed_qa_confirmed OR (packed_by IS NOT NULL AND packed_at IS NOT NULL)",
            name="packing",
        ),
    )


class StandaloneOwnerRelease(Base):
    __tablename__ = "standalone_owner_release"
    singleton: Mapped[bool] = mapped_column(Boolean, primary_key=True, server_default=text("true"))
    enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    __table_args__ = (CheckConstraint("singleton", name="singleton"),)


class StandaloneActivationIntent(Identity, Base):
    __tablename__ = "standalone_activation_intents"
    logical_item_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("order_item_qr_allocations.logical_item_id", ondelete="RESTRICT"))
    actor_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, auth_fk())
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    state_revision: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("statement_timestamp()"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("statement_timestamp()+interval '5 minutes'"))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("state_revision>0", name="revision"), CheckConstraint("expires_at>created_at AND expires_at<=created_at+interval '5 minutes'", name="expiry"), Index("ix_standalone_intents_actor", "actor_user_id", "created_at"))


class StandaloneOwnerEvent(Identity, Created, Base):
    __tablename__ = "standalone_owner_events"
    qr_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("qr_codes.id", ondelete="RESTRICT"))
    actor_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, auth_fk())
    event_type: Mapped[str] = mapped_column(Text)
    state_revision: Mapped[int] = mapped_column(Integer)
    __table_args__ = (UniqueConstraint("qr_id", "state_revision"), CheckConstraint("state_revision>0", name="revision"), CheckConstraint("event_type IN ('activated','owner_disabled','owner_enabled')", name="event"), Index("uq_standalone_activation_once", "qr_id", unique=True, postgresql_where=text("event_type='activated'")))


class StandaloneOwnerReceipt(Created, Base):
    __tablename__ = "standalone_owner_receipts"
    actor_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, auth_fk(), primary_key=True)
    operation: Mapped[str] = mapped_column(Text, primary_key=True)
    key_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    request_hash: Mapped[str] = mapped_column(Text)
    result: Mapped[dict] = mapped_column(JSONB)
    __table_args__ = (CheckConstraint("key_hash ~ '^[0-9a-f]{64}$' AND request_hash ~ '^[0-9a-f]{64}$'", name="hashes"), CheckConstraint("jsonb_typeof(result)='object'", name="result"))


class ShipmentItem(Base):
    __tablename__ = "shipment_items"
    shipment_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("shipments.id", ondelete="RESTRICT"), primary_key=True)
    logical_item_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("order_item_qr_allocations.logical_item_id", ondelete="RESTRICT"), primary_key=True, unique=True)
    print_job_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("print_jobs.id", ondelete="RESTRICT"))
    packed_qa_confirmed: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    packed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, auth_fk())
    packed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("NOT packed_qa_confirmed OR (packed_by IS NOT NULL AND packed_at IS NOT NULL)", name="packing"),)


class TypedPrintHandoff(Base):
    __tablename__ = "typed_print_handoffs"
    event_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("typed_allocation_events.id", ondelete="RESTRICT"), primary_key=True)
    durable_job_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("durable_jobs.id", ondelete="RESTRICT"), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("clock_timestamp()"))


class PairPrintQA(Identity, Base):
    __tablename__ = "pair_print_qa"
    pair_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tag_pairs.id", ondelete="RESTRICT")
    )
    qa_round: Mapped[int] = mapped_column(Integer)
    lost_scan_passed: Mapped[bool] = mapped_column(Boolean)
    ice_scan_passed: Mapped[bool] = mapped_column(Boolean)
    pair_match_passed: Mapped[bool] = mapped_column(Boolean)
    credential_concealed: Mapped[bool] = mapped_column(Boolean)
    bilingual_label_passed: Mapped[bool] = mapped_column(Boolean)
    quiet_zone_passed: Mapped[bool] = mapped_column(Boolean)
    indoor_size_passed: Mapped[bool] = mapped_column(Boolean)
    outdoor_size_passed: Mapped[bool] = mapped_column(Boolean)
    packaging_method: Mapped[str] = mapped_column(String(30))
    tamper_evidence_passed: Mapped[bool] = mapped_column(Boolean)
    approved: Mapped[bool] = mapped_column(Boolean)
    inspected_by: Mapped[uuid.UUID] = mapped_column(Uuid, auth_fk())
    inspected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    notes: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        UniqueConstraint("pair_id", "qa_round"),
        CheckConstraint("qa_round > 0", name="round"),
        CheckConstraint(
            "packaging_method IN ('scratch_off','sealed_sleeve','peel_seal')",
            name="packaging",
        ),
        CheckConstraint(
            "NOT approved OR (lost_scan_passed AND ice_scan_passed AND pair_match_passed AND credential_concealed AND bilingual_label_passed AND quiet_zone_passed AND indoor_size_passed AND outdoor_size_passed AND tamper_evidence_passed)",
            name="approval",
        ),
    )
