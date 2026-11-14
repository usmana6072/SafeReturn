-- Offline/unapplied. No policy, authority, retention duration, key or report seeds.
CREATE TABLE public.abuse_intake_policies (
 policy_id uuid NOT NULL, version integer NOT NULL CHECK(version>0),
 body jsonb NOT NULL CHECK(jsonb_typeof(body)='object'),
 sha256 char(64) NOT NULL CHECK(sha256~'^[0-9a-f]{64}$'),
 effective_at timestamptz NOT NULL, expires_at timestamptz NOT NULL,
 revoked_at timestamptz, PRIMARY KEY(policy_id,version), CHECK(expires_at>effective_at)
);
CREATE TABLE public.abuse_report_attempts (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), kind text NOT NULL CHECK(kind IN('peer','target')),
 scope_hash char(64) NOT NULL CHECK(scope_hash~'^[0-9a-f]{64}$'),
 policy_id uuid NOT NULL, policy_version integer NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(), retention_until timestamptz NOT NULL,
 FOREIGN KEY(policy_id,policy_version) REFERENCES public.abuse_intake_policies(policy_id,version) ON DELETE RESTRICT
);
CREATE INDEX ix_abuse_attempt_scope ON public.abuse_report_attempts(kind,scope_hash,created_at);
CREATE TABLE public.abuse_report_proofs (
 proof_hash char(64) PRIMARY KEY CHECK(proof_hash~'^[0-9a-f]{64}$'),
 policy_id uuid NOT NULL, policy_version integer NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(), retention_until timestamptz NOT NULL,
 FOREIGN KEY(policy_id,policy_version) REFERENCES public.abuse_intake_policies(policy_id,version) ON DELETE RESTRICT
);
CREATE TABLE public.abuse_reports (
 report_id uuid PRIMARY KEY, case_id uuid NOT NULL UNIQUE REFERENCES public.support_cases(id) ON DELETE RESTRICT,
 category text NOT NULL CHECK(category IN('spam','fraud','unsafe_content','other')),
 status text NOT NULL DEFAULT 'received' CHECK(status='received'),
 context_ciphertext bytea NOT NULL CHECK(octet_length(context_ciphertext) BETWEEN 32 AND 2048),
 context_key_version smallint NOT NULL CHECK(context_key_version>0),
 duplicate_hash char(64) NOT NULL CHECK(duplicate_hash~'^[0-9a-f]{64}$'),
 policy_id uuid NOT NULL, policy_version integer NOT NULL, hmac_key_version integer NOT NULL CHECK(hmac_key_version>0),
 consent_version text NOT NULL CHECK(consent_version='abuse-report-v1'),
 consent_accepted boolean NOT NULL DEFAULT true CHECK(consent_accepted),
 consent_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 retention_until timestamptz, case_retention_until timestamptz,
 FOREIGN KEY(policy_id,policy_version) REFERENCES public.abuse_intake_policies(policy_id,version) ON DELETE RESTRICT
);
CREATE INDEX ix_abuse_duplicate ON public.abuse_reports(duplicate_hash);
CREATE TABLE public.abuse_report_receipts (
 scope_hash char(64) NOT NULL CHECK(scope_hash~'^[0-9a-f]{64}$'),
 retry_hash char(64) NOT NULL CHECK(retry_hash~'^[0-9a-f]{64}$'),
 body_hash char(64) NOT NULL CHECK(body_hash~'^[0-9a-f]{64}$'),
 report_id uuid NOT NULL REFERENCES public.abuse_reports(report_id) ON DELETE RESTRICT,
 policy_id uuid NOT NULL, policy_version integer NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(), retention_until timestamptz NOT NULL,
 PRIMARY KEY(scope_hash,retry_hash),
 FOREIGN KEY(policy_id,policy_version) REFERENCES public.abuse_intake_policies(policy_id,version) ON DELETE RESTRICT
);
CREATE TABLE public.abuse_report_events (
 event_id uuid PRIMARY KEY, report_id uuid NOT NULL UNIQUE REFERENCES public.abuse_reports(report_id) ON DELETE RESTRICT,
 case_id uuid NOT NULL REFERENCES public.support_cases(id) ON DELETE RESTRICT,
 actor_kind text NOT NULL CHECK(actor_kind='anonymous'), event_type text NOT NULL CHECK(event_type='received'),
 policy_id uuid NOT NULL, policy_version integer NOT NULL,
 occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(), retention_until timestamptz,
 FOREIGN KEY(policy_id,policy_version) REFERENCES public.abuse_intake_policies(policy_id,version) ON DELETE RESTRICT
);

