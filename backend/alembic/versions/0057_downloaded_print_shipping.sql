CREATE OR REPLACE FUNCTION public.sr_typed_fulfillment_eligible(oid uuid) RETURNS boolean
LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT public.sr_is_staff(ARRAY['operations']) AND public.sr_typed_print_clear(oid)
 AND EXISTS (
  SELECT 1 FROM public.print_jobs j JOIN public.print_artifacts a ON a.print_job_id=j.id
  WHERE j.order_id=oid
  AND j.job_revision=(SELECT max(job_revision) FROM public.print_jobs WHERE order_id=oid)
  AND j.status IN ('downloaded','qa_passed')
  AND a.format='pdf' AND a.deleted_at IS NULL
  AND a.deletion_hold_reason IS DISTINCT FROM 'retention.deleting'
  AND (a.retention_until IS NULL OR a.retention_until>clock_timestamp())
 )
$$;
