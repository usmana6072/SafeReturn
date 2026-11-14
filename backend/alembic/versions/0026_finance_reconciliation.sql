-- Synthetic/offline review only. Application is a separate authorized DB gate.
-- No table writes, bank-data replication, index changes or automatic remediation.
CREATE FUNCTION public.sr_finance_reconciliation_rows(cutoff timestamptz)
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
    (NOT EXISTS(SELECT 1 FROM public.order_pair_units u WHERE u.order_id=o.id)
     OR EXISTS(SELECT 1 FROM public.order_pair_units u WHERE u.order_id=o.id AND u.status<>'allocated'))
 )
 SELECT a.oid AS order_id,a.aid AS attempt_id,a.code AS reason_code,
  a.stamp AS observed_since,a.amount AS attempt_amount,a.total AS order_amount,
  a.cur AS currency,a.ocur AS order_currency FROM attempt_signals a
 UNION ALL
 SELECT o.id,NULL::uuid,o.code,o.created_at,NULL::numeric,o.total_pkr,NULL::text,o.currency_code::text FROM order_signals o;
END $$;

CREATE FUNCTION public.sr_finance_reconciliation(
 cutoff timestamptz,filter_reason text,after_stamp timestamptz,after_order uuid,
 after_attempt uuid,after_reason text,take integer)
RETURNS TABLE(order_id uuid,attempt_id uuid,reason_code text,observed_since timestamptz,
 attempt_amount numeric,order_amount numeric,currency text,order_currency text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 IF NOT public.sr_is_staff(ARRAY['finance']) THEN
  RAISE EXCEPTION 'finance authority required' USING ERRCODE='42501';
 END IF;
 IF take IS NULL OR take<1 OR take>1001 OR (filter_reason IS NOT NULL AND filter_reason NOT IN
  ('REVIEW_PENDING','ATTEMPT_ORDER_AMOUNT_MISMATCH','ATTEMPT_ORDER_CURRENCY_MISMATCH',
   'VERIFIED_HISTORY_MISMATCH','ORDER_SETTLEMENT_MISMATCH','VERIFIED_ALLOCATION_MISMATCH','DUPLICATE_VERIFIED_REFERENCE')) THEN
  RAISE EXCEPTION 'invalid query bounds' USING ERRCODE='22023';
 END IF;
 RETURN QUERY SELECT r.* FROM public.sr_finance_reconciliation_rows(cutoff) r
 WHERE (filter_reason IS NULL OR r.reason_code=filter_reason)
 AND (after_stamp IS NULL OR
  (r.observed_since,r.order_id,coalesce(r.attempt_id,'00000000-0000-0000-0000-000000000000'::uuid),r.reason_code COLLATE "C")>
  (after_stamp,after_order,after_attempt,after_reason COLLATE "C"))
 ORDER BY r.observed_since,r.order_id,coalesce(r.attempt_id,'00000000-0000-0000-0000-000000000000'::uuid),r.reason_code COLLATE "C"
 LIMIT take;
END $$;

CREATE FUNCTION public.sr_finance_reconciliation_counts(cutoff timestamptz)
RETURNS TABLE(reason_code text,n bigint)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 IF NOT public.sr_is_staff(ARRAY['finance']) THEN
  RAISE EXCEPTION 'finance authority required' USING ERRCODE='42501';
 END IF;
 RETURN QUERY
 WITH signals AS MATERIALIZED (SELECT * FROM public.sr_finance_reconciliation_rows(cutoff)),
 reasons(code) AS (VALUES ('REVIEW_PENDING'),('ATTEMPT_ORDER_AMOUNT_MISMATCH'),
  ('ATTEMPT_ORDER_CURRENCY_MISMATCH'),('VERIFIED_HISTORY_MISMATCH'),
  ('ORDER_SETTLEMENT_MISMATCH'),('VERIFIED_ALLOCATION_MISMATCH'),('DUPLICATE_VERIFIED_REFERENCE'))
 SELECT x.code AS reason_code,(SELECT count(*) FROM (SELECT 1 FROM signals r WHERE r.reason_code=x.code LIMIT 1000) capped) AS n
 FROM reasons x
 UNION ALL
 SELECT 'AFFECTED_ORDERS',count(*) FROM (SELECT DISTINCT r.order_id FROM signals r LIMIT 1000) affected;
END $$;

REVOKE ALL ON FUNCTION public.sr_finance_reconciliation_rows(timestamptz),
 public.sr_finance_reconciliation(timestamptz,text,timestamptz,uuid,uuid,text,integer),
 public.sr_finance_reconciliation_counts(timestamptz)
 FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION
 public.sr_finance_reconciliation(timestamptz,text,timestamptz,uuid,uuid,text,integer),
 public.sr_finance_reconciliation_counts(timestamptz) TO safereturn_api;
