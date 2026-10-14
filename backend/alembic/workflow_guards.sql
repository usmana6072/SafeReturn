-- Frozen source for revision 0003_workflows_security.
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
REVOKE ALL ON FUNCTION public.sr_api_pair_ownership() FROM PUBLIC,anon,authenticated;
