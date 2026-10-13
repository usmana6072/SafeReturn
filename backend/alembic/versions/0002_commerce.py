"""Add catalog, immutable purchases, reservations, payments and fulfillment.

Frozen PostgreSQL DDL; existing identity tables and managed Auth are untouched.
"""

from sqlalchemy import inspect

from alembic import op

revision = "0002_commerce"
down_revision = "0001_identity_profiles"
branch_labels = None
depends_on = None

TABLES = [
    "product_categories",
    "orders",
    "products",
    "shipping_addresses",
    "order_shipping_snapshots",
    "payment_attempts",
    "product_images",
    "product_variants",
    "shipments",
    "order_items",
    "order_pair_units",
    "pair_print_qa",
    "payment_evidence",
    "payment_reviews",
    "shipment_pairs",
    "order_item_qr_uses",
]
DDL = [
    """CREATE TABLE product_categories (
	slug TEXT NOT NULL,
	name TEXT NOT NULL,
	is_active BOOLEAN DEFAULT true NOT NULL,
	sort_order INTEGER DEFAULT '0' NOT NULL,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	CONSTRAINT pk_product_categories PRIMARY KEY (id),
	CONSTRAINT uq_product_categories_slug UNIQUE (slug)
)""",
    """ALTER TABLE public.product_categories ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.product_categories FROM PUBLIC, anon, authenticated""",
    """CREATE TABLE orders (
	order_number VARCHAR(40) NOT NULL,
	customer_user_id UUID NOT NULL,
	order_status VARCHAR(24) DEFAULT 'draft' NOT NULL,
	payment_status VARCHAR(24) DEFAULT 'awaiting_transfer' NOT NULL,
	fulfillment_status VARCHAR(24) DEFAULT 'unallocated' NOT NULL,
	currency_code VARCHAR(3) DEFAULT 'PKR' NOT NULL,
	subtotal_pkr NUMERIC(12, 2) NOT NULL,
	shipping_pkr NUMERIC(12, 2) DEFAULT '0' NOT NULL,
	tax_pkr NUMERIC(12, 2) DEFAULT '0' NOT NULL,
	discount_pkr NUMERIC(12, 2) DEFAULT '0' NOT NULL,
	total_pkr NUMERIC(12, 2) NOT NULL,
	placed_at TIMESTAMP WITH TIME ZONE,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_orders PRIMARY KEY (id),
	CONSTRAINT ck_orders_status CHECK (order_status IN ('draft','placed','processing','fulfilled','cancelled')),
	CONSTRAINT ck_orders_payment CHECK (payment_status IN ('awaiting_transfer','proof_submitted','under_review','verified','rejected','refunded')),
	CONSTRAINT ck_orders_fulfillment CHECK (fulfillment_status IN ('unallocated','allocated','packed','dispatched','delivered','exception')),
	CONSTRAINT ck_orders_currency CHECK (currency_code ~ '^[A-Z]{3}$'),
	CONSTRAINT ck_orders_amounts CHECK (subtotal_pkr >= 0 AND shipping_pkr >= 0 AND tax_pkr >= 0 AND discount_pkr >= 0 AND total_pkr >= 0),
	CONSTRAINT ck_orders_total CHECK (total_pkr = subtotal_pkr + shipping_pkr + tax_pkr - discount_pkr),
	CONSTRAINT ck_orders_placement CHECK (order_status IN ('draft','cancelled') OR placed_at IS NOT NULL),
	CONSTRAINT ck_orders_no_unplace CHECK (placed_at IS NULL OR order_status <> 'draft'),
	CONSTRAINT uq_orders_order_number UNIQUE (order_number),
	CONSTRAINT fk_orders_customer_user_id FOREIGN KEY(customer_user_id) REFERENCES auth.users (id) ON DELETE RESTRICT
)""",
    """CREATE INDEX idx_orders_customer ON orders (customer_user_id, created_at)""",
    """ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.orders FROM PUBLIC, anon, authenticated""",
    """CREATE TRIGGER sr_touch BEFORE UPDATE ON public.orders FOR EACH ROW EXECUTE FUNCTION public.sr_touch_updated_at()""",
    """CREATE TABLE products (
	category_id UUID,
	slug TEXT NOT NULL,
	name TEXT NOT NULL,
	description TEXT,
	lifecycle_status TEXT DEFAULT 'draft' NOT NULL,
	is_featured BOOLEAN DEFAULT false NOT NULL,
	featured_sort_order INTEGER DEFAULT '0' NOT NULL,
	allows_new_pair BOOLEAN DEFAULT true NOT NULL,
	allows_existing_qr BOOLEAN DEFAULT false NOT NULL,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_products PRIMARY KEY (id),
	CONSTRAINT ck_products_lifecycle CHECK (lifecycle_status IN ('draft','published','archived')),
	CONSTRAINT fk_products_category_id FOREIGN KEY(category_id) REFERENCES product_categories (id) ON DELETE RESTRICT,
	CONSTRAINT uq_products_slug UNIQUE (slug)
)""",
    """CREATE INDEX idx_products_featured ON products (featured_sort_order, id) WHERE lifecycle_status='published' AND is_featured""",
    """ALTER TABLE public.products ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.products FROM PUBLIC, anon, authenticated""",
    """CREATE TRIGGER sr_touch BEFORE UPDATE ON public.products FOR EACH ROW EXECUTE FUNCTION public.sr_touch_updated_at()""",
    """CREATE TABLE shipping_addresses (
	customer_user_id UUID NOT NULL,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	recipient_name_ciphertext BYTEA NOT NULL,
	phone_ciphertext BYTEA NOT NULL,
	address_ciphertext BYTEA NOT NULL,
	city VARCHAR(100) NOT NULL,
	province VARCHAR(100),
	postal_code VARCHAR(20),
	key_version SMALLINT NOT NULL,
	CONSTRAINT pk_shipping_addresses PRIMARY KEY (id),
	CONSTRAINT ck_shipping_addresses_encryption CHECK (key_version > 0 AND octet_length(recipient_name_ciphertext) > 0 AND octet_length(phone_ciphertext) > 0 AND octet_length(address_ciphertext) > 0),
	CONSTRAINT fk_shipping_addresses_customer_user_id FOREIGN KEY(customer_user_id) REFERENCES auth.users (id) ON DELETE RESTRICT
)""",
    """CREATE INDEX idx_addresses_customer ON shipping_addresses (customer_user_id)""",
    """ALTER TABLE public.shipping_addresses ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.shipping_addresses FROM PUBLIC, anon, authenticated""",
    """CREATE TABLE order_shipping_snapshots (
	order_id UUID NOT NULL,
	source_address_id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	recipient_name_ciphertext BYTEA NOT NULL,
	phone_ciphertext BYTEA NOT NULL,
	address_ciphertext BYTEA NOT NULL,
	city VARCHAR(100) NOT NULL,
	province VARCHAR(100),
	postal_code VARCHAR(20),
	key_version SMALLINT NOT NULL,
	CONSTRAINT pk_order_shipping_snapshots PRIMARY KEY (order_id),
	CONSTRAINT ck_order_shipping_snapshots_encryption CHECK (key_version > 0 AND octet_length(recipient_name_ciphertext) > 0 AND octet_length(phone_ciphertext) > 0 AND octet_length(address_ciphertext) > 0),
	CONSTRAINT fk_order_shipping_snapshots_order_id FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE RESTRICT,
	CONSTRAINT fk_order_shipping_snapshots_source_address_id FOREIGN KEY(source_address_id) REFERENCES shipping_addresses (id) ON DELETE RESTRICT
)""",
    """ALTER TABLE public.order_shipping_snapshots ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.order_shipping_snapshots FROM PUBLIC, anon, authenticated""",
    """CREATE TABLE payment_attempts (
	order_id UUID NOT NULL,
	provider_key TEXT NOT NULL,
	provider_external_id TEXT,
	idempotency_key TEXT NOT NULL,
	amount NUMERIC(12, 2) NOT NULL,
	currency_code VARCHAR(3) DEFAULT 'PKR' NOT NULL,
	state TEXT DEFAULT 'initiated' NOT NULL,
	sender_reference_masked TEXT,
	sender_holder_ciphertext BYTEA,
	sender_account_ciphertext BYTEA,
	sender_key_version SMALLINT,
	provider_payload_ref TEXT,
	reviewed_by UUID,
	verified_at TIMESTAMP WITH TIME ZONE,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_payment_attempts PRIMARY KEY (id),
	CONSTRAINT ck_payment_attempts_state CHECK (state IN ('initiated','submitted','under_review','verified','rejected','expired','refunded','disputed')),
	CONSTRAINT ck_payment_attempts_amount CHECK (amount >= 0),
	CONSTRAINT ck_payment_attempts_currency CHECK (currency_code ~ '^[A-Z]{3}$'),
	CONSTRAINT ck_payment_attempts_verification CHECK (state <> 'verified' OR verified_at IS NOT NULL),
	CONSTRAINT ck_payment_attempts_sender_key CHECK ((sender_holder_ciphertext IS NULL AND sender_account_ciphertext IS NULL AND sender_key_version IS NULL) OR ((sender_holder_ciphertext IS NOT NULL OR sender_account_ciphertext IS NOT NULL) AND sender_key_version IS NOT NULL AND sender_key_version > 0)),
	CONSTRAINT uq_payment_attempts_provider_key UNIQUE (provider_key, idempotency_key),
	CONSTRAINT fk_payment_attempts_order_id FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE RESTRICT,
	CONSTRAINT fk_payment_attempts_reviewed_by FOREIGN KEY(reviewed_by) REFERENCES auth.users (id) ON DELETE RESTRICT
)""",
    """CREATE INDEX idx_payments_order ON payment_attempts (order_id, created_at)""",
    """CREATE UNIQUE INDEX uq_payment_provider_external ON payment_attempts (provider_key, provider_external_id) WHERE provider_external_id IS NOT NULL""",
    """ALTER TABLE public.payment_attempts ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.payment_attempts FROM PUBLIC, anon, authenticated""",
    """CREATE TRIGGER sr_touch BEFORE UPDATE ON public.payment_attempts FOR EACH ROW EXECUTE FUNCTION public.sr_touch_updated_at()""",
    """CREATE TABLE product_images (
	product_id UUID NOT NULL,
	cloudinary_public_id TEXT NOT NULL,
	alt_text TEXT NOT NULL,
	sort_order INTEGER DEFAULT '0' NOT NULL,
	is_primary BOOLEAN DEFAULT false NOT NULL,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_product_images PRIMARY KEY (id),
	CONSTRAINT uq_product_images_product_id UNIQUE (product_id, cloudinary_public_id),
	CONSTRAINT fk_product_images_product_id FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT
)""",
    """ALTER TABLE public.product_images ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.product_images FROM PUBLIC, anon, authenticated""",
    """CREATE TABLE product_variants (
	product_id UUID NOT NULL,
	sku TEXT NOT NULL,
	name TEXT NOT NULL,
	size_mm NUMERIC(7, 2),
	material TEXT,
	color TEXT,
	currency_code VARCHAR(3) DEFAULT 'PKR' NOT NULL,
	unit_price NUMERIC(12, 2) NOT NULL,
	fulfillment_method TEXT NOT NULL,
	template_key TEXT,
	template_version INTEGER DEFAULT '1' NOT NULL,
	is_active BOOLEAN DEFAULT true NOT NULL,
	sort_order INTEGER DEFAULT '0' NOT NULL,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_product_variants PRIMARY KEY (id),
	CONSTRAINT ck_product_variants_size CHECK (size_mm > 0),
	CONSTRAINT ck_product_variants_price CHECK (unit_price >= 0),
	CONSTRAINT ck_product_variants_currency CHECK (currency_code ~ '^[A-Z]{3}$'),
	CONSTRAINT ck_product_variants_method CHECK (fulfillment_method IN ('pdf_label','manufacturer_artwork','manual')),
	CONSTRAINT ck_product_variants_template_version CHECK (template_version > 0),
	CONSTRAINT fk_product_variants_product_id FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT,
	CONSTRAINT uq_product_variants_sku UNIQUE (sku)
)""",
    """CREATE INDEX idx_product_variants_live ON product_variants (product_id, sort_order) WHERE is_active""",
    """ALTER TABLE public.product_variants ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.product_variants FROM PUBLIC, anon, authenticated""",
    """CREATE TRIGGER sr_touch BEFORE UPDATE ON public.product_variants FOR EACH ROW EXECUTE FUNCTION public.sr_touch_updated_at()""",
    """CREATE TABLE shipments (
	order_id UUID NOT NULL,
	shipping_address_id UUID NOT NULL,
	carrier VARCHAR(80),
	tracking_reference VARCHAR(150),
	status VARCHAR(24) DEFAULT 'preparing' NOT NULL,
	packed_at TIMESTAMP WITH TIME ZONE,
	dispatched_at TIMESTAMP WITH TIME ZONE,
	delivered_at TIMESTAMP WITH TIME ZONE,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_shipments PRIMARY KEY (id),
	CONSTRAINT ck_shipments_status CHECK (status IN ('preparing','packed','dispatched','delivered','exception','returned')),
	CONSTRAINT ck_shipments_packed CHECK (status <> 'packed' OR packed_at IS NOT NULL),
	CONSTRAINT ck_shipments_dispatch CHECK (status <> 'dispatched' OR dispatched_at IS NOT NULL),
	CONSTRAINT ck_shipments_delivery CHECK (status <> 'delivered' OR delivered_at IS NOT NULL),
	CONSTRAINT fk_shipments_order_id FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE RESTRICT,
	CONSTRAINT fk_shipments_shipping_address_id FOREIGN KEY(shipping_address_id) REFERENCES shipping_addresses (id) ON DELETE RESTRICT
)""",
    """CREATE INDEX idx_shipments_order ON shipments (order_id)""",
    """ALTER TABLE public.shipments ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.shipments FROM PUBLIC, anon, authenticated""",
    """CREATE TABLE order_items (
	order_id UUID NOT NULL,
	product_id UUID NOT NULL,
	variant_id UUID NOT NULL,
	product_name_snapshot TEXT NOT NULL,
	variant_name_snapshot TEXT NOT NULL,
	sku_snapshot TEXT NOT NULL,
	size_mm_snapshot NUMERIC(7, 2),
	material_snapshot TEXT,
	fulfillment_method_snapshot TEXT NOT NULL,
	template_key_snapshot TEXT,
	template_version_snapshot INTEGER NOT NULL,
	quantity INTEGER NOT NULL,
	unit_price_snapshot NUMERIC(12, 2) NOT NULL,
	tax_snapshot NUMERIC(12, 2) DEFAULT '0' NOT NULL,
	discount_snapshot NUMERIC(12, 2) DEFAULT '0' NOT NULL,
	line_total NUMERIC(12, 2) NOT NULL,
	currency_code VARCHAR(3) DEFAULT 'PKR' NOT NULL,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_order_items PRIMARY KEY (id),
	CONSTRAINT ck_order_items_quantities CHECK (quantity > 0 AND template_version_snapshot > 0),
	CONSTRAINT ck_order_items_size CHECK (size_mm_snapshot > 0),
	CONSTRAINT ck_order_items_amounts CHECK (unit_price_snapshot >= 0 AND tax_snapshot >= 0 AND discount_snapshot >= 0 AND line_total >= 0),
	CONSTRAINT ck_order_items_line_total CHECK (line_total = quantity * unit_price_snapshot + tax_snapshot - discount_snapshot),
	CONSTRAINT ck_order_items_method CHECK (fulfillment_method_snapshot IN ('pdf_label','manufacturer_artwork','manual')),
	CONSTRAINT ck_order_items_currency CHECK (currency_code ~ '^[A-Z]{3}$'),
	CONSTRAINT fk_order_items_order_id FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE RESTRICT,
	CONSTRAINT fk_order_items_product_id FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT,
	CONSTRAINT fk_order_items_variant_id FOREIGN KEY(variant_id) REFERENCES product_variants (id) ON DELETE RESTRICT
)""",
    """CREATE INDEX idx_order_items_order ON order_items (order_id, id)""",
    """ALTER TABLE public.order_items ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.order_items FROM PUBLIC, anon, authenticated""",
    """CREATE TABLE order_pair_units (
	order_id UUID NOT NULL,
	pair_id UUID NOT NULL,
	kind TEXT DEFAULT 'new_pair' NOT NULL,
	status TEXT DEFAULT 'reserved' NOT NULL,
	reserved_until TIMESTAMP WITH TIME ZONE,
	allocated_at TIMESTAMP WITH TIME ZONE,
	allocated_by UUID,
	released_at TIMESTAMP WITH TIME ZONE,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_order_pair_units PRIMARY KEY (id),
	CONSTRAINT ck_order_pair_units_kind CHECK (kind = 'new_pair'),
	CONSTRAINT ck_order_pair_units_status CHECK (status IN ('reserved','allocated','released','cancelled')),
	CONSTRAINT ck_order_pair_units_reservation CHECK (status <> 'reserved' OR reserved_until IS NOT NULL),
	CONSTRAINT ck_order_pair_units_allocation CHECK (status <> 'allocated' OR allocated_at IS NOT NULL),
	CONSTRAINT ck_order_pair_units_release CHECK (status NOT IN ('released','cancelled') OR released_at IS NOT NULL),
	CONSTRAINT fk_order_pair_units_order_id FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE RESTRICT,
	CONSTRAINT fk_order_pair_units_pair_id FOREIGN KEY(pair_id) REFERENCES tag_pairs (id) ON DELETE RESTRICT,
	CONSTRAINT fk_order_pair_units_allocated_by FOREIGN KEY(allocated_by) REFERENCES auth.users (id) ON DELETE RESTRICT
)""",
    """CREATE INDEX idx_pair_units_expiry ON order_pair_units (reserved_until) WHERE status='reserved'""",
    """CREATE INDEX idx_pair_units_order ON order_pair_units (order_id)""",
    """CREATE UNIQUE INDEX uq_pair_one_live_claim ON order_pair_units (pair_id) WHERE status IN ('reserved','allocated')""",
    """ALTER TABLE public.order_pair_units ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.order_pair_units FROM PUBLIC, anon, authenticated""",
    """CREATE TABLE pair_print_qa (
	pair_id UUID NOT NULL,
	qa_round INTEGER NOT NULL,
	lost_scan_passed BOOLEAN NOT NULL,
	ice_scan_passed BOOLEAN NOT NULL,
	pair_match_passed BOOLEAN NOT NULL,
	credential_concealed BOOLEAN NOT NULL,
	bilingual_label_passed BOOLEAN NOT NULL,
	quiet_zone_passed BOOLEAN NOT NULL,
	indoor_size_passed BOOLEAN NOT NULL,
	outdoor_size_passed BOOLEAN NOT NULL,
	packaging_method VARCHAR(30) NOT NULL,
	tamper_evidence_passed BOOLEAN NOT NULL,
	approved BOOLEAN NOT NULL,
	inspected_by UUID NOT NULL,
	inspected_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	notes TEXT,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	CONSTRAINT pk_pair_print_qa PRIMARY KEY (id),
	CONSTRAINT uq_pair_print_qa_pair_id UNIQUE (pair_id, qa_round),
	CONSTRAINT ck_pair_print_qa_round CHECK (qa_round > 0),
	CONSTRAINT ck_pair_print_qa_packaging CHECK (packaging_method IN ('scratch_off','sealed_sleeve','peel_seal')),
	CONSTRAINT ck_pair_print_qa_approval CHECK (NOT approved OR (lost_scan_passed AND ice_scan_passed AND pair_match_passed AND credential_concealed AND bilingual_label_passed AND quiet_zone_passed AND indoor_size_passed AND outdoor_size_passed AND tamper_evidence_passed)),
	CONSTRAINT fk_pair_print_qa_pair_id FOREIGN KEY(pair_id) REFERENCES tag_pairs (id) ON DELETE RESTRICT,
	CONSTRAINT fk_pair_print_qa_inspected_by FOREIGN KEY(inspected_by) REFERENCES auth.users (id) ON DELETE RESTRICT
)""",
    """ALTER TABLE public.pair_print_qa ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.pair_print_qa FROM PUBLIC, anon, authenticated""",
    """CREATE TABLE payment_evidence (
	attempt_id UUID NOT NULL,
	bucket TEXT DEFAULT 'private-payment-evidence' NOT NULL,
	object_key TEXT NOT NULL,
	sha256_hex VARCHAR(64) NOT NULL,
	content_type TEXT NOT NULL,
	bytes_size BIGINT NOT NULL,
	retention_until TIMESTAMP WITH TIME ZONE,
	deletion_hold_reason TEXT,
	deleted_at TIMESTAMP WITH TIME ZONE,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_payment_evidence PRIMARY KEY (id),
	CONSTRAINT ck_payment_evidence_size CHECK (bytes_size > 0),
	CONSTRAINT ck_payment_evidence_hash CHECK (sha256_hex ~ '^[0-9a-f]{64}$'),
	CONSTRAINT ck_payment_evidence_private_bucket CHECK (bucket = 'private-payment-evidence'),
	CONSTRAINT ck_payment_evidence_content_type CHECK (content_type IN ('image/jpeg','image/png','application/pdf')),
	CONSTRAINT fk_payment_evidence_attempt_id FOREIGN KEY(attempt_id) REFERENCES payment_attempts (id) ON DELETE RESTRICT,
	CONSTRAINT uq_payment_evidence_object_key UNIQUE (object_key)
)""",
    """CREATE INDEX idx_evidence_attempt ON payment_evidence (attempt_id)""",
    """ALTER TABLE public.payment_evidence ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.payment_evidence FROM PUBLIC, anon, authenticated""",
    """CREATE TABLE payment_reviews (
	attempt_id UUID NOT NULL,
	reviewed_by UUID NOT NULL,
	decision VARCHAR(24) NOT NULL,
	bank_verified BOOLEAN DEFAULT false NOT NULL,
	bank_reference_fingerprint BYTEA,
	bank_reference_key_version SMALLINT,
	reason TEXT,
	reviewed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	CONSTRAINT pk_payment_reviews PRIMARY KEY (id),
	CONSTRAINT ck_payment_reviews_decision CHECK (decision IN ('verify','reject','request_more_info')),
	CONSTRAINT ck_payment_reviews_bank_confirmation CHECK (decision <> 'verify' OR (bank_verified AND bank_reference_fingerprint IS NOT NULL AND bank_reference_key_version IS NOT NULL AND bank_reference_key_version > 0)),
	CONSTRAINT fk_payment_reviews_attempt_id FOREIGN KEY(attempt_id) REFERENCES payment_attempts (id) ON DELETE RESTRICT,
	CONSTRAINT fk_payment_reviews_reviewed_by FOREIGN KEY(reviewed_by) REFERENCES auth.users (id) ON DELETE RESTRICT
)""",
    """CREATE INDEX idx_review_attempt ON payment_reviews (attempt_id)""",
    """CREATE UNIQUE INDEX uq_review_settlement ON payment_reviews (bank_reference_fingerprint) WHERE decision='verify'""",
    """ALTER TABLE public.payment_reviews ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.payment_reviews FROM PUBLIC, anon, authenticated""",
    """CREATE TABLE shipment_pairs (
	shipment_id UUID NOT NULL,
	pair_id UUID NOT NULL,
	packed_qa_confirmed BOOLEAN DEFAULT false NOT NULL,
	packed_by UUID,
	packed_at TIMESTAMP WITH TIME ZONE,
	CONSTRAINT pk_shipment_pairs PRIMARY KEY (shipment_id, pair_id),
	CONSTRAINT ck_shipment_pairs_packing CHECK (NOT packed_qa_confirmed OR (packed_by IS NOT NULL AND packed_at IS NOT NULL)),
	CONSTRAINT fk_shipment_pairs_shipment_id FOREIGN KEY(shipment_id) REFERENCES shipments (id) ON DELETE RESTRICT,
	CONSTRAINT uq_shipment_pairs_pair_id UNIQUE (pair_id),
	CONSTRAINT fk_shipment_pairs_pair_id FOREIGN KEY(pair_id) REFERENCES tag_pairs (id) ON DELETE RESTRICT,
	CONSTRAINT fk_shipment_pairs_packed_by FOREIGN KEY(packed_by) REFERENCES auth.users (id) ON DELETE RESTRICT
)""",
    """ALTER TABLE public.shipment_pairs ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.shipment_pairs FROM PUBLIC, anon, authenticated""",
    """CREATE TABLE order_item_qr_uses (
	order_item_id UUID NOT NULL,
	qr_code_id UUID NOT NULL,
	pair_unit_id UUID,
	use_kind TEXT NOT NULL,
	tag_type_snapshot TEXT NOT NULL,
	copies INTEGER NOT NULL,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_order_item_qr_uses PRIMARY KEY (id),
	CONSTRAINT ck_order_item_qr_uses_kind CHECK (use_kind IN ('new_pair','existing_owned')),
	CONSTRAINT ck_order_item_qr_uses_type CHECK (tag_type_snapshot IN ('lost','ice')),
	CONSTRAINT ck_order_item_qr_uses_copies CHECK (copies > 0),
	CONSTRAINT ck_order_item_qr_uses_pair_unit CHECK ((use_kind='new_pair' AND pair_unit_id IS NOT NULL) OR (use_kind='existing_owned' AND pair_unit_id IS NULL)),
	CONSTRAINT uq_order_item_qr_uses_order_item_id UNIQUE (order_item_id, qr_code_id, use_kind),
	CONSTRAINT fk_order_item_qr_uses_order_item_id FOREIGN KEY(order_item_id) REFERENCES order_items (id) ON DELETE RESTRICT,
	CONSTRAINT fk_order_item_qr_uses_qr_code_id FOREIGN KEY(qr_code_id) REFERENCES qr_codes (id) ON DELETE RESTRICT,
	CONSTRAINT fk_order_item_qr_uses_pair_unit_id FOREIGN KEY(pair_unit_id) REFERENCES order_pair_units (id) ON DELETE RESTRICT
)""",
    """CREATE INDEX idx_order_qr_uses_qr ON order_item_qr_uses (qr_code_id)""",
    """CREATE INDEX idx_order_qr_uses_unit ON order_item_qr_uses (pair_unit_id)""",
    """ALTER TABLE public.order_item_qr_uses ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.order_item_qr_uses FROM PUBLIC, anon, authenticated""",
    """-- Frozen guard source for revision 0002_commerce. Services still authorize actors.
CREATE FUNCTION public.sr_order_history() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE oid uuid; placed timestamptz;
BEGIN
 IF TG_TABLE_NAME = 'orders' THEN
  IF TG_OP = 'DELETE' THEN
   IF OLD.placed_at IS NOT NULL THEN RAISE EXCEPTION 'Placed order history is immutable' USING ERRCODE='23514'; END IF;
   RETURN OLD;
  END IF;
  IF TG_OP = 'UPDATE' AND OLD.placed_at IS NOT NULL AND
     (NEW.id,NEW.order_number,NEW.customer_user_id,NEW.currency_code,NEW.subtotal_pkr,
      NEW.shipping_pkr,NEW.tax_pkr,NEW.discount_pkr,NEW.total_pkr,NEW.placed_at,NEW.created_at)
     IS DISTINCT FROM
     (OLD.id,OLD.order_number,OLD.customer_user_id,OLD.currency_code,OLD.subtotal_pkr,
      OLD.shipping_pkr,OLD.tax_pkr,OLD.discount_pkr,OLD.total_pkr,OLD.placed_at,OLD.created_at) THEN
   RAISE EXCEPTION 'Placed order snapshots are immutable' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
 END IF;
 IF TG_TABLE_NAME = 'order_item_qr_uses' THEN
  IF TG_OP='DELETE' THEN
   SELECT order_id INTO oid FROM public.order_items WHERE id=OLD.order_item_id;
  ELSE
   SELECT order_id INTO oid FROM public.order_items WHERE id=NEW.order_item_id;
   IF TG_OP='UPDATE' AND NEW.order_item_id <> OLD.order_item_id THEN
    RAISE EXCEPTION 'Cannot move historical QR use' USING ERRCODE='23514';
   END IF;
  END IF;
 ELSE
  IF TG_OP='DELETE' THEN oid:=OLD.order_id; ELSE oid:=NEW.order_id; END IF;
  IF TG_OP='UPDATE' AND NEW.order_id <> OLD.order_id THEN
   RAISE EXCEPTION 'Cannot move purchase snapshot' USING ERRCODE='23514';
  END IF;
 END IF;
 SELECT placed_at INTO placed FROM public.orders WHERE id=oid FOR UPDATE;
 IF placed IS NOT NULL THEN
  RAISE EXCEPTION 'Placed purchase records are immutable' USING ERRCODE='23514';
 END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; END IF;
 IF TG_TABLE_NAME='order_items' THEN
  IF NOT EXISTS (SELECT 1 FROM public.product_variants WHERE id=NEW.variant_id AND product_id=NEW.product_id) THEN
   RAISE EXCEPTION 'Variant does not belong to product' USING ERRCODE='23514';
  END IF;
 ELSIF TG_TABLE_NAME='order_shipping_snapshots' THEN
  IF NOT EXISTS (
   SELECT 1 FROM public.shipping_addresses a JOIN public.orders o ON o.customer_user_id=a.customer_user_id
    WHERE a.id=NEW.source_address_id AND o.id=NEW.order_id
  ) THEN RAISE EXCEPTION 'Shipping address owner mismatch' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE TRIGGER sr_order_history BEFORE INSERT OR UPDATE OR DELETE ON public.orders
FOR EACH ROW EXECUTE FUNCTION public.sr_order_history();
CREATE TRIGGER sr_item_history BEFORE INSERT OR UPDATE OR DELETE ON public.order_items
FOR EACH ROW EXECUTE FUNCTION public.sr_order_history();
CREATE TRIGGER sr_use_history BEFORE INSERT OR UPDATE OR DELETE ON public.order_item_qr_uses
FOR EACH ROW EXECUTE FUNCTION public.sr_order_history();
CREATE TRIGGER sr_shipping_history BEFORE INSERT OR UPDATE OR DELETE ON public.order_shipping_snapshots
FOR EACH ROW EXECUTE FUNCTION public.sr_order_history();

CREATE FUNCTION public.sr_qr_use_relation() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE qr_row public.qr_codes%ROWTYPE; oid uuid; customer uuid; product public.products%ROWTYPE;
BEGIN
 SELECT i.order_id,o.customer_user_id INTO oid,customer
 FROM public.order_items i JOIN public.orders o ON o.id=i.order_id
 JOIN public.products p ON p.id=i.product_id WHERE i.id=NEW.order_item_id;
 PERFORM 1 FROM public.orders WHERE id=oid FOR UPDATE;
 SELECT p.* INTO product FROM public.products p JOIN public.order_items i ON i.product_id=p.id WHERE i.id=NEW.order_item_id;
 -- Read and lock the parent before QR, matching the identity mutation lock order.
 PERFORM 1 FROM public.tag_pairs p JOIN public.qr_codes q ON q.pair_id=p.id
 WHERE q.id=NEW.qr_code_id FOR UPDATE OF p;
 SELECT * INTO qr_row FROM public.qr_codes WHERE id=NEW.qr_code_id FOR SHARE;
 IF NOT FOUND OR qr_row.tag_type <> NEW.tag_type_snapshot OR NOT qr_row.is_current
    OR qr_row.public_status IN ('revoked','admin_suspended') THEN
  RAISE EXCEPTION 'QR use does not match eligible identity' USING ERRCODE='23514';
 END IF;
 IF NEW.use_kind='new_pair' THEN
  IF NOT product.allows_new_pair OR NOT EXISTS (
   SELECT 1 FROM public.order_pair_units u WHERE u.id=NEW.pair_unit_id
    AND u.order_id=oid AND u.pair_id=qr_row.pair_id AND u.status IN ('reserved','allocated')
  ) THEN RAISE EXCEPTION 'QR use pair/order mismatch' USING ERRCODE='23514'; END IF;
 ELSE
  IF NOT product.allows_existing_qr OR NOT EXISTS (
   SELECT 1 FROM public.tag_pairs WHERE id=qr_row.pair_id AND owner_user_id=customer AND ownership_status='active'
  ) THEN RAISE EXCEPTION 'Existing QR is not owned by customer or reuse is disabled' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_qr_use_relation BEFORE INSERT OR UPDATE ON public.order_item_qr_uses
FOR EACH ROW EXECUTE FUNCTION public.sr_qr_use_relation();

CREATE FUNCTION public.sr_pair_claim_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE ownership text; placed timestamptz;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Reservation history cannot be deleted' USING ERRCODE='23514'; END IF;
 SELECT placed_at INTO placed FROM public.orders WHERE id=NEW.order_id FOR UPDATE;
 SELECT ownership_status INTO ownership FROM public.tag_pairs WHERE id=NEW.pair_id FOR UPDATE;
 IF TG_OP='INSERT' THEN
  IF placed IS NOT NULL OR ownership <> 'unclaimed' THEN
   RAISE EXCEPTION 'Pair is not eligible for new reservation' USING ERRCODE='23514';
  END IF;
 ELSE
  IF (NEW.id,NEW.order_id,NEW.pair_id,NEW.kind,NEW.created_at) IS DISTINCT FROM
     (OLD.id,OLD.order_id,OLD.pair_id,OLD.kind,OLD.created_at) THEN
   RAISE EXCEPTION 'Reservation identity is immutable' USING ERRCODE='23514';
  END IF;
  IF OLD.status='allocated' AND (NEW.status <> 'allocated' OR NEW.allocated_at IS DISTINCT FROM OLD.allocated_at) THEN
   RAISE EXCEPTION 'Permanent allocation cannot be recycled' USING ERRCODE='23514';
  END IF;
  IF OLD.status IN ('released','cancelled') AND NEW.status <> OLD.status THEN
   RAISE EXCEPTION 'Closed reservation cannot be resurrected' USING ERRCODE='23514';
  END IF;
 END IF;
 IF NEW.status IN ('released','cancelled') AND EXISTS (
  SELECT 1 FROM public.payment_attempts WHERE order_id=NEW.order_id
   AND state IN ('submitted','under_review','verified','disputed')
 ) THEN RAISE EXCEPTION 'Payment reconciliation prevents reservation release' USING ERRCODE='23514'; END IF;
 IF NEW.status='allocated' AND NOT EXISTS (
  SELECT 1 FROM public.orders o JOIN public.payment_attempts p ON p.order_id=o.id
   WHERE o.id=NEW.order_id AND o.placed_at IS NOT NULL AND o.payment_status='verified'
    AND p.state='verified' AND p.amount=o.total_pkr AND p.currency_code=o.currency_code
 ) THEN RAISE EXCEPTION 'Allocation requires verified settlement' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_pair_claim_guard BEFORE INSERT OR UPDATE OR DELETE ON public.order_pair_units
FOR EACH ROW EXECUTE FUNCTION public.sr_pair_claim_guard();

CREATE FUNCTION public.sr_payment_history() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE oid uuid;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Payment history cannot be deleted' USING ERRCODE='23514'; END IF;
 IF TG_TABLE_NAME='payment_reviews' THEN
  IF TG_OP='UPDATE' THEN RAISE EXCEPTION 'Payment reviews are append only' USING ERRCODE='23514'; END IF;
  SELECT order_id INTO oid FROM public.payment_attempts WHERE id=NEW.attempt_id;
 ELSE
  oid:=NEW.order_id;
  IF TG_OP='UPDATE' AND (NEW.id,NEW.order_id,NEW.provider_key,NEW.idempotency_key,NEW.amount,NEW.currency_code,NEW.created_at)
     IS DISTINCT FROM (OLD.id,OLD.order_id,OLD.provider_key,OLD.idempotency_key,OLD.amount,OLD.currency_code,OLD.created_at) THEN
   RAISE EXCEPTION 'Payment identity and amount are immutable' USING ERRCODE='23514';
  END IF;
  IF TG_OP='UPDATE' AND OLD.verified_at IS NOT NULL AND
     (NEW.verified_at IS DISTINCT FROM OLD.verified_at OR NEW.state NOT IN ('verified','refunded','disputed')) THEN
   RAISE EXCEPTION 'Verified payment history cannot be erased' USING ERRCODE='23514';
  END IF;
 END IF;
 PERFORM 1 FROM public.orders WHERE id=oid FOR UPDATE;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_payment_history BEFORE INSERT OR UPDATE OR DELETE ON public.payment_attempts
FOR EACH ROW EXECUTE FUNCTION public.sr_payment_history();
CREATE TRIGGER sr_review_history BEFORE INSERT OR UPDATE OR DELETE ON public.payment_reviews
FOR EACH ROW EXECUTE FUNCTION public.sr_payment_history();

CREATE FUNCTION public.sr_check_payment() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE pid uuid; p public.payment_attempts%ROWTYPE; o public.orders%ROWTYPE;
BEGIN
 IF TG_TABLE_NAME='payment_reviews' THEN pid:=NEW.attempt_id; ELSE pid:=NEW.id; END IF;
 SELECT * INTO p FROM public.payment_attempts WHERE id=pid;
 SELECT * INTO o FROM public.orders WHERE id=p.order_id FOR UPDATE;
 IF p.state='verified' THEN
  IF o.placed_at IS NULL OR p.amount <> o.total_pkr OR p.currency_code <> o.currency_code THEN
   RAISE EXCEPTION 'Verified payment amount/currency/order mismatch' USING ERRCODE='23514';
  END IF;
  IF p.provider_key='manual_bank' AND (p.reviewed_by IS NULL OR NOT EXISTS (
   SELECT 1 FROM public.payment_reviews r WHERE r.attempt_id=p.id AND r.decision='verify'
    AND r.bank_verified AND r.reviewed_by=p.reviewed_by
  )) THEN RAISE EXCEPTION 'Manual payment requires independent bank review' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER sr_payment_verified AFTER INSERT OR UPDATE ON public.payment_attempts
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_check_payment();
CREATE CONSTRAINT TRIGGER sr_review_verified AFTER INSERT ON public.payment_reviews
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_check_payment();

CREATE FUNCTION public.sr_check_order() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE oid uuid; o public.orders%ROWTYPE; subtotal numeric;
BEGIN
 IF TG_TABLE_NAME='orders' THEN
  oid:=NEW.id;
 ELSIF TG_TABLE_NAME='order_item_qr_uses' THEN
  IF TG_OP='DELETE' THEN
   SELECT order_id INTO oid FROM public.order_items WHERE id=OLD.order_item_id;
  ELSE SELECT order_id INTO oid FROM public.order_items WHERE id=NEW.order_item_id; END IF;
 ELSE
  IF TG_OP='DELETE' THEN oid:=OLD.order_id; ELSE oid:=NEW.order_id; END IF;
 END IF;
 SELECT * INTO o FROM public.orders WHERE id=oid FOR UPDATE;
 IF NOT FOUND OR o.placed_at IS NULL THEN RETURN NULL; END IF;
 SELECT sum(line_total) INTO subtotal FROM public.order_items WHERE order_id=oid;
 IF subtotal IS NULL OR subtotal <> o.subtotal_pkr OR NOT EXISTS (
  SELECT 1 FROM public.order_shipping_snapshots WHERE order_id=oid
 ) THEN RAISE EXCEPTION 'Placed order requires matching lines and shipping snapshot' USING ERRCODE='23514'; END IF;
 IF EXISTS (
  SELECT 1 FROM public.order_items i WHERE i.order_id=oid AND
   (i.currency_code <> o.currency_code OR i.quantity <> COALESCE((
    SELECT sum(u.copies) FROM public.order_item_qr_uses u WHERE u.order_item_id=i.id
   ),0))
 ) THEN RAISE EXCEPTION 'Order copy quantities or currency mismatch' USING ERRCODE='23514'; END IF;
 IF EXISTS (
  SELECT 1 FROM public.order_pair_units p WHERE p.order_id=oid AND
   (NOT EXISTS (SELECT 1 FROM public.order_item_qr_uses u WHERE u.pair_unit_id=p.id AND u.tag_type_snapshot='lost')
    OR NOT EXISTS (SELECT 1 FROM public.order_item_qr_uses u WHERE u.pair_unit_id=p.id AND u.tag_type_snapshot='ice'))
 ) THEN RAISE EXCEPTION 'New pair requires both Lost and ICE copies' USING ERRCODE='23514'; END IF;
 IF o.payment_status='verified' AND NOT EXISTS (
  SELECT 1 FROM public.payment_attempts p WHERE p.order_id=oid AND p.state='verified'
   AND p.amount=o.total_pkr AND p.currency_code=o.currency_code
 ) THEN RAISE EXCEPTION 'Order payment status requires matching verified attempt' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER sr_order_complete AFTER INSERT OR UPDATE ON public.orders
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_check_order();
CREATE CONSTRAINT TRIGGER sr_item_complete AFTER INSERT OR UPDATE OR DELETE ON public.order_items
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_check_order();
CREATE CONSTRAINT TRIGGER sr_use_complete AFTER INSERT OR UPDATE OR DELETE ON public.order_item_qr_uses
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_check_order();
CREATE CONSTRAINT TRIGGER sr_unit_complete AFTER INSERT OR UPDATE ON public.order_pair_units
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_check_order();
CREATE CONSTRAINT TRIGGER sr_shipping_complete AFTER INSERT OR UPDATE OR DELETE ON public.order_shipping_snapshots
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_check_order();
CREATE CONSTRAINT TRIGGER sr_payment_order_complete AFTER INSERT OR UPDATE ON public.payment_attempts
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_check_order();

CREATE FUNCTION public.sr_shipment_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE oid uuid; sid uuid; p uuid;
BEGIN
 IF TG_TABLE_NAME='shipments' THEN
  oid:=NEW.order_id;
  IF TG_OP='UPDATE' AND (NEW.id,NEW.order_id,NEW.shipping_address_id) IS DISTINCT FROM
      (OLD.id,OLD.order_id,OLD.shipping_address_id) THEN
   RAISE EXCEPTION 'Shipment identity is immutable' USING ERRCODE='23514';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM public.order_shipping_snapshots WHERE order_id=oid AND source_address_id=NEW.shipping_address_id) THEN
   RAISE EXCEPTION 'Shipment must use purchase shipping snapshot' USING ERRCODE='23514';
  END IF;
 ELSE
  SELECT order_id INTO oid FROM public.shipments WHERE id=NEW.shipment_id;
  p:=NEW.pair_id;
  IF TG_OP='UPDATE' AND (NEW.shipment_id,NEW.pair_id) IS DISTINCT FROM (OLD.shipment_id,OLD.pair_id) THEN
   RAISE EXCEPTION 'Shipment pair membership is immutable' USING ERRCODE='23514';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM public.order_pair_units WHERE order_id=oid AND pair_id=p AND status='allocated') THEN
   RAISE EXCEPTION 'Shipment pair is not allocated to this order' USING ERRCODE='23514';
  END IF;
  IF NEW.packed_qa_confirmed AND NOT COALESCE((
   SELECT approved FROM public.pair_print_qa WHERE pair_id=p ORDER BY qa_round DESC LIMIT 1
  ),false) THEN RAISE EXCEPTION 'Packing requires latest physical QA approval' USING ERRCODE='23514'; END IF;
 END IF;
 PERFORM 1 FROM public.orders o JOIN public.payment_attempts a ON a.order_id=o.id
 WHERE o.id=oid AND o.payment_status='verified' AND o.placed_at IS NOT NULL
  AND a.state='verified' AND a.amount=o.total_pkr AND a.currency_code=o.currency_code FOR UPDATE OF o;
 IF NOT FOUND THEN RAISE EXCEPTION 'Shipment requires verified paid order' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_shipment_guard BEFORE INSERT OR UPDATE ON public.shipments
FOR EACH ROW EXECUTE FUNCTION public.sr_shipment_guard();
CREATE TRIGGER sr_shipment_pair_guard BEFORE INSERT OR UPDATE ON public.shipment_pairs
FOR EACH ROW EXECUTE FUNCTION public.sr_shipment_guard();

CREATE FUNCTION public.sr_check_shipment() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE sid uuid; s public.shipments%ROWTYPE;
BEGIN
 IF TG_TABLE_NAME='shipments' THEN sid:=NEW.id;
 ELSIF TG_OP='DELETE' THEN sid:=OLD.shipment_id; ELSE sid:=NEW.shipment_id; END IF;
 SELECT * INTO s FROM public.shipments WHERE id=sid FOR UPDATE;
 IF NOT FOUND OR s.status NOT IN ('packed','dispatched','delivered') THEN RETURN NULL; END IF;
 IF NOT EXISTS (
  SELECT 1 FROM public.orders o JOIN public.payment_attempts a ON a.order_id=o.id
   WHERE o.id=s.order_id AND o.payment_status='verified' AND a.state='verified'
    AND a.amount=o.total_pkr AND a.currency_code=o.currency_code
 ) THEN RAISE EXCEPTION 'Shipment release requires matching verified settlement' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS (SELECT 1 FROM public.shipment_pairs WHERE shipment_id=sid) OR EXISTS (
  SELECT 1 FROM public.shipment_pairs p WHERE p.shipment_id=sid AND
   (NOT p.packed_qa_confirmed OR NOT COALESCE((
     SELECT approved FROM public.pair_print_qa WHERE pair_id=p.pair_id ORDER BY qa_round DESC LIMIT 1
    ),false))
 ) THEN RAISE EXCEPTION 'Shipment release requires packed QA-approved pairs' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER sr_shipment_complete AFTER INSERT OR UPDATE ON public.shipments
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_check_shipment();
CREATE CONSTRAINT TRIGGER sr_shipment_pairs_complete AFTER INSERT OR UPDATE OR DELETE ON public.shipment_pairs
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_check_shipment();""",
]


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = set(inspector.get_table_names(schema="public"))
    legacy = {
        "payment_submissions",
        "order_pair_allocations",
        "payment_proofs",
        "pair_reservations",
    }
    if existing.intersection(set(TABLES) | legacy):
        raise RuntimeError(
            "Existing commerce tables require explicit reconciliation; nothing changed"
        )
    if not {"tag_pairs", "qr_codes", "qr_batches"}.issubset(existing):
        raise RuntimeError("Initial identity revision is required")
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute("SET LOCAL search_path = public, pg_catalog")
    for statement in DDL:
        op.execute(statement)


def downgrade():
    raise RuntimeError(
        "Destructive downgrade disabled; author a reviewed additive forward fix"
    )
