-- Owner-approved 5.3B. No live authority provisioning or migration application.
CREATE TABLE public.financial_case_bindings (
 case_id uuid PRIMARY KEY REFERENCES public.support_cases(id) ON DELETE RESTRICT,
 order_id uuid NOT NULL REFERENCES public.orders(id) ON DELETE RESTRICT,
 attempt_id uuid NOT NULL REFERENCES public.payment_attempts(id) ON DELETE RESTRICT,
 provisioned_by uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE public.financial_case_authorities (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), case_id uuid NOT NULL REFERENCES public.financial_case_bindings(case_id) ON DELETE RESTRICT,
 finance_user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 can_review boolean NOT NULL, can_decide boolean NOT NULL CHECK(NOT can_decide OR can_review),
 provisioned_by uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT CHECK(provisioned_by<>finance_user_id),
 revision integer NOT NULL DEFAULT 1 CHECK(revision>0), revoked_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE UNIQUE INDEX uq_financial_case_authority ON public.financial_case_authorities(case_id,finance_user_id) WHERE revoked_at IS NULL;
CREATE TABLE public.financial_case_authority_events (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), authority_id uuid NOT NULL REFERENCES public.financial_case_authorities(id) ON DELETE RESTRICT,
 revision integer NOT NULL, actor_user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 event_type text NOT NULL CHECK(event_type IN('provisioned','revoked')), created_at timestamptz NOT NULL DEFAULT clock_timestamp(), UNIQUE(authority_id,revision)
);
CREATE TABLE public.financial_case_decisions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), case_id uuid NOT NULL REFERENCES public.financial_case_bindings(case_id) ON DELETE RESTRICT,
 case_revision integer NOT NULL CHECK(case_revision>0), order_revision integer NOT NULL CHECK(order_revision>0),
 actor_user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 decision text NOT NULL CHECK(decision IN('investigate','confirm_dispute','resolve_no_change','escalate')),
 effective_decision text NOT NULL CHECK(effective_decision IN('investigate','confirm_dispute','resolve_no_change','escalate')),
 reason_code text NOT NULL CHECK(reason_code IN('review_started','settlement_disputed','no_financial_change','requires_review')),
 settlement_review_reference uuid REFERENCES public.payment_reviews(id) ON DELETE RESTRICT,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(), UNIQUE(case_id,case_revision)
);
CREATE TABLE public.order_financial_fences (
 case_id uuid PRIMARY KEY REFERENCES public.financial_case_bindings(case_id) ON DELETE RESTRICT,
 order_id uuid NOT NULL REFERENCES public.orders(id) ON DELETE RESTRICT,
 decision_id uuid NOT NULL REFERENCES public.financial_case_decisions(id) ON DELETE RESTRICT,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX idx_order_financial_fences ON public.order_financial_fences(order_id);
DO $$ DECLARE relation text; BEGIN
 FOREACH relation IN ARRAY ARRAY['financial_case_bindings','financial_case_authorities','financial_case_authority_events','financial_case_decisions','order_financial_fences'] LOOP
  EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',relation);
  EXECUTE format('REVOKE ALL ON public.%I FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker',relation);
 END LOOP;
 FOREACH relation IN ARRAY ARRAY['financial_case_bindings','financial_case_authority_events','financial_case_decisions','order_financial_fences'] LOOP
  EXECUTE format('CREATE TRIGGER sr_financial_append BEFORE UPDATE OR DELETE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.sr_append_only()',relation);
 END LOOP;
END $$;

-- Controlled runbook only: no runtime grant/authority editor is introduced.
CREATE FUNCTION public.sr_financial_provision_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE oid uuid; uid uuid:=public.sr_actor_id();
BEGIN
 IF TG_OP='DELETE' OR uid IS NULL OR NOT EXISTS(SELECT 1 FROM public.staff_roles WHERE user_id=uid AND role='security_admin' AND revoked_at IS NULL) THEN
  RAISE EXCEPTION 'Controlled security provisioning required' USING ERRCODE='42501'; END IF;
 IF TG_TABLE_NAME='financial_case_bindings' THEN
  IF NEW.provisioned_by<>uid OR NOT EXISTS(SELECT 1 FROM public.support_cases c JOIN public.payment_attempts a ON a.id=NEW.attempt_id
    WHERE c.id=NEW.case_id AND c.case_type='payment' AND c.order_id=NEW.order_id AND a.order_id=NEW.order_id
    AND (c.pair_id IS NULL OR EXISTS(SELECT 1 FROM public.order_pair_units u WHERE u.order_id=NEW.order_id AND u.pair_id=c.pair_id))) THEN
   RAISE EXCEPTION 'Invalid financial case binding' USING ERRCODE='23514'; END IF;
  PERFORM 1 FROM public.orders WHERE id=NEW.order_id FOR UPDATE;
 ELSE
  SELECT order_id INTO oid FROM public.financial_case_bindings WHERE case_id=NEW.case_id;
  PERFORM 1 FROM public.orders WHERE id=oid FOR UPDATE;
  IF NEW.finance_user_id=uid THEN RAISE EXCEPTION 'Self authority forbidden' USING ERRCODE='42501'; END IF;
  IF TG_OP='INSERT' THEN
   IF NEW.provisioned_by<>uid OR NEW.revision<>1 OR NEW.revoked_at IS NOT NULL THEN RAISE EXCEPTION 'Invalid initial authority' USING ERRCODE='23514'; END IF;
  ELSE
   IF OLD.revoked_at IS NOT NULL OR NEW.revoked_at IS NULL OR
    (NEW.id,NEW.case_id,NEW.finance_user_id,NEW.can_review,NEW.can_decide,NEW.provisioned_by,NEW.created_at) IS DISTINCT FROM
    (OLD.id,OLD.case_id,OLD.finance_user_id,OLD.can_review,OLD.can_decide,OLD.provisioned_by,OLD.created_at) THEN
     RAISE EXCEPTION 'Authority may only be revoked' USING ERRCODE='23514'; END IF;
   NEW.revision:=OLD.revision+1; NEW.revoked_at:=clock_timestamp();
  END IF;
  INSERT INTO public.financial_case_authority_events(authority_id,revision,actor_user_id,event_type)
   VALUES(NEW.id,NEW.revision,uid,CASE WHEN TG_OP='INSERT' THEN 'provisioned' ELSE 'revoked' END);
 END IF;
 INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,reason,safe_details)
 VALUES(uid,'staff','finance.case.authority','support_case',NEW.case_id,'controlled financial case authority',jsonb_build_object('operation',TG_OP));
 RETURN NEW;
