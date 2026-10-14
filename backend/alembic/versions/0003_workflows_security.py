"""Add durable/private workflows and fail-closed API/worker role separation.

No passwords in migration. Existing rows and history are preserved.
Cross-table integrity triggers become pinned-path definers to survive RLS.
"""

from sqlalchemy import inspect, text

from alembic import op

revision = "0003_workflows_security"
down_revision = "0002_commerce"
branch_labels = None
depends_on = None

TABLES = [
    "audit_events",
    "idempotency_records",
    "notification_outbox",
    "retention_holds",
    "finance_sheet_sync",
    "notification_attempts",
    "print_jobs",
    "durable_jobs",
    "print_artifacts",
    "support_cases",
    "finder_messages",
    "scan_contexts",
    "activation_intents",
    "finder_message_locations",
]
ROLES = [
    "safereturn_api",
    "safereturn_worker",
    "safereturn_api_login",
    "safereturn_worker_login",
]
DDL = [
    """CREATE TABLE audit_events (
	actor_user_id UUID,
	actor_kind VARCHAR(20) NOT NULL,
	action VARCHAR(100) NOT NULL,
	target_type VARCHAR(60) NOT NULL,
	target_id UUID,
	request_id VARCHAR(100),
	reason TEXT,
	safe_details JSONB DEFAULT '{}'::jsonb NOT NULL,
	occurred_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	CONSTRAINT pk_audit_events PRIMARY KEY (id),
	CONSTRAINT ck_audit_events_actor CHECK (actor_kind IN ('customer','staff','system','anonymous')),
	CONSTRAINT ck_audit_events_details CHECK (jsonb_typeof(safe_details)='object'),
	CONSTRAINT fk_audit_events_actor_user_id FOREIGN KEY(actor_user_id) REFERENCES auth.users (id) ON DELETE RESTRICT
)""",
    """CREATE INDEX idx_audit_actor ON audit_events (actor_user_id, occurred_at DESC)""",
    """CREATE INDEX idx_audit_target ON audit_events (target_type, target_id, occurred_at DESC)""",
    """ALTER TABLE public.audit_events ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.audit_events FROM PUBLIC,anon,authenticated""",
    """CREATE TABLE idempotency_records (
	actor_scope VARCHAR(100) NOT NULL,
	actor_user_id UUID,
	operation VARCHAR(80) NOT NULL,
	idempotency_key VARCHAR(160) NOT NULL,
	request_hash VARCHAR(64) NOT NULL,
	response_status INTEGER,
	response_body_ciphertext BYTEA,
	response_key_version SMALLINT,
	state VARCHAR(20) DEFAULT 'processing' NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_idempotency_records PRIMARY KEY (id),
	CONSTRAINT uq_idempotency_records_actor_scope UNIQUE (actor_scope, operation, idempotency_key),
	CONSTRAINT ck_idempotency_records_request_hash CHECK (request_hash ~ '^[0-9a-f]{64}$'),
	CONSTRAINT ck_idempotency_records_state CHECK (state IN ('processing','completed','failed')),
	CONSTRAINT ck_idempotency_records_expiry CHECK (expires_at>created_at),
	CONSTRAINT ck_idempotency_records_response_status CHECK (response_status BETWEEN 100 AND 599),
	CONSTRAINT ck_idempotency_records_response_key CHECK ((response_body_ciphertext IS NULL AND response_key_version IS NULL) OR (response_body_ciphertext IS NOT NULL AND response_key_version IS NOT NULL AND response_key_version>0)),
	CONSTRAINT fk_idempotency_records_actor_user_id FOREIGN KEY(actor_user_id) REFERENCES auth.users (id) ON DELETE RESTRICT
)""",
    """ALTER TABLE public.idempotency_records ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.idempotency_records FROM PUBLIC,anon,authenticated""",
    """CREATE TABLE notification_outbox (
	event_type VARCHAR(60) NOT NULL,
	aggregate_type VARCHAR(40) NOT NULL,
	aggregate_id UUID NOT NULL,
	recipient_user_id UUID,
	recipient_email_snapshot_ciphertext BYTEA,
	recipient_email_key_version SMALLINT,
	payload_version SMALLINT DEFAULT '1' NOT NULL,
	status VARCHAR(16) DEFAULT 'pending' NOT NULL,
	provider_message_id VARCHAR(150),
	idempotency_key VARCHAR(160) NOT NULL,
	sent_at TIMESTAMP WITH TIME ZONE,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	payload_ciphertext BYTEA,
	payload_key_version SMALLINT,
	attempt_count INTEGER DEFAULT '0' NOT NULL,
	next_attempt_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	lease_owner VARCHAR(100),
	lease_until TIMESTAMP WITH TIME ZONE,
	last_error_code VARCHAR(80),
	CONSTRAINT pk_notification_outbox PRIMARY KEY (id),
	CONSTRAINT ck_notification_outbox_status CHECK (status IN ('pending','leased','retry','sent','dead')),
	CONSTRAINT ck_notification_outbox_versions CHECK (attempt_count>=0 AND payload_version>0),
	CONSTRAINT ck_notification_outbox_lease CHECK ((status='leased' AND lease_owner IS NOT NULL AND lease_until IS NOT NULL) OR (status<>'leased' AND lease_owner IS NULL AND lease_until IS NULL)),
	CONSTRAINT ck_notification_outbox_payload_key CHECK ((payload_ciphertext IS NULL AND payload_key_version IS NULL) OR (payload_ciphertext IS NOT NULL AND octet_length(payload_ciphertext)>0 AND payload_key_version IS NOT NULL AND payload_key_version>0)),
	CONSTRAINT ck_notification_outbox_email_key CHECK ((recipient_email_snapshot_ciphertext IS NULL AND recipient_email_key_version IS NULL) OR (recipient_email_snapshot_ciphertext IS NOT NULL AND recipient_email_key_version IS NOT NULL AND recipient_email_key_version>0)),
	CONSTRAINT ck_notification_outbox_sent CHECK (status<>'sent' OR sent_at IS NOT NULL),
	CONSTRAINT fk_notification_outbox_recipient_user_id FOREIGN KEY(recipient_user_id) REFERENCES auth.users (id) ON DELETE RESTRICT,
	CONSTRAINT uq_notification_outbox_idempotency_key UNIQUE (idempotency_key)
)""",
    """CREATE INDEX idx_outbox_aggregate ON notification_outbox (aggregate_type, aggregate_id)""",
    """CREATE INDEX idx_outbox_due ON notification_outbox (next_attempt_at, created_at) WHERE status IN ('pending','retry')""",
    """CREATE INDEX idx_outbox_lease ON notification_outbox (lease_until) WHERE status='leased'""",
    """ALTER TABLE public.notification_outbox ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.notification_outbox FROM PUBLIC,anon,authenticated""",
    """CREATE TABLE retention_holds (
	resource_type VARCHAR(40) NOT NULL,
	resource_id UUID NOT NULL,
	reason_code VARCHAR(80) NOT NULL,
	placed_by UUID NOT NULL,
	released_by UUID,
	released_at TIMESTAMP WITH TIME ZONE,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_retention_holds PRIMARY KEY (id),
	CONSTRAINT ck_retention_holds_resource CHECK (resource_type IN ('order','finder_message','print_artifact','payment_evidence')),
	CONSTRAINT ck_retention_holds_reason CHECK (reason_code ~ '^[a-zA-Z0-9_.-]+$'),
	CONSTRAINT ck_retention_holds_release CHECK ((released_at IS NULL AND released_by IS NULL) OR (released_at IS NOT NULL AND released_by IS NOT NULL)),
	CONSTRAINT fk_retention_holds_placed_by FOREIGN KEY(placed_by) REFERENCES auth.users (id) ON DELETE RESTRICT,
	CONSTRAINT fk_retention_holds_released_by FOREIGN KEY(released_by) REFERENCES auth.users (id) ON DELETE RESTRICT
)""",
    """CREATE INDEX idx_retention_active ON retention_holds (resource_type, resource_id) WHERE released_at IS NULL""",
    """ALTER TABLE public.retention_holds ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.retention_holds FROM PUBLIC,anon,authenticated""",
    """CREATE TABLE finance_sheet_sync (
	order_id UUID NOT NULL,
	sheet_row_key TEXT,
	last_export_version INTEGER DEFAULT '0' NOT NULL,
	status TEXT DEFAULT 'pending' NOT NULL,
	attempt_count INTEGER DEFAULT '0' NOT NULL,
	last_error_code VARCHAR(80),
	last_synced_at TIMESTAMP WITH TIME ZONE,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	CONSTRAINT pk_finance_sheet_sync PRIMARY KEY (id),
	CONSTRAINT ck_finance_sheet_sync_status CHECK (status IN ('pending','synced','retry','failed')),
	CONSTRAINT ck_finance_sheet_sync_versions CHECK (last_export_version>=0 AND attempt_count>=0),
	CONSTRAINT uq_finance_sheet_sync_order_id UNIQUE (order_id),
	CONSTRAINT fk_finance_sheet_sync_order_id FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE RESTRICT
)""",
    """ALTER TABLE public.finance_sheet_sync ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.finance_sheet_sync FROM PUBLIC,anon,authenticated""",
    """CREATE TRIGGER sr_touch BEFORE UPDATE ON public.finance_sheet_sync FOR EACH ROW EXECUTE FUNCTION public.sr_touch_updated_at()""",
    """CREATE TABLE notification_attempts (
	outbox_id UUID NOT NULL,
	attempt_number INTEGER NOT NULL,
	attempted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	finished_at TIMESTAMP WITH TIME ZONE,
	outcome VARCHAR(20) DEFAULT 'unknown' NOT NULL,
	provider_message_id VARCHAR(150),
	error_code VARCHAR(80),
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	CONSTRAINT pk_notification_attempts PRIMARY KEY (id),
	CONSTRAINT uq_notification_attempts_outbox_id UNIQUE (outbox_id, attempt_number),
	CONSTRAINT ck_notification_attempts_attempt CHECK (attempt_number>0),
	CONSTRAINT ck_notification_attempts_outcome CHECK (outcome IN ('success','transient_failure','permanent_failure','unknown')),
	CONSTRAINT fk_notification_attempts_outbox_id FOREIGN KEY(outbox_id) REFERENCES notification_outbox (id) ON DELETE RESTRICT
)""",
    """ALTER TABLE public.notification_attempts ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.notification_attempts FROM PUBLIC,anon,authenticated""",
    """CREATE TABLE print_jobs (
	order_id UUID NOT NULL,
	job_revision INTEGER NOT NULL,
	status TEXT DEFAULT 'queued' NOT NULL,
	template_fingerprint TEXT NOT NULL,
	render_config JSONB NOT NULL,
	attempt_count INTEGER DEFAULT '0' NOT NULL,
	failure_code VARCHAR(80),
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_print_jobs PRIMARY KEY (id),
	CONSTRAINT uq_print_jobs_order_id UNIQUE (order_id, job_revision),
	CONSTRAINT ck_print_jobs_versions CHECK (job_revision>0 AND attempt_count>=0),
	CONSTRAINT ck_print_jobs_status CHECK (status IN ('queued','rendering','ready','downloaded','qa_passed','failed','superseded','deleted')),
	CONSTRAINT ck_print_jobs_config CHECK (jsonb_typeof(render_config)='object'),
	CONSTRAINT fk_print_jobs_order_id FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE RESTRICT
)""",
    """CREATE INDEX idx_print_jobs_order ON print_jobs (order_id, created_at)""",
    """ALTER TABLE public.print_jobs ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.print_jobs FROM PUBLIC,anon,authenticated""",
    """CREATE TRIGGER sr_touch BEFORE UPDATE ON public.print_jobs FOR EACH ROW EXECUTE FUNCTION public.sr_touch_updated_at()""",
    """CREATE TABLE durable_jobs (
	job_kind VARCHAR(40) NOT NULL,
	aggregate_type VARCHAR(40) NOT NULL,
	aggregate_id UUID NOT NULL,
	order_id UUID,
	print_job_id UUID,
	status VARCHAR(16) DEFAULT 'pending' NOT NULL,
	idempotency_key VARCHAR(160) NOT NULL,
	completed_at TIMESTAMP WITH TIME ZONE,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	payload_ciphertext BYTEA,
	payload_key_version SMALLINT,
	attempt_count INTEGER DEFAULT '0' NOT NULL,
	next_attempt_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	lease_owner VARCHAR(100),
	lease_until TIMESTAMP WITH TIME ZONE,
	last_error_code VARCHAR(80),
	CONSTRAINT pk_durable_jobs PRIMARY KEY (id),
	CONSTRAINT ck_durable_jobs_kind CHECK (job_kind IN ('allocation.finalize','print.render','finance.sync','retention.cleanup')),
	CONSTRAINT ck_durable_jobs_status CHECK (status IN ('pending','leased','retry','completed','dead')),
	CONSTRAINT ck_durable_jobs_attempts CHECK (attempt_count>=0),
	CONSTRAINT ck_durable_jobs_lease CHECK ((status='leased' AND lease_owner IS NOT NULL AND lease_until IS NOT NULL) OR (status<>'leased' AND lease_owner IS NULL AND lease_until IS NULL)),
	CONSTRAINT ck_durable_jobs_payload_key CHECK ((payload_ciphertext IS NULL AND payload_key_version IS NULL) OR (payload_ciphertext IS NOT NULL AND octet_length(payload_ciphertext)>0 AND payload_key_version IS NOT NULL AND payload_key_version>0)),
	CONSTRAINT ck_durable_jobs_completion CHECK (status<>'completed' OR completed_at IS NOT NULL),
	CONSTRAINT ck_durable_jobs_order CHECK (job_kind='retention.cleanup' OR order_id IS NOT NULL),
	CONSTRAINT ck_durable_jobs_print_job CHECK (job_kind<>'print.render' OR print_job_id IS NOT NULL),
	CONSTRAINT fk_durable_jobs_order_id FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE RESTRICT,
	CONSTRAINT fk_durable_jobs_print_job_id FOREIGN KEY(print_job_id) REFERENCES print_jobs (id) ON DELETE RESTRICT,
	CONSTRAINT uq_durable_jobs_idempotency_key UNIQUE (idempotency_key)
)""",
    """CREATE INDEX idx_jobs_due ON durable_jobs (next_attempt_at, created_at) WHERE status IN ('pending','retry')""",
    """CREATE INDEX idx_jobs_lease ON durable_jobs (lease_until) WHERE status='leased'""",
    """ALTER TABLE public.durable_jobs ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.durable_jobs FROM PUBLIC,anon,authenticated""",
    """CREATE TABLE print_artifacts (
	print_job_id UUID NOT NULL,
	bucket TEXT DEFAULT 'private-order-print' NOT NULL,
	object_key TEXT NOT NULL,
	format TEXT NOT NULL,
	sha256_hex VARCHAR(64) NOT NULL,
	size_bytes BIGINT NOT NULL,
	retention_until TIMESTAMP WITH TIME ZONE,
	deletion_hold_reason TEXT,
	deleted_at TIMESTAMP WITH TIME ZONE,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_print_artifacts PRIMARY KEY (id),
	CONSTRAINT ck_print_artifacts_bucket CHECK (bucket='private-order-print'),
	CONSTRAINT ck_print_artifacts_format CHECK (format IN ('pdf','svg','other_approved')),
	CONSTRAINT ck_print_artifacts_integrity CHECK (sha256_hex ~ '^[0-9a-f]{64}$' AND size_bytes>0),
	CONSTRAINT fk_print_artifacts_print_job_id FOREIGN KEY(print_job_id) REFERENCES print_jobs (id) ON DELETE RESTRICT,
	CONSTRAINT uq_print_artifacts_object_key UNIQUE (object_key)
)""",
    """CREATE INDEX idx_artifacts_cleanup ON print_artifacts (retention_until) WHERE deleted_at IS NULL""",
    """ALTER TABLE public.print_artifacts ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.print_artifacts FROM PUBLIC,anon,authenticated""",
    """CREATE TABLE support_cases (
	pair_id UUID,
	order_id UUID,
	opened_by_user_id UUID,
	case_type VARCHAR(40) NOT NULL,
	status VARCHAR(20) DEFAULT 'open' NOT NULL,
	assigned_staff_id UUID,
	description_ciphertext BYTEA,
	description_key_version SMALLINT,
	closed_at TIMESTAMP WITH TIME ZONE,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_support_cases PRIMARY KEY (id),
	CONSTRAINT ck_support_cases_type CHECK (case_type IN ('activation','lost_tag','payment','privacy','ownership_dispute','other')),
	CONSTRAINT ck_support_cases_status CHECK (status IN ('open','investigating','resolved','closed')),
	CONSTRAINT ck_support_cases_description_key CHECK ((description_ciphertext IS NULL AND description_key_version IS NULL) OR (description_ciphertext IS NOT NULL AND description_key_version IS NOT NULL AND description_key_version>0)),
	CONSTRAINT fk_support_cases_pair_id FOREIGN KEY(pair_id) REFERENCES tag_pairs (id) ON DELETE RESTRICT,
	CONSTRAINT fk_support_cases_order_id FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE RESTRICT,
	CONSTRAINT fk_support_cases_opened_by_user_id FOREIGN KEY(opened_by_user_id) REFERENCES auth.users (id) ON DELETE RESTRICT,
	CONSTRAINT fk_support_cases_assigned_staff_id FOREIGN KEY(assigned_staff_id) REFERENCES auth.users (id) ON DELETE RESTRICT
)""",
    """ALTER TABLE public.support_cases ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.support_cases FROM PUBLIC,anon,authenticated""",
    """CREATE TABLE finder_messages (
	qr_id UUID NOT NULL,
	recipient_owner_user_id UUID NOT NULL,
	finder_name VARCHAR(80),
	finder_email_ciphertext BYTEA,
	finder_phone_ciphertext BYTEA,
	finder_contact_key_version SMALLINT NOT NULL,
	preferred_contact VARCHAR(12),
	message_text_ciphertext BYTEA NOT NULL,
	message_key_version SMALLINT NOT NULL,
	status VARCHAR(24) DEFAULT 'new' NOT NULL,
	abuse_flag BOOLEAN DEFAULT false NOT NULL,
	consent_version VARCHAR(30) NOT NULL,
	consent_at TIMESTAMP WITH TIME ZONE NOT NULL,
	submitted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	deleted_at TIMESTAMP WITH TIME ZONE,
	retention_until TIMESTAMP WITH TIME ZONE,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	CONSTRAINT pk_finder_messages PRIMARY KEY (id),
	CONSTRAINT ck_finder_messages_status CHECK (status IN ('new','viewed','archived','flagged','deleted')),
	CONSTRAINT ck_finder_messages_preferred_contact CHECK (preferred_contact IN ('email','phone')),
	CONSTRAINT ck_finder_messages_contact CHECK (finder_email_ciphertext IS NOT NULL OR finder_phone_ciphertext IS NOT NULL),
	CONSTRAINT ck_finder_messages_encryption CHECK (finder_contact_key_version > 0 AND message_key_version > 0 AND octet_length(message_text_ciphertext) > 0),
	CONSTRAINT ck_finder_messages_email CHECK (finder_email_ciphertext IS NULL OR octet_length(finder_email_ciphertext) > 0),
	CONSTRAINT ck_finder_messages_phone CHECK (finder_phone_ciphertext IS NULL OR octet_length(finder_phone_ciphertext) > 0),
	CONSTRAINT ck_finder_messages_consent CHECK (length(consent_version) > 0),
	CONSTRAINT fk_finder_messages_qr_id FOREIGN KEY(qr_id) REFERENCES qr_codes (id) ON DELETE RESTRICT,
	CONSTRAINT fk_finder_messages_recipient_owner_user_id FOREIGN KEY(recipient_owner_user_id) REFERENCES auth.users (id) ON DELETE RESTRICT
)""",
    """CREATE INDEX idx_finder_qr ON finder_messages (qr_id, submitted_at DESC)""",
    """CREATE INDEX idx_finder_recipient ON finder_messages (recipient_owner_user_id, submitted_at DESC)""",
    """ALTER TABLE public.finder_messages ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.finder_messages FROM PUBLIC,anon,authenticated""",
    """CREATE TABLE scan_contexts (
	qr_code_id UUID NOT NULL,
	public_token_digest VARCHAR(64) NOT NULL,
	session_binding_digest VARCHAR(64) NOT NULL,
	bound_actor_user_id UUID,
	state VARCHAR(16) DEFAULT 'pending' NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	consumed_at TIMESTAMP WITH TIME ZONE,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_scan_contexts PRIMARY KEY (id),
	CONSTRAINT ck_scan_contexts_digests CHECK (public_token_digest ~ '^[0-9a-f]{64}$' AND session_binding_digest ~ '^[0-9a-f]{64}$'),
	CONSTRAINT ck_scan_contexts_state CHECK (state IN ('pending','consumed','expired','revoked')),
	CONSTRAINT ck_scan_contexts_expiry CHECK (expires_at>created_at),
	CONSTRAINT ck_scan_contexts_consumption CHECK (state<>'consumed' OR (consumed_at IS NOT NULL AND bound_actor_user_id IS NOT NULL)),
	CONSTRAINT fk_scan_contexts_qr_code_id FOREIGN KEY(qr_code_id) REFERENCES qr_codes (id) ON DELETE RESTRICT,
	CONSTRAINT fk_scan_contexts_bound_actor_user_id FOREIGN KEY(bound_actor_user_id) REFERENCES auth.users (id) ON DELETE RESTRICT
)""",
    """CREATE INDEX idx_scan_expiry ON scan_contexts (expires_at) WHERE state='pending'""",
    """ALTER TABLE public.scan_contexts ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.scan_contexts FROM PUBLIC,anon,authenticated""",
    """CREATE TABLE activation_intents (
	actor_user_id UUID NOT NULL,
	pair_id UUID NOT NULL,
	lost_qr_id UUID NOT NULL,
	ice_qr_id UUID NOT NULL,
	scan_context_id UUID,
	method VARCHAR(24) NOT NULL,
	order_pair_unit_id UUID,
	verifier_key_version SMALLINT,
	state VARCHAR(16) DEFAULT 'pending' NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	consumed_at TIMESTAMP WITH TIME ZONE,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_activation_intents PRIMARY KEY (id),
	CONSTRAINT ck_activation_intents_method CHECK (method IN ('order_entitlement','concealed_credential')),
	CONSTRAINT ck_activation_intents_entitlement CHECK ((method='order_entitlement' AND order_pair_unit_id IS NOT NULL AND verifier_key_version IS NULL) OR (method='concealed_credential' AND order_pair_unit_id IS NULL AND verifier_key_version IS NOT NULL AND verifier_key_version>0)),
	CONSTRAINT ck_activation_intents_state CHECK (state IN ('pending','consumed','expired','revoked')),
	CONSTRAINT ck_activation_intents_distinct_tags CHECK (lost_qr_id<>ice_qr_id),
	CONSTRAINT ck_activation_intents_expiry CHECK (expires_at>created_at),
	CONSTRAINT ck_activation_intents_consumption CHECK (state<>'consumed' OR consumed_at IS NOT NULL),
	CONSTRAINT fk_activation_intents_actor_user_id FOREIGN KEY(actor_user_id) REFERENCES auth.users (id) ON DELETE RESTRICT,
	CONSTRAINT fk_activation_intents_pair_id FOREIGN KEY(pair_id) REFERENCES tag_pairs (id) ON DELETE RESTRICT,
	CONSTRAINT fk_activation_intents_lost_qr_id FOREIGN KEY(lost_qr_id) REFERENCES qr_codes (id) ON DELETE RESTRICT,
	CONSTRAINT fk_activation_intents_ice_qr_id FOREIGN KEY(ice_qr_id) REFERENCES qr_codes (id) ON DELETE RESTRICT,
	CONSTRAINT fk_activation_intents_scan_context_id FOREIGN KEY(scan_context_id) REFERENCES scan_contexts (id) ON DELETE RESTRICT,
	CONSTRAINT fk_activation_intents_order_pair_unit_id FOREIGN KEY(order_pair_unit_id) REFERENCES order_pair_units (id) ON DELETE RESTRICT
)""",
    """CREATE INDEX idx_activation_actor ON activation_intents (actor_user_id, created_at)""",
    """CREATE INDEX idx_activation_expiry ON activation_intents (expires_at) WHERE state='pending'""",
    """ALTER TABLE public.activation_intents ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.activation_intents FROM PUBLIC,anon,authenticated""",
    """CREATE TABLE finder_message_locations (
	finder_message_id UUID NOT NULL,
	latitude_ciphertext BYTEA NOT NULL,
	longitude_ciphertext BYTEA NOT NULL,
	accuracy_m NUMERIC(10, 2),
	location_source VARCHAR(30) DEFAULT 'browser_geolocation' NOT NULL,
	consent_at TIMESTAMP WITH TIME ZONE NOT NULL,
	consent_version VARCHAR(30) NOT NULL,
	key_version SMALLINT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_finder_message_locations PRIMARY KEY (finder_message_id),
	CONSTRAINT ck_finder_message_locations_accuracy CHECK (accuracy_m >= 0),
	CONSTRAINT ck_finder_message_locations_source CHECK (location_source = 'browser_geolocation'),
	CONSTRAINT ck_finder_message_locations_encryption CHECK (key_version > 0 AND octet_length(latitude_ciphertext)>0 AND octet_length(longitude_ciphertext)>0),
	CONSTRAINT ck_finder_message_locations_consent CHECK (length(consent_version)>0),
	CONSTRAINT fk_finder_message_locations_finder_message_id FOREIGN KEY(finder_message_id) REFERENCES finder_messages (id) ON DELETE CASCADE
)""",
    """ALTER TABLE public.finder_message_locations ENABLE ROW LEVEL SECURITY""",
    """REVOKE ALL ON TABLE public.finder_message_locations FROM PUBLIC,anon,authenticated""",
    """-- Frozen role/policy helpers for 0003. Only the trusted API/worker may execute.
CREATE ROLE safereturn_api NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE safereturn_worker NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
-- Passwords are provisioned separately into ignored environment configuration.
CREATE ROLE safereturn_api_login LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE safereturn_worker_login LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT safereturn_api TO safereturn_api_login;
GRANT safereturn_worker TO safereturn_worker_login;
DO $$ BEGIN
 EXECUTE pg_catalog.format('GRANT safereturn_api TO %I',current_user);
 EXECUTE pg_catalog.format('GRANT safereturn_worker TO %I',current_user);
END $$;
GRANT USAGE ON SCHEMA public TO safereturn_api,safereturn_worker;

CREATE FUNCTION public.sr_actor_id() RETURNS uuid LANGUAGE sql STABLE SET search_path=pg_catalog
AS $$ SELECT NULLIF(pg_catalog.current_setting('safereturn.actor_id',true),'')::uuid $$;
CREATE FUNCTION public.sr_mfa() RETURNS boolean LANGUAGE sql STABLE SET search_path=pg_catalog
AS $$ SELECT COALESCE(pg_catalog.current_setting('safereturn.mfa_verified',true)='true',false) $$;
CREATE FUNCTION public.sr_worker_id() RETURNS text LANGUAGE sql STABLE SET search_path=pg_catalog
AS $$ SELECT NULLIF(pg_catalog.current_setting('safereturn.worker_id',true),'') $$;
CREATE FUNCTION public.sr_submission_id() RETURNS uuid LANGUAGE sql STABLE SET search_path=pg_catalog
AS $$ SELECT NULLIF(pg_catalog.current_setting('safereturn.submission_id',true),'')::uuid $$;
CREATE FUNCTION public.sr_scan_binding() RETURNS text LANGUAGE sql STABLE SET search_path=pg_catalog
AS $$ SELECT NULLIF(pg_catalog.current_setting('safereturn.scan_binding',true),'') $$;

CREATE FUNCTION public.sr_is_staff(required_roles text[]) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT public.sr_mfa() AND EXISTS (SELECT 1 FROM public.staff_roles
 WHERE user_id=public.sr_actor_id() AND revoked_at IS NULL AND role=ANY(required_roles))
$$;
CREATE FUNCTION public.sr_owns_pair(pid uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS (SELECT 1 FROM public.tag_pairs WHERE id=pid AND owner_user_id=public.sr_actor_id())
$$;
CREATE FUNCTION public.sr_owns_qr(qid uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS (SELECT 1 FROM public.qr_codes q JOIN public.tag_pairs p ON p.id=q.pair_id
 WHERE q.id=qid AND p.owner_user_id=public.sr_actor_id())
$$;
CREATE FUNCTION public.sr_owns_order(oid uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS (SELECT 1 FROM public.orders WHERE id=oid AND customer_user_id=public.sr_actor_id())
$$;
CREATE FUNCTION public.sr_entitled_pair(pid uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS (SELECT 1 FROM public.order_pair_units u JOIN public.orders o ON o.id=u.order_id
 WHERE u.pair_id=pid AND u.status IN ('reserved','allocated') AND o.customer_user_id=public.sr_actor_id())
$$;
CREATE FUNCTION public.sr_can_message(mid uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS (SELECT 1 FROM public.finder_messages WHERE id=mid AND
 (recipient_owner_user_id=public.sr_actor_id() OR
  (id=public.sr_submission_id() AND submitted_at=pg_catalog.transaction_timestamp())))
$$;
CREATE FUNCTION public.sr_scan_pair(pid uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT public.sr_actor_id() IS NOT NULL AND EXISTS (
 SELECT 1 FROM public.scan_contexts s JOIN public.qr_codes q ON q.id=s.qr_code_id
 WHERE q.pair_id=pid AND s.session_binding_digest=public.sr_scan_binding()
 AND s.bound_actor_user_id=public.sr_actor_id() AND s.expires_at>pg_catalog.now())
$$;
CREATE FUNCTION public.sr_worker_print(jid uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS (SELECT 1 FROM public.durable_jobs WHERE print_job_id=jid AND job_kind='print.render'
 AND status='leased' AND lease_owner=public.sr_worker_id() AND lease_until>pg_catalog.now())
$$;
CREATE FUNCTION public.sr_worker_cleanup(kind text,rid uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS (SELECT 1 FROM public.durable_jobs WHERE job_kind='retention.cleanup'
 AND aggregate_type=kind AND aggregate_id=rid AND status='leased'
 AND lease_owner=public.sr_worker_id() AND lease_until>pg_catalog.now())
$$;
CREATE FUNCTION public.sr_worker_order(oid uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS (SELECT 1 FROM public.durable_jobs WHERE order_id=oid AND status='leased'
 AND lease_owner=public.sr_worker_id() AND lease_until>pg_catalog.now())
$$;""",
    """-- Frozen source for revision 0003_workflows_security.
CREATE FUNCTION public.sr_append_only() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN RAISE EXCEPTION 'Append-only history cannot be changed' USING ERRCODE='23514'; END $$;
CREATE TRIGGER sr_audit_append BEFORE UPDATE OR DELETE ON public.audit_events
FOR EACH ROW EXECUTE FUNCTION public.sr_append_only();

CREATE FUNCTION public.sr_safe_json() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE k text; v jsonb;
BEGIN
 IF TG_TABLE_NAME='audit_events' THEN
  FOR k,v IN SELECT * FROM pg_catalog.jsonb_each(NEW.safe_details) LOOP
   IF k NOT IN ('from_status','to_status','reason_code','version','event_id','outcome')
      OR pg_catalog.jsonb_typeof(v) NOT IN ('string','number','boolean','null') THEN
    RAISE EXCEPTION 'Audit details require approved minimal metadata' USING ERRCODE='23514';
   END IF;
  END LOOP;
 ELSE
  FOR k,v IN SELECT * FROM pg_catalog.jsonb_each(NEW.render_config) LOOP
   IF k NOT IN ('template_key','template_version','locale','dpi','page_size','margin_mm','logo_asset_id')
      OR pg_catalog.jsonb_typeof(v) NOT IN ('string','number','boolean','null') THEN
    RAISE EXCEPTION 'Render configuration must not contain personal data or secrets' USING ERRCODE='23514';
   END IF;
  END LOOP;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_audit_details BEFORE INSERT ON public.audit_events FOR EACH ROW EXECUTE FUNCTION public.sr_safe_json();
CREATE TRIGGER sr_render_config BEFORE INSERT OR UPDATE ON public.print_jobs FOR EACH ROW EXECUTE FUNCTION public.sr_safe_json();

-- Cross-resource guards use a pinned search path and fully-qualified tables.
-- Definer execution is needed for anonymous INSERTs/worker actions whose RLS
-- intentionally hides private parent records. No dynamic SQL or public grants.
CREATE FUNCTION public.sr_finder_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP='INSERT' THEN
  PERFORM 1 FROM public.tag_pairs p JOIN public.qr_codes q ON q.pair_id=p.id
   WHERE q.id=NEW.qr_id AND q.tag_type='lost' AND q.is_current AND q.public_status='active'
    AND p.ownership_status='active' AND p.owner_user_id=NEW.recipient_owner_user_id FOR UPDATE OF p;
  IF NOT FOUND THEN RAISE EXCEPTION 'Message requires active Lost QR and matching recipient' USING ERRCODE='23514'; END IF;
  NEW.submitted_at:=pg_catalog.transaction_timestamp();
 ELSE
  IF (NEW.id,NEW.qr_id,NEW.recipient_owner_user_id,NEW.finder_name,NEW.finder_email_ciphertext,
      NEW.finder_phone_ciphertext,NEW.finder_contact_key_version,NEW.preferred_contact,
      NEW.message_text_ciphertext,NEW.message_key_version,NEW.consent_version,NEW.consent_at,NEW.submitted_at)
     IS DISTINCT FROM
     (OLD.id,OLD.qr_id,OLD.recipient_owner_user_id,OLD.finder_name,OLD.finder_email_ciphertext,
      OLD.finder_phone_ciphertext,OLD.finder_contact_key_version,OLD.preferred_contact,
      OLD.message_text_ciphertext,OLD.message_key_version,OLD.consent_version,OLD.consent_at,OLD.submitted_at) THEN
   RAISE EXCEPTION 'Message recipient and consent/content snapshots are immutable' USING ERRCODE='23514';
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_finder_guard BEFORE INSERT OR UPDATE ON public.finder_messages FOR EACH ROW EXECUTE FUNCTION public.sr_finder_guard();

CREATE FUNCTION public.sr_finder_outbox_check() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE mid uuid;
BEGIN
 IF TG_TABLE_NAME='finder_messages' THEN mid:=NEW.id;
 ELSE
  IF TG_OP='DELETE' THEN
   IF OLD.event_type<>'finder_message.created' THEN RETURN NULL; END IF;
   mid:=OLD.aggregate_id;
  ELSE
   IF NEW.event_type<>'finder_message.created' THEN RETURN NULL; END IF;
   mid:=NEW.aggregate_id;
  END IF;
 END IF;
 IF EXISTS (SELECT 1 FROM public.finder_messages WHERE id=mid) AND NOT EXISTS (
  SELECT 1 FROM public.notification_outbox o JOIN public.finder_messages m ON m.id=o.aggregate_id
   WHERE m.id=mid AND o.event_type='finder_message.created' AND o.aggregate_type='finder_message'
    AND o.recipient_user_id=m.recipient_owner_user_id
 ) THEN RAISE EXCEPTION 'Finder message requires its durable notification event' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER sr_finder_has_outbox AFTER INSERT ON public.finder_messages
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_finder_outbox_check();
CREATE CONSTRAINT TRIGGER sr_outbox_preserves_message AFTER INSERT OR UPDATE OR DELETE ON public.notification_outbox
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_finder_outbox_check();

CREATE FUNCTION public.sr_outbox_relation() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NEW.event_type='finder_message.created' AND NOT EXISTS (
  SELECT 1 FROM public.finder_messages WHERE id=NEW.aggregate_id AND NEW.aggregate_type='finder_message'
   AND recipient_owner_user_id=NEW.recipient_user_id
 ) THEN RAISE EXCEPTION 'Notification recipient/aggregate mismatch' USING ERRCODE='23514'; END IF;
 IF TG_OP='UPDATE' AND (NEW.id,NEW.event_type,NEW.aggregate_type,NEW.aggregate_id,NEW.recipient_user_id,
   NEW.recipient_email_snapshot_ciphertext,NEW.recipient_email_key_version,NEW.payload_ciphertext,
   NEW.payload_key_version,NEW.payload_version,NEW.idempotency_key,NEW.created_at) IS DISTINCT FROM
  (OLD.id,OLD.event_type,OLD.aggregate_type,OLD.aggregate_id,OLD.recipient_user_id,
   OLD.recipient_email_snapshot_ciphertext,OLD.recipient_email_key_version,OLD.payload_ciphertext,
   OLD.payload_key_version,OLD.payload_version,OLD.idempotency_key,OLD.created_at) THEN
  RAISE EXCEPTION 'Notification event identity/payload is immutable' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_outbox_relation BEFORE INSERT OR UPDATE ON public.notification_outbox FOR EACH ROW EXECUTE FUNCTION public.sr_outbox_relation();

CREATE FUNCTION public.sr_lease_transition() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE wid text:=NULLIF(pg_catalog.current_setting('safereturn.worker_id',true),'');
BEGIN
 IF current_user='safereturn_worker' THEN
  IF NEW.status='leased' THEN
   IF NOT ((OLD.status IN ('pending','retry') AND OLD.next_attempt_at<=pg_catalog.now()) OR
      (OLD.status='leased' AND OLD.lease_until<=pg_catalog.now())) OR
      NEW.lease_owner IS DISTINCT FROM wid OR NEW.lease_until<=pg_catalog.now() OR
      NEW.attempt_count<>OLD.attempt_count+1 THEN
    RAISE EXCEPTION 'Worker claim must be due, bounded and owned' USING ERRCODE='23514';
   END IF;
  ELSE
   IF OLD.status<>'leased' OR OLD.lease_owner IS DISTINCT FROM wid OR OLD.lease_until<=pg_catalog.now()
      OR NEW.attempt_count<>OLD.attempt_count THEN
    RAISE EXCEPTION 'Worker completion requires its unexpired lease' USING ERRCODE='23514';
   END IF;
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_outbox_lease BEFORE UPDATE ON public.notification_outbox FOR EACH ROW EXECUTE FUNCTION public.sr_lease_transition();
CREATE TRIGGER sr_jobs_lease BEFORE UPDATE ON public.durable_jobs FOR EACH ROW EXECUTE FUNCTION public.sr_lease_transition();

CREATE FUNCTION public.sr_idempotency_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF (NEW.id,NEW.actor_scope,NEW.actor_user_id,NEW.operation,NEW.idempotency_key,NEW.request_hash,NEW.created_at,NEW.expires_at)
    IS DISTINCT FROM (OLD.id,OLD.actor_scope,OLD.actor_user_id,OLD.operation,OLD.idempotency_key,OLD.request_hash,OLD.created_at,OLD.expires_at)
    OR (OLD.state='completed' AND NEW IS DISTINCT FROM OLD) THEN
  RAISE EXCEPTION 'Idempotency binding and completed decision are immutable' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_idempotency_guard BEFORE UPDATE ON public.idempotency_records FOR EACH ROW EXECUTE FUNCTION public.sr_idempotency_guard();

CREATE FUNCTION public.sr_context_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF TG_TABLE_NAME='scan_contexts' THEN
  IF TG_OP='INSERT' AND NOT EXISTS (
   SELECT 1 FROM public.qr_codes WHERE id=NEW.qr_code_id AND is_current AND public_status='unactivated'
    AND NEW.public_token_digest=pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to(public_token,'UTF8')),'hex')
  ) THEN RAISE EXCEPTION 'Scan context must match current unactivated public token' USING ERRCODE='23514'; END IF;
  IF TG_OP='UPDATE' THEN
   IF (NEW.id,NEW.qr_code_id,NEW.public_token_digest,NEW.session_binding_digest,NEW.created_at,NEW.expires_at)
      IS DISTINCT FROM (OLD.id,OLD.qr_code_id,OLD.public_token_digest,OLD.session_binding_digest,OLD.created_at,OLD.expires_at)
      OR (OLD.bound_actor_user_id IS NOT NULL AND NEW.bound_actor_user_id IS DISTINCT FROM OLD.bound_actor_user_id)
      OR (OLD.state<>'pending' AND NEW IS DISTINCT FROM OLD) THEN
    RAISE EXCEPTION 'Scan binding cannot be moved or replayed' USING ERRCODE='23514';
   END IF;
  END IF;
 ELSE
  IF TG_OP='UPDATE' THEN
   IF (NEW.id,NEW.actor_user_id,NEW.pair_id,NEW.lost_qr_id,NEW.ice_qr_id,NEW.scan_context_id,NEW.method,
      NEW.order_pair_unit_id,NEW.verifier_key_version,NEW.created_at,NEW.expires_at) IS DISTINCT FROM
      (OLD.id,OLD.actor_user_id,OLD.pair_id,OLD.lost_qr_id,OLD.ice_qr_id,OLD.scan_context_id,OLD.method,
      OLD.order_pair_unit_id,OLD.verifier_key_version,OLD.created_at,OLD.expires_at)
      OR (OLD.state<>'pending' AND NEW IS DISTINCT FROM OLD) THEN
    RAISE EXCEPTION 'Activation intent cannot change actor, entitlement or be replayed' USING ERRCODE='23514';
   END IF;
  END IF;
  IF TG_OP='INSERT' OR NEW.state='consumed' THEN
   PERFORM 1 FROM public.tag_pairs WHERE id=NEW.pair_id AND ownership_status='unclaimed' FOR UPDATE;
   IF NOT FOUND OR NOT EXISTS (SELECT 1 FROM public.qr_codes WHERE id=NEW.lost_qr_id AND pair_id=NEW.pair_id AND tag_type='lost' AND is_current AND public_status='unactivated')
    OR NOT EXISTS (SELECT 1 FROM public.qr_codes WHERE id=NEW.ice_qr_id AND pair_id=NEW.pair_id AND tag_type='ice' AND is_current AND public_status='unactivated') THEN
    RAISE EXCEPTION 'Activation intent requires current unclaimed pair' USING ERRCODE='23514';
   END IF;
   IF NEW.scan_context_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM public.scan_contexts WHERE id=NEW.scan_context_id AND bound_actor_user_id=NEW.actor_user_id
     AND qr_code_id IN (NEW.lost_qr_id,NEW.ice_qr_id) AND expires_at>pg_catalog.now()
   ) THEN RAISE EXCEPTION 'Activation scan context does not belong to actor/pair' USING ERRCODE='23514'; END IF;
   IF NEW.method='order_entitlement' AND NOT EXISTS (
    SELECT 1 FROM public.order_pair_units u JOIN public.orders o ON o.id=u.order_id
     WHERE u.id=NEW.order_pair_unit_id AND u.pair_id=NEW.pair_id AND u.status='allocated'
      AND o.customer_user_id=NEW.actor_user_id AND o.payment_status='verified'
   ) THEN RAISE EXCEPTION 'Activation intent requires paid allocation to actor' USING ERRCODE='23514'; END IF;
   IF NEW.method='concealed_credential' AND NOT EXISTS (
    SELECT 1 FROM public.pair_activation_credentials WHERE pair_id=NEW.pair_id AND status='unused'
     AND verifier_key_version=NEW.verifier_key_version
   ) THEN RAISE EXCEPTION 'Activation credential is not eligible' USING ERRCODE='23514'; END IF;
  END IF;
 END IF;
 IF NEW.state='consumed' AND NEW.expires_at<=pg_catalog.now() THEN
  RAISE EXCEPTION 'Expired context cannot be consumed' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_scan_binding BEFORE INSERT OR UPDATE ON public.scan_contexts FOR EACH ROW EXECUTE FUNCTION public.sr_context_guard();
CREATE TRIGGER sr_activation_binding BEFORE INSERT OR UPDATE ON public.activation_intents FOR EACH ROW EXECUTE FUNCTION public.sr_context_guard();

CREATE FUNCTION public.sr_print_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NOT EXISTS (
  SELECT 1 FROM public.orders o JOIN public.payment_attempts a ON a.order_id=o.id
   WHERE o.id=NEW.order_id AND o.payment_status='verified' AND a.state='verified'
    AND a.amount=o.total_pkr AND a.currency_code=o.currency_code
 ) OR NOT EXISTS (SELECT 1 FROM public.order_pair_units WHERE order_id=NEW.order_id AND status='allocated') THEN
  RAISE EXCEPTION 'Print production requires settled allocated order' USING ERRCODE='23514';
 END IF;
 IF TG_OP='UPDATE' AND (NEW.id,NEW.order_id,NEW.job_revision,NEW.template_fingerprint,NEW.render_config,NEW.created_at)
  IS DISTINCT FROM (OLD.id,OLD.order_id,OLD.job_revision,OLD.template_fingerprint,OLD.render_config,OLD.created_at) THEN
  RAISE EXCEPTION 'Print job specification is immutable' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_print_guard BEFORE INSERT OR UPDATE ON public.print_jobs FOR EACH ROW EXECUTE FUNCTION public.sr_print_guard();

CREATE FUNCTION public.sr_job_relation() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NEW.job_kind IN ('allocation.finalize','finance.sync') AND
    (NEW.aggregate_type<>'order' OR NEW.aggregate_id IS DISTINCT FROM NEW.order_id) THEN
  RAISE EXCEPTION 'Order job aggregate mismatch' USING ERRCODE='23514';
 END IF;
 IF NEW.job_kind='print.render' AND (NEW.aggregate_type<>'print_job' OR NEW.aggregate_id IS DISTINCT FROM NEW.print_job_id) THEN
  RAISE EXCEPTION 'Render job aggregate mismatch' USING ERRCODE='23514';
 END IF;
 IF NEW.job_kind='print.render' AND NOT EXISTS (SELECT 1 FROM public.print_jobs WHERE id=NEW.print_job_id AND order_id=NEW.order_id) THEN
  RAISE EXCEPTION 'Render job does not belong to order' USING ERRCODE='23514';
 END IF;
 IF TG_OP='UPDATE' AND (NEW.id,NEW.job_kind,NEW.aggregate_type,NEW.aggregate_id,NEW.order_id,NEW.print_job_id,
   NEW.payload_ciphertext,NEW.payload_key_version,NEW.idempotency_key,NEW.created_at) IS DISTINCT FROM
  (OLD.id,OLD.job_kind,OLD.aggregate_type,OLD.aggregate_id,OLD.order_id,OLD.print_job_id,
   OLD.payload_ciphertext,OLD.payload_key_version,OLD.idempotency_key,OLD.created_at) THEN
  RAISE EXCEPTION 'Durable job binding/payload is immutable' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_job_relation BEFORE INSERT OR UPDATE ON public.durable_jobs FOR EACH ROW EXECUTE FUNCTION public.sr_job_relation();

CREATE FUNCTION public.sr_print_ready() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE jid uuid; status_value text;
BEGIN
 IF TG_TABLE_NAME='print_jobs' THEN jid:=NEW.id;
 ELSE
  IF TG_OP='DELETE' THEN jid:=OLD.print_job_id; ELSE jid:=NEW.print_job_id; END IF;
 END IF;
 SELECT status INTO status_value FROM public.print_jobs WHERE id=jid;
 IF status_value IN ('ready','downloaded','qa_passed') AND NOT EXISTS (
  SELECT 1 FROM public.print_artifacts WHERE print_job_id=jid AND deleted_at IS NULL
 ) THEN RAISE EXCEPTION 'Ready print job requires retained private artifact' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER sr_print_ready AFTER INSERT OR UPDATE ON public.print_jobs
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_print_ready();
CREATE CONSTRAINT TRIGGER sr_artifact_ready AFTER INSERT OR UPDATE OR DELETE ON public.print_artifacts
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_print_ready();
REVOKE ALL ON FUNCTION public.sr_print_ready() FROM PUBLIC,anon,authenticated;

CREATE FUNCTION public.sr_retention_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE kind text; rid uuid; oid uuid;
BEGIN
 IF TG_TABLE_NAME='retention_holds' THEN
  IF TG_OP='UPDATE' AND ((NEW.id,NEW.resource_type,NEW.resource_id,NEW.reason_code,NEW.placed_by,NEW.created_at)
     IS DISTINCT FROM (OLD.id,OLD.resource_type,OLD.resource_id,OLD.reason_code,OLD.placed_by,OLD.created_at)
     OR OLD.released_at IS NOT NULL) THEN
   RAISE EXCEPTION 'Hold identity and released history are immutable' USING ERRCODE='23514';
  END IF;
  -- Hold placement and deletion serialize on the same parent resource. Do not
  -- permit a hold to be attached after the private object has been tombstoned.
  IF NEW.resource_type='order' THEN PERFORM 1 FROM public.orders WHERE id=NEW.resource_id FOR UPDATE;
  ELSIF NEW.resource_type='finder_message' THEN PERFORM 1 FROM public.finder_messages WHERE id=NEW.resource_id AND deleted_at IS NULL FOR UPDATE;
  ELSIF NEW.resource_type='print_artifact' THEN PERFORM 1 FROM public.print_artifacts WHERE id=NEW.resource_id AND deleted_at IS NULL FOR UPDATE;
  ELSE PERFORM 1 FROM public.payment_evidence WHERE id=NEW.resource_id AND deleted_at IS NULL FOR UPDATE; END IF;
  IF NOT FOUND THEN RAISE EXCEPTION 'Hold resource is unavailable' USING ERRCODE='23514'; END IF;
  IF NOT ((NEW.resource_type='order' AND EXISTS (SELECT 1 FROM public.orders WHERE id=NEW.resource_id))
   OR (NEW.resource_type='finder_message' AND EXISTS (SELECT 1 FROM public.finder_messages WHERE id=NEW.resource_id))
   OR (NEW.resource_type='print_artifact' AND EXISTS (SELECT 1 FROM public.print_artifacts WHERE id=NEW.resource_id))
   OR (NEW.resource_type='payment_evidence' AND EXISTS (SELECT 1 FROM public.payment_evidence WHERE id=NEW.resource_id))) THEN
   RAISE EXCEPTION 'Hold requires existing resource' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
 END IF;
 IF NEW.deleted_at IS NOT NULL AND OLD.deleted_at IS NULL THEN
  kind:=CASE TG_TABLE_NAME WHEN 'print_artifacts' THEN 'print_artifact' WHEN 'payment_evidence' THEN 'payment_evidence' ELSE 'finder_message' END;
  rid:=NEW.id;
  IF TG_TABLE_NAME='print_artifacts' THEN SELECT order_id INTO oid FROM public.print_jobs WHERE id=NEW.print_job_id;
  ELSIF TG_TABLE_NAME='payment_evidence' THEN SELECT order_id INTO oid FROM public.payment_attempts WHERE id=NEW.attempt_id; END IF;
  IF oid IS NOT NULL THEN PERFORM 1 FROM public.orders WHERE id=oid FOR UPDATE; END IF;
  PERFORM 1 FROM public.retention_holds WHERE released_at IS NULL AND
   ((resource_type=kind AND resource_id=rid) OR (resource_type='order' AND resource_id=oid)) FOR SHARE;
  IF FOUND OR NEW.retention_until IS NULL OR NEW.retention_until>pg_catalog.now() THEN
   RAISE EXCEPTION 'Deletion requires approved due retention and no active hold' USING ERRCODE='23514';
  END IF;
  IF TG_TABLE_NAME<>'finder_messages' THEN
   IF NEW.deletion_hold_reason IS NOT NULL THEN
    RAISE EXCEPTION 'Object has retention hold' USING ERRCODE='23514';
   END IF;
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_hold_guard BEFORE INSERT OR UPDATE ON public.retention_holds FOR EACH ROW EXECUTE FUNCTION public.sr_retention_guard();
CREATE TRIGGER sr_message_retention BEFORE UPDATE ON public.finder_messages FOR EACH ROW EXECUTE FUNCTION public.sr_retention_guard();
CREATE TRIGGER sr_artifact_retention BEFORE UPDATE ON public.print_artifacts FOR EACH ROW EXECUTE FUNCTION public.sr_retention_guard();
CREATE TRIGGER sr_evidence_retention BEFORE UPDATE ON public.payment_evidence FOR EACH ROW EXECUTE FUNCTION public.sr_retention_guard();

CREATE FUNCTION public.sr_api_private_update() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF current_user='safereturn_api' THEN
  IF TG_TABLE_NAME='qr_codes' THEN
   IF NOT public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) AND
    (NEW.public_status NOT IN ('active','owner_disabled') OR
     (pg_catalog.to_jsonb(NEW)-ARRAY['public_status','updated_at']) IS DISTINCT FROM
     (pg_catalog.to_jsonb(OLD)-ARRAY['public_status','updated_at'])) THEN
    RAISE EXCEPTION 'Owner may only toggle own QR public status' USING ERRCODE='23514';
   END IF;
  ELSE
   IF NOT public.sr_is_staff(ARRAY['security_admin','superadmin']) AND
    (NEW.deleted_at,NEW.retention_until) IS DISTINCT FROM (OLD.deleted_at,OLD.retention_until) THEN
    RAISE EXCEPTION 'Retention deadlines/deletion require privacy authorization' USING ERRCODE='23514';
   END IF;
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_api_qr_update BEFORE UPDATE ON public.qr_codes FOR EACH ROW EXECUTE FUNCTION public.sr_api_private_update();
CREATE TRIGGER sr_api_message_update BEFORE UPDATE ON public.finder_messages FOR EACH ROW EXECUTE FUNCTION public.sr_api_private_update();

CREATE FUNCTION public.sr_api_pair_ownership() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF current_user='safereturn_api' AND
  (NEW.owner_user_id,NEW.ownership_status,NEW.activated_at) IS DISTINCT FROM
  (OLD.owner_user_id,OLD.ownership_status,OLD.activated_at) THEN
  RAISE EXCEPTION 'Ownership changes require reviewed atomic activation/transfer procedure' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_api_pair_ownership BEFORE UPDATE ON public.tag_pairs FOR EACH ROW EXECUTE FUNCTION public.sr_api_pair_ownership();
REVOKE ALL ON FUNCTION public.sr_api_pair_ownership() FROM PUBLIC,anon,authenticated;""",
    """-- Frozen role/column grants and row policies for 0003.
GRANT SELECT ON TABLE public.user_profiles TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.user_profiles FOR SELECT TO safereturn_api USING (user_id=public.sr_actor_id() OR public.sr_is_staff(ARRAY['support','security_admin','superadmin']));
GRANT INSERT ON TABLE public.user_profiles TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.user_profiles FOR INSERT TO safereturn_api WITH CHECK (user_id=public.sr_actor_id());
GRANT UPDATE ON TABLE public.user_profiles TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.user_profiles FOR UPDATE TO safereturn_api USING (user_id=public.sr_actor_id()) WITH CHECK (user_id=public.sr_actor_id());
GRANT SELECT ON TABLE public.staff_roles TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.staff_roles FOR SELECT TO safereturn_api USING (user_id=public.sr_actor_id());
GRANT SELECT ON TABLE public.qr_batches TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.qr_batches FOR SELECT TO safereturn_api USING (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT INSERT ON TABLE public.qr_batches TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.qr_batches FOR INSERT TO safereturn_api WITH CHECK (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT SELECT ON TABLE public.pair_print_qa TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.pair_print_qa FOR SELECT TO safereturn_api USING (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT INSERT ON TABLE public.pair_print_qa TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.pair_print_qa FOR INSERT TO safereturn_api WITH CHECK (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT UPDATE ON TABLE public.qr_batches TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.qr_batches FOR UPDATE TO safereturn_api USING (public.sr_is_staff(ARRAY['operations','security_admin','superadmin'])) WITH CHECK (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT SELECT ON TABLE public.tag_pairs TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.tag_pairs FOR SELECT TO safereturn_api USING (public.sr_owns_pair(id) OR public.sr_entitled_pair(id) OR (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin']) OR public.sr_is_staff(ARRAY['support','security_admin','superadmin'])));
GRANT INSERT ON TABLE public.tag_pairs TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.tag_pairs FOR INSERT TO safereturn_api WITH CHECK (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) AND owner_user_id IS NULL AND ownership_status='unclaimed');
GRANT UPDATE ON TABLE public.tag_pairs TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.tag_pairs FOR UPDATE TO safereturn_api USING (public.sr_is_staff(ARRAY['operations','security_admin','superadmin'])) WITH CHECK (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT SELECT ON TABLE public.qr_codes TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.qr_codes FOR SELECT TO safereturn_api USING (true);
GRANT INSERT ON TABLE public.qr_codes TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.qr_codes FOR INSERT TO safereturn_api WITH CHECK (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT UPDATE ON TABLE public.qr_codes TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.qr_codes FOR UPDATE TO safereturn_api USING (public.sr_owns_pair(pair_id) OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin'])) WITH CHECK (public.sr_owns_pair(pair_id) OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT SELECT ON TABLE public.pair_activation_credentials TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.pair_activation_credentials FOR SELECT TO safereturn_api USING (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) OR public.sr_scan_pair(pair_id));
GRANT INSERT ON TABLE public.pair_activation_credentials TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.pair_activation_credentials FOR INSERT TO safereturn_api WITH CHECK (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT UPDATE ON TABLE public.pair_activation_credentials TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.pair_activation_credentials FOR UPDATE TO safereturn_api USING (public.sr_is_staff(ARRAY['operations','security_admin','superadmin'])) WITH CHECK (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT SELECT ON TABLE public.lost_item_profiles TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.lost_item_profiles FOR SELECT TO safereturn_api USING (public.sr_owns_qr(qr_id) OR public.sr_is_staff(ARRAY['security_admin','superadmin']));
GRANT INSERT ON TABLE public.lost_item_profiles TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.lost_item_profiles FOR INSERT TO safereturn_api WITH CHECK (public.sr_owns_qr(qr_id) OR public.sr_is_staff(ARRAY['security_admin','superadmin']));
GRANT UPDATE ON TABLE public.lost_item_profiles TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.lost_item_profiles FOR UPDATE TO safereturn_api USING (public.sr_owns_qr(qr_id) OR public.sr_is_staff(ARRAY['security_admin','superadmin'])) WITH CHECK (public.sr_owns_qr(qr_id) OR public.sr_is_staff(ARRAY['security_admin','superadmin']));
GRANT SELECT ON TABLE public.ice_profiles TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.ice_profiles FOR SELECT TO safereturn_api USING (public.sr_owns_qr(qr_id) OR public.sr_is_staff(ARRAY['security_admin','superadmin']));
GRANT INSERT ON TABLE public.ice_profiles TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.ice_profiles FOR INSERT TO safereturn_api WITH CHECK (public.sr_owns_qr(qr_id) OR public.sr_is_staff(ARRAY['security_admin','superadmin']));
GRANT UPDATE ON TABLE public.ice_profiles TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.ice_profiles FOR UPDATE TO safereturn_api USING (public.sr_owns_qr(qr_id) OR public.sr_is_staff(ARRAY['security_admin','superadmin'])) WITH CHECK (public.sr_owns_qr(qr_id) OR public.sr_is_staff(ARRAY['security_admin','superadmin']));
GRANT SELECT ON TABLE public.tag_contact_preferences TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.tag_contact_preferences FOR SELECT TO safereturn_api USING (public.sr_owns_qr(qr_id) OR public.sr_is_staff(ARRAY['security_admin','superadmin']));
GRANT INSERT ON TABLE public.tag_contact_preferences TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.tag_contact_preferences FOR INSERT TO safereturn_api WITH CHECK (public.sr_owns_qr(qr_id) OR public.sr_is_staff(ARRAY['security_admin','superadmin']));
GRANT UPDATE ON TABLE public.tag_contact_preferences TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.tag_contact_preferences FOR UPDATE TO safereturn_api USING (public.sr_owns_qr(qr_id) OR public.sr_is_staff(ARRAY['security_admin','superadmin'])) WITH CHECK (public.sr_owns_qr(qr_id) OR public.sr_is_staff(ARRAY['security_admin','superadmin']));
GRANT SELECT ON TABLE public.ice_contacts TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.ice_contacts FOR SELECT TO safereturn_api USING (public.sr_owns_qr(ice_qr_id) OR public.sr_is_staff(ARRAY['security_admin','superadmin']));
GRANT INSERT ON TABLE public.ice_contacts TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.ice_contacts FOR INSERT TO safereturn_api WITH CHECK (public.sr_owns_qr(ice_qr_id) OR public.sr_is_staff(ARRAY['security_admin','superadmin']));
GRANT UPDATE ON TABLE public.ice_contacts TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.ice_contacts FOR UPDATE TO safereturn_api USING (public.sr_owns_qr(ice_qr_id) OR public.sr_is_staff(ARRAY['security_admin','superadmin'])) WITH CHECK (public.sr_owns_qr(ice_qr_id) OR public.sr_is_staff(ARRAY['security_admin','superadmin']));
GRANT DELETE ON TABLE public.ice_contacts TO safereturn_api;
CREATE POLICY sr_safereturn_api_delete ON public.ice_contacts FOR DELETE TO safereturn_api USING (public.sr_owns_qr(ice_qr_id) OR public.sr_is_staff(ARRAY['security_admin','superadmin']));
GRANT SELECT ON TABLE public.product_categories TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.product_categories FOR SELECT TO safereturn_api USING (is_active OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT INSERT ON TABLE public.product_categories TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.product_categories FOR INSERT TO safereturn_api WITH CHECK (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT UPDATE ON TABLE public.product_categories TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.product_categories FOR UPDATE TO safereturn_api USING (public.sr_is_staff(ARRAY['operations','security_admin','superadmin'])) WITH CHECK (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT SELECT ON TABLE public.products TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.products FOR SELECT TO safereturn_api USING (lifecycle_status='published' OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT INSERT ON TABLE public.products TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.products FOR INSERT TO safereturn_api WITH CHECK (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT UPDATE ON TABLE public.products TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.products FOR UPDATE TO safereturn_api USING (public.sr_is_staff(ARRAY['operations','security_admin','superadmin'])) WITH CHECK (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT SELECT ON TABLE public.product_variants TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.product_variants FOR SELECT TO safereturn_api USING ((is_active AND EXISTS(SELECT 1 FROM public.products WHERE id=product_id AND lifecycle_status='published')) OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT INSERT ON TABLE public.product_variants TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.product_variants FOR INSERT TO safereturn_api WITH CHECK (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT UPDATE ON TABLE public.product_variants TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.product_variants FOR UPDATE TO safereturn_api USING (public.sr_is_staff(ARRAY['operations','security_admin','superadmin'])) WITH CHECK (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT SELECT ON TABLE public.product_images TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.product_images FOR SELECT TO safereturn_api USING (EXISTS(SELECT 1 FROM public.products WHERE id=product_id AND lifecycle_status='published') OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT INSERT ON TABLE public.product_images TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.product_images FOR INSERT TO safereturn_api WITH CHECK (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT UPDATE ON TABLE public.product_images TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.product_images FOR UPDATE TO safereturn_api USING (public.sr_is_staff(ARRAY['operations','security_admin','superadmin'])) WITH CHECK (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT SELECT ON TABLE public.orders TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.orders FOR SELECT TO safereturn_api USING (customer_user_id=public.sr_actor_id() OR (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin']) OR public.sr_is_staff(ARRAY['support','security_admin','superadmin'])));
GRANT INSERT ON TABLE public.orders TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.orders FOR INSERT TO safereturn_api WITH CHECK (customer_user_id=public.sr_actor_id() AND payment_status='awaiting_transfer' AND fulfillment_status='unallocated');
GRANT UPDATE ON TABLE public.orders TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.orders FOR UPDATE TO safereturn_api USING (customer_user_id=public.sr_actor_id() OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin'])) WITH CHECK ((customer_user_id=public.sr_actor_id() AND payment_status IN ('awaiting_transfer','proof_submitted','under_review') AND fulfillment_status='unallocated') OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin']));
GRANT SELECT ON TABLE public.order_items TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.order_items FOR SELECT TO safereturn_api USING (public.sr_owns_order(order_id) OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin']));
GRANT INSERT ON TABLE public.order_items TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.order_items FOR INSERT TO safereturn_api WITH CHECK (public.sr_owns_order(order_id) OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin']));
GRANT UPDATE ON TABLE public.order_items TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.order_items FOR UPDATE TO safereturn_api USING (public.sr_owns_order(order_id) OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin'])) WITH CHECK (public.sr_owns_order(order_id) OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin']));
GRANT SELECT ON TABLE public.order_shipping_snapshots TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.order_shipping_snapshots FOR SELECT TO safereturn_api USING (public.sr_owns_order(order_id) OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin']));
GRANT INSERT ON TABLE public.order_shipping_snapshots TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.order_shipping_snapshots FOR INSERT TO safereturn_api WITH CHECK (public.sr_owns_order(order_id) OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin']));
GRANT UPDATE ON TABLE public.order_shipping_snapshots TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.order_shipping_snapshots FOR UPDATE TO safereturn_api USING (public.sr_owns_order(order_id) OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin'])) WITH CHECK (public.sr_owns_order(order_id) OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin']));
GRANT SELECT ON TABLE public.order_pair_units TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.order_pair_units FOR SELECT TO safereturn_api USING (public.sr_owns_order(order_id) OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin']));
GRANT INSERT ON TABLE public.order_pair_units TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.order_pair_units FOR INSERT TO safereturn_api WITH CHECK ((public.sr_owns_order(order_id) AND status='reserved') OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin']));
GRANT UPDATE ON TABLE public.order_pair_units TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.order_pair_units FOR UPDATE TO safereturn_api USING (public.sr_owns_order(order_id) OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin'])) WITH CHECK ((public.sr_owns_order(order_id) AND status IN ('reserved','released','cancelled')) OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin']));
GRANT SELECT ON TABLE public.order_item_qr_uses TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.order_item_qr_uses FOR SELECT TO safereturn_api USING (EXISTS(SELECT 1 FROM public.order_items WHERE id=order_item_id AND public.sr_owns_order(order_id)) OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin']));
GRANT INSERT ON TABLE public.order_item_qr_uses TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.order_item_qr_uses FOR INSERT TO safereturn_api WITH CHECK (EXISTS(SELECT 1 FROM public.order_items WHERE id=order_item_id AND public.sr_owns_order(order_id)) OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin']));
GRANT UPDATE ON TABLE public.order_item_qr_uses TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.order_item_qr_uses FOR UPDATE TO safereturn_api USING (EXISTS(SELECT 1 FROM public.order_items WHERE id=order_item_id AND public.sr_owns_order(order_id)) OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin'])) WITH CHECK (EXISTS(SELECT 1 FROM public.order_items WHERE id=order_item_id AND public.sr_owns_order(order_id)) OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin']));
GRANT SELECT ON TABLE public.payment_attempts TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.payment_attempts FOR SELECT TO safereturn_api USING (public.sr_owns_order(order_id) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin']));
GRANT INSERT ON TABLE public.payment_attempts TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.payment_attempts FOR INSERT TO safereturn_api WITH CHECK ((public.sr_owns_order(order_id) AND state IN ('initiated','submitted') AND verified_at IS NULL) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin']));
GRANT UPDATE ON TABLE public.payment_attempts TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.payment_attempts FOR UPDATE TO safereturn_api USING (public.sr_owns_order(order_id) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin'])) WITH CHECK ((public.sr_owns_order(order_id) AND state IN ('initiated','submitted','under_review') AND verified_at IS NULL) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin']));
GRANT SELECT ON TABLE public.payment_evidence TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.payment_evidence FOR SELECT TO safereturn_api USING (EXISTS(SELECT 1 FROM public.payment_attempts WHERE id=attempt_id AND public.sr_owns_order(order_id)) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin']));
GRANT INSERT ON TABLE public.payment_evidence TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.payment_evidence FOR INSERT TO safereturn_api WITH CHECK (EXISTS(SELECT 1 FROM public.payment_attempts WHERE id=attempt_id AND public.sr_owns_order(order_id)) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin']));
GRANT UPDATE ON TABLE public.payment_evidence TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.payment_evidence FOR UPDATE TO safereturn_api USING (public.sr_is_staff(ARRAY['finance','security_admin','superadmin'])) WITH CHECK (public.sr_is_staff(ARRAY['finance','security_admin','superadmin']));
GRANT SELECT ON TABLE public.payment_reviews TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.payment_reviews FOR SELECT TO safereturn_api USING (public.sr_is_staff(ARRAY['finance','security_admin','superadmin']));
GRANT INSERT ON TABLE public.payment_reviews TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.payment_reviews FOR INSERT TO safereturn_api WITH CHECK (public.sr_is_staff(ARRAY['finance','security_admin','superadmin']) AND reviewed_by=public.sr_actor_id());
GRANT SELECT ON TABLE public.shipping_addresses TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.shipping_addresses FOR SELECT TO safereturn_api USING (customer_user_id=public.sr_actor_id() OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT INSERT ON TABLE public.shipping_addresses TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.shipping_addresses FOR INSERT TO safereturn_api WITH CHECK (customer_user_id=public.sr_actor_id());
GRANT UPDATE ON TABLE public.shipping_addresses TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.shipping_addresses FOR UPDATE TO safereturn_api USING (customer_user_id=public.sr_actor_id()) WITH CHECK (customer_user_id=public.sr_actor_id());
GRANT SELECT ON TABLE public.shipments TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.shipments FOR SELECT TO safereturn_api USING (public.sr_owns_order(order_id) OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT INSERT ON TABLE public.shipments TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.shipments FOR INSERT TO safereturn_api WITH CHECK (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT UPDATE ON TABLE public.shipments TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.shipments FOR UPDATE TO safereturn_api USING (public.sr_is_staff(ARRAY['operations','security_admin','superadmin'])) WITH CHECK (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT SELECT ON TABLE public.shipment_pairs TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.shipment_pairs FOR SELECT TO safereturn_api USING (EXISTS(SELECT 1 FROM public.shipments WHERE id=shipment_id AND public.sr_owns_order(order_id)) OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT INSERT ON TABLE public.shipment_pairs TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.shipment_pairs FOR INSERT TO safereturn_api WITH CHECK (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT UPDATE ON TABLE public.shipment_pairs TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.shipment_pairs FOR UPDATE TO safereturn_api USING (public.sr_is_staff(ARRAY['operations','security_admin','superadmin'])) WITH CHECK (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT SELECT ON TABLE public.finder_messages TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.finder_messages FOR SELECT TO safereturn_api USING (public.sr_can_message(id) OR public.sr_is_staff(ARRAY['security_admin','superadmin']));
GRANT INSERT ON TABLE public.finder_messages TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.finder_messages FOR INSERT TO safereturn_api WITH CHECK (id=public.sr_submission_id() AND status='new' AND deleted_at IS NULL);
GRANT UPDATE (status,abuse_flag,deleted_at,retention_until) ON TABLE public.finder_messages TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.finder_messages FOR UPDATE TO safereturn_api USING (recipient_owner_user_id=public.sr_actor_id() OR public.sr_is_staff(ARRAY['security_admin','superadmin'])) WITH CHECK (recipient_owner_user_id=public.sr_actor_id() OR public.sr_is_staff(ARRAY['security_admin','superadmin']));
GRANT SELECT ON TABLE public.finder_message_locations TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.finder_message_locations FOR SELECT TO safereturn_api USING (public.sr_can_message(finder_message_id) OR public.sr_is_staff(ARRAY['security_admin','superadmin']));
GRANT INSERT ON TABLE public.finder_message_locations TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.finder_message_locations FOR INSERT TO safereturn_api WITH CHECK (public.sr_can_message(finder_message_id));
GRANT SELECT ON TABLE public.notification_outbox TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.notification_outbox FOR SELECT TO safereturn_api USING (recipient_user_id=public.sr_actor_id() OR (aggregate_type='finder_message' AND public.sr_can_message(aggregate_id)) OR public.sr_is_staff(ARRAY['security_admin','superadmin']));
GRANT INSERT ON TABLE public.notification_outbox TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.notification_outbox FOR INSERT TO safereturn_api WITH CHECK (status='pending' AND attempt_count=0 AND ((event_type='finder_message.created' AND public.sr_can_message(aggregate_id)) OR recipient_user_id=public.sr_actor_id() OR (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin']) OR public.sr_is_staff(ARRAY['support','security_admin','superadmin']))));
GRANT SELECT ON TABLE public.notification_attempts TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.notification_attempts FOR SELECT TO safereturn_api USING (EXISTS(SELECT 1 FROM public.notification_outbox WHERE id=outbox_id AND recipient_user_id=public.sr_actor_id()) OR public.sr_is_staff(ARRAY['security_admin','superadmin']));
GRANT SELECT ON TABLE public.audit_events TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.audit_events FOR SELECT TO safereturn_api USING (actor_user_id=public.sr_actor_id() OR public.sr_is_staff(ARRAY['security_admin','superadmin']));
GRANT INSERT ON TABLE public.audit_events TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.audit_events FOR INSERT TO safereturn_api WITH CHECK ((actor_user_id=public.sr_actor_id() AND (actor_kind='customer' OR (actor_kind='staff' AND public.sr_is_staff(ARRAY['support','operations','finance','security_admin','superadmin'])))) OR (actor_user_id IS NULL AND public.sr_actor_id() IS NULL AND actor_kind='anonymous'));
GRANT SELECT ON TABLE public.idempotency_records TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.idempotency_records FOR SELECT TO safereturn_api USING (actor_user_id=public.sr_actor_id() AND actor_scope=public.sr_actor_id()::text);
GRANT INSERT ON TABLE public.idempotency_records TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.idempotency_records FOR INSERT TO safereturn_api WITH CHECK (actor_user_id=public.sr_actor_id() AND actor_scope=public.sr_actor_id()::text);
GRANT UPDATE ON TABLE public.idempotency_records TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.idempotency_records FOR UPDATE TO safereturn_api USING (actor_user_id=public.sr_actor_id() AND actor_scope=public.sr_actor_id()::text) WITH CHECK (actor_user_id=public.sr_actor_id() AND actor_scope=public.sr_actor_id()::text);
GRANT SELECT ON TABLE public.scan_contexts TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.scan_contexts FOR SELECT TO safereturn_api USING (session_binding_digest=public.sr_scan_binding() AND (bound_actor_user_id IS NULL OR bound_actor_user_id=public.sr_actor_id()));
GRANT INSERT ON TABLE public.scan_contexts TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.scan_contexts FOR INSERT TO safereturn_api WITH CHECK (session_binding_digest=public.sr_scan_binding() AND (bound_actor_user_id IS NULL OR bound_actor_user_id=public.sr_actor_id()) AND state='pending' AND expires_at>now());
GRANT UPDATE ON TABLE public.scan_contexts TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.scan_contexts FOR UPDATE TO safereturn_api USING (session_binding_digest=public.sr_scan_binding() AND (bound_actor_user_id IS NULL OR bound_actor_user_id=public.sr_actor_id())) WITH CHECK (session_binding_digest=public.sr_scan_binding() AND (bound_actor_user_id IS NULL OR bound_actor_user_id=public.sr_actor_id()));
GRANT SELECT ON TABLE public.activation_intents TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.activation_intents FOR SELECT TO safereturn_api USING (actor_user_id=public.sr_actor_id());
GRANT INSERT ON TABLE public.activation_intents TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.activation_intents FOR INSERT TO safereturn_api WITH CHECK (actor_user_id=public.sr_actor_id() AND state='pending' AND expires_at>now());
GRANT UPDATE (state,consumed_at) ON TABLE public.activation_intents TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.activation_intents FOR UPDATE TO safereturn_api USING (actor_user_id=public.sr_actor_id()) WITH CHECK (actor_user_id=public.sr_actor_id());
GRANT SELECT ON TABLE public.print_jobs TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.print_jobs FOR SELECT TO safereturn_api USING (public.sr_owns_order(order_id) OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT INSERT ON TABLE public.print_jobs TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.print_jobs FOR INSERT TO safereturn_api WITH CHECK (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT UPDATE ON TABLE public.print_jobs TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.print_jobs FOR UPDATE TO safereturn_api USING (public.sr_is_staff(ARRAY['operations','security_admin','superadmin'])) WITH CHECK (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT SELECT ON TABLE public.finance_sheet_sync TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.finance_sheet_sync FOR SELECT TO safereturn_api USING (public.sr_is_staff(ARRAY['finance','security_admin','superadmin']));
GRANT INSERT ON TABLE public.finance_sheet_sync TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.finance_sheet_sync FOR INSERT TO safereturn_api WITH CHECK (public.sr_is_staff(ARRAY['finance','security_admin','superadmin']));
GRANT UPDATE ON TABLE public.finance_sheet_sync TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.finance_sheet_sync FOR UPDATE TO safereturn_api USING (public.sr_is_staff(ARRAY['finance','security_admin','superadmin'])) WITH CHECK (public.sr_is_staff(ARRAY['finance','security_admin','superadmin']));
GRANT SELECT ON TABLE public.print_artifacts TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.print_artifacts FOR SELECT TO safereturn_api USING (EXISTS(SELECT 1 FROM public.print_jobs WHERE id=print_job_id AND public.sr_owns_order(order_id)) OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT INSERT ON TABLE public.print_artifacts TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.print_artifacts FOR INSERT TO safereturn_api WITH CHECK (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
GRANT UPDATE ON TABLE public.print_artifacts TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.print_artifacts FOR UPDATE TO safereturn_api USING (public.sr_is_staff(ARRAY['security_admin','superadmin'])) WITH CHECK (public.sr_is_staff(ARRAY['security_admin','superadmin']));
GRANT SELECT ON TABLE public.durable_jobs TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.durable_jobs FOR SELECT TO safereturn_api USING (public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) OR public.sr_is_staff(ARRAY['finance','security_admin','superadmin']) OR public.sr_is_staff(ARRAY['security_admin','superadmin']));
GRANT INSERT ON TABLE public.durable_jobs TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.durable_jobs FOR INSERT TO safereturn_api WITH CHECK (status='pending' AND attempt_count=0 AND ((job_kind='print.render' AND public.sr_is_staff(ARRAY['operations','security_admin','superadmin'])) OR (job_kind IN ('allocation.finalize','finance.sync') AND public.sr_is_staff(ARRAY['finance','security_admin','superadmin'])) OR (job_kind='retention.cleanup' AND public.sr_is_staff(ARRAY['security_admin','superadmin']))));
GRANT SELECT ON TABLE public.retention_holds TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.retention_holds FOR SELECT TO safereturn_api USING (public.sr_is_staff(ARRAY['security_admin','superadmin']));
GRANT INSERT ON TABLE public.retention_holds TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.retention_holds FOR INSERT TO safereturn_api WITH CHECK (public.sr_is_staff(ARRAY['security_admin','superadmin']) AND placed_by=public.sr_actor_id());
GRANT UPDATE (released_by,released_at) ON TABLE public.retention_holds TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.retention_holds FOR UPDATE TO safereturn_api USING (public.sr_is_staff(ARRAY['security_admin','superadmin'])) WITH CHECK (public.sr_is_staff(ARRAY['security_admin','superadmin']) AND released_by=public.sr_actor_id());
GRANT SELECT ON TABLE public.support_cases TO safereturn_api;
CREATE POLICY sr_safereturn_api_select ON public.support_cases FOR SELECT TO safereturn_api USING (opened_by_user_id=public.sr_actor_id() OR public.sr_is_staff(ARRAY['support','security_admin','superadmin']));
GRANT INSERT ON TABLE public.support_cases TO safereturn_api;
CREATE POLICY sr_safereturn_api_insert ON public.support_cases FOR INSERT TO safereturn_api WITH CHECK (opened_by_user_id=public.sr_actor_id() OR public.sr_is_staff(ARRAY['support','security_admin','superadmin']));
GRANT UPDATE ON TABLE public.support_cases TO safereturn_api;
CREATE POLICY sr_safereturn_api_update ON public.support_cases FOR UPDATE TO safereturn_api USING (public.sr_is_staff(ARRAY['support','security_admin','superadmin'])) WITH CHECK (public.sr_is_staff(ARRAY['support','security_admin','superadmin']));
GRANT SELECT ON TABLE public.notification_outbox TO safereturn_worker;
CREATE POLICY sr_safereturn_worker_select ON public.notification_outbox FOR SELECT TO safereturn_worker USING (public.sr_worker_id() IS NOT NULL);
GRANT UPDATE (status,attempt_count,next_attempt_at,lease_owner,lease_until,last_error_code,provider_message_id,sent_at) ON TABLE public.notification_outbox TO safereturn_worker;
CREATE POLICY sr_safereturn_worker_update ON public.notification_outbox FOR UPDATE TO safereturn_worker USING (public.sr_worker_id() IS NOT NULL AND (status IN ('pending','retry') OR (status='leased' AND (lease_owner=public.sr_worker_id() OR lease_until<=now())))) WITH CHECK (public.sr_worker_id() IS NOT NULL);
GRANT SELECT ON TABLE public.durable_jobs TO safereturn_worker;
CREATE POLICY sr_safereturn_worker_select ON public.durable_jobs FOR SELECT TO safereturn_worker USING (public.sr_worker_id() IS NOT NULL);
GRANT UPDATE (status,attempt_count,next_attempt_at,lease_owner,lease_until,last_error_code,completed_at) ON TABLE public.durable_jobs TO safereturn_worker;
CREATE POLICY sr_safereturn_worker_update ON public.durable_jobs FOR UPDATE TO safereturn_worker USING (public.sr_worker_id() IS NOT NULL AND (status IN ('pending','retry') OR (status='leased' AND (lease_owner=public.sr_worker_id() OR lease_until<=now())))) WITH CHECK (public.sr_worker_id() IS NOT NULL);
GRANT SELECT ON TABLE public.notification_attempts TO safereturn_worker;
CREATE POLICY sr_safereturn_worker_select ON public.notification_attempts FOR SELECT TO safereturn_worker USING (public.sr_worker_id() IS NOT NULL);
GRANT INSERT ON TABLE public.notification_attempts TO safereturn_worker;
CREATE POLICY sr_safereturn_worker_insert ON public.notification_attempts FOR INSERT TO safereturn_worker WITH CHECK (EXISTS(SELECT 1 FROM public.notification_outbox o WHERE o.id=outbox_id AND o.status='leased' AND o.lease_owner=public.sr_worker_id() AND o.lease_until>now()));
GRANT UPDATE (finished_at,outcome,provider_message_id,error_code) ON TABLE public.notification_attempts TO safereturn_worker;
CREATE POLICY sr_safereturn_worker_update ON public.notification_attempts FOR UPDATE TO safereturn_worker USING (EXISTS(SELECT 1 FROM public.notification_outbox o WHERE o.id=outbox_id AND o.status='leased' AND o.lease_owner=public.sr_worker_id() AND o.lease_until>now())) WITH CHECK (EXISTS(SELECT 1 FROM public.notification_outbox o WHERE o.id=outbox_id AND o.status='leased' AND o.lease_owner=public.sr_worker_id() AND o.lease_until>now()));
GRANT INSERT ON TABLE public.audit_events TO safereturn_worker;
CREATE POLICY sr_safereturn_worker_insert ON public.audit_events FOR INSERT TO safereturn_worker WITH CHECK (actor_kind='system' AND actor_user_id IS NULL AND public.sr_worker_id() IS NOT NULL);
GRANT SELECT (id,order_number,order_status,payment_status,fulfillment_status,currency_code,subtotal_pkr,shipping_pkr,tax_pkr,discount_pkr,total_pkr,placed_at,created_at) ON TABLE public.orders TO safereturn_worker;
CREATE POLICY sr_safereturn_worker_select ON public.orders FOR SELECT TO safereturn_worker USING (public.sr_worker_order(id));
GRANT SELECT ON TABLE public.order_items TO safereturn_worker;
CREATE POLICY sr_safereturn_worker_select ON public.order_items FOR SELECT TO safereturn_worker USING (public.sr_worker_order(order_id));
GRANT SELECT ON TABLE public.order_item_qr_uses TO safereturn_worker;
CREATE POLICY sr_safereturn_worker_select ON public.order_item_qr_uses FOR SELECT TO safereturn_worker USING (EXISTS(SELECT 1 FROM public.order_items i WHERE i.id=order_item_id AND public.sr_worker_order(i.order_id)));
GRANT SELECT (id,order_id,pair_id,kind,status) ON TABLE public.order_pair_units TO safereturn_worker;
CREATE POLICY sr_safereturn_worker_select ON public.order_pair_units FOR SELECT TO safereturn_worker USING (public.sr_worker_order(order_id));
GRANT SELECT (id,pair_id,tag_type,serial_number,public_token,public_status,is_current,ecc_level,qr_version,printed_size_mm) ON TABLE public.qr_codes TO safereturn_worker;
CREATE POLICY sr_safereturn_worker_select ON public.qr_codes FOR SELECT TO safereturn_worker USING (EXISTS(SELECT 1 FROM public.order_item_qr_uses u JOIN public.order_items i ON i.id=u.order_item_id WHERE u.qr_code_id=qr_codes.id AND public.sr_worker_order(i.order_id)));
GRANT SELECT ON TABLE public.print_jobs TO safereturn_worker;
CREATE POLICY sr_safereturn_worker_select ON public.print_jobs FOR SELECT TO safereturn_worker USING (public.sr_worker_order(order_id));
GRANT SELECT ON TABLE public.print_artifacts TO safereturn_worker;
CREATE POLICY sr_safereturn_worker_select ON public.print_artifacts FOR SELECT TO safereturn_worker USING (public.sr_worker_print(print_job_id) OR public.sr_worker_cleanup('print_artifact',id));
GRANT SELECT ON TABLE public.finance_sheet_sync TO safereturn_worker;
CREATE POLICY sr_safereturn_worker_select ON public.finance_sheet_sync FOR SELECT TO safereturn_worker USING (public.sr_worker_order(order_id));
GRANT UPDATE (status,attempt_count,failure_code,updated_at) ON TABLE public.print_jobs TO safereturn_worker;
CREATE POLICY sr_safereturn_worker_update ON public.print_jobs FOR UPDATE TO safereturn_worker USING (public.sr_worker_print(id)) WITH CHECK (public.sr_worker_print(id));
GRANT INSERT ON TABLE public.print_artifacts TO safereturn_worker;
CREATE POLICY sr_safereturn_worker_insert ON public.print_artifacts FOR INSERT TO safereturn_worker WITH CHECK (public.sr_worker_print(print_job_id));
GRANT UPDATE (deleted_at) ON TABLE public.print_artifacts TO safereturn_worker;
CREATE POLICY sr_safereturn_worker_update ON public.print_artifacts FOR UPDATE TO safereturn_worker USING (public.sr_worker_cleanup('print_artifact',id)) WITH CHECK (public.sr_worker_cleanup('print_artifact',id));
GRANT UPDATE (sheet_row_key,last_export_version,status,attempt_count,last_error_code,last_synced_at,updated_at) ON TABLE public.finance_sheet_sync TO safereturn_worker;
CREATE POLICY sr_safereturn_worker_update ON public.finance_sheet_sync FOR UPDATE TO safereturn_worker USING (public.sr_worker_id() IS NOT NULL) WITH CHECK (public.sr_worker_id() IS NOT NULL);
ALTER FUNCTION public.sr_guard_qr() SECURITY DEFINER;
ALTER FUNCTION public.sr_guard_qr() SET search_path TO pg_catalog;
ALTER FUNCTION public.sr_check_pair() SECURITY DEFINER;
ALTER FUNCTION public.sr_check_pair() SET search_path TO pg_catalog;
ALTER FUNCTION public.sr_profile_type() SECURITY DEFINER;
ALTER FUNCTION public.sr_profile_type() SET search_path TO pg_catalog;
ALTER FUNCTION public.sr_order_history() SECURITY DEFINER;
ALTER FUNCTION public.sr_order_history() SET search_path TO pg_catalog;
ALTER FUNCTION public.sr_qr_use_relation() SECURITY DEFINER;
ALTER FUNCTION public.sr_qr_use_relation() SET search_path TO pg_catalog;
ALTER FUNCTION public.sr_pair_claim_guard() SECURITY DEFINER;
ALTER FUNCTION public.sr_pair_claim_guard() SET search_path TO pg_catalog;
ALTER FUNCTION public.sr_payment_history() SECURITY DEFINER;
ALTER FUNCTION public.sr_payment_history() SET search_path TO pg_catalog;
ALTER FUNCTION public.sr_check_payment() SECURITY DEFINER;
ALTER FUNCTION public.sr_check_payment() SET search_path TO pg_catalog;
ALTER FUNCTION public.sr_check_order() SECURITY DEFINER;
ALTER FUNCTION public.sr_check_order() SET search_path TO pg_catalog;
ALTER FUNCTION public.sr_shipment_guard() SECURITY DEFINER;
ALTER FUNCTION public.sr_shipment_guard() SET search_path TO pg_catalog;
ALTER FUNCTION public.sr_check_shipment() SECURITY DEFINER;
ALTER FUNCTION public.sr_check_shipment() SET search_path TO pg_catalog;
REVOKE ALL ON FUNCTION public.sr_actor_id() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_append_only() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_can_message(uuid) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_check_order() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_check_pair() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_check_payment() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_check_shipment() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_context_guard() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_entitled_pair(uuid) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_finder_guard() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_finder_outbox_check() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_guard_qr() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_idempotency_guard() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_is_staff(text[]) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_job_relation() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_lease_transition() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_mfa() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_order_history() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_outbox_relation() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_owns_order(uuid) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_owns_pair(uuid) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_owns_qr(uuid) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_pair_claim_guard() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_payment_history() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_print_guard() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_profile_type() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_qr_use_relation() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_retention_guard() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_safe_json() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_scan_binding() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_scan_pair(uuid) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_shipment_guard() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_submission_id() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_touch_updated_at() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_worker_id() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_worker_print(uuid) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.sr_actor_id() TO safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_can_message(uuid) TO safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_entitled_pair(uuid) TO safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_is_staff(text[]) TO safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_mfa() TO safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_owns_order(uuid) TO safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_owns_pair(uuid) TO safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_owns_qr(uuid) TO safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_scan_binding() TO safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_scan_pair(uuid) TO safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_submission_id() TO safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_worker_id() TO safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_worker_print(uuid) TO safereturn_worker;
REVOKE ALL ON FUNCTION public.sr_worker_cleanup(text,uuid) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.sr_worker_cleanup(text,uuid) TO safereturn_worker;
REVOKE ALL ON FUNCTION public.sr_api_private_update() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.sr_worker_order(uuid) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.sr_worker_order(uuid) TO safereturn_worker;
GRANT SELECT (id,order_id,provider_key,state,amount,currency_code,verified_at) ON public.payment_attempts TO safereturn_worker;
CREATE POLICY sr_safereturn_worker_select ON public.payment_attempts FOR SELECT TO safereturn_worker USING (public.sr_worker_order(order_id));""",
]


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = set(inspector.get_table_names(schema="public"))
    if existing.intersection(TABLES):
        raise RuntimeError(
            "Existing workflow tables require explicit reconciliation; nothing changed"
        )
    if bind.execute(
        text("SELECT count(*) FROM pg_roles WHERE rolname=ANY(:roles)"),
        {"roles": ROLES},
    ).scalar_one():
        raise RuntimeError(
            "Existing runtime roles require explicit reconciliation; nothing changed"
        )
    if not {"orders", "qr_codes"}.issubset(existing):
        raise RuntimeError("Previous identity/commerce revision is required")
    op.execute("SET LOCAL lock_timeout='5s'")
    op.execute("SET LOCAL search_path=public,pg_catalog")
    for statement in DDL:
        op.execute(statement)


def downgrade():
    raise RuntimeError(
        "Destructive downgrade disabled; use reviewed forward fix for roles and durable history"
    )
