-- Approved Task 5.7B. Read-only, scalar/count-only helpers; no table grants.
CREATE FUNCTION public.sr_dashboard_summary(grp text) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE values_out jsonb;
BEGIN
 IF grp='catalog' THEN
  IF NOT public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) THEN RETURN NULL; END IF;
  SELECT jsonb_build_object(
   'catalog.products',(SELECT count(*) FROM (SELECT 1 FROM public.products LIMIT 1000) c),
   'catalog.variants',(SELECT count(*) FROM (SELECT 1 FROM public.product_variants LIMIT 1000) c)) INTO values_out;
 ELSIF grp='fulfillment' THEN
  IF NOT public.sr_is_staff(ARRAY['operations']) THEN RETURN NULL; END IF;
  SELECT jsonb_build_object('fulfillment.ready_orders',(SELECT count(*) FROM (
   SELECT 1 FROM public.orders o JOIN public.order_shipping_snapshots a ON a.order_id=o.id
   WHERE public.sr_fulfillment_eligible(o.id) AND o.fulfillment_status IN('allocated','packed')
   AND NOT EXISTS(SELECT 1 FROM public.shipments s WHERE s.order_id=o.id AND s.status IN('dispatched','delivered','exception','returned')) LIMIT 1000) c),
   'fulfillment.requires_review',(SELECT count(*) FROM (
    SELECT 1 FROM public.shipments s JOIN public.orders o ON o.id=s.order_id
    WHERE s.status IN('preparing','packed','dispatched') AND NOT public.sr_fulfillment_eligible(o.id) LIMIT 1000) c)) INTO values_out;
  SELECT values_out || coalesce(jsonb_object_agg('shipments.'||state,
   (SELECT count(*) FROM (SELECT 1 FROM public.shipments s WHERE s.status=state LIMIT 1000) c)),'{}'::jsonb)
   INTO values_out FROM unnest(ARRAY['preparing','packed','dispatched','delivered','exception','returned']) state;
 ELSIF grp='notifications' THEN
  IF NOT public.sr_is_staff(ARRAY['operations','security_admin']) THEN RETURN NULL; END IF;
  SELECT jsonb_object_agg('notifications.'||state,
   (SELECT count(*) FROM (SELECT 1 FROM public.notification_outbox n WHERE n.status=state LIMIT 1000) c))
   INTO values_out FROM unnest(ARRAY['pending','leased','retry','sent','dead']) state;
 ELSIF grp='support' THEN
  IF NOT public.sr_is_staff(ARRAY['support']) THEN RETURN NULL; END IF;
  SELECT jsonb_object_agg('support.'||state,
   (SELECT count(*) FROM (SELECT 1 FROM public.support_cases s WHERE s.status=state
    AND (s.assigned_staff_id IS NULL OR s.assigned_staff_id=public.sr_actor_id()) LIMIT 1000) c))
   INTO values_out FROM unnest(ARRAY['open','investigating']) state;
 ELSIF grp='finance_mirror' THEN
  IF NOT public.sr_is_staff(ARRAY['finance','security_admin','superadmin']) THEN RETURN NULL; END IF;
  SELECT jsonb_build_object('finance_mirror.records',(SELECT count(*) FROM (SELECT 1 FROM public.finance_sheet_sync LIMIT 1000) c)) INTO values_out;
 ELSE
  RAISE EXCEPTION 'Unsupported dashboard group' USING ERRCODE='22023';
 END IF;
 RETURN values_out;
END $$;
CREATE FUNCTION public.sr_dashboard_trend(series text,range_end timestamptz) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE values_out jsonb;
BEGIN
 IF range_end IS NULL OR range_end IS DISTINCT FROM (date_trunc('day',range_end AT TIME ZONE 'UTC') AT TIME ZONE 'UTC') OR range_end>(date_trunc('day',clock_timestamp() AT TIME ZONE 'UTC') AT TIME ZONE 'UTC') OR range_end<clock_timestamp()-interval '2 days' THEN
  RAISE EXCEPTION 'Invalid dashboard bounds' USING ERRCODE='22023'; END IF;
 IF series='shipments_dispatched' THEN
  IF NOT public.sr_is_staff(ARRAY['operations']) THEN RETURN NULL; END IF;
  SELECT jsonb_agg(jsonb_build_object('start',day,'end',day+interval '24 hours','n',
   (SELECT count(*) FROM (SELECT 1 FROM public.shipments s WHERE s.dispatched_at>=day AND s.dispatched_at<day+interval '24 hours' LIMIT 1000) c)) ORDER BY day)
  INTO values_out FROM generate_series(range_end-interval '720 hours',range_end-interval '24 hours',interval '24 hours') day;
 ELSIF series='notifications_created' THEN
  IF NOT public.sr_is_staff(ARRAY['operations','security_admin']) THEN RETURN NULL; END IF;
  SELECT jsonb_agg(jsonb_build_object('start',day,'end',day+interval '24 hours','n',
   (SELECT count(*) FROM (SELECT 1 FROM public.notification_outbox n WHERE n.created_at>=day AND n.created_at<day+interval '24 hours' LIMIT 1000) c)) ORDER BY day)
  INTO values_out FROM generate_series(range_end-interval '720 hours',range_end-interval '24 hours',interval '24 hours') day;
 ELSE
  RAISE EXCEPTION 'Unsupported dashboard series' USING ERRCODE='22023';
 END IF;
 RETURN values_out;
END $$;
REVOKE ALL ON FUNCTION public.sr_dashboard_summary(text),public.sr_dashboard_trend(text,timestamptz) FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_dashboard_summary(text),public.sr_dashboard_trend(text,timestamptz) TO safereturn_api;