CREATE FUNCTION public.sr_abuse_gate(exclusive boolean) RETURNS void
LANGUAGE plpgsql VOLATILE SET search_path=pg_catalog AS $$ BEGIN
 IF exclusive THEN PERFORM pg_advisory_xact_lock(51350001); ELSE PERFORM pg_advisory_xact_lock_shared(51350001); END IF;
END $$;

CREATE FUNCTION public.sr_abuse_policy(pid uuid, ver integer) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE p public.abuse_intake_policies;
BEGIN
 PERFORM public.sr_abuse_gate(false);
 SELECT * INTO p FROM public.abuse_intake_policies WHERE policy_id=pid AND version=ver
 AND revoked_at IS NULL AND effective_at<=clock_timestamp() AND expires_at>clock_timestamp();
 IF NOT FOUND THEN RETURN NULL; END IF;
 RETURN jsonb_build_object('policy_id',p.policy_id,'version',p.version,'body',p.body,'sha256',p.sha256,'revoked',false,
  'effective_at',p.effective_at,'expires_at',p.expires_at);
END $$;

CREATE FUNCTION public.sr_abuse_deadline(body jsonb,kind text,created timestamptz) RETURNS timestamptz
LANGUAGE sql VOLATILE SET search_path=pg_catalog AS $$
 SELECT CASE WHEN body->'retention'->kind->>'anchor'='created_at'
 THEN created+make_interval(secs=>(body->'retention'->kind->>'duration_seconds')::integer) ELSE NULL END
$$;

