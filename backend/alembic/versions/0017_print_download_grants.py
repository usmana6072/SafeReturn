"""Scoped private print access, immutable QA and authorized manifest projection."""

from alembic import op

revision = "0017_print_download_grants"
down_revision = "0016_checkout_quotes"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
SET LOCAL lock_timeout='5s';
CREATE TABLE public.print_download_grants (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), artifact_id uuid NOT NULL REFERENCES public.print_artifacts(id) ON DELETE RESTRICT,
 granted_to uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT, token_hash bytea NOT NULL UNIQUE CHECK(octet_length(token_hash)=32),
 expires_at timestamptz NOT NULL CHECK(expires_at>created_at), used_at timestamptz, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_print_grants_expiry ON public.print_download_grants(expires_at) WHERE used_at IS NULL;
ALTER TABLE public.print_download_grants ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.print_download_grants FROM PUBLIC,anon,authenticated;
GRANT SELECT,INSERT ON public.print_download_grants TO safereturn_api;
GRANT UPDATE(used_at) ON public.print_download_grants TO safereturn_api;
CREATE POLICY sr_print_grant_select ON public.print_download_grants FOR SELECT TO safereturn_api USING(granted_to=public.sr_actor_id() AND public.sr_is_staff(ARRAY['operations']));
CREATE POLICY sr_print_grant_insert ON public.print_download_grants FOR INSERT TO safereturn_api WITH CHECK(granted_to=public.sr_actor_id() AND public.sr_is_staff(ARRAY['operations']) AND expires_at<=clock_timestamp()+interval '5 minutes');
CREATE POLICY sr_print_grant_use ON public.print_download_grants FOR UPDATE TO safereturn_api USING(granted_to=public.sr_actor_id() AND public.sr_is_staff(ARRAY['operations']) AND used_at IS NULL AND expires_at>clock_timestamp()) WITH CHECK(granted_to=public.sr_actor_id() AND public.sr_is_staff(ARRAY['operations']));
CREATE TABLE public.print_job_qa (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), print_job_id uuid NOT NULL REFERENCES public.print_jobs(id),
 inspected_by uuid NOT NULL REFERENCES auth.users(id), approved boolean NOT NULL,
 artifact_sha256 char(64) NOT NULL CHECK(artifact_sha256~'^[0-9a-f]{64}$'),
 observations jsonb NOT NULL CHECK(jsonb_typeof(observations)='object'), reason text NOT NULL CHECK(length(trim(reason)) BETWEEN 4 AND 1000), created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.print_job_qa ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.print_job_qa FROM PUBLIC,anon,authenticated;
