"""Initial identity/pair/QR/independent profile schema; additive only.

Frozen PostgreSQL DDL, not imported from mutable application models.
Managed Supabase auth.users is referenced and never modified.
"""

from sqlalchemy import inspect, text

from alembic import op

revision = "0001_identity_profiles"
down_revision = None
branch_labels = None
depends_on = None

TABLES = [
    "qr_batches",
    "staff_roles",
    "user_profiles",
    "tag_pairs",
    "pair_activation_credentials",
    "qr_codes",
    "ice_profiles",
    "lost_item_profiles",
    "tag_contact_preferences",
    "ice_contacts",
]
DDL = [
    """-- This file is a frozen part of revision 0001; do not edit after sharing.
CREATE FUNCTION public.sr_touch_updated_at() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
BEGIN NEW.updated_at := now(); RETURN NEW; END $$;""",
    """CREATE TABLE qr_batches (
	batch_code VARCHAR(40) NOT NULL,
	supplier_name VARCHAR(120),
	print_material VARCHAR(60),
	ecc_level VARCHAR(1) NOT NULL,
	generated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	printed_at TIMESTAMP WITH TIME ZONE,
	qa_approved_at TIMESTAMP WITH TIME ZONE,
	qa_approved_by UUID,
	print_manifest_checksum VARCHAR(64),
	status VARCHAR(24) DEFAULT 'draft' NOT NULL,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_qr_batches PRIMARY KEY (id),
	CONSTRAINT ck_qr_batches_ecc CHECK (ecc_level IN ('M','Q')),
	CONSTRAINT ck_qr_batches_status CHECK (status IN ('draft','generated','printed','qa_passed','rejected','closed')),
	CONSTRAINT uq_qr_batches_batch_code UNIQUE (batch_code),
	CONSTRAINT fk_qr_batches_qa_approved_by FOREIGN KEY(qa_approved_by) REFERENCES auth.users (id) ON DELETE RESTRICT
)""",
    """ALTER TABLE public.qr_batches ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.qr_batches FROM PUBLIC, anon, authenticated""",
    """CREATE TRIGGER sr_touch BEFORE UPDATE ON public.qr_batches FOR EACH ROW EXECUTE FUNCTION public.sr_touch_updated_at()""",
    """CREATE TABLE staff_roles (
	user_id UUID NOT NULL,
	role VARCHAR(40) NOT NULL,
	granted_by UUID,
	granted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	revoked_at TIMESTAMP WITH TIME ZONE,
	reason TEXT,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	CONSTRAINT pk_staff_roles PRIMARY KEY (id),
	CONSTRAINT ck_staff_roles_role CHECK (role IN ('support','operations','finance','security_admin','superadmin')),
	CONSTRAINT fk_staff_roles_user_id FOREIGN KEY(user_id) REFERENCES auth.users (id) ON DELETE RESTRICT,
	CONSTRAINT fk_staff_roles_granted_by FOREIGN KEY(granted_by) REFERENCES auth.users (id) ON DELETE RESTRICT
)""",
    """CREATE UNIQUE INDEX uq_staff_active_role ON staff_roles (user_id, role) WHERE revoked_at IS NULL""",
    """ALTER TABLE public.staff_roles ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.staff_roles FROM PUBLIC, anon, authenticated""",
    """CREATE TABLE user_profiles (
	user_id UUID NOT NULL,
	display_name VARCHAR(120),
	preferred_locale VARCHAR(5) DEFAULT 'en' NOT NULL,
	phone_ciphertext BYTEA,
	phone_key_version SMALLINT,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_user_profiles PRIMARY KEY (user_id),
	CONSTRAINT ck_user_profiles_locale CHECK (preferred_locale IN ('en','ur')),
	CONSTRAINT ck_user_profiles_phone_key CHECK ((phone_ciphertext IS NULL AND phone_key_version IS NULL) OR (phone_ciphertext IS NOT NULL AND phone_key_version > 0 AND phone_key_version IS NOT NULL)),
	CONSTRAINT fk_user_profiles_user_id FOREIGN KEY(user_id) REFERENCES auth.users (id) ON DELETE CASCADE
)""",
    """ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.user_profiles FROM PUBLIC, anon, authenticated""",
    """CREATE TRIGGER sr_touch BEFORE UPDATE ON public.user_profiles FOR EACH ROW EXECUTE FUNCTION public.sr_touch_updated_at()""",
    """CREATE TABLE tag_pairs (
	pair_reference VARCHAR(40) NOT NULL,
	batch_id UUID NOT NULL,
	owner_user_id UUID,
	inventory_status VARCHAR(24) DEFAULT 'generated' NOT NULL,
	ownership_status VARCHAR(24) DEFAULT 'unclaimed' NOT NULL,
	activated_at TIMESTAMP WITH TIME ZONE,
	revoked_at TIMESTAMP WITH TIME ZONE,
	row_version INTEGER DEFAULT '1' NOT NULL,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_tag_pairs PRIMARY KEY (id),
	CONSTRAINT ck_tag_pairs_inventory CHECK (inventory_status IN ('generated','printed','qa_passed','reserved','packed','shipped','delivered','rejected')),
	CONSTRAINT ck_tag_pairs_ownership CHECK (ownership_status IN ('unclaimed','active','transfer_pending','disputed','revoked')),
	CONSTRAINT ck_tag_pairs_active_owner CHECK (ownership_status <> 'active' OR (owner_user_id IS NOT NULL AND activated_at IS NOT NULL)),
	CONSTRAINT ck_tag_pairs_unclaimed CHECK (ownership_status <> 'unclaimed' OR activated_at IS NULL),
	CONSTRAINT ck_tag_pairs_revocation CHECK (revoked_at IS NULL OR ownership_status = 'revoked'),
	CONSTRAINT ck_tag_pairs_version CHECK (row_version > 0),
	CONSTRAINT uq_tag_pairs_pair_reference UNIQUE (pair_reference),
	CONSTRAINT fk_tag_pairs_batch_id FOREIGN KEY(batch_id) REFERENCES qr_batches (id) ON DELETE RESTRICT,
	CONSTRAINT fk_tag_pairs_owner_user_id FOREIGN KEY(owner_user_id) REFERENCES auth.users (id) ON DELETE RESTRICT
)""",
    """CREATE INDEX ix_pair_batch ON tag_pairs (batch_id, inventory_status)""",
    """CREATE INDEX ix_pair_owner ON tag_pairs (owner_user_id, ownership_status)""",
    """ALTER TABLE public.tag_pairs ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.tag_pairs FROM PUBLIC, anon, authenticated""",
    """CREATE TRIGGER sr_touch BEFORE UPDATE ON public.tag_pairs FOR EACH ROW EXECUTE FUNCTION public.sr_touch_updated_at()""",
    """CREATE TABLE pair_activation_credentials (
	pair_id UUID NOT NULL,
	secret_verifier BYTEA NOT NULL,
	verifier_key_version SMALLINT NOT NULL,
	status VARCHAR(20) DEFAULT 'unused' NOT NULL,
	failed_attempts INTEGER DEFAULT '0' NOT NULL,
	locked_until TIMESTAMP WITH TIME ZONE,
	consumed_at TIMESTAMP WITH TIME ZONE,
	rotated_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_pair_activation_credentials PRIMARY KEY (pair_id),
	CONSTRAINT ck_pair_activation_credentials_status CHECK (status IN ('unused','locked','consumed','revoked')),
	CONSTRAINT ck_pair_activation_credentials_verifier CHECK (verifier_key_version > 0 AND octet_length(secret_verifier) > 0),
	CONSTRAINT ck_pair_activation_credentials_attempts CHECK (failed_attempts >= 0),
	CONSTRAINT ck_pair_activation_credentials_consumed CHECK (status <> 'consumed' OR consumed_at IS NOT NULL),
	CONSTRAINT fk_pair_activation_credentials_pair_id FOREIGN KEY(pair_id) REFERENCES tag_pairs (id) ON DELETE RESTRICT
)""",
    """ALTER TABLE public.pair_activation_credentials ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.pair_activation_credentials FROM PUBLIC, anon, authenticated""",
    """CREATE TRIGGER sr_touch BEFORE UPDATE ON public.pair_activation_credentials FOR EACH ROW EXECUTE FUNCTION public.sr_touch_updated_at()""",
    """CREATE TABLE qr_codes (
	pair_id UUID NOT NULL,
	tag_type VARCHAR(8) NOT NULL,
	serial_number VARCHAR(50) NOT NULL,
	public_token VARCHAR(80) NOT NULL,
	public_status VARCHAR(24) DEFAULT 'unactivated' NOT NULL,
	is_current BOOLEAN DEFAULT true NOT NULL,
	replaces_qr_id UUID,
	ecc_level VARCHAR(1) NOT NULL,
	qr_version SMALLINT,
	printed_size_mm NUMERIC(5, 2),
	revoked_at TIMESTAMP WITH TIME ZONE,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_qr_codes PRIMARY KEY (id),
	CONSTRAINT ck_qr_codes_type CHECK (tag_type IN ('lost','ice')),
	CONSTRAINT ck_qr_codes_status CHECK (public_status IN ('unactivated','active','owner_disabled','admin_suspended','revoked')),
	CONSTRAINT ck_qr_codes_ecc CHECK (ecc_level IN ('M','Q')),
	CONSTRAINT ck_qr_codes_revocation CHECK (public_status <> 'revoked' OR revoked_at IS NOT NULL),
	CONSTRAINT ck_qr_codes_replacement_self CHECK (replaces_qr_id <> id),
	CONSTRAINT ck_qr_codes_qr_version CHECK (qr_version BETWEEN 1 AND 40),
	CONSTRAINT ck_qr_codes_size CHECK (printed_size_mm > 0),
	CONSTRAINT fk_qr_codes_pair_id FOREIGN KEY(pair_id) REFERENCES tag_pairs (id) ON DELETE RESTRICT,
	CONSTRAINT uq_qr_codes_serial_number UNIQUE (serial_number),
	CONSTRAINT uq_qr_codes_public_token UNIQUE (public_token),
	CONSTRAINT fk_qr_codes_replaces_qr_id FOREIGN KEY(replaces_qr_id) REFERENCES qr_codes (id) ON DELETE RESTRICT
)""",
    """CREATE UNIQUE INDEX uq_current_pair_tag_type ON qr_codes (pair_id, tag_type) WHERE is_current""",
    """CREATE UNIQUE INDEX uq_qr_replacement ON qr_codes (replaces_qr_id) WHERE replaces_qr_id IS NOT NULL""",
    """ALTER TABLE public.qr_codes ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.qr_codes FROM PUBLIC, anon, authenticated""",
    """CREATE TRIGGER sr_touch BEFORE UPDATE ON public.qr_codes FOR EACH ROW EXECUTE FUNCTION public.sr_touch_updated_at()""",
    """CREATE TABLE ice_profiles (
	display_name VARCHAR(120),
	blood_group VARCHAR(8),
	emergency_instructions TEXT,
	medical_notes_ciphertext BYTEA,
	medical_notes_key_version SMALLINT,
	show_medical_notes BOOLEAN DEFAULT false NOT NULL,
	publication_consent_at TIMESTAMP WITH TIME ZONE,
	publication_consent_version VARCHAR(30),
	qr_id UUID NOT NULL,
	profile_version INTEGER DEFAULT '1' NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	published BOOLEAN DEFAULT false NOT NULL,
	CONSTRAINT pk_ice_profiles PRIMARY KEY (qr_id),
	CONSTRAINT ck_ice_profiles_version CHECK (profile_version > 0),
	CONSTRAINT ck_ice_profiles_blood_group CHECK (blood_group IN ('A+','A-','B+','B-','AB+','AB-','O+','O-')),
	CONSTRAINT ck_ice_profiles_medical_key CHECK ((medical_notes_ciphertext IS NULL AND medical_notes_key_version IS NULL) OR (medical_notes_ciphertext IS NOT NULL AND medical_notes_key_version IS NOT NULL AND medical_notes_key_version > 0)),
	CONSTRAINT ck_ice_profiles_consent CHECK (NOT published OR (publication_consent_at IS NOT NULL AND publication_consent_version IS NOT NULL)),
	CONSTRAINT ck_ice_profiles_medical_consent CHECK (NOT show_medical_notes OR (medical_notes_ciphertext IS NOT NULL AND publication_consent_at IS NOT NULL AND publication_consent_version IS NOT NULL)),
	CONSTRAINT fk_ice_profiles_qr_id FOREIGN KEY(qr_id) REFERENCES qr_codes (id) ON DELETE RESTRICT
)""",
    """ALTER TABLE public.ice_profiles ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.ice_profiles FROM PUBLIC, anon, authenticated""",
    """CREATE TRIGGER sr_touch BEFORE UPDATE ON public.ice_profiles FOR EACH ROW EXECUTE FUNCTION public.sr_touch_updated_at()""",
    """CREATE TABLE lost_item_profiles (
	item_label VARCHAR(120),
	description TEXT,
	reward_text VARCHAR(200),
	return_instructions TEXT,
	published_at TIMESTAMP WITH TIME ZONE,
	qr_id UUID NOT NULL,
	profile_version INTEGER DEFAULT '1' NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	published BOOLEAN DEFAULT false NOT NULL,
	CONSTRAINT pk_lost_item_profiles PRIMARY KEY (qr_id),
	CONSTRAINT ck_lost_item_profiles_version CHECK (profile_version > 0),
	CONSTRAINT fk_lost_item_profiles_qr_id FOREIGN KEY(qr_id) REFERENCES qr_codes (id) ON DELETE RESTRICT
)""",
    """ALTER TABLE public.lost_item_profiles ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.lost_item_profiles FROM PUBLIC, anon, authenticated""",
    """CREATE TRIGGER sr_touch BEFORE UPDATE ON public.lost_item_profiles FOR EACH ROW EXECUTE FUNCTION public.sr_touch_updated_at()""",
    """CREATE TABLE tag_contact_preferences (
	qr_id UUID NOT NULL,
	whatsapp_enabled BOOLEAN DEFAULT false NOT NULL,
	whatsapp_phone_ciphertext BYTEA,
	whatsapp_phone_key_version SMALLINT,
	whatsapp_consent_at TIMESTAMP WITH TIME ZONE,
	whatsapp_consent_version VARCHAR(30),
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_tag_contact_preferences PRIMARY KEY (qr_id),
	CONSTRAINT ck_tag_contact_preferences_whatsapp_consent CHECK (NOT whatsapp_enabled OR (whatsapp_phone_ciphertext IS NOT NULL AND whatsapp_phone_key_version IS NOT NULL AND whatsapp_phone_key_version > 0 AND whatsapp_consent_at IS NOT NULL AND whatsapp_consent_version IS NOT NULL)),
	CONSTRAINT fk_tag_contact_preferences_qr_id FOREIGN KEY(qr_id) REFERENCES qr_codes (id) ON DELETE RESTRICT
)""",
    """ALTER TABLE public.tag_contact_preferences ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.tag_contact_preferences FROM PUBLIC, anon, authenticated""",
    """CREATE TRIGGER sr_touch BEFORE UPDATE ON public.tag_contact_preferences FOR EACH ROW EXECUTE FUNCTION public.sr_touch_updated_at()""",
    """CREATE TABLE ice_contacts (
	ice_qr_id UUID NOT NULL,
	relationship_label VARCHAR(60) NOT NULL,
	display_name VARCHAR(120),
	phone_ciphertext BYTEA NOT NULL,
	phone_key_version SMALLINT NOT NULL,
	display_order SMALLINT DEFAULT '0' NOT NULL,
	published BOOLEAN DEFAULT false NOT NULL,
	publication_consent_at TIMESTAMP WITH TIME ZONE,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_ice_contacts PRIMARY KEY (id),
	CONSTRAINT ck_ice_contacts_phone CHECK (phone_key_version > 0 AND octet_length(phone_ciphertext) > 0),
	CONSTRAINT ck_ice_contacts_display_order CHECK (display_order >= 0),
	CONSTRAINT ck_ice_contacts_consent CHECK (NOT published OR publication_consent_at IS NOT NULL),
	CONSTRAINT fk_ice_contacts_ice_qr_id FOREIGN KEY(ice_qr_id) REFERENCES ice_profiles (qr_id) ON DELETE RESTRICT
)""",
    """CREATE INDEX ix_ice_contact_display ON ice_contacts (ice_qr_id, published, display_order)""",
    """ALTER TABLE public.ice_contacts ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.ice_contacts FROM PUBLIC, anon, authenticated""",
    """CREATE TRIGGER sr_touch BEFORE UPDATE ON public.ice_contacts FOR EACH ROW EXECUTE FUNCTION public.sr_touch_updated_at()""",
    """-- Immediate parent locks serialize child mutations, including transactions that
-- began before a competing activation/replacement committed. Identity fields
-- cannot be moved between pairs or purposes and invalidate existing profiles.
CREATE FUNCTION public.sr_guard_qr() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
BEGIN
 IF TG_OP = 'DELETE' THEN
  PERFORM 1 FROM public.tag_pairs WHERE id = OLD.pair_id FOR UPDATE;
  RETURN OLD;
 END IF;
 PERFORM 1 FROM public.tag_pairs WHERE id = NEW.pair_id FOR UPDATE;
 IF TG_OP = 'UPDATE' AND
    (NEW.id, NEW.pair_id, NEW.tag_type, NEW.public_token, NEW.serial_number, NEW.replaces_qr_id)
    IS DISTINCT FROM
    (OLD.id, OLD.pair_id, OLD.tag_type, OLD.public_token, OLD.serial_number, OLD.replaces_qr_id) THEN
  RAISE EXCEPTION 'QR identity fields are immutable' USING ERRCODE = '23514';
 END IF;
 IF NEW.replaces_qr_id IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM public.qr_codes q WHERE q.id = NEW.replaces_qr_id
    AND q.pair_id = NEW.pair_id AND q.tag_type = NEW.tag_type
    AND NOT q.is_current AND q.public_status = 'revoked'
 ) THEN
  RAISE EXCEPTION 'Invalid QR replacement relationship' USING ERRCODE = '23514';
 END IF;
 RETURN NEW;
END $$;

CREATE TRIGGER sr_guard_qr BEFORE INSERT OR UPDATE OR DELETE ON public.qr_codes
FOR EACH ROW EXECUTE FUNCTION public.sr_guard_qr();

CREATE FUNCTION public.sr_check_pair() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE pid uuid; n integer;
BEGIN
 IF TG_TABLE_NAME = 'tag_pairs' THEN pid := NEW.id;
 ELSIF TG_OP = 'DELETE' THEN pid := OLD.pair_id;
 ELSE pid := NEW.pair_id;
 END IF;
 PERFORM 1 FROM public.tag_pairs WHERE id = pid FOR UPDATE;
 IF NOT FOUND THEN RETURN NULL; END IF;
 SELECT count(*) INTO n FROM public.qr_codes WHERE pair_id = pid AND is_current;
 -- The type CHECK and partial uniqueness imply one lost and one ice when n=2.
 IF n <> 2 THEN
  RAISE EXCEPTION 'Pair requires one current Lost and one current ICE QR' USING ERRCODE = '23514';
 END IF;
 RETURN NULL;
END $$;

CREATE CONSTRAINT TRIGGER sr_pair_exactly_two
AFTER INSERT OR UPDATE ON public.tag_pairs DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION public.sr_check_pair();

CREATE CONSTRAINT TRIGGER sr_qr_exactly_two
AFTER INSERT OR UPDATE OR DELETE ON public.qr_codes DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION public.sr_check_pair();

CREATE FUNCTION public.sr_profile_type() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE purpose text;
BEGIN
 SELECT tag_type INTO purpose FROM public.qr_codes WHERE id = NEW.qr_id FOR SHARE;
 IF purpose IS DISTINCT FROM TG_ARGV[0] THEN
  RAISE EXCEPTION 'Profile purpose does not match QR identity' USING ERRCODE = '23514';
 END IF;
 RETURN NEW;
END $$;

CREATE TRIGGER sr_lost_profile_type BEFORE INSERT OR UPDATE ON public.lost_item_profiles
FOR EACH ROW EXECUTE FUNCTION public.sr_profile_type('lost');
CREATE TRIGGER sr_ice_profile_type BEFORE INSERT OR UPDATE ON public.ice_profiles
FOR EACH ROW EXECUTE FUNCTION public.sr_profile_type('ice');
CREATE TRIGGER sr_whatsapp_type BEFORE INSERT OR UPDATE ON public.tag_contact_preferences
FOR EACH ROW EXECUTE FUNCTION public.sr_profile_type('lost');""",
]


def upgrade():
    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names(schema="public"))
    if existing.intersection(TABLES):
        raise RuntimeError(
            "Existing domain tables require explicit reconciliation; nothing changed"
        )
    if not inspect(bind).has_table("users", schema="auth"):
        raise RuntimeError("Managed Supabase auth.users is required")
    if (
        bind.execute(
            text(
                "SELECT count(*) FROM information_schema.columns WHERE table_schema='auth' AND table_name='users' AND column_name='id' AND data_type='uuid'"
            )
        ).scalar_one()
        != 1
    ):
        raise RuntimeError("Supabase auth.users.id must be UUID")
    op.execute("SET LOCAL lock_timeout = '5s'")
    for statement in DDL:
        op.execute(statement)


def downgrade():
    raise RuntimeError("Destructive downgrade disabled; author a reviewed forward fix")
