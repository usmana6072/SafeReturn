-- Source only. Checkout release remains disabled. No legacy row is converted.
CREATE TABLE public.typed_order_settlements (
 order_id uuid PRIMARY KEY REFERENCES public.orders(id) ON DELETE RESTRICT,
 attempt_id uuid NOT NULL UNIQUE REFERENCES public.payment_attempts(id) ON DELETE RESTRICT,
 state text NOT NULL CHECK(state IN ('reconciliation_pending','allocated')),
 reason_code text CHECK(reason_code IN ('stock_shortage','financial_review','cancellation_review','template_review')),
 revision integer NOT NULL DEFAULT 1 CHECK(revision>0),
 verified_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 allocated_at timestamptz,
 CHECK((state='allocated' AND allocated_at IS NOT NULL AND reason_code IS NULL)
    OR (state='reconciliation_pending' AND allocated_at IS NULL AND reason_code IS NOT NULL))
);
CREATE TABLE public.order_item_qr_allocations (
 logical_item_id uuid PRIMARY KEY REFERENCES public.order_logical_items(id) ON DELETE RESTRICT,
 qr_id uuid NOT NULL UNIQUE REFERENCES public.qr_codes(id) ON DELETE RESTRICT,
 order_id uuid NOT NULL REFERENCES public.typed_order_settlements(order_id) ON DELETE RESTRICT,
 purchaser_user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 allocated_by uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 allocated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX ix_typed_allocations_order ON public.order_item_qr_allocations(order_id,logical_item_id);
-- Durable, immutable handoff for Phase 6; old pair print workers cannot consume it.
CREATE TABLE public.typed_allocation_events (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 order_id uuid NOT NULL REFERENCES public.typed_order_settlements(order_id) ON DELETE RESTRICT,
 settlement_revision integer NOT NULL CHECK(settlement_revision>0),
 event_kind text NOT NULL CHECK(event_kind IN ('allocation.ready','allocation.reconciliation')),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(order_id,settlement_revision)
);
ALTER TABLE public.typed_order_settlements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.order_item_qr_allocations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.typed_allocation_events ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.typed_order_settlements,public.order_item_qr_allocations,public.typed_allocation_events
 FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM public.standalone_qr_states WHERE inventory_status='allocated') THEN
  RAISE EXCEPTION 'Existing standalone allocated fixtures require explicit reconciliation' USING ERRCODE='23514'; END IF;
END $$;

CREATE FUNCTION public.sr_typed_allocation_authorized(sid uuid,roles text[]) RETURNS boolean
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF roles IS NULL OR cardinality(roles)=0 OR NOT roles<@ARRAY['finance','operations']::text[]
  OR NOT public.sr_mfa() OR NOT EXISTS(SELECT 1 FROM public.sr_account_session_state(sid) WHERE email_verified AND mfa_active)
 THEN RETURN false; END IF;
 PERFORM 1 FROM public.staff_roles WHERE user_id=public.sr_actor_id() AND role=ANY(roles) AND revoked_at IS NULL ORDER BY role FOR SHARE;
 RETURN FOUND;
END $$;

