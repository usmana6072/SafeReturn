-- Owner-approved BTR-06 extension. No deployment/application authorized here.
ALTER TABLE public.orders ADD COLUMN revision integer NOT NULL DEFAULT 1 CHECK(revision>0);
CREATE TABLE public.order_cancellation_requests (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), order_id uuid NOT NULL REFERENCES public.orders(id) ON DELETE RESTRICT,
 status text NOT NULL CHECK(status IN('requested','investigating','approved','rejected','escalated','completed')),
 revision integer NOT NULL DEFAULT 1 CHECK(revision>0), reason_code text NOT NULL CHECK(reason_code IN('ordered_by_mistake','no_longer_needed','other')),
 reconciliation_id uuid, receipt jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE UNIQUE INDEX uq_active_order_cancellation ON public.order_cancellation_requests(order_id)
 WHERE status IN('requested','investigating','approved','escalated');
CREATE TABLE public.order_cancellation_reconciliations (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), request_id uuid NOT NULL REFERENCES public.order_cancellation_requests(id) ON DELETE RESTRICT,
 finance_user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 order_revision integer NOT NULL, request_revision integer NOT NULL,
 outcome text NOT NULL CHECK(outcome IN('clear','escalate')), reason_code text NOT NULL CHECK(reason_code IN('no_settlement_pending','settlement_requires_review')),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(), valid_until timestamptz NOT NULL,
 CHECK(valid_until>created_at AND valid_until<=created_at+interval '300 seconds')
);
ALTER TABLE public.order_cancellation_requests ADD CONSTRAINT fk_cancellation_reconciliation
 FOREIGN KEY(reconciliation_id) REFERENCES public.order_cancellation_reconciliations(id) ON DELETE RESTRICT;
CREATE TABLE public.order_cancellation_events (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), request_id uuid NOT NULL REFERENCES public.order_cancellation_requests(id) ON DELETE RESTRICT,
 request_revision integer NOT NULL, actor_user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 action text NOT NULL, reason_code text NOT NULL, reconciliation_id uuid REFERENCES public.order_cancellation_reconciliations(id) ON DELETE RESTRICT,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(), UNIQUE(request_id,request_revision)
);
CREATE TABLE public.order_cancellation_consumptions (
 reconciliation_id uuid PRIMARY KEY REFERENCES public.order_cancellation_reconciliations(id) ON DELETE RESTRICT,
 executor_user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 transaction_id xid8 NOT NULL DEFAULT pg_current_xact_id(),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
ALTER TABLE public.order_cancellation_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.order_cancellation_reconciliations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.order_cancellation_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.order_cancellation_consumptions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.order_cancellation_requests,public.order_cancellation_reconciliations,
 public.order_cancellation_events,public.order_cancellation_consumptions FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT SELECT ON public.order_cancellation_requests TO safereturn_api;
CREATE POLICY sr_cancellation_read ON public.order_cancellation_requests FOR SELECT TO safereturn_api
 USING(public.sr_owns_order(order_id) OR public.sr_is_staff(ARRAY['operations','finance']));

CREATE FUNCTION public.sr_cancellation_immutable() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN RAISE EXCEPTION 'Cancellation evidence is immutable' USING ERRCODE='23514'; END $$;
CREATE TRIGGER sr_cancellation_evidence BEFORE UPDATE OR DELETE ON public.order_cancellation_reconciliations FOR EACH ROW EXECUTE FUNCTION public.sr_cancellation_immutable();
CREATE TRIGGER sr_cancellation_events BEFORE UPDATE OR DELETE ON public.order_cancellation_events FOR EACH ROW EXECUTE FUNCTION public.sr_cancellation_immutable();
CREATE TRIGGER sr_cancellation_consumptions BEFORE UPDATE OR DELETE ON public.order_cancellation_consumptions FOR EACH ROW EXECUTE FUNCTION public.sr_cancellation_immutable();
CREATE TRIGGER sr_cancellation_requests_keep BEFORE DELETE ON public.order_cancellation_requests FOR EACH ROW EXECUTE FUNCTION public.sr_cancellation_immutable();

-- Existing runtime UPDATE grants must not bypass the reviewed release protocol.
-- An attestation consumed in an earlier transaction cannot authorize a timer or
-- stale worker. Direct writes to consumption/history tables are revoked above.
CREATE FUNCTION public.sr_cancellation_execution_authorized(oid uuid) RETURNS boolean
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT 1 FROM public.order_cancellation_requests r
 JOIN public.order_cancellation_reconciliations a ON a.id=r.reconciliation_id
 JOIN public.order_cancellation_consumptions c ON c.reconciliation_id=a.id
 WHERE r.order_id=oid AND r.status='approved' AND r.revision=a.request_revision+1
 AND a.outcome='clear' AND a.valid_until>clock_timestamp()
 AND a.finance_user_id<>c.executor_user_id AND c.executor_user_id=public.sr_actor_id()
 AND c.transaction_id=pg_current_xact_id())
