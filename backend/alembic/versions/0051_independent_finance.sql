-- PREPARED ONLY. No migration application or runtime grants authorized.
-- Exact order reconciliation; never scans legacy orders or pair relations.
CREATE FUNCTION public.sr_independent_finance_snapshot(sid uuid,oid uuid)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE o public.orders; allocation jsonb; history jsonb; signals jsonb;
BEGIN
 IF NOT public.sr_typed_allocation_authorized(sid,ARRAY['finance']) THEN
  RETURN jsonb_build_object('error','FORBIDDEN'); END IF;
 SELECT * INTO o FROM public.orders WHERE id=oid AND commerce_model='single_qr';
 IF o.id IS NULL THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
 allocation:=public.sr_typed_allocation_status(oid);
 SELECT coalesce(jsonb_agg(to_jsonb(r) ORDER BY r.reviewed_at DESC,r.review_id DESC),'[]'::jsonb)
 INTO history FROM (
  SELECT r.id review_id,r.attempt_id,r.decision,r.bank_verified,r.reason,r.reviewed_at,
   CASE WHEN r.bank_verified AND r.decision='verify' THEN a.amount::text ELSE NULL END settled_amount,
   CASE WHEN r.bank_verified AND r.decision='verify' THEN a.currency_code::text ELSE NULL END settled_currency,
   r.bank_reference_fingerprint IS NOT NULL settlement_reference_recorded
  FROM public.payment_reviews r JOIN public.payment_attempts a ON a.id=r.attempt_id
  WHERE a.order_id=oid ORDER BY r.reviewed_at DESC,r.id DESC LIMIT 100
 ) r;
 SELECT coalesce(jsonb_agg(code ORDER BY code),'[]'::jsonb) INTO signals FROM (
  SELECT 'REVIEW_PENDING' code WHERE EXISTS(SELECT 1 FROM public.payment_attempts WHERE order_id=oid AND state IN('submitted','under_review'))
  UNION SELECT 'ATTEMPT_ORDER_AMOUNT_MISMATCH' WHERE EXISTS(SELECT 1 FROM public.payment_attempts WHERE order_id=oid AND amount<>o.total_pkr)
  UNION SELECT 'ATTEMPT_ORDER_CURRENCY_MISMATCH' WHERE EXISTS(SELECT 1 FROM public.payment_attempts WHERE order_id=oid AND currency_code<>o.currency_code)
  UNION SELECT 'MULTIPLE_OPEN_ATTEMPTS' WHERE (SELECT count(*) FROM public.payment_attempts WHERE order_id=oid AND state IN('submitted','under_review'))>1
  UNION SELECT 'ORDER_SETTLEMENT_MISMATCH' WHERE
   (o.payment_status='verified') IS DISTINCT FROM EXISTS(SELECT 1 FROM public.typed_order_settlements WHERE order_id=oid)
  UNION SELECT 'VERIFIED_ALLOCATION_MISMATCH' WHERE o.payment_status='verified' AND
   ((allocation->>'state') IS DISTINCT FROM 'allocated' OR
    (SELECT count(*) FROM public.order_item_qr_allocations WHERE order_id=oid) <>
    (SELECT count(*) FROM public.order_logical_items WHERE order_id=oid))
  UNION SELECT 'VERIFIED_HISTORY_MISMATCH' WHERE EXISTS(
   SELECT 1 FROM public.payment_attempts a WHERE a.order_id=oid AND
    ((a.state='verified') IS DISTINCT FROM EXISTS(SELECT 1 FROM public.payment_reviews r WHERE r.attempt_id=a.id AND r.decision='verify' AND r.bank_verified)
     OR (a.state='verified' AND a.verified_at IS NULL)))
  UNION SELECT 'DUPLICATE_VERIFIED_REFERENCE' WHERE EXISTS(
   SELECT 1 FROM public.payment_attempts a JOIN public.payment_reviews r ON r.attempt_id=a.id
    JOIN public.payment_reviews other ON other.bank_reference_fingerprint=r.bank_reference_fingerprint
     AND other.attempt_id<>r.attempt_id AND other.decision='verify'
   WHERE a.order_id=oid AND r.decision='verify' AND r.bank_reference_fingerprint IS NOT NULL)
 ) checks;
 IF NOT public.sr_typed_allocation_authorized(sid,ARRAY['finance']) THEN
  RAISE EXCEPTION 'Finance authority changed' USING ERRCODE='42501'; END IF;
 INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,reason,safe_details)
 VALUES(public.sr_actor_id(),'staff','finance.independent.read','order',oid,'independent finance reconciliation','{}'::jsonb);
 RETURN jsonb_build_object('order_id',o.id,'order_number',o.order_number,'order_status',o.order_status,
  'payment_status',o.payment_status,'fulfillment_status',o.fulfillment_status,'amount_due',o.total_pkr::text,
  'currency',o.currency_code,'allocation',allocation,'signals',signals,'reviews',history,
  'history_limit',100,'can_review',o.customer_user_id<>public.sr_actor_id() AND o.order_status='placed' AND o.payment_status NOT IN('verified','refunded'),
  'unavailable_checks',jsonb_build_array('BANK_LEDGER_AMOUNT_COMPARISON','RAW_SETTLEMENT_REFERENCE_RETRIEVAL'));