CREATE FUNCTION public.sr_typed_claim_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE o public.orders; i public.order_logical_items; q public.qr_codes; s public.standalone_qr_states;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Permanent QR claims cannot be rewritten or recycled' USING ERRCODE='23514'; END IF;
 SELECT * INTO o FROM public.orders WHERE id=NEW.order_id FOR UPDATE;
 SELECT * INTO i FROM public.order_logical_items WHERE id=NEW.logical_item_id;
 SELECT * INTO q FROM public.qr_codes WHERE id=NEW.qr_id FOR UPDATE;
 SELECT * INTO s FROM public.standalone_qr_states WHERE qr_id=NEW.qr_id FOR UPDATE;
 IF o.id IS NULL OR i.id IS NULL OR q.id IS NULL OR s.qr_id IS NULL
  OR o.commerce_model<>'single_qr' OR o.payment_status<>'verified' OR o.order_status<>'placed'
  OR i.order_id<>o.id OR NEW.purchaser_user_id<>o.customer_user_id OR NEW.allocated_by<>public.sr_actor_id()
  OR q.pair_id IS NOT NULL OR q.tag_type<>i.qr_type_snapshot OR NOT q.is_current OR q.public_status<>'unactivated'
  OR s.inventory_status<>'available' OR s.ownership_status<>'unclaimed' OR s.owner_user_id IS NOT NULL
  OR NOT EXISTS(SELECT 1 FROM public.typed_order_settlements WHERE order_id=o.id AND state='reconciliation_pending')
 THEN RAISE EXCEPTION 'Paid item/QR claim mismatch' USING ERRCODE='23514'; END IF;
 PERFORM public.sr_financial_require_clear(o.id);
 RETURN NEW;
END $$;
CREATE TRIGGER sr_typed_claim_guard BEFORE INSERT OR UPDATE OR DELETE ON public.order_item_qr_allocations
 FOR EACH ROW EXECUTE FUNCTION public.sr_typed_claim_guard();

CREATE FUNCTION public.sr_typed_settlement_history() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP='DELETE' OR (TG_TABLE_NAME='typed_allocation_events' AND TG_OP='UPDATE') THEN
  RAISE EXCEPTION 'Typed settlement/event history is permanent' USING ERRCODE='23514'; END IF;
 IF TG_OP='UPDATE' THEN
  IF (NEW.order_id,NEW.attempt_id,NEW.verified_at) IS DISTINCT FROM (OLD.order_id,OLD.attempt_id,OLD.verified_at)
   OR OLD.state='allocated' OR NEW.revision<>OLD.revision+1 THEN
   RAISE EXCEPTION 'Typed settlement identity or terminal allocation cannot change' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_typed_settlement_history BEFORE UPDATE OR DELETE ON public.typed_order_settlements
 FOR EACH ROW EXECUTE FUNCTION public.sr_typed_settlement_history();
CREATE TRIGGER sr_typed_event_history BEFORE UPDATE OR DELETE ON public.typed_allocation_events
 FOR EACH ROW EXECUTE FUNCTION public.sr_typed_settlement_history();

CREATE FUNCTION public.sr_typed_settlement_complete(oid uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE o public.orders; t public.typed_order_settlements; expected integer; assigned integer;
BEGIN
 SELECT * INTO o FROM public.orders WHERE id=oid FOR UPDATE;
 IF o.id IS NULL OR o.commerce_model<>'single_qr' THEN RETURN; END IF;
 SELECT * INTO t FROM public.typed_order_settlements WHERE order_id=oid;
 SELECT count(*) INTO assigned FROM public.order_item_qr_allocations WHERE order_id=oid;
 IF t.order_id IS NULL THEN
  IF o.payment_status='verified' OR o.fulfillment_status NOT IN ('unallocated','exception') OR assigned<>0 OR EXISTS(SELECT 1 FROM public.payment_attempts WHERE order_id=oid AND verified_at IS NOT NULL)
   THEN RAISE EXCEPTION 'Typed verification requires a settlement ledger' USING ERRCODE='23514'; END IF;
  RETURN;
 END IF;
 IF NOT EXISTS(SELECT 1 FROM public.payment_attempts a JOIN public.payment_reviews r ON r.attempt_id=a.id
  WHERE a.id=t.attempt_id AND a.order_id=oid AND a.verified_at IS NOT NULL AND a.state IN ('verified','disputed')
   AND a.amount=o.total_pkr AND a.currency_code=o.currency_code AND r.decision='verify' AND r.bank_verified
   AND r.reviewed_by=a.reviewed_by)
  OR EXISTS(SELECT 1 FROM public.payment_attempts WHERE order_id=oid AND id<>t.attempt_id AND verified_at IS NOT NULL)
  OR o.payment_status<>'verified' THEN RAISE EXCEPTION 'Typed financial truth mismatch' USING ERRCODE='23514'; END IF;
 SELECT count(*) INTO expected FROM public.order_logical_items WHERE order_id=oid;
 IF expected=0 OR (t.state='allocated' AND (assigned<>expected OR o.fulfillment_status NOT IN ('allocated','exception')))
  OR (t.state='reconciliation_pending' AND (assigned<>0 OR o.fulfillment_status NOT IN ('unallocated','exception')))
 THEN RAISE EXCEPTION 'Typed allocation must be all or nothing' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM public.order_item_qr_allocations a JOIN public.order_logical_items i ON i.id=a.logical_item_id
  JOIN public.qr_codes q ON q.id=a.qr_id JOIN public.standalone_qr_states s ON s.qr_id=q.id
  WHERE a.order_id=oid AND (i.order_id<>oid OR i.qr_type_snapshot<>q.tag_type OR q.pair_id IS NOT NULL OR s.inventory_status<>'allocated'))
 THEN RAISE EXCEPTION 'Permanent claim state/type mismatch' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.typed_allocation_events WHERE order_id=oid AND settlement_revision=t.revision
  AND event_kind=CASE t.state WHEN 'allocated' THEN 'allocation.ready' ELSE 'allocation.reconciliation' END)
 THEN RAISE EXCEPTION 'Typed settlement requires durable handoff' USING ERRCODE='23514'; END IF;