$$;
CREATE FUNCTION public.sr_cancellation_release_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF TG_TABLE_NAME='order_pair_units' THEN
   IF OLD.status='reserved' AND NEW.status IN('released','cancelled') AND NOT public.sr_cancellation_execution_authorized(NEW.order_id) THEN
     RAISE EXCEPTION 'Independent cancellation execution required' USING ERRCODE='23514';
   END IF;
 ELSE
   IF OLD.placed_at IS NOT NULL AND NEW.order_status='cancelled' AND OLD.order_status<>'cancelled' AND
    (NOT public.sr_cancellation_execution_authorized(NEW.id) OR EXISTS(SELECT 1 FROM public.order_pair_units WHERE order_id=NEW.id AND status IN('reserved','allocated'))) THEN
     RAISE EXCEPTION 'Complete reconciled cancellation required' USING ERRCODE='23514';
   END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_cancellation_release_guard BEFORE UPDATE ON public.order_pair_units FOR EACH ROW EXECUTE FUNCTION public.sr_cancellation_release_guard();
CREATE TRIGGER sr_cancellation_release_guard BEFORE UPDATE ON public.orders FOR EACH ROW EXECUTE FUNCTION public.sr_cancellation_release_guard();

-- An authoritative core revision, independent of updated_at or case/job revisions.
CREATE FUNCTION public.sr_order_revision() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN NEW.revision:=OLD.revision+1; RETURN NEW; END $$;
CREATE TRIGGER sr_order_revision BEFORE UPDATE ON public.orders FOR EACH ROW EXECUTE FUNCTION public.sr_order_revision();

-- Parent lock serializes child admission with cancellation. Existing child-first
-- workers may deadlock/retry; PostgreSQL deadlock/lease rehearsal is a release gate.
CREATE FUNCTION public.sr_cancellation_child_fence() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE oid uuid; state text; entry jsonb;
BEGIN
 IF TG_OP='DELETE' THEN entry:=to_jsonb(OLD); ELSE entry:=to_jsonb(NEW); END IF;
 IF TG_TABLE_NAME IN('tag_pairs','pair_print_qa','qr_codes','pair_activation_credentials') THEN
   FOR oid IN SELECT order_id FROM public.order_pair_units WHERE pair_id=CASE WHEN TG_TABLE_NAME='tag_pairs' THEN (entry->>'id')::uuid ELSE (entry->>'pair_id')::uuid END ORDER BY order_id LOOP
     UPDATE public.orders SET revision=revision+1 WHERE id=oid;
   END LOOP;
 ELSE
   oid:=(entry->>'order_id')::uuid;
   IF oid IS NULL AND TG_TABLE_NAME IN('payment_reviews','payment_evidence') THEN
     SELECT order_id INTO oid FROM public.payment_attempts WHERE id=(entry->>'attempt_id')::uuid;
   ELSIF oid IS NULL AND TG_TABLE_NAME IN('print_artifacts','print_job_qa') THEN
     SELECT order_id INTO oid FROM public.print_jobs WHERE id=(entry->>'print_job_id')::uuid;
   ELSIF oid IS NULL AND TG_TABLE_NAME='shipment_pairs' THEN
     SELECT order_id INTO oid FROM public.shipments WHERE id=(entry->>'shipment_id')::uuid;
   END IF;
   IF oid IS NOT NULL THEN
     SELECT order_status INTO state FROM public.orders WHERE id=oid FOR UPDATE;
     IF state='cancelled' AND TG_OP<>'DELETE' AND
       (TG_TABLE_NAME IN('print_jobs','print_artifacts','print_job_qa','shipments','shipment_pairs') OR
        (TG_TABLE_NAME='durable_jobs' AND (entry->>'job_kind' LIKE 'print.%' OR entry->>'idempotency_key' LIKE 'print.request:%'))) THEN
       RAISE EXCEPTION 'Cancelled order production is fenced' USING ERRCODE='23514';
     END IF;
     UPDATE public.orders SET revision=revision+1 WHERE id=oid;
   END IF;
 END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; END IF; RETURN NEW;
