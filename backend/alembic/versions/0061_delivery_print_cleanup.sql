CREATE OR REPLACE FUNCTION public.sr_find_delivered_orders_with_artifacts()
RETURNS TABLE (order_id uuid)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT DISTINCT o.id
 FROM public.orders o
 JOIN public.shipments s ON s.order_id=o.id
 JOIN public.print_jobs j ON j.order_id=o.id
 JOIN public.print_artifacts a ON a.print_job_id=j.id
 WHERE o.fulfillment_status='delivered'
   AND s.status='delivered'
   AND a.deleted_at IS NULL;
$$;

CREATE OR REPLACE FUNCTION public.sr_delivery_print_cleanup(oid uuid)
RETURNS TABLE (artifact_id uuid, object_key text, print_job_id uuid)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE o public.orders;
BEGIN
 SELECT * INTO o FROM public.orders WHERE id=oid FOR UPDATE;
 IF o.id IS NULL OR o.fulfillment_status<>'delivered' THEN RETURN; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.shipments WHERE order_id=oid AND status='delivered') THEN RETURN; END IF;

 UPDATE public.print_artifacts a
 SET retention_until=clock_timestamp()-interval '1 minute'
 WHERE a.print_job_id IN (SELECT j.id FROM public.print_jobs j WHERE j.order_id=oid)
   AND a.deleted_at IS NULL
   AND (a.retention_until IS NULL OR a.retention_until>clock_timestamp());

 RETURN QUERY
 SELECT a.id, a.object_key, a.print_job_id
 FROM public.print_artifacts a
 JOIN public.print_jobs j ON j.id=a.print_job_id
 WHERE j.order_id=oid AND a.deleted_at IS NULL;
END $$;

CREATE OR REPLACE FUNCTION public.sr_delivery_print_finish(aid uuid)
RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE jid uuid;
BEGIN
 SELECT print_job_id INTO jid FROM public.print_artifacts WHERE id=aid;
 IF jid IS NULL THEN RETURN; END IF;

 UPDATE public.print_artifacts
 SET deleted_at=clock_timestamp(), deletion_hold_reason=NULL
 WHERE id=aid AND deleted_at IS NULL;

 IF NOT EXISTS(SELECT 1 FROM public.print_artifacts WHERE print_job_id=jid AND deleted_at IS NULL) THEN
  UPDATE public.print_jobs SET status='deleted' WHERE id=jid;
 END IF;

 INSERT INTO public.audit_events(actor_kind,action,target_type,target_id,safe_details)
 VALUES('system','storage.artifact_deleted','print_artifact',aid,'{"outcome":"delivered_auto_deleted"}'::jsonb);
END $$;

GRANT EXECUTE ON FUNCTION public.sr_find_delivered_orders_with_artifacts() TO safereturn_api, safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_delivery_print_cleanup(uuid) TO safereturn_api, safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_delivery_print_finish(uuid) TO safereturn_api, safereturn_worker;