CREATE FUNCTION public.sr_abuse_case_marker(cid uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT public.sr_is_staff(ARRAY['support']) AND EXISTS(SELECT 1 FROM public.abuse_reports r JOIN public.support_cases c ON c.id=r.case_id
 WHERE c.id=cid AND (c.assigned_staff_id IS NULL OR c.assigned_staff_id=public.sr_actor_id()))
$$;

CREATE FUNCTION public.sr_abuse_case_readable(cid uuid) RETURNS boolean
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE r public.abuse_reports; p jsonb;
BEGIN
 SELECT * INTO r FROM public.abuse_reports WHERE case_id=cid;
 IF NOT FOUND THEN RETURN true; END IF;
 IF public.sr_abuse_case_marker(cid) IS NOT TRUE THEN RETURN false; END IF;
 p:=public.sr_abuse_policy(r.policy_id,r.policy_version);
 RETURN p IS NOT NULL AND (p->'body'->>'triage_enabled')::boolean IS TRUE
 AND (r.retention_until IS NULL OR r.retention_until>clock_timestamp())
 AND (r.case_retention_until IS NULL OR r.case_retention_until>clock_timestamp());
END $$;

CREATE FUNCTION public.sr_abuse_case_policy(cid uuid) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE r public.abuse_reports;
BEGIN
 IF public.sr_abuse_case_marker(cid) IS NOT TRUE THEN RETURN NULL; END IF;
 SELECT * INTO r FROM public.abuse_reports WHERE case_id=cid;
 IF NOT public.sr_abuse_case_readable(cid) THEN RETURN jsonb_build_object('error','PROVIDER_UNAVAILABLE'); END IF;
 RETURN public.sr_abuse_policy(r.policy_id,r.policy_version);
END $$;

CREATE FUNCTION public.sr_abuse_intake(action text,payload jsonb) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE p jsonb; b jsonb; budget_kind text; scope text:=payload->>'scope'; limit_count integer;
 old public.abuse_report_receipts; r public.abuse_reports;
 pid uuid:=(payload->>'policy_id')::uuid; ver integer:=(payload->>'policy_version')::integer;
 stamp timestamptz;
BEGIN
 -- Only the anonymous backend transaction calls this service. No public DB grants.
 IF public.sr_actor_id() IS NOT NULL THEN RETURN NULL; END IF;
 p:=public.sr_abuse_policy(pid,ver); b:=p->'body';
 IF p IS NULL OR (b->>'intake_enabled')::boolean IS NOT TRUE THEN RETURN jsonb_build_object('error','PROVIDER_UNAVAILABLE'); END IF;
 IF scope IS NULL OR scope!~'^[0-9a-f]{64}$' THEN RETURN NULL; END IF;
 IF action IN('peer','target') THEN
  budget_kind:=action; limit_count:=CASE WHEN action='peer' THEN 20 ELSE 5 END;
  PERFORM pg_advisory_xact_lock(hashtextextended('abuse-budget:'||budget_kind||':'||scope,0));
  IF (SELECT count(*) FROM public.abuse_report_attempts WHERE scope_hash=scope AND kind=budget_kind
   AND created_at>clock_timestamp()-interval '15 minutes')>=limit_count THEN RETURN jsonb_build_object('allowed',false); END IF;
  stamp:=clock_timestamp();
  INSERT INTO public.abuse_report_attempts(kind,scope_hash,policy_id,policy_version,created_at,retention_until)
   VALUES(budget_kind,scope,pid,ver,stamp,public.sr_abuse_deadline(b,'budget',stamp));
  RETURN jsonb_build_object('allowed',true);
 ELSIF action='proof' THEN
  IF payload->>'proof' IS NULL OR payload->>'proof'!~'^[0-9a-f]{64}$' THEN RETURN NULL; END IF;
  stamp:=clock_timestamp();
  INSERT INTO public.abuse_report_proofs(proof_hash,policy_id,policy_version,created_at,retention_until)
   VALUES(payload->>'proof',pid,ver,stamp,public.sr_abuse_deadline(b,'proof',stamp)) ON CONFLICT DO NOTHING;
  RETURN jsonb_build_object('allowed',FOUND);
 ELSIF action<>'submit' THEN RETURN NULL; END IF;
 IF payload->>'retry' IS NULL OR payload->>'retry'!~'^[0-9a-f]{64}$' OR payload->>'body' IS NULL OR payload->>'body'!~'^[0-9a-f]{64}$'
 OR payload->>'duplicate' IS NULL OR payload->>'duplicate'!~'^[0-9a-f]{64}$' THEN RETURN NULL; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended('abuse-retry:'||scope||':'||(payload->>'retry'),0));
 SELECT * INTO old FROM public.abuse_report_receipts WHERE scope_hash=scope AND retry_hash=payload->>'retry' FOR UPDATE;
 IF FOUND THEN
  IF old.body_hash<>payload->>'body' THEN RETURN jsonb_build_object('error','IDEMPOTENCY_KEY_REUSED'); END IF;
  IF old.retention_until<=clock_timestamp() THEN RETURN jsonb_build_object('error','PROVIDER_UNAVAILABLE'); END IF;
  RETURN jsonb_build_object('status','accepted');
 END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended('abuse-duplicate:'||(payload->>'duplicate'),0));
 SELECT ar.* INTO r FROM public.abuse_reports ar JOIN public.support_cases c ON c.id=ar.case_id
  WHERE ar.duplicate_hash=payload->>'duplicate' AND c.status IN('open','investigating')
  AND (ar.retention_until IS NULL OR ar.retention_until>clock_timestamp())
  AND (ar.case_retention_until IS NULL OR ar.case_retention_until>clock_timestamp())
  ORDER BY ar.created_at,ar.report_id LIMIT 1;
 IF NOT FOUND THEN
  stamp:=clock_timestamp();
  IF payload->>'category' IS NULL OR payload->>'category' NOT IN('spam','fraud','unsafe_content','other') THEN RETURN NULL; END IF;
  INSERT INTO public.support_cases(id,case_type,status,priority,description_ciphertext,description_key_version,description_format,created_at)
   VALUES((payload->>'case_id')::uuid,'other','open','normal',decode(payload->>'description_ciphertext','hex'),(payload->>'description_key_version')::smallint,1,stamp);
  INSERT INTO public.abuse_reports(report_id,case_id,category,context_ciphertext,context_key_version,duplicate_hash,
   policy_id,policy_version,hmac_key_version,consent_version,created_at,consent_at,retention_until,case_retention_until)
   VALUES((payload->>'report_id')::uuid,(payload->>'case_id')::uuid,payload->>'category',decode(payload->>'context_ciphertext','hex'),
    (payload->>'context_key_version')::smallint,payload->>'duplicate',pid,ver,(b->>'hmac_key_version')::integer,'abuse-report-v1',stamp,stamp,
    public.sr_abuse_deadline(b,'report',stamp),public.sr_abuse_deadline(b,'case',stamp)) RETURNING * INTO r;
  INSERT INTO public.abuse_report_events(event_id,report_id,case_id,actor_kind,event_type,policy_id,policy_version,occurred_at,retention_until)
   VALUES((payload->>'event_id')::uuid,r.report_id,r.case_id,'anonymous','received',pid,ver,stamp,public.sr_abuse_deadline(b,'audit',stamp));
 END IF;
 stamp:=clock_timestamp();
 INSERT INTO public.abuse_report_receipts(scope_hash,retry_hash,body_hash,report_id,policy_id,policy_version,created_at,retention_until)
  VALUES(scope,payload->>'retry',payload->>'body',r.report_id,pid,ver,stamp,public.sr_abuse_deadline(b,'receipt',stamp));
 RETURN jsonb_build_object('status','accepted');