GRANT SELECT,INSERT ON public.print_job_qa TO safereturn_api;
CREATE POLICY sr_print_qa_read ON public.print_job_qa FOR SELECT TO safereturn_api USING(public.sr_is_staff(ARRAY['operations']));
CREATE POLICY sr_print_qa_insert ON public.print_job_qa FOR INSERT TO safereturn_api WITH CHECK(inspected_by=public.sr_actor_id() AND public.sr_is_staff(ARRAY['operations']));
CREATE TRIGGER sr_print_qa_append BEFORE UPDATE OR DELETE ON public.print_job_qa FOR EACH ROW EXECUTE FUNCTION public.sr_append_only();
CREATE UNIQUE INDEX uq_print_active_pdf ON public.print_artifacts(print_job_id) WHERE format='pdf' AND deleted_at IS NULL;
CREATE FUNCTION public.sr_print_artifact_identity() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF (NEW.id,NEW.print_job_id,NEW.bucket,NEW.object_key,NEW.format,NEW.sha256_hex,NEW.size_bytes,NEW.created_at) IS DISTINCT FROM (OLD.id,OLD.print_job_id,OLD.bucket,OLD.object_key,OLD.format,OLD.sha256_hex,OLD.size_bytes,OLD.created_at) THEN RAISE EXCEPTION 'Print artifact identity is immutable' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_print_artifact_identity BEFORE UPDATE ON public.print_artifacts FOR EACH ROW EXECUTE FUNCTION public.sr_print_artifact_identity();
CREATE FUNCTION public.sr_print_qa_complete() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NEW.status='qa_passed' AND NOT EXISTS(SELECT 1 FROM public.print_job_qa q JOIN public.print_artifacts a ON a.print_job_id=q.print_job_id WHERE q.print_job_id=NEW.id AND q.approved AND q.artifact_sha256=a.sha256_hex AND a.deleted_at IS NULL) THEN RAISE EXCEPTION 'Print release requires artifact-specific physical QA' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER sr_print_qa_complete AFTER INSERT OR UPDATE ON public.print_jobs DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_print_qa_complete();
REVOKE ALL ON FUNCTION public.sr_print_artifact_identity(),public.sr_print_qa_complete() FROM PUBLIC,anon,authenticated;
CREATE FUNCTION public.sr_print_occurrences(oid uuid) RETURNS TABLE(use_id uuid,qr_id uuid,tag_type text,copies integer,size_mm numeric,template_key text,template_version integer,public_token text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE n integer;
BEGIN
 IF NOT(public.sr_is_staff(ARRAY['operations']) OR EXISTS(SELECT 1 FROM public.durable_jobs d WHERE d.order_id=oid AND d.job_kind IN('print.render','allocation.finalize') AND d.status='leased' AND d.lease_owner=public.sr_worker_id() AND d.lease_until>clock_timestamp())) THEN RETURN; END IF;
 PERFORM 1 FROM public.orders WHERE id=oid AND order_status='placed' AND payment_status='verified' AND EXISTS(SELECT 1 FROM public.payment_attempts WHERE order_id=oid AND state='verified' AND amount=public.orders.total_pkr AND currency_code=public.orders.currency_code) FOR SHARE;
 IF NOT FOUND THEN RETURN; END IF;
 RETURN QUERY SELECT u.id,q.id,q.tag_type::text,u.copies,i.size_mm_snapshot,i.template_key_snapshot,i.template_version_snapshot,q.public_token::text
 FROM public.order_item_qr_uses u JOIN public.order_items i ON i.id=u.order_item_id
 JOIN public.qr_codes q ON q.id=u.qr_code_id JOIN public.tag_pairs p ON p.id=q.pair_id
 LEFT JOIN public.order_pair_units pu ON pu.id=u.pair_unit_id AND pu.order_id=i.order_id AND pu.pair_id=q.pair_id
 WHERE i.order_id=oid AND i.fulfillment_method_snapshot='pdf_label' AND u.tag_type_snapshot=q.tag_type AND q.is_current AND q.revoked_at IS NULL AND q.public_status IN('unactivated','active') AND p.revoked_at IS NULL
 AND ((u.use_kind='new_pair' AND pu.status='allocated') OR (u.use_kind='existing_owned' AND p.owner_user_id=(SELECT customer_user_id FROM public.orders WHERE id=oid)))
 ORDER BY CASE q.tag_type WHEN 'lost' THEN 0 ELSE 1 END,i.size_mm_snapshot,i.variant_id,u.id
 FOR SHARE OF q,p;
 GET DIAGNOSTICS n=ROW_COUNT;
 IF n=0 OR n<>(SELECT count(*) FROM public.order_item_qr_uses u JOIN public.order_items i ON i.id=u.order_item_id WHERE i.order_id=oid) THEN RAISE EXCEPTION 'Print binding is no longer valid' USING ERRCODE='23514'; END IF;
END $$;
REVOKE ALL ON FUNCTION public.sr_print_occurrences(uuid) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.sr_print_occurrences(uuid) TO safereturn_api,safereturn_worker;
CREATE FUNCTION public.sr_print_order_lock(oid uuid) RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NOT(public.sr_is_staff(ARRAY['operations']) OR EXISTS(SELECT 1 FROM public.durable_jobs d WHERE d.order_id=oid AND d.job_kind='allocation.finalize' AND d.idempotency_key LIKE 'print.request:%' AND d.status='leased' AND d.lease_owner=public.sr_worker_id() AND d.lease_until>clock_timestamp())) THEN RETURN NULL; END IF;
 PERFORM 1 FROM public.orders WHERE id=oid FOR UPDATE;
 IF FOUND THEN RETURN oid; END IF;
 RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION public.sr_print_order_lock(uuid) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.sr_print_order_lock(uuid) TO safereturn_api,safereturn_worker;
CREATE OR REPLACE FUNCTION public.sr_print_guard() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NEW.status IN('queued','rendering','ready','downloaded','qa_passed') AND (NOT EXISTS(SELECT 1 FROM public.orders o JOIN public.payment_attempts a ON a.order_id=o.id WHERE o.id=NEW.order_id AND o.order_status='placed' AND o.payment_status='verified' AND a.state='verified' AND a.amount=o.total_pkr AND a.currency_code=o.currency_code) OR NOT EXISTS(SELECT 1 FROM public.order_pair_units WHERE order_id=NEW.order_id AND status='allocated')) THEN RAISE EXCEPTION 'Print production requires settled allocated order' USING ERRCODE='23514'; END IF;
 IF TG_OP='UPDATE' AND (NEW.id,NEW.order_id,NEW.job_revision,NEW.template_fingerprint,NEW.render_config,NEW.created_at) IS DISTINCT FROM (OLD.id,OLD.order_id,OLD.job_revision,OLD.template_fingerprint,OLD.render_config,OLD.created_at) THEN RAISE EXCEPTION 'Print job specification is immutable' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION public.sr_insert_print_job(jid uuid,oid uuid,rev integer,fp text,cfg jsonb,payload bytea,kv smallint) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NOT(public.sr_is_staff(ARRAY['operations']) OR EXISTS(SELECT 1 FROM public.durable_jobs d WHERE d.order_id=oid AND d.job_kind='allocation.finalize' AND d.idempotency_key LIKE 'print.request:%' AND d.status='leased' AND d.lease_owner=public.sr_worker_id() AND d.lease_until>clock_timestamp())) THEN RAISE EXCEPTION 'Print enqueue denied' USING ERRCODE='42501'; END IF;
 IF cfg->>'template_key' IS DISTINCT FROM 'safereturn-locked-v1' OR payload IS NULL OR octet_length(payload)<32 OR kv IS NULL OR kv<1 OR fp IS NULL OR fp!~'^[0-9a-f]{64}$' THEN RAISE EXCEPTION 'Invalid frozen print configuration' USING ERRCODE='23514'; END IF;
 PERFORM 1 FROM public.orders WHERE id=oid FOR UPDATE;
 INSERT INTO public.print_jobs(id,order_id,job_revision,status,template_fingerprint,render_config) VALUES(jid,oid,rev,'queued',fp,cfg);
 INSERT INTO public.durable_jobs(job_kind,aggregate_type,aggregate_id,order_id,print_job_id,idempotency_key,payload_ciphertext,payload_key_version)
 VALUES('print.render','print_job',jid,oid,jid,'print.render:'||jid,payload,kv);
END $$;
REVOKE ALL ON FUNCTION public.sr_insert_print_job(uuid,uuid,integer,text,jsonb,bytea,smallint) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.sr_insert_print_job(uuid,uuid,integer,text,jsonb,bytea,smallint) TO safereturn_api,safereturn_worker;
""")


def downgrade():
    raise RuntimeError(
        "Private printing is forward-only; restore prior application with worker disabled"
    )
