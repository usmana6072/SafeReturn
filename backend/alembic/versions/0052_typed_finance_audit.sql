-- Prepared additive compatibility repair. No grants, rows, or audit-policy changes.
-- Only audit metadata differs from the existing typed functions. Durable records retain details.

CREATE OR REPLACE FUNCTION public.sr_typed_inventory_generate(
 sid uuid,label text,kind text,quantity integer,ecc text,request_key text,tokens jsonb
) RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE actor uuid:=public.sr_actor_id(); digest text; old public.typed_inventory_receipts;
 bid uuid; created timestamptz; result jsonb;
BEGIN
 IF NOT public.sr_typed_inventory_authorized(sid) THEN RETURN jsonb_build_object('error','FORBIDDEN'); END IF;
 IF label IS NULL OR char_length(label) NOT BETWEEN 3 AND 40 OR label !~ '^[A-Za-z0-9][A-Za-z0-9._-]+$'
  OR kind IS NULL OR kind NOT IN ('lost','ice') OR quantity IS NULL OR quantity NOT BETWEEN 1 AND 1000
  OR ecc IS NULL OR ecc NOT IN ('M','Q') OR request_key IS NULL OR request_key !~ '^[A-Za-z0-9._:-]{8,160}$'
 THEN RAISE EXCEPTION 'Invalid typed generation request' USING ERRCODE='22023'; END IF;
 digest:=encode(sha256(convert_to(jsonb_build_object('label',label,'type',kind,'quantity',quantity,'ecc',ecc)::text,'UTF8')),'hex');
 PERFORM pg_advisory_xact_lock(hashtextextended('typed-inventory:'||actor::text||':'||request_key,0));
 -- A replay can wait behind another transaction; recheck session expiry after waiting.
 IF NOT public.sr_typed_inventory_authorized(sid) THEN RETURN jsonb_build_object('error','FORBIDDEN'); END IF;
 SELECT * INTO old FROM public.typed_inventory_receipts WHERE actor_user_id=actor AND idempotency_key=request_key;
 IF FOUND THEN
  IF old.request_hash<>digest THEN RETURN jsonb_build_object('error','IDEMPOTENCY_KEY_REUSED'); END IF;
  RETURN old.response;
 END IF;
 -- Same label lock protocol as the legacy pair generator; uniqueness is the final guard.
 PERFORM pg_advisory_xact_lock(hashtextextended(label,0));
 IF EXISTS(SELECT 1 FROM public.qr_batches WHERE batch_code=label) THEN
  RETURN jsonb_build_object('error','BATCH_LABEL_CONFLICT');
 END IF;
 IF tokens IS NULL OR jsonb_typeof(tokens)<>'array' THEN
  RAISE EXCEPTION 'Invalid generated tokens' USING ERRCODE='22023';
 END IF;
 IF jsonb_array_length(tokens)<>quantity OR EXISTS (
  SELECT 1 FROM jsonb_array_elements(tokens) t WHERE jsonb_typeof(t)<>'string' OR (t#>>'{}') !~ '^[A-Za-z0-9_-]{43}$'
 ) OR (SELECT count(DISTINCT t#>>'{}') FROM jsonb_array_elements(tokens) t)<>quantity THEN
  RAISE EXCEPTION 'Invalid generated tokens' USING ERRCODE='22023';
 END IF;
 bid:=gen_random_uuid();
 INSERT INTO public.qr_batches(id,batch_code,ecc_level,status,generation_mode,qr_type,requested_quantity)
 VALUES(bid,label,ecc,'generated','standalone',kind,quantity) RETURNING created_at INTO created;
 INSERT INTO public.qr_codes(id,batch_id,tag_type,serial_number,public_token,ecc_level)
 SELECT gen_random_uuid(),bid,kind,'SR-'||replace(bid::text,'-','')||'-'||lpad(ordinality::text,6,'0'),value#>>'{}',ecc
 FROM jsonb_array_elements(tokens) WITH ORDINALITY;
 INSERT INTO public.standalone_qr_states(qr_id)
 SELECT id FROM public.qr_codes WHERE batch_id=bid AND pair_id IS NULL;
 result:=jsonb_build_object('batch_id',bid,'batch_label',label,'qr_type',kind,
  'generated_quantity',quantity,'status','generated','created_at',created);
 INSERT INTO public.typed_inventory_receipts(actor_user_id,idempotency_key,request_hash,batch_id,response)
 VALUES(actor,request_key,digest,bid,result);
 INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,request_id,safe_details)
 VALUES(actor,'staff','inventory.typed_batch.generated','qr_batch',bid,
  encode(sha256(convert_to(actor::text||':'||request_key,'UTF8')),'hex'),
  jsonb_build_object('event_id',bid,'outcome','success'));
 IF NOT public.sr_typed_inventory_authorized(sid) THEN
  RAISE EXCEPTION 'Inventory authority changed' USING ERRCODE='42501';
 END IF;
 RETURN result;
END $$;

CREATE OR REPLACE FUNCTION public.sr_typed_settle(sid uuid,aid uuid,bank_verified boolean,settled numeric,currency text,fingerprint bytea,note text)
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
 VALUES(public.sr_actor_id(),'staff','payment.typed_settled','order',oid,'verified bank settlement',jsonb_build_object('event_id',rid,'outcome',result->>'state','reason_code',result->>'reason_code'));
 IF NOT public.sr_typed_allocation_authorized(sid,ARRAY['finance']) THEN RAISE EXCEPTION 'Settlement authority changed' USING ERRCODE='42501'; END IF;
 PERFORM public.sr_typed_settlement_complete(oid);
 RETURN jsonb_build_object('attempt_id',aid,'state','verified','order_id',oid,'review_id',rid,'fulfillment_eligible',false,'allocation',result);
END $$;

CREATE OR REPLACE FUNCTION public.sr_typed_allocation_retry(sid uuid,oid uuid) RETURNS jsonb
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
 VALUES(public.sr_actor_id(),'staff','allocation.typed_retry','order',oid,'authorized reconciliation retry',jsonb_build_object('event_id',oid,'outcome',result->>'state','reason_code',result->>'reason_code'));
 IF NOT public.sr_typed_allocation_authorized(sid,ARRAY['finance','operations']) THEN RAISE EXCEPTION 'Allocation authority changed' USING ERRCODE='42501'; END IF;
 PERFORM public.sr_typed_settlement_complete(oid);
 RETURN jsonb_build_object('order_id',oid,'payment_status','verified','allocation',result,'fulfillment_eligible',false);
END $$;