END $$;
DO $$ DECLARE relation text; BEGIN
 FOREACH relation IN ARRAY ARRAY['payment_attempts','payment_reviews','payment_evidence','order_pair_units','tag_pairs','print_jobs','print_artifacts','print_job_qa','shipments','shipment_pairs','durable_jobs','pair_print_qa','qr_codes','pair_activation_credentials'] LOOP
   EXECUTE format('CREATE TRIGGER sr_cancellation_revision BEFORE INSERT OR UPDATE OR DELETE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.sr_cancellation_child_fence()',relation);
 END LOOP;
END $$;

CREATE FUNCTION public.sr_cancellation_eligibility(oid uuid,rid uuid) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE o public.orders;
BEGIN
 IF NOT public.sr_is_staff(ARRAY['operations','finance']) THEN RETURN NULL; END IF;
 IF oid IS NULL THEN SELECT order_id INTO oid FROM public.order_cancellation_requests WHERE id=rid; END IF;
 SELECT * INTO o FROM public.orders WHERE id=oid FOR UPDATE;
 IF NOT FOUND THEN RETURN NULL; END IF;
 PERFORM 1 FROM public.payment_attempts WHERE order_id=oid ORDER BY id FOR UPDATE;
 PERFORM 1 FROM public.order_pair_units WHERE order_id=oid ORDER BY id FOR UPDATE;
 PERFORM 1 FROM public.tag_pairs WHERE id IN(SELECT pair_id FROM public.order_pair_units WHERE order_id=oid) ORDER BY id FOR UPDATE;
 RETURN jsonb_build_object('order_status',o.order_status,'payment_status',o.payment_status,'fulfillment_status',o.fulfillment_status,
  'attempt_states',COALESCE((SELECT jsonb_agg(state ORDER BY id) FROM public.payment_attempts WHERE order_id=oid),'[]'::jsonb),
  'units',COALESCE((SELECT jsonb_agg(jsonb_build_object('status',u.status,'ownership_status',t.ownership_status,'owner_user_id',t.owner_user_id,'activated_at',t.activated_at,'inventory_status',t.inventory_status) ORDER BY u.id) FROM public.order_pair_units u JOIN public.tag_pairs t ON t.id=u.pair_id WHERE u.order_id=oid),'[]'::jsonb),
  'production',EXISTS(SELECT 1 FROM public.print_jobs WHERE order_id=oid) OR EXISTS(SELECT 1 FROM public.pair_print_qa WHERE inspected_at>=o.placed_at AND pair_id IN(SELECT pair_id FROM public.order_pair_units WHERE order_id=oid)) OR EXISTS(SELECT 1 FROM public.durable_jobs WHERE order_id=oid AND (job_kind LIKE 'print.%' OR idempotency_key LIKE 'print.request:%')),
  'shipment',EXISTS(SELECT 1 FROM public.shipments WHERE order_id=oid));
END $$;