END $$;

CREATE FUNCTION public.sr_abuse_history_fixed() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN RAISE EXCEPTION 'Abuse intake history is immutable' USING ERRCODE='23514'; END $$;
CREATE TRIGGER sr_abuse_reports_fixed BEFORE UPDATE OR DELETE ON public.abuse_reports FOR EACH ROW EXECUTE FUNCTION public.sr_abuse_history_fixed();
CREATE TRIGGER sr_abuse_receipts_fixed BEFORE UPDATE OR DELETE ON public.abuse_report_receipts FOR EACH ROW EXECUTE FUNCTION public.sr_abuse_history_fixed();
CREATE TRIGGER sr_abuse_events_fixed BEFORE UPDATE OR DELETE ON public.abuse_report_events FOR EACH ROW EXECUTE FUNCTION public.sr_abuse_history_fixed();
CREATE TRIGGER sr_abuse_attempts_fixed BEFORE UPDATE OR DELETE ON public.abuse_report_attempts FOR EACH ROW EXECUTE FUNCTION public.sr_abuse_history_fixed();
CREATE TRIGGER sr_abuse_proofs_fixed BEFORE UPDATE OR DELETE ON public.abuse_report_proofs FOR EACH ROW EXECUTE FUNCTION public.sr_abuse_history_fixed();
CREATE FUNCTION public.sr_abuse_policy_fixed() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 PERFORM public.sr_abuse_gate(true);
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Policy history is permanent' USING ERRCODE='23514'; END IF;
 IF TG_OP='UPDATE' AND ((to_jsonb(NEW)-'revoked_at') IS DISTINCT FROM (to_jsonb(OLD)-'revoked_at')
  OR (OLD.revoked_at IS NOT NULL AND NEW.revoked_at IS DISTINCT FROM OLD.revoked_at)) THEN
  RAISE EXCEPTION 'Approved policy is immutable' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_abuse_policy_fixed BEFORE INSERT OR UPDATE OR DELETE ON public.abuse_intake_policies FOR EACH ROW EXECUTE FUNCTION public.sr_abuse_policy_fixed();