END $$;
-- AFTER validates and records the authority row so its immutable event FK exists.
CREATE TRIGGER sr_financial_binding BEFORE INSERT ON public.financial_case_bindings FOR EACH ROW EXECUTE FUNCTION public.sr_financial_provision_guard();
CREATE TRIGGER sr_financial_authority AFTER INSERT OR UPDATE OR DELETE ON public.financial_case_authorities FOR EACH ROW EXECUTE FUNCTION public.sr_financial_provision_guard();
-- A BEFORE guard sets the authoritative revocation version/time; the AFTER guard
-- validates provenance and appends its event. Never grant runtime table writes.
CREATE FUNCTION public.sr_financial_revoke_stamp() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN NEW.revision:=OLD.revision+1; NEW.revoked_at:=clock_timestamp(); RETURN NEW; END $$;
CREATE TRIGGER sr_financial_revoke_stamp BEFORE UPDATE ON public.financial_case_authorities FOR EACH ROW EXECUTE FUNCTION public.sr_financial_revoke_stamp();

CREATE FUNCTION public.sr_financial_order_clear(oid uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT NOT EXISTS(SELECT 1 FROM public.order_financial_fences WHERE order_id=oid)
$$;
CREATE FUNCTION public.sr_financial_order_lock_clear(oid uuid) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 PERFORM 1 FROM public.orders WHERE id=oid FOR UPDATE;
 RETURN FOUND AND public.sr_financial_order_clear(oid);
END $$;
CREATE FUNCTION public.sr_financial_require_clear(oid uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NOT public.sr_financial_order_lock_clear(oid) THEN
  RAISE EXCEPTION 'Financial review prevents entitlement or production' USING ERRCODE='23514',CONSTRAINT='financial_review_fence'; END IF;
END $$;

CREATE FUNCTION public.sr_financial_case_context(cid uuid,deciding boolean,reference uuid) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE uid uuid:=public.sr_actor_id(); b public.financial_case_bindings; c public.support_cases;
 o public.orders; a public.payment_attempts; g public.financial_case_authorities; review jsonb; verifiers jsonb;
BEGIN
 IF NOT public.sr_is_staff(ARRAY['finance']) OR NOT EXISTS(SELECT 1 FROM public.financial_case_authorities
   WHERE case_id=cid AND finance_user_id=uid AND can_review AND revoked_at IS NULL) THEN RETURN NULL; END IF;
 SELECT * INTO b FROM public.financial_case_bindings WHERE case_id=cid;
 IF NOT FOUND THEN RETURN NULL; END IF;
 SELECT * INTO o FROM public.orders WHERE id=b.order_id FOR UPDATE;
 PERFORM 1 FROM public.payment_attempts WHERE order_id=o.id ORDER BY id FOR UPDATE;
 PERFORM 1 FROM public.order_pair_units WHERE order_id=o.id ORDER BY id FOR UPDATE;
 PERFORM 1 FROM public.tag_pairs WHERE id IN(SELECT pair_id FROM public.order_pair_units WHERE order_id=o.id) ORDER BY id FOR UPDATE;
 SELECT * INTO c FROM public.support_cases WHERE id=cid FOR UPDATE;
 SELECT * INTO g FROM public.financial_case_authorities WHERE case_id=cid AND finance_user_id=uid AND can_review AND revoked_at IS NULL FOR UPDATE;
 IF NOT FOUND OR c.case_type<>'payment' OR c.order_id IS DISTINCT FROM b.order_id OR
  (c.pair_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.order_pair_units WHERE order_id=o.id AND pair_id=c.pair_id)) THEN RETURN NULL; END IF;
 SELECT * INTO a FROM public.payment_attempts WHERE id=b.attempt_id AND order_id=o.id;
 IF NOT FOUND THEN RETURN NULL; END IF;
 SELECT COALESCE(jsonb_agg(DISTINCT reviewed_by),'[]'::jsonb) INTO verifiers FROM public.payment_reviews WHERE attempt_id=a.id AND decision='verify' AND bank_verified;
 IF deciding AND (NOT g.can_decide OR g.provisioned_by=uid OR verifiers ? uid::text) THEN RETURN NULL; END IF;
 IF reference IS NOT NULL THEN
  SELECT jsonb_build_object('id',id,'decision',decision,'bank_verified',bank_verified) INTO review FROM public.payment_reviews WHERE id=reference AND attempt_id=a.id;
 END IF;
 RETURN jsonb_build_object('case',jsonb_build_object('id',c.id,'type',c.case_type,'status',c.status,'revision',c.case_revision),
  'order',jsonb_build_object('id',o.id,'revision',o.revision,'payment_status',o.payment_status,'amount',o.total_pkr::text,'currency',o.currency_code),
  'attempt',jsonb_build_object('id',a.id,'state',a.state,'amount',a.amount::text,'currency',a.currency_code,'verified_at',a.verified_at),
  'authority',jsonb_build_object('can_review',g.can_review,'can_decide',g.can_decide,'provisioned_by',g.provisioned_by,'revoked',false),
  'verified_reviewers',verifiers,'review_reference',review,'fence_active',NOT public.sr_financial_order_clear(o.id),
  'shipments',COALESCE((SELECT jsonb_agg(jsonb_build_object('id',id,'status',status,'dispatched_at',dispatched_at) ORDER BY id) FROM public.shipments WHERE order_id=o.id),'[]'::jsonb),
  'has_active_hold',EXISTS(SELECT 1 FROM public.retention_holds h WHERE h.released_at IS NULL AND (
    (h.resource_type='order' AND h.resource_id=o.id) OR (h.resource_type='payment_evidence' AND EXISTS(SELECT 1 FROM public.payment_evidence e WHERE e.id=h.resource_id AND e.attempt_id=a.id)) OR
    (h.resource_type='print_artifact' AND EXISTS(SELECT 1 FROM public.print_artifacts ar JOIN public.print_jobs j ON j.id=ar.print_job_id WHERE ar.id=h.resource_id AND j.order_id=o.id)))));
END $$;

CREATE FUNCTION public.sr_financial_case_history(cid uuid,before_revision integer,page_limit integer) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF page_limit NOT BETWEEN 1 AND 101 OR public.sr_financial_case_context(cid,false,NULL) IS NULL THEN RETURN NULL; END IF;
 INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,reason,safe_details)
 VALUES(public.sr_actor_id(),'staff','finance.case.read','support_case',cid,'authorized bounded financial review','{}'::jsonb);
 RETURN COALESCE((SELECT jsonb_agg(row_to_json(d) ORDER BY d.revision DESC) FROM (
  SELECT id AS decision_id,case_revision AS revision,decision,effective_decision,reason_code,created_at FROM public.financial_case_decisions
  WHERE case_id=cid AND case_revision<before_revision ORDER BY case_revision DESC LIMIT page_limit) d),'[]'::jsonb);