END $$;

CREATE FUNCTION public.sr_typed_settlement_check() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE oid uuid;
BEGIN
 IF TG_TABLE_NAME='orders' THEN oid:=NEW.id;
 ELSIF TG_TABLE_NAME='standalone_qr_states' THEN
  SELECT order_id INTO oid FROM public.order_item_qr_allocations WHERE qr_id=NEW.qr_id;
  IF NEW.inventory_status='allocated' AND oid IS NULL THEN RAISE EXCEPTION 'Allocated typed inventory requires a permanent claim' USING ERRCODE='23514'; END IF;
 ELSE oid:=NEW.order_id; END IF;
 PERFORM public.sr_typed_settlement_complete(oid); RETURN NULL;
END $$;
DO $$ DECLARE tbl text; BEGIN
 FOREACH tbl IN ARRAY ARRAY['orders','payment_attempts','typed_order_settlements','order_item_qr_allocations','typed_allocation_events','standalone_qr_states'] LOOP
  EXECUTE format('CREATE CONSTRAINT TRIGGER sr_typed_settlement_complete AFTER INSERT OR UPDATE ON public.%I DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_typed_settlement_check()',tbl);
 END LOOP;
END $$;

-- Keep physical production closed until Phase 6, independently of settlement.
CREATE FUNCTION public.sr_typed_production_gate() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM public.orders WHERE id=NEW.order_id AND commerce_model='single_qr')
  AND (TG_TABLE_NAME<>'durable_jobs' OR to_jsonb(NEW)->>'job_kind' IN ('allocation.finalize','print.render'))
 THEN RAISE EXCEPTION 'Typed production is not released' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_typed_production_gate BEFORE INSERT ON public.print_jobs FOR EACH ROW EXECUTE FUNCTION public.sr_typed_production_gate();
CREATE TRIGGER sr_typed_production_gate BEFORE INSERT ON public.shipments FOR EACH ROW EXECUTE FUNCTION public.sr_typed_production_gate();
CREATE TRIGGER sr_typed_production_gate BEFORE INSERT ON public.durable_jobs FOR EACH ROW EXECUTE FUNCTION public.sr_typed_production_gate();