CREATE FUNCTION public.sr_cancellation_command(oid uuid,pid uuid,act text,p jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE uid uuid:=public.sr_actor_id(); o public.orders; r public.order_cancellation_requests;
 a public.order_cancellation_reconciliations; rid uuid; aid uuid; next_status text; why text;
 clear_state boolean; now_at timestamptz; result jsonb;
BEGIN
 IF uid IS NULL OR p->'confirmed' IS DISTINCT FROM 'true'::jsonb OR act NOT IN('request','reconcile','decision','release') THEN RETURN jsonb_build_object('error','INVALID_REQUEST'); END IF;
 IF act='reconcile' AND NOT public.sr_is_staff(ARRAY['finance']) OR act IN('decision','release') AND NOT public.sr_is_staff(ARRAY['operations']) THEN
   RETURN jsonb_build_object('error','FORBIDDEN'); END IF;
 IF act='release' THEN SELECT order_id INTO oid FROM public.order_cancellation_requests WHERE id=(p->>'request_id')::uuid; END IF;
 SELECT * INTO o FROM public.orders WHERE id=oid FOR UPDATE;
 IF NOT FOUND OR (act='request' AND o.customer_user_id<>uid) THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
 IF act='release' AND NOT EXISTS(SELECT 1 FROM public.order_pair_units WHERE order_id=oid AND pair_id=pid) THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
 -- Stable order -> attempts -> units -> pairs -> request/attestation/job rows.
 PERFORM 1 FROM public.payment_attempts WHERE order_id=oid ORDER BY id FOR UPDATE;
 PERFORM 1 FROM public.order_pair_units WHERE order_id=oid ORDER BY id FOR UPDATE;
 PERFORM 1 FROM public.tag_pairs WHERE id IN(SELECT pair_id FROM public.order_pair_units WHERE order_id=oid) ORDER BY id FOR UPDATE;
 IF o.revision IS DISTINCT FROM COALESCE((p->>'expected_revision')::int,(p->>'expected_order_revision')::int) THEN RETURN jsonb_build_object('error','VERSION_MISMATCH'); END IF;
 IF act='request' THEN
   IF p->>'reason_code' NOT IN('ordered_by_mistake','no_longer_needed','other') OR o.order_status IN('draft','cancelled','fulfilled') THEN RETURN jsonb_build_object('error','CANCELLATION_UNAVAILABLE'); END IF;
   SELECT * INTO r FROM public.order_cancellation_requests WHERE order_id=oid AND status IN('requested','investigating','approved','escalated') FOR UPDATE;
   IF FOUND THEN RETURN r.receipt; END IF;
   rid:=gen_random_uuid();
   result:=jsonb_build_object('request_id',rid,'order_id',oid,'request_status','requested','revision',o.revision,'next_action','await_review');
   INSERT INTO public.order_cancellation_requests(id,order_id,status,reason_code,receipt) VALUES(rid,oid,'requested',p->>'reason_code',result) RETURNING * INTO r;
   next_status:='requested'; why:=p->>'reason_code';
 ELSE
   SELECT * INTO r FROM public.order_cancellation_requests WHERE id=(p->>'request_id')::uuid AND order_id=oid FOR UPDATE;
   IF NOT FOUND THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
   IF r.revision IS DISTINCT FROM (p->>'expected_request_revision')::int THEN RETURN jsonb_build_object('error','VERSION_MISMATCH'); END IF;
   IF r.status IN('rejected','completed') THEN RETURN jsonb_build_object('error','CANCELLATION_CLOSED'); END IF;
   clear_state:=COALESCE((p->>'application_clear')::boolean,false) AND o.order_status='placed' AND o.payment_status IN('awaiting_transfer','rejected') AND o.fulfillment_status='unallocated'
    AND EXISTS(SELECT 1 FROM public.order_pair_units WHERE order_id=oid)
    AND NOT EXISTS(SELECT 1 FROM public.payment_attempts WHERE order_id=oid AND state NOT IN('rejected','expired'))
    AND NOT EXISTS(SELECT 1 FROM public.order_pair_units u JOIN public.tag_pairs t ON t.id=u.pair_id WHERE u.order_id=oid AND (u.status<>'reserved' OR t.ownership_status<>'unclaimed' OR t.owner_user_id IS NOT NULL OR t.activated_at IS NOT NULL OR t.inventory_status NOT IN('generated','printed','qa_passed','reserved')))
    AND NOT EXISTS(SELECT 1 FROM public.print_jobs WHERE order_id=oid)
    AND NOT EXISTS(SELECT 1 FROM public.shipments WHERE order_id=oid)
    AND NOT EXISTS(SELECT 1 FROM public.durable_jobs WHERE order_id=oid AND (job_kind LIKE 'print.%' OR idempotency_key LIKE 'print.request:%'))
    AND NOT EXISTS(SELECT 1 FROM public.pair_print_qa WHERE inspected_at>=o.placed_at AND pair_id IN(SELECT pair_id FROM public.order_pair_units WHERE order_id=oid));
   now_at:=clock_timestamp();
   IF act='reconcile' THEN
     IF r.status<>'investigating' THEN RETURN jsonb_build_object('error','REVIEW_REQUIRED'); END IF;
     IF p->>'outcome' NOT IN('clear','escalate') OR p->>'reason_code' NOT IN('no_settlement_pending','settlement_requires_review') OR ((p->>'outcome'='clear')<>(p->>'reason_code'='no_settlement_pending')) THEN RETURN jsonb_build_object('error','INVALID_REQUEST'); END IF;
     IF p->>'outcome'='clear' AND NOT clear_state THEN RETURN jsonb_build_object('error','RECONCILIATION_REQUIRED'); END IF;
     aid:=gen_random_uuid();
     INSERT INTO public.order_cancellation_reconciliations(id,request_id,finance_user_id,order_revision,request_revision,outcome,reason_code,created_at,valid_until)
      VALUES(aid,r.id,uid,o.revision,r.revision,p->>'outcome',p->>'reason_code',now_at,now_at+interval '300 seconds');
     INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,reason,safe_details) VALUES(uid,'staff','cancellation.reconciled','order',oid,p->>'reason_code',jsonb_build_object('reconciliation_id',aid));
     RETURN jsonb_build_object('reconciliation_id',aid,'order_revision',o.revision,'request_revision',r.revision,'valid_until',now_at+interval '300 seconds','outcome',p->>'outcome');
   END IF;
   IF act='decision' THEN
     why:=p->>'reason_code';
     next_status:=CASE p->>'decision' WHEN 'investigate' THEN 'investigating' WHEN 'approve' THEN 'approved' WHEN 'reject' THEN 'rejected' WHEN 'escalate' THEN 'escalated' END;
     IF next_status IS NULL OR why<>(CASE p->>'decision' WHEN 'investigate' THEN 'review_started' WHEN 'approve' THEN 'eligible_unpaid' WHEN 'reject' THEN 'request_declined' WHEN 'escalate' THEN 'requires_review' END) OR
      NOT ((r.status IN('requested','escalated') AND next_status='investigating') OR (r.status='investigating' AND next_status IN('approved','rejected','escalated'))) THEN RETURN jsonb_build_object('error','INVALID_TRANSITION'); END IF;
   ELSIF act='release' THEN
     IF r.status<>'approved' THEN RETURN jsonb_build_object('error','REVIEW_REQUIRED'); END IF;
     next_status:='completed'; why:='eligible_unpaid';
   END IF;
   IF next_status IN('approved','completed') THEN
     SELECT * INTO a FROM public.order_cancellation_reconciliations WHERE id=(p->>'reconciliation_id')::uuid AND request_id=r.id FOR UPDATE;
     now_at:=clock_timestamp(); -- Waiting for the attestation lock cannot extend action validity.
     IF NOT FOUND OR a.finance_user_id=uid OR a.outcome<>'clear' OR EXISTS(SELECT 1 FROM public.order_cancellation_consumptions WHERE reconciliation_id=a.id) THEN RETURN jsonb_build_object('error','INDEPENDENT_RECONCILIATION_REQUIRED'); END IF;
     IF NOT clear_state OR a.valid_until<=now_at OR a.order_revision<>o.revision OR
        a.request_revision<>r.revision-(CASE WHEN act='release' THEN 1 ELSE 0 END) OR (act='release' AND r.reconciliation_id IS DISTINCT FROM a.id) THEN
       next_status:='investigating'; why:='requires_review';
     ELSIF act='release' THEN
       INSERT INTO public.order_cancellation_consumptions(reconciliation_id,executor_user_id) VALUES(a.id,uid);
       UPDATE public.order_pair_units SET status='cancelled',released_at=clock_timestamp() WHERE order_id=oid AND status='reserved';
       UPDATE public.orders SET order_status='cancelled' WHERE id=oid;
       SELECT * INTO o FROM public.orders WHERE id=oid;
     END IF;
   END IF;
   UPDATE public.order_cancellation_requests SET status=next_status,revision=revision+1,
    reconciliation_id=CASE WHEN next_status='approved' THEN a.id ELSE NULL END WHERE id=r.id RETURNING * INTO r;
   result:=jsonb_build_object('request_id',r.id,'order_id',oid,'request_status',r.status,'revision',o.revision,'request_revision',r.revision,'next_action',CASE WHEN r.status='completed' THEN 'none' ELSE 'await_review' END);
 END IF;
 INSERT INTO public.order_cancellation_events(request_id,request_revision,actor_user_id,action,reason_code,reconciliation_id)
 VALUES(r.id,r.revision,uid,next_status,why,CASE WHEN next_status IN('approved','completed') THEN a.id ELSE NULL END);
 INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,reason,safe_details)
 VALUES(uid,CASE WHEN act='request' THEN 'customer' ELSE 'staff' END,'cancellation.'||act,'order',oid,why,jsonb_build_object('request_id',r.id,'request_revision',r.revision,'status',next_status));
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION public.sr_order_revision(),public.sr_cancellation_child_fence(),public.sr_cancellation_immutable(),public.sr_cancellation_command(uuid,uuid,text,jsonb),public.sr_cancellation_eligibility(uuid,uuid) FROM PUBLIC,anon,authenticated,safereturn_worker;
REVOKE ALL ON FUNCTION public.sr_cancellation_execution_authorized(uuid),public.sr_cancellation_release_guard() FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_cancellation_command(uuid,uuid,text,jsonb),public.sr_cancellation_eligibility(uuid,uuid) TO safereturn_api;
