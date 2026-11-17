CREATE OR REPLACE FUNCTION public.sr_standalone_entitled(iid uuid) RETURNS boolean
LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS (
  SELECT 1 FROM public.order_item_qr_allocations a JOIN public.orders o ON o.id=a.order_id
  JOIN public.typed_order_settlements t ON t.order_id=o.id JOIN public.payment_attempts p ON p.id=t.attempt_id
  JOIN public.standalone_qr_states s ON s.qr_id=a.qr_id JOIN public.qr_codes q ON q.id=a.qr_id
  WHERE a.logical_item_id=iid AND a.purchaser_user_id=public.sr_actor_id() AND o.customer_user_id=public.sr_actor_id()
  AND o.commerce_model='single_qr' AND o.order_status='placed' AND o.payment_status='verified'
  AND o.fulfillment_status IN ('allocated','packed','dispatched','delivered')
  AND t.state='allocated' AND p.state='verified' AND p.amount=o.total_pkr AND p.currency_code=o.currency_code
  AND public.sr_financial_order_clear(o.id)
  AND NOT EXISTS(SELECT 1 FROM public.template_order_holds WHERE order_id=o.id)
  AND NOT EXISTS(SELECT 1 FROM public.order_item_sizes z JOIN public.order_logical_items i ON i.id=z.logical_item_id WHERE i.order_id=o.id AND NOT public.sr_template_revision_clear(z.revision_id,true))
  AND NOT EXISTS(SELECT 1 FROM public.order_cancellation_requests WHERE order_id=o.id AND status IN ('requested','investigating','approved','escalated'))
  AND (
   EXISTS (
    SELECT 1 FROM (
     SELECT j.id,j.status FROM public.print_jobs j WHERE j.order_id=o.id ORDER BY j.job_revision DESC LIMIT 1
    ) latest JOIN public.print_artifacts f ON f.print_job_id=latest.id
    WHERE latest.status IN ('ready','downloaded','qa_passed') AND f.format='pdf' AND f.deleted_at IS NULL
    AND (f.retention_until IS NULL OR f.retention_until>clock_timestamp())
   )
   -- Delivered purchases retain entitlement after the PDF retention period.
   OR (o.fulfillment_status='delivered' AND EXISTS (
    SELECT 1 FROM public.shipment_items m JOIN public.shipments h ON h.id=m.shipment_id
    WHERE m.logical_item_id=a.logical_item_id AND h.order_id=o.id AND h.status='delivered'
    AND h.delivered_at IS NOT NULL AND m.packed_qa_confirmed
   ))
  )
  AND s.inventory_status='allocated' AND s.ownership_status='unclaimed' AND s.owner_user_id IS NULL
  AND q.pair_id IS NULL AND q.is_current AND q.public_status='unactivated' AND q.revoked_at IS NULL
 )
$$;

DO $$
DECLARE definition text; updated text;
BEGIN
 SELECT pg_get_functiondef('public.sr_standalone_confirm(uuid,uuid,text,text)'::regprocedure) INTO definition;
 updated := replace(definition,
  '''delivered purchaser entitlement'',jsonb_build_object(''revision'',s.row_version)',
  '''verified purchaser entitlement'',jsonb_build_object(''version'',s.row_version)');
 IF updated = definition THEN RAISE EXCEPTION 'Unexpected standalone activation audit definition'; END IF;
 EXECUTE updated;

 SELECT pg_get_functiondef('public.sr_standalone_availability(uuid,uuid,integer,text,text,text)'::regprocedure) INTO definition;
 updated := replace(definition,
  'jsonb_build_object(''from_status'',q.public_status,''to_status'',wanted,''revision'',s.row_version)',
  'jsonb_build_object(''from_status'',q.public_status,''to_status'',wanted,''version'',s.row_version)');
 IF updated = definition THEN RAISE EXCEPTION 'Unexpected standalone availability audit definition'; END IF;
 EXECUTE updated;
END $$;