CREATE OR REPLACE FUNCTION public.sr_item_order_model_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP='UPDATE' AND (NEW.commerce_model IS DISTINCT FROM OLD.commerce_model OR NEW.payment_instructions_snapshot IS DISTINCT FROM OLD.payment_instructions_snapshot)
 THEN RAISE EXCEPTION 'Order model/instructions are immutable' USING ERRCODE='23514'; END IF;
 IF NEW.commerce_model='single_qr' THEN
  IF TG_OP='INSERT' AND NOT public.sr_single_checkout_enabled() THEN RAISE EXCEPTION 'Single checkout is not released' USING ERRCODE='23514'; END IF;
  IF NEW.payment_instructions_snapshot IS NULL OR NEW.payment_status='refunded' OR NEW.fulfillment_status NOT IN ('unallocated','allocated','exception') THEN
   RAISE EXCEPTION 'Typed physical production/refund is not released' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION public.sr_item_payment_gate() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NEW.state='refunded' AND EXISTS(SELECT 1 FROM public.orders WHERE id=NEW.order_id AND commerce_model='single_qr') THEN
  RAISE EXCEPTION 'Typed refunds require independent reconciliation' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION public.sr_typed_allocate(oid uuid) RETURNS text
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE o public.orders; t public.typed_order_settlements; i public.order_logical_items;
 kind text; wanted integer; selected uuid[]; candidates uuid[]:='{}'::uuid[]; why text; idx integer:=0;
BEGIN
 PERFORM public.sr_template_registry_gate(false);
 SELECT * INTO o FROM public.orders WHERE id=oid FOR UPDATE;
 SELECT * INTO t FROM public.typed_order_settlements WHERE order_id=oid FOR UPDATE;
 IF t.order_id IS NULL OR o.payment_status<>'verified' OR o.commerce_model<>'single_qr' OR o.order_status<>'placed' THEN
  RAISE EXCEPTION 'Verified placed typed order required' USING ERRCODE='23514'; END IF;
 IF t.state='allocated' THEN RETURN 'allocated'; END IF;
 IF NOT public.sr_financial_order_lock_clear(oid) THEN why:='financial_review';
 ELSIF EXISTS(SELECT 1 FROM public.order_cancellation_requests WHERE order_id=oid AND status IN ('requested','investigating','approved','escalated')) THEN why:='cancellation_review';
 ELSIF EXISTS(SELECT 1 FROM public.order_item_sizes s JOIN public.order_logical_items x ON x.id=s.logical_item_id
  WHERE x.order_id=oid AND NOT public.sr_template_revision_clear(s.revision_id,true)) THEN why:='template_review';
 END IF;
 IF why IS NULL THEN
  -- All allocators acquire the required type locks in the same order. A shortage
  -- is decided before any permanent claim or inventory transition is written.
  FOR kind,wanted IN SELECT qr_type_snapshot,count(*)::integer FROM public.order_logical_items WHERE order_id=oid GROUP BY qr_type_snapshot ORDER BY qr_type_snapshot LOOP
   PERFORM pg_advisory_xact_lock(51410001,CASE kind WHEN 'ice' THEN 0 ELSE 1 END);
  END LOOP;
  FOR kind,wanted IN SELECT qr_type_snapshot,count(*)::integer FROM public.order_logical_items WHERE order_id=oid GROUP BY qr_type_snapshot ORDER BY qr_type_snapshot LOOP
   SELECT COALESCE(array_agg(id ORDER BY id),'{}'::uuid[]) INTO selected FROM (
    SELECT q.id FROM public.qr_codes q JOIN public.standalone_qr_states s ON s.qr_id=q.id JOIN public.qr_batches b ON b.id=q.batch_id
    WHERE q.pair_id IS NULL AND q.tag_type=kind AND q.is_current AND q.public_status='unactivated'
     AND b.generation_mode='standalone' AND b.qr_type=kind AND b.status='generated'
     AND s.inventory_status='available' AND s.ownership_status='unclaimed' AND s.owner_user_id IS NULL
     AND s.activated_at IS NULL AND s.revoked_at IS NULL
     AND NOT EXISTS(SELECT 1 FROM public.order_item_qr_allocations WHERE qr_id=q.id)
    ORDER BY q.id FOR UPDATE OF q,s SKIP LOCKED LIMIT wanted
   ) available;
   IF cardinality(selected)<>wanted THEN why:='stock_shortage'; EXIT; END IF;
   candidates:=candidates||selected;
  END LOOP;
 END IF;
 IF why IS NOT NULL THEN
  IF t.reason_code IS DISTINCT FROM why THEN
   UPDATE public.typed_order_settlements SET reason_code=why,revision=revision+1 WHERE order_id=oid;
  END IF;
  RETURN 'reconciliation_pending';
 END IF;
 FOR i IN SELECT * FROM public.order_logical_items WHERE order_id=oid ORDER BY qr_type_snapshot,id LOOP
  idx:=idx+1;
  INSERT INTO public.order_item_qr_allocations(logical_item_id,qr_id,order_id,purchaser_user_id,allocated_by)
   VALUES(i.id,candidates[idx],oid,o.customer_user_id,public.sr_actor_id());
  UPDATE public.standalone_qr_states SET inventory_status='allocated',row_version=row_version+1 WHERE qr_id=candidates[idx];
 END LOOP;
 UPDATE public.typed_order_settlements SET state='allocated',reason_code=NULL,allocated_at=clock_timestamp(),revision=revision+1 WHERE order_id=oid;
 UPDATE public.orders SET fulfillment_status='allocated' WHERE id=oid;
 RETURN 'allocated';