END $$;

CREATE FUNCTION public.sr_financial_case_apply(cid uuid,p jsonb,plan jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE s jsonb; oid uuid; uid uuid:=public.sr_actor_id(); effective text; fence boolean;
 reference uuid:=(p->>'settlement_review_reference')::uuid; did uuid:=gen_random_uuid(); cr integer; orev integer; out_fence boolean;
BEGIN
 s:=public.sr_financial_case_context(cid,true,reference);
 IF s IS NULL THEN RETURN NULL; END IF;
 oid:=(s->'order'->>'id')::uuid;
 IF p->'confirmed' IS DISTINCT FROM 'true'::jsonb OR p->>'decision' NOT IN('investigate','confirm_dispute','resolve_no_change','escalate') OR
  p->>'reason_code' IS DISTINCT FROM (CASE p->>'decision' WHEN 'investigate' THEN 'review_started' WHEN 'confirm_dispute' THEN 'settlement_disputed' WHEN 'resolve_no_change' THEN 'no_financial_change' WHEN 'escalate' THEN 'requires_review' END) THEN RETURN jsonb_build_object('error','INVALID_REQUEST'); END IF;
 IF (s->'case'->>'revision')::int IS DISTINCT FROM (p->>'expected_revision')::int OR (s->'order'->>'revision')::int IS DISTINCT FROM (p->>'expected_order_revision')::int THEN RETURN jsonb_build_object('error','VERSION_MISMATCH'); END IF;
 IF s->'case'->>'status' IN('resolved','closed') THEN RETURN jsonb_build_object('error','CASE_CLOSED'); END IF;
 IF (reference IS NOT NULL AND (s->'review_reference'->>'id')::uuid IS DISTINCT FROM reference) OR (p->>'decision' IN('confirm_dispute','resolve_no_change') AND reference IS NULL) THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
 IF p->>'decision'='confirm_dispute' AND (s->'review_reference'->>'decision' IS DISTINCT FROM 'verify' OR s->'review_reference'->'bank_verified' IS DISTINCT FROM 'true'::jsonb OR s->'attempt'->>'verified_at' IS NULL OR
  (s->'attempt'->>'amount')::numeric IS DISTINCT FROM (s->'order'->>'amount')::numeric OR s->'attempt'->>'currency' IS DISTINCT FROM s->'order'->>'currency') THEN RETURN jsonb_build_object('error','VERIFIED_SETTLEMENT_REQUIRED'); END IF;
 effective:=p->>'decision';
 IF effective='confirm_dispute' AND EXISTS(SELECT 1 FROM public.shipments WHERE order_id=oid AND (dispatched_at IS NOT NULL OR status IN('dispatched','delivered','returned'))) THEN effective:='escalate'; END IF;
 fence:=effective IN('confirm_dispute','escalate');
 IF plan->>'effective_decision' IS DISTINCT FROM effective OR (plan->>'activate_fence')::boolean IS DISTINCT FROM fence THEN RETURN jsonb_build_object('error','VERSION_MISMATCH'); END IF;
 UPDATE public.support_cases SET case_revision=case_revision+1 WHERE id=cid RETURNING case_revision INTO cr;
 INSERT INTO public.financial_case_decisions(id,case_id,case_revision,order_revision,actor_user_id,decision,effective_decision,reason_code,settlement_review_reference)
 VALUES(did,cid,cr,(s->'order'->>'revision')::int,uid,p->>'decision',effective,p->>'reason_code',reference);
 IF fence THEN
  INSERT INTO public.order_financial_fences(case_id,order_id,decision_id) VALUES(cid,oid,did) ON CONFLICT(case_id) DO NOTHING;
  IF NOT EXISTS(SELECT 1 FROM public.shipments WHERE order_id=oid AND (dispatched_at IS NOT NULL OR status IN('dispatched','delivered','returned'))) THEN
   UPDATE public.shipments SET status='exception' WHERE order_id=oid AND status IN('preparing','packed');
   IF FOUND THEN UPDATE public.orders SET fulfillment_status='exception' WHERE id=oid; END IF;
  END IF;
 END IF;
 SELECT revision INTO orev FROM public.orders WHERE id=oid;
 out_fence:=NOT public.sr_financial_order_clear(oid);
 INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,reason,safe_details)
 VALUES(uid,'staff','finance.case.decided','support_case',cid,p->>'reason_code',jsonb_build_object('decision_id',did,'case_revision',cr,'effective_decision',effective));
 RETURN jsonb_build_object('decision_id',did,'case_id',cid,'case_revision',cr,'order_id',oid,'order_revision',orev,'decision',p->>'decision','effective_decision',effective,
  'dispute_fence',CASE WHEN out_fence THEN 'active' ELSE 'none' END,'next_action',CASE WHEN effective='escalate' THEN 'escalated' WHEN out_fence THEN 'await_reconciliation' ELSE 'review_recorded' END,'refund_execution_enabled',false);
