-- Task 5.4A approved synthetic implementation. No automatic historical adoption.
CREATE TABLE public.manufacturing_sources (
 batch_id uuid PRIMARY KEY REFERENCES public.qr_batches(id) ON DELETE RESTRICT,
 generation_actor uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 generation_key text NOT NULL, generation_request_hash text NOT NULL CHECK(generation_request_hash ~ '^[0-9a-f]{64}$'),
 printer_key_fingerprint text NOT NULL CHECK(printer_key_fingerprint ~ '^[0-9a-f]{64}$'),
 manifest_sha256 text NOT NULL CHECK(manifest_sha256 ~ '^[0-9a-f]{64}$'),
 identity_sha256 text NOT NULL CHECK(identity_sha256 ~ '^[0-9a-f]{64}$'),
 pair_count integer NOT NULL CHECK(pair_count BETWEEN 1 AND 1000),
 payload_ciphertext bytea NOT NULL CHECK(octet_length(payload_ciphertext) BETWEEN 32 AND 2800000),
 payload_key_version smallint NOT NULL CHECK(payload_key_version>0),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE public.manufacturing_approvals (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), batch_id uuid NOT NULL REFERENCES public.manufacturing_sources(batch_id) ON DELETE RESTRICT,
 executor uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 approver uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT CHECK(approver<>executor),
 printer_key_fingerprint text NOT NULL CHECK(printer_key_fingerprint ~ '^[0-9a-f]{64}$'),
 manifest_sha256 text NOT NULL CHECK(manifest_sha256 ~ '^[0-9a-f]{64}$'),
 acknowledgement_public_key text NOT NULL CHECK(length(acknowledgement_public_key) BETWEEN 43 AND 44),
 approval_reference uuid NOT NULL, revoked_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE UNIQUE INDEX uq_mfg_active_approval ON public.manufacturing_approvals(batch_id) WHERE revoked_at IS NULL;
CREATE TABLE public.manufacturing_exports (
 id uuid PRIMARY KEY, batch_id uuid NOT NULL UNIQUE REFERENCES public.manufacturing_sources(batch_id) ON DELETE RESTRICT,
 approval_id uuid NOT NULL REFERENCES public.manufacturing_approvals(id) ON DELETE RESTRICT,
 revision integer NOT NULL DEFAULT 1 CHECK(revision BETWEEN 1 AND 2147483646),
 status text NOT NULL DEFAULT 'queued' CHECK(status IN('queued','ready','awaiting_ack','accepted','failed')),
 delivery_id uuid, created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE public.manufacturing_events (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), batch_id uuid NOT NULL REFERENCES public.manufacturing_sources(batch_id) ON DELETE RESTRICT,
 job_id uuid REFERENCES public.manufacturing_exports(id) ON DELETE RESTRICT,
 event_type text NOT NULL CHECK(event_type IN('source_registered','approved','revoked','queued','ready','failed','grant_issued','download_consumed','accepted','not_received')),
 revision integer NOT NULL, actor_id uuid REFERENCES auth.users(id) ON DELETE RESTRICT,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE public.manufacturing_receipts (
 scope text PRIMARY KEY CHECK(scope ~ '^[0-9a-f]{64}$'), batch_id uuid NOT NULL REFERENCES public.manufacturing_sources(batch_id) ON DELETE RESTRICT,
 actor_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 request_hash text NOT NULL CHECK(request_hash ~ '^[0-9a-f]{64}$'),
 cipher bytea NOT NULL CHECK(octet_length(cipher) BETWEEN 32 AND 16000), key_version smallint NOT NULL CHECK(key_version>0),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE public.manufacturing_grants (
 id uuid PRIMARY KEY, job_id uuid NOT NULL REFERENCES public.manufacturing_exports(id) ON DELETE RESTRICT,
 actor_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT, session_id uuid NOT NULL,
 revision integer NOT NULL, token_hash text NOT NULL CHECK(token_hash ~ '^[0-9a-f]{64}$'),
 expires_at timestamptz NOT NULL, used_at timestamptz, superseded_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(), CHECK(expires_at>created_at AND expires_at<=created_at+interval '300 seconds')
);
CREATE INDEX idx_mfg_grants_job ON public.manufacturing_grants(job_id,session_id);
CREATE TABLE public.manufacturing_handoffs (
 delivery_id uuid PRIMARY KEY, job_id uuid NOT NULL REFERENCES public.manufacturing_exports(id) ON DELETE RESTRICT,
 recorder uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 signed_record jsonb NOT NULL, signature text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
DO $$ DECLARE rel text; BEGIN
 FOREACH rel IN ARRAY ARRAY['manufacturing_sources','manufacturing_approvals','manufacturing_exports','manufacturing_events','manufacturing_receipts','manufacturing_grants','manufacturing_handoffs'] LOOP
  EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',rel);
  EXECUTE format('REVOKE ALL ON public.%I FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker',rel);
 END LOOP;
 FOREACH rel IN ARRAY ARRAY['manufacturing_sources','manufacturing_events','manufacturing_receipts','manufacturing_handoffs'] LOOP
  EXECUTE format('CREATE TRIGGER sr_mfg_append BEFORE UPDATE OR DELETE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.sr_append_only()',rel);
 END LOOP;
END $$;
ALTER TABLE public.durable_jobs DROP CONSTRAINT ck_durable_jobs_kind;
ALTER TABLE public.durable_jobs ADD CONSTRAINT ck_durable_jobs_kind CHECK(job_kind IN('allocation.finalize','print.render','finance.sync','retention.cleanup','manufacturing.export'));
ALTER TABLE public.durable_jobs DROP CONSTRAINT ck_durable_jobs_order;
ALTER TABLE public.durable_jobs ADD CONSTRAINT ck_durable_jobs_order CHECK(job_kind IN('retention.cleanup','manufacturing.export') OR order_id IS NOT NULL);

-- Row locks always begin batch -> approval -> export -> durable job -> grant.
-- All provisioning/revocation uses that same batch lock. No runtime table writes.
CREATE FUNCTION public.sr_mfg_pairs(bid uuid) RETURNS jsonb
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT COALESCE(jsonb_agg(jsonb_build_object('pair_reference',p.pair_reference,'tags',
  (SELECT COALESCE(jsonb_agg(jsonb_build_object('tag_type',q.tag_type,'public_token',q.public_token) ORDER BY q.tag_type),'[]'::jsonb)
   FROM (SELECT tag_type,public_token FROM public.qr_codes WHERE pair_id=p.id AND is_current ORDER BY tag_type LIMIT 3) q)) ORDER BY p.pair_reference),'[]'::jsonb)
 FROM (SELECT id,pair_reference FROM public.tag_pairs WHERE batch_id=bid ORDER BY pair_reference LIMIT 1001) p
$$;
CREATE FUNCTION public.sr_mfg_eligible(bid uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT 1 FROM public.qr_batches WHERE id=bid AND status='generated' AND printed_at IS NULL)
 AND NOT EXISTS(SELECT 1 FROM public.tag_pairs p WHERE p.batch_id=bid AND
  (p.owner_user_id IS NOT NULL OR p.ownership_status<>'unclaimed' OR p.inventory_status<>'generated' OR EXISTS(SELECT 1 FROM public.order_pair_units u WHERE u.pair_id=p.id AND u.status IN('reserved','allocated'))
   OR EXISTS(SELECT 1 FROM public.qr_codes q WHERE q.pair_id=p.id AND (NOT q.is_current OR q.public_status<>'unactivated'))))
$$;
CREATE FUNCTION public.sr_mfg_authorized(bid uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT 1 FROM public.manufacturing_approvals a JOIN public.manufacturing_sources s ON s.batch_id=a.batch_id
 WHERE a.batch_id=bid AND a.revoked_at IS NULL AND a.executor<>a.approver
 AND a.manifest_sha256=s.manifest_sha256 AND a.printer_key_fingerprint=s.printer_key_fingerprint
 AND EXISTS(SELECT 1 FROM public.staff_roles WHERE user_id=a.executor AND role='operations' AND revoked_at IS NULL)
 AND EXISTS(SELECT 1 FROM public.staff_roles WHERE user_id=a.approver AND role='security_admin' AND revoked_at IS NULL))
$$;
CREATE FUNCTION public.sr_mfg_context(bid uuid,sid uuid) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE s public.manufacturing_sources; a public.manufacturing_approvals; j public.manufacturing_exports; attempts integer;
BEGIN
 IF NOT public.sr_is_staff(ARRAY['operations']) OR NOT EXISTS(SELECT 1 FROM public.sr_account_session_state(sid)) THEN RETURN NULL; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.manufacturing_approvals WHERE batch_id=bid AND executor=public.sr_actor_id() AND revoked_at IS NULL) THEN RETURN NULL; END IF;
 PERFORM 1 FROM public.qr_batches WHERE id=bid FOR UPDATE;
 SELECT * INTO a FROM public.manufacturing_approvals WHERE batch_id=bid AND revoked_at IS NULL FOR UPDATE;
 IF NOT FOUND OR a.executor<>public.sr_actor_id() OR NOT public.sr_mfg_authorized(bid) THEN RETURN NULL; END IF;
 SELECT * INTO s FROM public.manufacturing_sources WHERE batch_id=bid;
 IF NOT FOUND THEN RETURN jsonb_build_object('error','ORIGINAL_PAYLOAD_REQUIRED'); END IF;
 PERFORM 1 FROM public.tag_pairs WHERE batch_id=bid ORDER BY id FOR UPDATE;
 PERFORM 1 FROM public.qr_codes WHERE pair_id IN(SELECT id FROM public.tag_pairs WHERE batch_id=bid) ORDER BY id FOR UPDATE;
 IF NOT public.sr_mfg_eligible(bid) OR s.manifest_sha256 IS DISTINCT FROM (SELECT print_manifest_checksum FROM public.qr_batches WHERE id=bid) THEN RETURN jsonb_build_object('error','BATCH_RECONCILIATION_REQUIRED'); END IF;
 SELECT * INTO j FROM public.manufacturing_exports WHERE batch_id=bid FOR UPDATE;
 IF j.id IS NOT NULL AND j.approval_id<>a.id THEN RETURN jsonb_build_object('error','PRODUCTION_AUTHORITY_CHANGED'); END IF;
 SELECT attempt_count INTO attempts FROM public.durable_jobs WHERE id=j.id FOR UPDATE;
 RETURN jsonb_build_object('approval_id',a.id,'executor',a.executor,'approver',a.approver,'printer_key_fingerprint',s.printer_key_fingerprint,
  'pair_count',s.pair_count,'identity_sha256',s.identity_sha256,'pairs',public.sr_mfg_pairs(bid),
  'manifest_sha256',s.manifest_sha256,'revision',COALESCE(j.revision,0),
  'source',jsonb_build_object('cipher',encode(s.payload_ciphertext,'base64'),'key_version',s.payload_key_version),
  'job',CASE WHEN j.id IS NULL THEN NULL ELSE jsonb_build_object('job_id',j.id,'batch_id',bid,'revision',j.revision,'status',j.status,'manifest_sha256',s.manifest_sha256,'attempt_count',COALESCE(attempts,0)) END);
END $$;

CREATE FUNCTION public.sr_mfg_apply(op text,bid uuid,body jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a public.manufacturing_approvals; s public.manufacturing_sources; j public.manufacturing_exports; g public.manufacturing_grants; r public.manufacturing_receipts;
 sid uuid; uid uuid:=public.sr_actor_id(); event_name text;
BEGIN
 IF NOT public.sr_is_staff(ARRAY['operations']) THEN RETURN NULL; END IF;
 PERFORM 1 FROM public.qr_batches WHERE id=bid FOR UPDATE;
 SELECT * INTO a FROM public.manufacturing_approvals WHERE batch_id=bid AND revoked_at IS NULL FOR UPDATE;
 IF NOT FOUND OR a.executor<>uid OR NOT public.sr_mfg_authorized(bid) THEN RETURN NULL; END IF;
 IF NOT public.sr_mfg_eligible(bid) THEN RETURN jsonb_build_object('error','BATCH_RECONCILIATION_REQUIRED'); END IF;
 SELECT * INTO s FROM public.manufacturing_sources WHERE batch_id=bid;
 SELECT * INTO j FROM public.manufacturing_exports WHERE batch_id=bid FOR UPDATE;
 IF op='receipt' THEN
  SELECT * INTO r FROM public.manufacturing_receipts WHERE scope=body->>'scope' AND batch_id=bid AND actor_id=uid;
  IF NOT FOUND THEN RETURN '{}'::jsonb; END IF;
  RETURN jsonb_build_object('request_hash',r.request_hash,'cipher',encode(r.cipher,'base64'),'key_version',r.key_version);
 ELSIF op='save_receipt' THEN
  INSERT INTO public.manufacturing_receipts(scope,batch_id,actor_id,request_hash,cipher,key_version)
  VALUES(body->>'scope',bid,uid,body->>'request_hash',decode(body->>'cipher','base64'),(body->>'key_version')::smallint);
  RETURN '{}'::jsonb;
 ELSIF op='enqueue' THEN
  IF j.id IS NOT NULL OR (body->>'expected_revision')::integer IS DISTINCT FROM 0 OR body->>'source_sha256' IS DISTINCT FROM s.manifest_sha256 THEN RETURN jsonb_build_object('error','VERSION_MISMATCH'); END IF;
  INSERT INTO public.manufacturing_exports(id,batch_id,approval_id) VALUES((body->>'job_id')::uuid,bid,a.id) RETURNING * INTO j;
  INSERT INTO public.durable_jobs(id,job_kind,aggregate_type,aggregate_id,idempotency_key,payload_ciphertext,payload_key_version)
   VALUES(j.id,'manufacturing.export','manufacturing_export',j.id,'manufacturing.export:'||bid::text,s.payload_ciphertext,s.payload_key_version);
  INSERT INTO public.manufacturing_events(batch_id,job_id,event_type,revision,actor_id) VALUES(bid,j.id,'queued',1,uid);
  RETURN jsonb_build_object('job_id',j.id,'batch_id',bid,'revision',1,'status','queued','manifest_sha256',s.manifest_sha256);
 END IF;
 IF j.id IS NULL OR j.id IS DISTINCT FROM (body->>'job_id')::uuid THEN RETURN NULL; END IF;
 IF j.approval_id<>a.id THEN RETURN jsonb_build_object('error','PRODUCTION_AUTHORITY_CHANGED'); END IF;
 sid:=(body->>'session_id')::uuid;
 IF NOT EXISTS(SELECT 1 FROM public.sr_account_session_state(sid)) THEN RETURN NULL; END IF;
 IF op='grant' THEN
  IF j.status<>'ready' THEN RETURN jsonb_build_object('error','HANDOFF_RECONCILIATION_REQUIRED'); END IF;
  IF j.revision IS DISTINCT FROM (body->>'expected_revision')::integer THEN RETURN jsonb_build_object('error','VERSION_MISMATCH'); END IF;
  UPDATE public.manufacturing_grants SET superseded_at=clock_timestamp() WHERE job_id=j.id AND session_id=sid AND used_at IS NULL AND superseded_at IS NULL;
  INSERT INTO public.manufacturing_grants(id,job_id,actor_id,session_id,revision,token_hash,expires_at,created_at)
   VALUES((body->>'grant_id')::uuid,j.id,uid,sid,j.revision,body->>'token_hash',clock_timestamp()+interval '299 seconds',clock_timestamp()) RETURNING * INTO g;
  INSERT INTO public.manufacturing_events(batch_id,job_id,event_type,revision,actor_id) VALUES(bid,j.id,'grant_issued',j.revision,uid);
  RETURN jsonb_build_object('grant_id',g.id,'job_id',j.id,'revision',j.revision,'expires_at',g.expires_at);
 ELSIF op IN('grant_live','consume') THEN
  SELECT * INTO g FROM public.manufacturing_grants WHERE id=(body->>'grant_id')::uuid AND job_id=j.id AND actor_id=uid AND session_id=sid FOR UPDATE;
  IF NOT FOUND OR g.used_at IS NOT NULL OR g.superseded_at IS NOT NULL OR g.expires_at<=clock_timestamp() OR g.revision<>j.revision OR j.status<>'ready' THEN RETURN jsonb_build_object('error','GRANT_GONE'); END IF;
  IF op='grant_live' THEN RETURN jsonb_build_object('token_hash',g.token_hash); END IF;
  IF g.token_hash IS DISTINCT FROM body->>'token_hash' THEN RETURN jsonb_build_object('error','GRANT_GONE'); END IF;
  UPDATE public.manufacturing_grants SET used_at=clock_timestamp() WHERE id=g.id AND used_at IS NULL AND superseded_at IS NULL AND expires_at>clock_timestamp() RETURNING * INTO g;
  IF NOT FOUND THEN RETURN jsonb_build_object('error','GRANT_GONE'); END IF;
  UPDATE public.manufacturing_exports SET status='awaiting_ack',revision=revision+1,delivery_id=g.id WHERE id=j.id;
  UPDATE public.manufacturing_grants SET superseded_at=clock_timestamp() WHERE job_id=j.id AND id<>g.id AND used_at IS NULL AND superseded_at IS NULL;
  INSERT INTO public.manufacturing_events(batch_id,job_id,event_type,revision,actor_id) VALUES(bid,j.id,'download_consumed',j.revision+1,uid);
  RETURN '{}'::jsonb;
 END IF;
 RAISE EXCEPTION 'Unknown manufacturing operation' USING ERRCODE='22023';
END $$;

-- Runtime source enrollment only from the completed original generation receipt.
CREATE FUNCTION public.sr_mfg_register(bid uuid,body jsonb) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE raw bytea; receipt public.idempotency_records; model jsonb; uid uuid:=public.sr_actor_id();
BEGIN
 IF NOT public.sr_is_staff(ARRAY['operations']) THEN RETURN false; END IF;
 PERFORM 1 FROM public.qr_batches WHERE id=bid AND status='generated' AND printed_at IS NULL FOR UPDATE;
 IF NOT FOUND THEN RETURN false; END IF;
 model:=(body->>'generation_request')::jsonb;
 IF model->>'printer_key_fingerprint' IS DISTINCT FROM body->>'printer_key_fingerprint' OR (model->>'pair_count')::integer IS DISTINCT FROM (body->>'pair_count')::integer THEN RETURN false; END IF;
 SELECT * INTO receipt FROM public.idempotency_records WHERE actor_scope=uid::text AND operation='admin.qr-batches.create' AND idempotency_key=body->>'generation_key' FOR UPDATE;
 IF NOT FOUND OR receipt.state<>'completed' OR receipt.response_key_version<>1 OR receipt.request_hash IS DISTINCT FROM encode(sha256(convert_to(body->>'generation_request','UTF8')),'hex') THEN RETURN false; END IF;
 raw:=receipt.response_body_ciphertext;
 IF encode(sha256(raw),'hex') IS DISTINCT FROM (SELECT print_manifest_checksum FROM public.qr_batches WHERE id=bid) OR NOT EXISTS(
  SELECT 1 FROM public.audit_events WHERE actor_user_id=uid AND actor_kind='staff' AND action='inventory.qr_batch.generated' AND target_id=bid AND request_id=encode(sha256(convert_to(body->>'generation_key','UTF8')),'hex')) THEN RETURN false; END IF;
 IF body->'pairs' IS DISTINCT FROM public.sr_mfg_pairs(bid) THEN RETURN false; END IF;
 IF jsonb_array_length(body->'pairs') IS DISTINCT FROM (body->>'pair_count')::integer OR EXISTS(
  SELECT 1 FROM jsonb_array_elements(body->'pairs') p WHERE jsonb_array_length(p->'tags')<>2 OR
  (SELECT count(DISTINCT t->>'tag_type') FROM jsonb_array_elements(p->'tags') t WHERE t->>'tag_type' IN('lost','ice'))<>2
 ) OR (SELECT count(DISTINCT t->>'public_token') FROM jsonb_array_elements(body->'pairs') p CROSS JOIN LATERAL jsonb_array_elements(p->'tags') t)<>2*(body->>'pair_count')::integer THEN RETURN false; END IF;
 INSERT INTO public.manufacturing_sources(batch_id,generation_actor,generation_key,generation_request_hash,printer_key_fingerprint,manifest_sha256,identity_sha256,pair_count,payload_ciphertext,payload_key_version)
 VALUES(bid,uid,body->>'generation_key',receipt.request_hash,body->>'printer_key_fingerprint',encode(sha256(raw),'hex'),body->>'identity_sha256',(body->>'pair_count')::integer,decode(body->>'cipher','base64'),(body->>'key_version')::smallint);
 INSERT INTO public.manufacturing_events(batch_id,event_type,revision,actor_id) VALUES(bid,'source_registered',0,uid);
 RETURN true;
END $$;

-- Controlled privileged runbook only: no runtime EXECUTE permission.
CREATE FUNCTION public.sr_mfg_provision(bid uuid,body jsonb) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE uid uuid:=public.sr_actor_id(); aid uuid:=gen_random_uuid(); executor_id uuid:=(body->>'executor')::uuid;
BEGIN
 IF NOT public.sr_is_staff(ARRAY['security_admin']) OR uid=executor_id THEN RAISE EXCEPTION 'Independent security approval required' USING ERRCODE='42501'; END IF;
 PERFORM 1 FROM public.qr_batches WHERE id=bid FOR UPDATE;
 IF NOT public.sr_mfg_eligible(bid) OR EXISTS(SELECT 1 FROM public.manufacturing_exports WHERE batch_id=bid) OR NOT EXISTS(SELECT 1 FROM public.staff_roles WHERE user_id=executor_id AND role='operations' AND revoked_at IS NULL) THEN RAISE EXCEPTION 'Batch authority conflict' USING ERRCODE='23514'; END IF;
 INSERT INTO public.manufacturing_approvals(id,batch_id,executor,approver,printer_key_fingerprint,manifest_sha256,acknowledgement_public_key,approval_reference)
 SELECT aid,bid,executor_id,uid,s.printer_key_fingerprint,s.manifest_sha256,body->>'acknowledgement_public_key',(body->>'approval_reference')::uuid FROM public.manufacturing_sources s
 WHERE s.batch_id=bid AND s.printer_key_fingerprint=body->>'printer_key_fingerprint' AND s.manifest_sha256=body->>'manifest_sha256';
 IF NOT FOUND THEN RAISE EXCEPTION 'Original source required' USING ERRCODE='23514'; END IF;
 INSERT INTO public.manufacturing_events(batch_id,event_type,revision,actor_id) VALUES(bid,'approved',0,uid);
 RETURN aid;
END $$;
CREATE FUNCTION public.sr_mfg_revoke(bid uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NOT public.sr_is_staff(ARRAY['security_admin']) THEN RAISE EXCEPTION 'Security authority required' USING ERRCODE='42501'; END IF;
 PERFORM 1 FROM public.qr_batches WHERE id=bid FOR UPDATE;
 UPDATE public.manufacturing_approvals SET revoked_at=clock_timestamp() WHERE batch_id=bid AND revoked_at IS NULL;
 IF FOUND THEN INSERT INTO public.manufacturing_events(batch_id,event_type,revision,actor_id) VALUES(bid,'revoked',0,public.sr_actor_id()); END IF;
 UPDATE public.manufacturing_grants SET superseded_at=clock_timestamp() WHERE job_id IN(SELECT id FROM public.manufacturing_exports WHERE batch_id=bid) AND used_at IS NULL AND superseded_at IS NULL;
END $$;

CREATE FUNCTION public.sr_mfg_claim(bid uuid) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE j public.manufacturing_exports; d public.durable_jobs; s public.manufacturing_sources; a public.manufacturing_approvals;
BEGIN
 IF public.sr_worker_id() IS NULL THEN RETURN NULL; END IF;
 PERFORM 1 FROM public.qr_batches WHERE id=bid FOR UPDATE SKIP LOCKED;
 IF NOT FOUND THEN RETURN NULL; END IF;
 SELECT * INTO a FROM public.manufacturing_approvals WHERE batch_id=bid AND revoked_at IS NULL FOR UPDATE;
 IF NOT FOUND OR NOT public.sr_mfg_authorized(bid) OR NOT public.sr_mfg_eligible(bid) THEN RETURN NULL; END IF;
 PERFORM 1 FROM public.tag_pairs WHERE batch_id=bid ORDER BY id FOR UPDATE;
 PERFORM 1 FROM public.qr_codes WHERE pair_id IN(SELECT id FROM public.tag_pairs WHERE batch_id=bid) ORDER BY id FOR UPDATE;
 SELECT * INTO j FROM public.manufacturing_exports WHERE batch_id=bid AND status='queued' FOR UPDATE;
 IF NOT FOUND OR j.approval_id<>a.id THEN RETURN NULL; END IF;
 SELECT * INTO d FROM public.durable_jobs WHERE id=j.id AND job_kind='manufacturing.export' AND ((status IN('pending','retry') AND next_attempt_at<=clock_timestamp()) OR (status='leased' AND lease_until<=clock_timestamp())) FOR UPDATE SKIP LOCKED;
 IF NOT FOUND THEN RETURN NULL; END IF;
 IF d.attempt_count>=5 THEN
  UPDATE public.durable_jobs SET status='dead',lease_owner=NULL,lease_until=NULL,last_error_code='attempts_exhausted' WHERE id=d.id;
  UPDATE public.manufacturing_exports SET status='failed',revision=revision+1 WHERE id=j.id;
  INSERT INTO public.manufacturing_events(batch_id,job_id,event_type,revision) VALUES(bid,j.id,'failed',j.revision+1);
  RETURN NULL;
 END IF;
 UPDATE public.durable_jobs SET status='leased',lease_owner=public.sr_worker_id(),lease_until=clock_timestamp()+interval '180 seconds',attempt_count=attempt_count+1 WHERE id=d.id RETURNING * INTO d;
 SELECT * INTO s FROM public.manufacturing_sources WHERE batch_id=bid;
 RETURN jsonb_build_object('job_id',j.id,'batch_id',bid,'attempt',d.attempt_count,'owner',d.lease_owner,'revision',j.revision,
 'manifest_sha256',s.manifest_sha256,'identity_sha256',s.identity_sha256,'pair_count',s.pair_count,'pairs',public.sr_mfg_pairs(bid),
 'source',jsonb_build_object('cipher',encode(d.payload_ciphertext,'base64'),'key_version',d.payload_key_version));
END $$;
CREATE FUNCTION public.sr_mfg_finish(bid uuid,body jsonb) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE j public.manufacturing_exports; d public.durable_jobs; a public.manufacturing_approvals; success boolean:=(body->>'success')::boolean;
BEGIN
 IF public.sr_worker_id() IS NULL OR public.sr_worker_id() IS DISTINCT FROM body->>'owner' THEN RETURN false; END IF;
 PERFORM 1 FROM public.qr_batches WHERE id=bid FOR UPDATE;
 SELECT * INTO a FROM public.manufacturing_approvals WHERE batch_id=bid AND revoked_at IS NULL FOR UPDATE;
 IF NOT FOUND OR NOT public.sr_mfg_authorized(bid) OR NOT public.sr_mfg_eligible(bid) THEN RETURN false; END IF;
 PERFORM 1 FROM public.tag_pairs WHERE batch_id=bid ORDER BY id FOR UPDATE;
 PERFORM 1 FROM public.qr_codes WHERE pair_id IN(SELECT id FROM public.tag_pairs WHERE batch_id=bid) ORDER BY id FOR UPDATE;
 IF NOT public.sr_mfg_eligible(bid) THEN RETURN false; END IF;
 IF body->'pairs' IS DISTINCT FROM public.sr_mfg_pairs(bid) OR body->>'manifest_sha256' IS DISTINCT FROM a.manifest_sha256 OR
 a.manifest_sha256 IS DISTINCT FROM (SELECT print_manifest_checksum FROM public.qr_batches WHERE id=bid) THEN RETURN false; END IF;
 SELECT * INTO j FROM public.manufacturing_exports WHERE batch_id=bid AND status='queued' FOR UPDATE;
 IF NOT FOUND OR j.id IS DISTINCT FROM (body->>'job_id')::uuid OR j.approval_id<>a.id OR j.revision IS DISTINCT FROM (body->>'revision')::integer THEN RETURN false; END IF;
 SELECT * INTO d FROM public.durable_jobs WHERE id=j.id AND job_kind='manufacturing.export' AND status='leased' AND lease_owner=public.sr_worker_id() AND attempt_count=(body->>'attempt')::integer AND lease_until>clock_timestamp() FOR UPDATE;
 IF NOT FOUND THEN RETURN false; END IF;
 IF success THEN
  UPDATE public.durable_jobs SET status='completed',completed_at=clock_timestamp(),lease_owner=NULL,lease_until=NULL,last_error_code=NULL WHERE id=d.id AND status='leased' AND lease_owner=public.sr_worker_id() AND attempt_count=(body->>'attempt')::integer AND lease_until>clock_timestamp();
  IF NOT FOUND THEN RETURN false; END IF;
  UPDATE public.manufacturing_exports SET status='ready',revision=revision+1 WHERE id=j.id;
  INSERT INTO public.manufacturing_events(batch_id,job_id,event_type,revision) VALUES(bid,j.id,'ready',j.revision+1);
 ELSE
  UPDATE public.durable_jobs SET status=CASE WHEN attempt_count>=5 THEN 'dead' ELSE 'retry' END,next_attempt_at=clock_timestamp()+interval '30 seconds',lease_owner=NULL,lease_until=NULL,last_error_code='sealed_transport_failed' WHERE id=d.id AND status='leased' AND lease_owner=public.sr_worker_id() AND attempt_count=(body->>'attempt')::integer AND lease_until>clock_timestamp();
  IF NOT FOUND THEN RETURN false; END IF;
  IF d.attempt_count>=5 THEN
   UPDATE public.manufacturing_exports SET status='failed',revision=revision+1 WHERE id=j.id;
   INSERT INTO public.manufacturing_events(batch_id,job_id,event_type,revision) VALUES(bid,j.id,'failed',j.revision+1);
  END IF;
 END IF;
 RETURN true;
END $$;

-- Private preflight for the independently controlled signed-record importer.
CREATE FUNCTION public.sr_mfg_handoff_context(bid uuid) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE j public.manufacturing_exports; a public.manufacturing_approvals;
BEGIN
 IF NOT public.sr_is_staff(ARRAY['security_admin']) THEN RETURN NULL; END IF;
 PERFORM 1 FROM public.qr_batches WHERE id=bid FOR UPDATE;
 SELECT * INTO a FROM public.manufacturing_approvals WHERE batch_id=bid AND revoked_at IS NULL FOR UPDATE;
 IF NOT FOUND OR a.approver<>public.sr_actor_id() OR NOT public.sr_mfg_authorized(bid) THEN RETURN NULL; END IF;
 SELECT * INTO j FROM public.manufacturing_exports WHERE batch_id=bid FOR UPDATE;
 IF NOT FOUND OR j.approval_id<>a.id OR j.status<>'awaiting_ack' THEN RETURN NULL; END IF;
 RETURN jsonb_build_object('job_id',j.id,'revision',j.revision,'delivery_id',j.delivery_id,'acknowledgement_public_key',a.acknowledgement_public_key,'manifest_sha256',a.manifest_sha256,'printer_key_fingerprint',a.printer_key_fingerprint);
END $$;
CREATE FUNCTION public.sr_mfg_record_handoff(bid uuid,body jsonb) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE ctx jsonb; record jsonb:=body->'record'; j public.manufacturing_exports;
BEGIN
 ctx:=public.sr_mfg_handoff_context(bid);
 IF ctx IS NULL OR record->>'format' IS DISTINCT FROM 'safereturn-printer-handoff-v1' OR record->>'batch_id' IS DISTINCT FROM bid::text OR
 record->>'job_id' IS DISTINCT FROM ctx->>'job_id' OR record->>'revision' IS DISTINCT FROM ctx->>'revision' OR record->>'delivery_id' IS DISTINCT FROM ctx->>'delivery_id' OR
 record->>'manifest_sha256' IS DISTINCT FROM ctx->>'manifest_sha256' OR record->>'printer_key_fingerprint' IS DISTINCT FROM ctx->>'printer_key_fingerprint' OR
 COALESCE(record->>'outcome','') NOT IN('accepted','not_received') THEN RETURN false; END IF;
 SELECT * INTO j FROM public.manufacturing_exports WHERE batch_id=bid FOR UPDATE;
 INSERT INTO public.manufacturing_handoffs(delivery_id,job_id,recorder,signed_record,signature) VALUES(j.delivery_id,j.id,public.sr_actor_id(),record,body->>'signature');
 UPDATE public.manufacturing_exports SET status=CASE WHEN record->>'outcome'='accepted' THEN 'accepted' ELSE 'ready' END,revision=revision+1 WHERE id=j.id;
 INSERT INTO public.manufacturing_events(batch_id,job_id,event_type,revision,actor_id) VALUES(bid,j.id,record->>'outcome',j.revision+1,public.sr_actor_id());
 RETURN true;
END $$;

-- No helper ownership changes; only migration owner may execute controlled custody helpers.
REVOKE ALL ON FUNCTION public.sr_mfg_pairs(uuid),public.sr_mfg_eligible(uuid),public.sr_mfg_authorized(uuid),public.sr_mfg_context(uuid,uuid),public.sr_mfg_apply(text,uuid,jsonb),public.sr_mfg_register(uuid,jsonb),public.sr_mfg_provision(uuid,jsonb),public.sr_mfg_revoke(uuid),public.sr_mfg_claim(uuid),public.sr_mfg_finish(uuid,jsonb),public.sr_mfg_handoff_context(uuid),public.sr_mfg_record_handoff(uuid,jsonb) FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_mfg_context(uuid,uuid),public.sr_mfg_apply(text,uuid,jsonb),public.sr_mfg_register(uuid,jsonb) TO safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_mfg_claim(uuid),public.sr_mfg_finish(uuid,jsonb) TO safereturn_worker;

-- Protect bindings even for controlled writers; historical events are append-only.
CREATE FUNCTION public.sr_mfg_binding_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Manufacturing history is immutable' USING ERRCODE='23514'; END IF;
 IF TG_TABLE_NAME='manufacturing_approvals' AND ((to_jsonb(NEW)-'revoked_at') IS DISTINCT FROM (to_jsonb(OLD)-'revoked_at') OR OLD.revoked_at IS NOT NULL OR NEW.revoked_at IS NULL) THEN
  RAISE EXCEPTION 'Only authority revocation is allowed' USING ERRCODE='23514';
 ELSIF TG_TABLE_NAME='manufacturing_exports' AND ((NEW.id,NEW.batch_id,NEW.approval_id,NEW.created_at) IS DISTINCT FROM (OLD.id,OLD.batch_id,OLD.approval_id,OLD.created_at) OR NEW.revision<>OLD.revision+1 OR OLD.status IN('accepted','failed')) THEN
  RAISE EXCEPTION 'Export binding or terminal history is immutable' USING ERRCODE='23514';
 ELSIF TG_TABLE_NAME='manufacturing_exports' AND NOT ((OLD.status='queued' AND NEW.status IN('ready','failed') AND NEW.delivery_id IS NOT DISTINCT FROM OLD.delivery_id) OR (OLD.status='ready' AND NEW.status='awaiting_ack' AND NEW.delivery_id IS NOT NULL) OR (OLD.status='awaiting_ack' AND NEW.status IN('accepted','ready') AND NEW.delivery_id IS NOT DISTINCT FROM OLD.delivery_id)) THEN
  RAISE EXCEPTION 'Invalid manufacturing transition' USING ERRCODE='23514';
 ELSIF TG_TABLE_NAME='manufacturing_grants' AND ((to_jsonb(NEW)-'used_at'-'superseded_at') IS DISTINCT FROM (to_jsonb(OLD)-'used_at'-'superseded_at') OR (OLD.used_at IS NOT NULL AND NEW.used_at IS DISTINCT FROM OLD.used_at) OR (OLD.superseded_at IS NOT NULL AND NEW.superseded_at IS DISTINCT FROM OLD.superseded_at)) THEN
  RAISE EXCEPTION 'Grant binding is immutable' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION public.sr_mfg_binding_guard() FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
CREATE TRIGGER sr_mfg_binding BEFORE UPDATE OR DELETE ON public.manufacturing_approvals FOR EACH ROW EXECUTE FUNCTION public.sr_mfg_binding_guard();
CREATE TRIGGER sr_mfg_binding BEFORE UPDATE OR DELETE ON public.manufacturing_exports FOR EACH ROW EXECUTE FUNCTION public.sr_mfg_binding_guard();
CREATE TRIGGER sr_mfg_binding BEFORE UPDATE OR DELETE ON public.manufacturing_grants FOR EACH ROW EXECUTE FUNCTION public.sr_mfg_binding_guard();
CREATE FUNCTION public.sr_mfg_job_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NEW.job_kind='manufacturing.export' AND (NEW.aggregate_type<>'manufacturing_export' OR NEW.aggregate_id<>NEW.id OR NEW.order_id IS NOT NULL OR NEW.print_job_id IS NOT NULL OR NOT EXISTS(
  SELECT 1 FROM public.manufacturing_exports j JOIN public.manufacturing_sources s ON s.batch_id=j.batch_id
  WHERE j.id=NEW.id AND NEW.payload_ciphertext=s.payload_ciphertext AND NEW.payload_key_version=s.payload_key_version)) THEN
  RAISE EXCEPTION 'Manufacturing durable binding conflict' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION public.sr_mfg_job_guard() FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
CREATE TRIGGER sr_mfg_job BEFORE INSERT OR UPDATE ON public.durable_jobs FOR EACH ROW EXECUTE FUNCTION public.sr_mfg_job_guard();