END $$;

CREATE FUNCTION public.sr_typed_settlement_handoff(oid uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE t public.typed_order_settlements; event_id uuid;
BEGIN
 SELECT * INTO t FROM public.typed_order_settlements WHERE order_id=oid;
 INSERT INTO public.typed_allocation_events(order_id,settlement_revision,event_kind)
 VALUES(oid,t.revision,CASE t.state WHEN 'allocated' THEN 'allocation.ready' ELSE 'allocation.reconciliation' END) ON CONFLICT DO NOTHING RETURNING id INTO event_id;
 IF event_id IS NULL THEN RETURN; END IF;
 INSERT INTO public.finance_sheet_sync(order_id,status) VALUES(oid,'pending') ON CONFLICT(order_id) DO UPDATE SET status='pending',updated_at=clock_timestamp();
 INSERT INTO public.durable_jobs(job_kind,aggregate_type,aggregate_id,order_id,idempotency_key)
 VALUES('finance.sync','order',oid,oid,'typed.finance:'||oid::text||':'||t.revision::text) ON CONFLICT(idempotency_key) DO NOTHING;
END $$;

CREATE FUNCTION public.sr_typed_allocation_status(oid uuid) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE o public.orders; t public.typed_order_settlements; requested integer; assigned integer;
BEGIN
 SELECT * INTO o FROM public.orders WHERE id=oid;
 IF o.id IS NULL OR (o.customer_user_id IS DISTINCT FROM public.sr_actor_id() AND NOT public.sr_is_staff(ARRAY['finance','operations'])) THEN RETURN NULL; END IF;
 IF o.commerce_model<>'single_qr' THEN RETURN jsonb_build_object('error','LEGACY_ORDER'); END IF;
 SELECT * INTO t FROM public.typed_order_settlements WHERE order_id=oid;
 SELECT count(*) INTO requested FROM public.order_logical_items WHERE order_id=oid;
 SELECT count(*) INTO assigned FROM public.order_item_qr_allocations WHERE order_id=oid;
 RETURN jsonb_build_object('state',COALESCE(t.state,'awaiting_verified_payment'),'reason_code',t.reason_code,'requested_count',requested,'allocated_count',assigned);
END $$;

CREATE FUNCTION public.sr_typed_settle(sid uuid,aid uuid,bank_verified boolean,settled numeric,currency text,fingerprint bytea,note text)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE oid uuid; o public.orders; a public.payment_attempts; rid uuid; result jsonb;
BEGIN
 PERFORM public.sr_template_registry_gate(false);
 IF NOT public.sr_typed_allocation_authorized(sid,ARRAY['finance']) THEN RETURN jsonb_build_object('error','FORBIDDEN'); END IF;
 SELECT order_id INTO oid FROM public.payment_attempts WHERE id=aid;
 SELECT * INTO o FROM public.orders WHERE id=oid FOR UPDATE;
 SELECT * INTO a FROM public.payment_attempts WHERE id=aid FOR UPDATE;
 IF a.id IS NULL OR o.id IS NULL THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
 IF NOT public.sr_typed_allocation_authorized(sid,ARRAY['finance']) THEN RETURN jsonb_build_object('error','FORBIDDEN'); END IF;
 IF o.commerce_model<>'single_qr' OR o.order_status<>'placed' OR o.payment_status IN ('verified','refunded') OR a.state NOT IN ('submitted','under_review')
  OR EXISTS(SELECT 1 FROM public.typed_order_settlements WHERE order_id=oid) THEN RETURN jsonb_build_object('error','PAYMENT_CLOSED'); END IF;
 IF bank_verified IS DISTINCT FROM true OR fingerprint IS NULL OR octet_length(fingerprint)<>32 OR note IS NULL OR length(note) NOT BETWEEN 4 AND 1000 THEN
  RETURN jsonb_build_object('error','BANK_VERIFICATION_REQUIRED'); END IF;
 IF settled IS NULL OR currency IS NULL OR settled<>a.amount OR settled<>o.total_pkr OR currency<>a.currency_code OR currency<>o.currency_code THEN
  RETURN jsonb_build_object('error','SETTLEMENT_MISMATCH'); END IF;
 rid:=gen_random_uuid();
 INSERT INTO public.payment_reviews(id,attempt_id,reviewed_by,decision,bank_verified,bank_reference_fingerprint,bank_reference_key_version,reason)
 VALUES(rid,aid,public.sr_actor_id(),'verify',true,fingerprint,1,note);
 UPDATE public.payment_attempts SET state='verified',reviewed_by=public.sr_actor_id(),verified_at=clock_timestamp() WHERE id=aid;
 UPDATE public.orders SET payment_status='verified' WHERE id=oid;
 INSERT INTO public.typed_order_settlements(order_id,attempt_id,state,reason_code) VALUES(oid,aid,'reconciliation_pending','stock_shortage');
 PERFORM public.sr_typed_allocate(oid);
 PERFORM public.sr_typed_settlement_handoff(oid);
 result:=public.sr_typed_allocation_status(oid);
 INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,reason,safe_details)
 VALUES(public.sr_actor_id(),'staff','payment.typed_settled','order',oid,'verified bank settlement',jsonb_build_object('review_id',rid,'allocation',result));
 IF NOT public.sr_typed_allocation_authorized(sid,ARRAY['finance']) THEN RAISE EXCEPTION 'Settlement authority changed' USING ERRCODE='42501'; END IF;
 PERFORM public.sr_typed_settlement_complete(oid);
 RETURN jsonb_build_object('attempt_id',aid,'state','verified','order_id',oid,'review_id',rid,'fulfillment_eligible',false,'allocation',result);