END $$;

CREATE FUNCTION public.sr_financial_fence_revision() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN UPDATE public.orders SET revision=revision+1 WHERE id=NEW.order_id; RETURN NEW; END $$;
CREATE TRIGGER sr_financial_fence_revision AFTER INSERT ON public.order_financial_fences FOR EACH ROW EXECUTE FUNCTION public.sr_financial_fence_revision();

-- Gate existing entitlement/production functions without changing their OIDs or
-- historical migrations/grants. Abort if the expected installed definition differs.
DO $$ DECLARE signature text; definition text; updated text; BEGIN
 FOREACH signature IN ARRAY ARRAY['public.sr_print_occurrences(uuid)','public.sr_print_order_lock(uuid)','public.sr_insert_print_job(uuid,uuid,integer,text,jsonb,bytea,smallint)'] LOOP
  SELECT pg_get_functiondef(signature::regprocedure) INTO definition;
  updated:=regexp_replace(definition,E'BEGIN\\s*','BEGIN PERFORM public.sr_financial_require_clear(oid); ');
  IF updated=definition THEN RAISE EXCEPTION 'Review installed print function before extending'; END IF;
  EXECUTE updated;
 END LOOP;
 SELECT pg_get_functiondef('public.sr_fulfillment_eligible(uuid)'::regprocedure) INTO definition;
 updated:=replace(definition,'SELECT public.sr_is_staff(ARRAY[''operations''])','SELECT public.sr_financial_order_clear(oid) AND public.sr_is_staff(ARRAY[''operations''])');
 IF updated=definition THEN RAISE EXCEPTION 'Review installed fulfillment function before extending'; END IF;
 EXECUTE updated;