-- Keep ordinary support semantics. No anonymous report can become an unrestricted
-- other-case through API099, a direct old helper, detachment or flag rollback.
ALTER FUNCTION public.sr_support_change(uuid,integer,text,text,text,uuid,bytea,smallint,text) RENAME TO sr_support_change_v34;
CREATE FUNCTION public.sr_support_change(case_id uuid,expected integer,action_name text,next_status text,urgency text,
 event_id uuid,note bytea,key_version smallint,request_tag text) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$ BEGIN
 IF public.sr_abuse_case_marker(case_id) THEN
  PERFORM public.sr_abuse_gate(false);
  IF NOT public.sr_abuse_case_readable(case_id) THEN RETURN jsonb_build_object('error','PROVIDER_UNAVAILABLE'); END IF;
  IF next_status IN('resolved','closed') THEN RETURN jsonb_build_object('error','ESCALATION_REQUIRED'); END IF;
 END IF;
 RETURN public.sr_support_change_v34(case_id,expected,action_name,next_status,urgency,event_id,note,key_version,request_tag);
END $$;
CREATE FUNCTION public.sr_abuse_case_guard() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$ BEGIN
 IF EXISTS(SELECT 1 FROM public.abuse_reports WHERE case_id=OLD.id) THEN
  PERFORM public.sr_abuse_gate(false);
  IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Report linkage is permanent' USING ERRCODE='23514'; END IF;
  IF NEW.status IN('resolved','closed') OR (NEW.id,NEW.case_type,NEW.pair_id,NEW.order_id,NEW.opened_by_user_id,NEW.description_ciphertext,NEW.description_key_version,NEW.description_format,NEW.created_at,NEW.closed_at)
   IS DISTINCT FROM (OLD.id,OLD.case_type,OLD.pair_id,OLD.order_id,OLD.opened_by_user_id,OLD.description_ciphertext,OLD.description_key_version,OLD.description_format,OLD.created_at,OLD.closed_at) THEN
   RAISE EXCEPTION 'Report requires separately authorized escalation' USING ERRCODE='23514';
  END IF;
 END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_abuse_case_guard BEFORE UPDATE OR DELETE ON public.support_cases FOR EACH ROW EXECUTE FUNCTION public.sr_abuse_case_guard();
CREATE POLICY sr_abuse_case_scope ON public.support_cases AS RESTRICTIVE FOR SELECT TO safereturn_api USING(public.sr_abuse_case_readable(id));

DO $$ DECLARE tbl text; fn record; BEGIN
 FOREACH tbl IN ARRAY ARRAY['abuse_intake_policies','abuse_report_attempts','abuse_report_proofs','abuse_reports','abuse_report_receipts','abuse_report_events'] LOOP
  EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',tbl);
  EXECUTE format('REVOKE ALL ON public.%I FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker',tbl);
 END LOOP;
 FOR fn IN SELECT p.oid::regprocedure AS signature FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname LIKE 'sr_abuse_%' LOOP
  EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker',fn.signature);
 END LOOP;
END $$;
REVOKE ALL ON FUNCTION public.sr_support_change_v34(uuid,integer,text,text,text,uuid,bytea,smallint,text),public.sr_support_change(uuid,integer,text,text,text,uuid,bytea,smallint,text) FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_support_change(uuid,integer,text,text,text,uuid,bytea,smallint,text) TO safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_abuse_policy(uuid,integer),public.sr_abuse_intake(text,jsonb),public.sr_abuse_case_marker(uuid),public.sr_abuse_case_readable(uuid),public.sr_abuse_case_policy(uuid) TO safereturn_api;