END $$;

CREATE FUNCTION public.sr_typed_allocation_retry(sid uuid,oid uuid) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE o public.orders; t public.typed_order_settlements; result jsonb;
BEGIN
 PERFORM public.sr_template_registry_gate(false);
 IF NOT public.sr_typed_allocation_authorized(sid,ARRAY['finance','operations']) THEN RETURN jsonb_build_object('error','FORBIDDEN'); END IF;
 SELECT * INTO o FROM public.orders WHERE id=oid FOR UPDATE;
 IF o.id IS NULL THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
 IF NOT public.sr_typed_allocation_authorized(sid,ARRAY['finance','operations']) THEN RETURN jsonb_build_object('error','FORBIDDEN'); END IF;
 SELECT * INTO t FROM public.typed_order_settlements WHERE order_id=oid;
 IF t.order_id IS NULL OR o.commerce_model<>'single_qr' THEN RETURN jsonb_build_object('error','VERIFIED_TYPED_ORDER_REQUIRED'); END IF;
 IF t.state<>'allocated' THEN
  IF o.order_status<>'placed' OR o.payment_status<>'verified' THEN RETURN jsonb_build_object('error','ORDER_RECONCILIATION_REQUIRED'); END IF;
  PERFORM public.sr_typed_allocate(oid);
  PERFORM public.sr_typed_settlement_handoff(oid);
 END IF;
 result:=public.sr_typed_allocation_status(oid);
 INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,reason,safe_details)
 VALUES(public.sr_actor_id(),'staff','allocation.typed_retry','order',oid,'authorized reconciliation retry',result);
 IF NOT public.sr_typed_allocation_authorized(sid,ARRAY['finance','operations']) THEN RAISE EXCEPTION 'Allocation authority changed' USING ERRCODE='42501'; END IF;
 PERFORM public.sr_typed_settlement_complete(oid);
 RETURN jsonb_build_object('order_id',oid,'payment_status','verified','allocation',result,'fulfillment_eligible',false);