END $$;

-- Direct writes, stale leases/grants and new paid claims cannot bypass the fence.
CREATE FUNCTION public.sr_financial_work_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE oid uuid; item jsonb:=to_jsonb(NEW); blocked boolean:=true;
BEGIN
 IF TG_TABLE_NAME='tag_pairs' THEN
  IF TG_OP='UPDATE' AND ((OLD.owner_user_id IS NULL AND NEW.owner_user_id IS NOT NULL) OR (OLD.activated_at IS NULL AND NEW.activated_at IS NOT NULL)) THEN
   IF EXISTS(SELECT 1 FROM public.order_pair_units u JOIN public.order_financial_fences f ON f.order_id=u.order_id WHERE u.pair_id=NEW.id) THEN RAISE EXCEPTION 'New paid claim requires financial review' USING ERRCODE='23514'; END IF;
  END IF; RETURN NEW;
 ELSIF TG_TABLE_NAME='orders' THEN
  IF TG_OP='INSERT' THEN RETURN NEW; END IF; -- A new order cannot already have an FK-bound fence.
  IF NEW.fulfillment_status IS DISTINCT FROM OLD.fulfillment_status AND NEW.fulfillment_status IN('allocated','packed','dispatched','delivered') THEN oid:=NEW.id; ELSE RETURN NEW; END IF;
 ELSE
  oid:=(item->>'order_id')::uuid;
  IF oid IS NULL AND TG_TABLE_NAME IN('print_artifacts','print_job_qa','durable_jobs') THEN SELECT order_id INTO oid FROM public.print_jobs WHERE id=(item->>'print_job_id')::uuid;
  ELSIF TG_TABLE_NAME='print_download_grants' THEN SELECT j.order_id INTO oid FROM public.print_artifacts a JOIN public.print_jobs j ON j.id=a.print_job_id WHERE a.id=(item->>'artifact_id')::uuid;
  ELSIF oid IS NULL AND TG_TABLE_NAME='shipment_pairs' THEN SELECT order_id INTO oid FROM public.shipments WHERE id=(item->>'shipment_id')::uuid;
  END IF;
  IF TG_TABLE_NAME='shipments' THEN blocked:=TG_OP='INSERT' OR item->>'status' IN('preparing','packed','dispatched','delivered');
  ELSIF TG_TABLE_NAME='print_jobs' THEN blocked:=TG_OP='INSERT' OR item->>'status' IN('queued','rendering','ready','downloaded','qa_passed');
  ELSIF TG_TABLE_NAME='print_artifacts' THEN blocked:=TG_OP='INSERT'; -- Existing retention/hold metadata remains independent.
  ELSIF TG_TABLE_NAME='print_download_grants' THEN blocked:=TG_OP='INSERT' OR item->>'used_at' IS NOT NULL;
  ELSIF TG_TABLE_NAME='durable_jobs' THEN blocked:=(item->>'job_kind' LIKE 'print.%' OR item->>'job_kind'='allocation.finalize') AND (TG_OP='INSERT' OR item->>'status' IN('leased','completed'));
  END IF;
 END IF;
 IF oid IS NOT NULL AND blocked THEN PERFORM public.sr_financial_require_clear(oid); END IF;
 RETURN NEW;