END $$;

CREATE FUNCTION public.sr_independent_finance_authorize(sid uuid,auth_time numeric,oid uuid)
RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NOT public.sr_typed_allocation_authorized(sid,ARRAY['finance']) OR auth_time IS NULL
  OR extract(epoch FROM clock_timestamp())-auth_time NOT BETWEEN 0 AND 300 THEN RETURN false; END IF;
 RETURN EXISTS(SELECT 1 FROM public.orders WHERE id=oid AND commerce_model='single_qr'
  AND customer_user_id<>public.sr_actor_id());
END $$;

CREATE FUNCTION public.sr_independent_finance_review(sid uuid,auth_time numeric,aid uuid,
 decision text,bank_verified boolean,settled numeric,currency text,fingerprint bytea,note text)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE oid uuid; o public.orders; a public.payment_attempts; result jsonb; rid uuid; next_state text;
BEGIN
 -- Lock order before attempt, exactly as the verified allocator does.
 PERFORM public.sr_template_registry_gate(false);
 IF NOT public.sr_typed_allocation_authorized(sid,ARRAY['finance']) THEN RETURN jsonb_build_object('error','FORBIDDEN'); END IF;
 SELECT order_id INTO oid FROM public.payment_attempts WHERE id=aid;
 IF NOT public.sr_independent_finance_authorize(sid,auth_time,oid) THEN RETURN jsonb_build_object('error','FORBIDDEN'); END IF;
 SELECT * INTO o FROM public.orders WHERE id=oid FOR UPDATE;
 SELECT * INTO a FROM public.payment_attempts WHERE id=aid FOR UPDATE;
 IF NOT public.sr_independent_finance_authorize(sid,auth_time,oid) THEN RETURN jsonb_build_object('error','FORBIDDEN'); END IF;
 IF decision='verify' THEN
  result:=public.sr_typed_settle(sid,aid,bank_verified,settled,currency,fingerprint,note);
 ELSE
  IF decision NOT IN('reject','request_more_info') OR decision IS NULL OR bank_verified IS DISTINCT FROM false
   OR settled IS NOT NULL OR currency IS NOT NULL OR fingerprint IS NOT NULL OR note IS NULL OR length(note) NOT BETWEEN 4 AND 1000
  THEN RETURN jsonb_build_object('error','INVALID_BANK_VERIFICATION'); END IF;
  IF o.order_status<>'placed' OR o.payment_status IN('verified','refunded') OR a.state NOT IN('submitted','under_review')
   OR EXISTS(SELECT 1 FROM public.typed_order_settlements WHERE order_id=oid)
  THEN RETURN jsonb_build_object('error','PAYMENT_CLOSED'); END IF;
  rid:=gen_random_uuid(); next_state:=CASE WHEN decision='reject' THEN 'rejected' ELSE 'under_review' END;
  INSERT INTO public.payment_reviews(id,attempt_id,reviewed_by,decision,bank_verified,reason)
   VALUES(rid,aid,public.sr_actor_id(),decision,false,note);
  UPDATE public.payment_attempts SET state=next_state,reviewed_by=public.sr_actor_id() WHERE id=aid;
  -- Rejecting one attempt must not hide another attempt awaiting review.
  UPDATE public.orders SET payment_status=CASE WHEN EXISTS(SELECT 1 FROM public.payment_attempts
   WHERE order_id=oid AND state IN('submitted','under_review')) THEN 'under_review' ELSE next_state END WHERE id=oid;
  INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,reason,safe_details)
   VALUES(public.sr_actor_id(),'staff','payment.independent.review','order',oid,'finance decision',jsonb_build_object('event_id',rid,'outcome',decision));
  result:=jsonb_build_object('attempt_id',aid,'order_id',oid,'review_id',rid,'state',next_state,
   'fulfillment_eligible',false,'allocation',public.sr_typed_allocation_status(oid));
 END IF;
 IF NOT public.sr_independent_finance_authorize(sid,auth_time,oid) THEN
  RAISE EXCEPTION 'Finance authority expired' USING ERRCODE='42501'; END IF;
 RETURN result;
END $$;

CREATE FUNCTION public.sr_independent_finance_retry(sid uuid,auth_time numeric,oid uuid)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE result jsonb;
BEGIN
 IF NOT public.sr_independent_finance_authorize(sid,auth_time,oid) THEN RETURN jsonb_build_object('error','FORBIDDEN'); END IF;
 result:=public.sr_typed_allocation_retry(sid,oid);
 IF NOT public.sr_independent_finance_authorize(sid,auth_time,oid) THEN
  RAISE EXCEPTION 'Finance authority expired' USING ERRCODE='42501'; END IF;
 RETURN result;
END $$;

-- Deliberately no grants. Migration application is NOT endpoint release.
REVOKE ALL ON FUNCTION public.sr_independent_finance_snapshot(uuid,uuid),
 public.sr_independent_finance_authorize(uuid,numeric,uuid),
 public.sr_independent_finance_review(uuid,numeric,uuid,text,boolean,numeric,text,bytea,text),
 public.sr_independent_finance_retry(uuid,numeric,uuid)
 FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