END $$;

REVOKE ALL ON FUNCTION public.sr_typed_allocation_authorized(uuid,text[]),public.sr_typed_claim_guard(),public.sr_typed_settlement_history(),
 public.sr_typed_settlement_complete(uuid),public.sr_typed_settlement_check(),public.sr_typed_production_gate(),public.sr_typed_allocate(uuid),
 public.sr_typed_settlement_handoff(uuid),public.sr_typed_allocation_status(uuid),public.sr_typed_settle(uuid,uuid,boolean,numeric,text,bytea,text),public.sr_typed_allocation_retry(uuid,uuid)
 FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_typed_allocation_status(uuid),public.sr_typed_settle(uuid,uuid,boolean,numeric,text,bytea,text),public.sr_typed_allocation_retry(uuid,uuid) TO safereturn_api;

-- Retain all prior financial signals; pending typed allocation remains actionable.
CREATE OR REPLACE FUNCTION public.sr_finance_reconciliation_rows(cutoff timestamptz)
RETURNS TABLE(order_id uuid,attempt_id uuid,reason_code text,observed_since timestamptz,
 attempt_amount numeric,order_amount numeric,currency text,order_currency text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 IF NOT public.sr_is_staff(ARRAY['finance']) THEN
  RAISE EXCEPTION 'finance authority required' USING ERRCODE='42501';
 END IF;
 IF cutoff IS NULL OR cutoff>statement_timestamp() THEN
  RAISE EXCEPTION 'invalid time ceiling' USING ERRCODE='22023';
 END IF;
 RETURN QUERY
 WITH attempts AS (
  SELECT a.id aid,a.order_id oid,a.state,a.amount,a.currency_code::text cur,
   a.created_at stamp,a.verified_at,o.total_pkr total,o.currency_code::text ocur,
   EXISTS(SELECT 1 FROM public.payment_reviews r WHERE r.attempt_id=a.id
     AND r.decision='verify' AND r.bank_verified) verified_review
  FROM public.payment_attempts a JOIN public.orders o ON o.id=a.order_id
  WHERE a.created_at<=cutoff AND o.created_at<=cutoff
 ), attempt_signals AS (
  SELECT a.*,'REVIEW_PENDING' code FROM attempts a WHERE a.state IN('submitted','under_review')
  UNION ALL SELECT a.*,'ATTEMPT_ORDER_AMOUNT_MISMATCH' FROM attempts a WHERE a.amount<>a.total
  UNION ALL SELECT a.*,'ATTEMPT_ORDER_CURRENCY_MISMATCH' FROM attempts a WHERE a.cur<>a.ocur
  UNION ALL SELECT a.*,'VERIFIED_HISTORY_MISMATCH' FROM attempts a WHERE
     (a.state='verified' AND (NOT a.verified_review OR a.verified_at IS NULL))
     OR (a.state<>'verified' AND a.verified_review)
  UNION ALL SELECT a.*,'DUPLICATE_VERIFIED_REFERENCE' FROM attempts a WHERE EXISTS(
     SELECT 1 FROM public.payment_reviews r JOIN public.payment_reviews other
       ON other.bank_reference_fingerprint=r.bank_reference_fingerprint
       AND other.attempt_id<>r.attempt_id AND other.decision='verify'
     WHERE r.attempt_id=a.aid AND r.decision='verify'
       AND r.bank_reference_fingerprint IS NOT NULL
       AND EXISTS(SELECT 1 FROM public.payment_attempts x
         WHERE x.id=other.attempt_id AND x.created_at<=cutoff))
 ), order_signals AS (
  SELECT o.id,o.created_at,o.total_pkr,o.currency_code,'ORDER_SETTLEMENT_MISMATCH' code FROM public.orders o
  WHERE o.created_at<=cutoff AND
    ((o.payment_status='verified' AND NOT EXISTS(SELECT 1 FROM attempts a WHERE a.oid=o.id AND a.state='verified'))
    OR (o.payment_status<>'verified' AND EXISTS(SELECT 1 FROM attempts a WHERE a.oid=o.id AND a.state='verified')))
  UNION ALL
  SELECT o.id,o.created_at,o.total_pkr,o.currency_code,'VERIFIED_ALLOCATION_MISMATCH' FROM public.orders o
  WHERE o.created_at<=cutoff AND o.payment_status='verified' AND
    ((o.commerce_model='legacy_pair' AND (NOT EXISTS(SELECT 1 FROM public.order_pair_units u WHERE u.order_id=o.id)
     OR EXISTS(SELECT 1 FROM public.order_pair_units u WHERE u.order_id=o.id AND u.status<>'allocated')))
     OR (o.commerce_model='single_qr' AND NOT EXISTS(SELECT 1 FROM public.typed_order_settlements t WHERE t.order_id=o.id AND t.state='allocated')))
 )
 SELECT a.oid AS order_id,a.aid AS attempt_id,a.code AS reason_code,
  a.stamp AS observed_since,a.amount AS attempt_amount,a.total AS order_amount,
  a.cur AS currency,a.ocur AS order_currency FROM attempt_signals a
 UNION ALL
 SELECT o.id,NULL::uuid,o.code,o.created_at,NULL::numeric,o.total_pkr,NULL::text,o.currency_code::text FROM order_signals o;
END $$;

-- Typed events enqueue finance once per committed ledger revision. Legacy body preserved.
CREATE OR REPLACE FUNCTION public.sr_finance_changed() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NEW.commerce_model='single_qr' THEN RETURN NEW; END IF;
 IF NEW.payment_status='verified' AND
   (NEW.payment_status,NEW.fulfillment_status) IS DISTINCT FROM (OLD.payment_status,OLD.fulfillment_status) THEN
  INSERT INTO public.finance_sheet_sync(order_id,status) VALUES(NEW.id,'pending')
   ON CONFLICT(order_id) DO UPDATE SET status='pending',updated_at=clock_timestamp();
  INSERT INTO public.durable_jobs(job_kind,aggregate_type,aggregate_id,order_id,idempotency_key)
   VALUES('finance.sync','order',NEW.id,NEW.id,'finance.changed:'||NEW.id::text||':'||txid_current()::text)
   ON CONFLICT(idempotency_key) DO NOTHING;
 END IF;
 RETURN NEW;
END $$;