END $$;
DO $$ DECLARE relation text; BEGIN
 FOREACH relation IN ARRAY ARRAY['orders','order_pair_units','tag_pairs','print_jobs','print_artifacts','print_job_qa','print_download_grants','shipments','shipment_pairs','durable_jobs'] LOOP
  EXECUTE format('CREATE TRIGGER sr_financial_work BEFORE INSERT OR UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.sr_financial_work_guard()',relation);
 END LOOP;
END $$;
REVOKE ALL ON FUNCTION public.sr_financial_provision_guard(),public.sr_financial_revoke_stamp(),public.sr_financial_order_clear(uuid),public.sr_financial_order_lock_clear(uuid),public.sr_financial_require_clear(uuid),public.sr_financial_case_context(uuid,boolean,uuid),public.sr_financial_case_history(uuid,integer,integer),public.sr_financial_case_apply(uuid,jsonb,jsonb),public.sr_financial_fence_revision(),public.sr_financial_work_guard() FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_financial_case_context(uuid,boolean,uuid),public.sr_financial_case_history(uuid,integer,integer),public.sr_financial_case_apply(uuid,jsonb,jsonb) TO safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_financial_order_clear(uuid),public.sr_financial_order_lock_clear(uuid) TO safereturn_api,safereturn_worker;
-- No refund or fence-removal/restoration function, table UPDATE grant or endpoint.
