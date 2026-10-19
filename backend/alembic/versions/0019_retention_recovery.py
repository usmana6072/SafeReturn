"""Lease-bound retention intent, hold/delete serialization and tombstone recovery.

No cutoff, policy approval, data deletion or role expansion is installed here.
"""

from alembic import op

revision = "0019_retention_recovery"
down_revision = "0018_fulfillment_eligibility"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='5s'")
    op.execute("""CREATE FUNCTION public.sr_worker_finance(oid uuid) RETURNS boolean
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT 1 FROM public.durable_jobs WHERE order_id=oid AND job_kind='finance.sync'
  AND status='leased' AND lease_owner=public.sr_worker_id() AND lease_until>clock_timestamp())
$$;
REVOKE ALL ON FUNCTION public.sr_worker_finance(uuid) FROM PUBLIC,anon,authenticated,safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_worker_finance(uuid) TO safereturn_worker;
DROP POLICY sr_safereturn_worker_select ON public.finance_sheet_sync;
DROP POLICY sr_safereturn_worker_update ON public.finance_sheet_sync;
CREATE POLICY sr_safereturn_worker_select ON public.finance_sheet_sync FOR SELECT TO safereturn_worker USING(public.sr_worker_finance(order_id));
CREATE POLICY sr_safereturn_worker_update ON public.finance_sheet_sync FOR UPDATE TO safereturn_worker
 USING(public.sr_worker_finance(order_id)) WITH CHECK(public.sr_worker_finance(order_id));
""")
    op.execute("""CREATE FUNCTION public.sr_retention_identity() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF (to_jsonb(NEW)-ARRAY['retention_until','deletion_hold_reason','deleted_at']) IS DISTINCT FROM
    (to_jsonb(OLD)-ARRAY['retention_until','deletion_hold_reason','deleted_at'])
 OR (OLD.deleted_at IS NOT NULL AND NEW.deleted_at IS DISTINCT FROM OLD.deleted_at) THEN
  RAISE EXCEPTION 'Retained object identity and tombstones are immutable' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION public.sr_retention_identity() FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
CREATE TRIGGER sr_retention_identity BEFORE UPDATE ON public.print_artifacts FOR EACH ROW EXECUTE FUNCTION public.sr_retention_identity();
CREATE TRIGGER sr_retention_identity BEFORE UPDATE ON public.payment_evidence FOR EACH ROW EXECUTE FUNCTION public.sr_retention_identity();
""")
    op.execute("""CREATE FUNCTION public.sr_retention_schedule(kind text) RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE added integer;
BEGIN
 IF public.sr_worker_id() IS NULL THEN RAISE EXCEPTION 'Worker required' USING ERRCODE='42501'; END IF;
 IF kind NOT IN ('print_artifact','payment_evidence') THEN RAISE EXCEPTION 'Invalid resource' USING ERRCODE='23514'; END IF;
 INSERT INTO public.durable_jobs(job_kind,aggregate_type,aggregate_id,order_id,idempotency_key)
 SELECT 'retention.cleanup',kind,a.id,a.order_id,'retention.cleanup:'||kind||':'||a.id::text FROM (
  SELECT a.id,j.order_id,a.retention_until,a.deleted_at FROM public.print_artifacts a JOIN public.print_jobs j ON j.id=a.print_job_id WHERE kind='print_artifact'
  UNION ALL SELECT e.id,p.order_id,e.retention_until,e.deleted_at FROM public.payment_evidence e JOIN public.payment_attempts p ON p.id=e.attempt_id WHERE kind='payment_evidence'
 ) a JOIN public.orders o ON o.id=a.order_id
 WHERE a.deleted_at IS NULL AND a.retention_until<=clock_timestamp() AND o.fulfillment_status='delivered' AND o.payment_status='verified'
 AND EXISTS(SELECT 1 FROM public.finance_sheet_sync s WHERE s.order_id=o.id AND s.status='synced')
 AND NOT EXISTS(SELECT 1 FROM public.durable_jobs d WHERE d.job_kind='retention.cleanup' AND d.aggregate_type=kind AND d.aggregate_id=a.id)
 ORDER BY a.retention_until,a.id LIMIT 100 ON CONFLICT(idempotency_key) DO NOTHING;
 GET DIAGNOSTICS added=ROW_COUNT;
 RETURN added;
END $$;
REVOKE ALL ON FUNCTION public.sr_retention_schedule(text) FROM PUBLIC,anon,authenticated,safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_retention_schedule(text) TO safereturn_worker;
CREATE FUNCTION public.sr_retention_retry(rid uuid, reason text) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE job public.durable_jobs;
BEGIN
 IF NOT public.sr_is_staff(ARRAY['security_admin','superadmin']) THEN RAISE EXCEPTION 'Security staff and MFA required' USING ERRCODE='42501'; END IF;
 IF reason IS NULL OR reason!~'^[A-Za-z0-9_.-]{1,80}$' THEN RAISE EXCEPTION 'Reason required' USING ERRCODE='23514'; END IF;
 SELECT * INTO job FROM public.durable_jobs WHERE job_kind='retention.cleanup' AND aggregate_id=rid ORDER BY created_at DESC,id DESC LIMIT 1 FOR UPDATE;
 IF NOT FOUND THEN RETURN NULL; END IF;
 IF job.status='dead' THEN
  UPDATE public.durable_jobs SET status='retry',attempt_count=0,next_attempt_at=clock_timestamp(),last_error_code=NULL WHERE id=job.id;
  INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,safe_details)
   VALUES(public.sr_actor_id(),'staff','storage.cleanup_retry',job.aggregate_type,rid,jsonb_build_object('reason_code',reason,'version',job.attempt_count));
 END IF;
 RETURN job.id;
END $$;
REVOKE ALL ON FUNCTION public.sr_retention_retry(uuid,text) FROM PUBLIC,anon,authenticated,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_retention_retry(uuid,text) TO safereturn_api;
""")
    op.execute("""CREATE FUNCTION public.sr_retention_held(kind text,rid uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT public.sr_is_staff(ARRAY['operations','finance','security_admin','superadmin']) AND EXISTS(
  SELECT 1 FROM public.retention_holds h WHERE h.released_at IS NULL AND
   ((h.resource_type=kind AND h.resource_id=rid) OR (h.resource_type='order' AND h.resource_id IN (
     SELECT j.order_id FROM public.print_artifacts a JOIN public.print_jobs j ON j.id=a.print_job_id WHERE kind='print_artifact' AND a.id=rid
     UNION ALL
     SELECT p.order_id FROM public.payment_evidence e JOIN public.payment_attempts p ON p.id=e.attempt_id WHERE kind='payment_evidence' AND e.id=rid))))
$$;
REVOKE ALL ON FUNCTION public.sr_retention_held(text,uuid) FROM PUBLIC,anon,authenticated,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_retention_held(text,uuid) TO safereturn_api;
""")
    op.execute("""CREATE FUNCTION public.sr_finance_changed() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
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
REVOKE ALL ON FUNCTION public.sr_finance_changed() FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
CREATE TRIGGER sr_finance_changed AFTER UPDATE OF payment_status,fulfillment_status ON public.orders
 FOR EACH ROW EXECUTE FUNCTION public.sr_finance_changed();
""")
    op.execute("""CREATE FUNCTION public.sr_retention_prepare(jid uuid, attempt integer, approval text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE job public.durable_jobs; oid uuid; art record; tab text;
BEGIN
 SELECT * INTO job FROM public.durable_jobs WHERE id=jid AND job_kind='retention.cleanup'
 AND status='leased' AND lease_owner=public.sr_worker_id() AND attempt_count=attempt
 AND lease_until>clock_timestamp() FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Lease lost' USING ERRCODE='42501'; END IF;
 IF approval IS NULL OR length(trim(approval)) NOT BETWEEN 1 AND 120 THEN
  RETURN jsonb_build_object('deleted',false,'reason','policy_not_approved'); END IF;
 IF job.aggregate_type='print_artifact' THEN
  SELECT j.order_id INTO oid FROM public.print_artifacts a JOIN public.print_jobs j ON j.id=a.print_job_id WHERE a.id=job.aggregate_id;
  tab:='print_artifacts';
 ELSIF job.aggregate_type='payment_evidence' THEN
  SELECT p.order_id INTO oid FROM public.payment_evidence e JOIN public.payment_attempts p ON p.id=e.attempt_id WHERE e.id=job.aggregate_id;
  tab:='payment_evidence';
 ELSE RETURN jsonb_build_object('deleted',false,'reason','unsupported_resource'); END IF;
 IF oid IS NULL THEN RETURN jsonb_build_object('deleted',false,'reason','not_found'); END IF;
 IF job.order_id IS DISTINCT FROM oid THEN RAISE EXCEPTION 'Wrong order' USING ERRCODE='42501'; END IF;
 PERFORM 1 FROM public.orders WHERE id=oid FOR UPDATE;
 EXECUTE format('SELECT * FROM public.%I WHERE id=$1 FOR UPDATE',tab) INTO art USING job.aggregate_id;
 IF art.deleted_at IS NOT NULL THEN RETURN jsonb_build_object('deleted',false,'reason','already_deleted'); END IF;
 -- A committed intent is replayed after an ambiguous remote response or DB failure.
 IF art.deletion_hold_reason='retention.deleting' AND EXISTS(
   SELECT 1 FROM public.audit_events WHERE target_id=job.aggregate_id
    AND target_type=job.aggregate_type AND action='storage.deletion_authorized' AND actor_kind='system')
 AND NOT EXISTS(SELECT 1 FROM public.retention_holds WHERE released_at IS NULL
   AND ((resource_type='order' AND resource_id=oid)
    OR (resource_type=job.aggregate_type AND resource_id=job.aggregate_id))) THEN
  RETURN jsonb_build_object('authorized',true,'bucket',art.bucket,'object_key',art.object_key); END IF;
 IF art.deletion_hold_reason IS NOT NULL OR EXISTS(SELECT 1 FROM public.retention_holds
  WHERE released_at IS NULL AND ((resource_type='order' AND resource_id=oid)
   OR (resource_type=job.aggregate_type AND resource_id=job.aggregate_id))) THEN
  RETURN jsonb_build_object('deleted',false,'reason','on_hold'); END IF;
 IF art.retention_until IS NULL THEN RETURN jsonb_build_object('deleted',false,'reason','no_retention_policy'); END IF;
 IF art.retention_until>clock_timestamp() THEN RETURN jsonb_build_object('deleted',false,'reason','retention_period_not_elapsed'); END IF;
 IF NOT EXISTS(SELECT 1 FROM public.orders WHERE id=oid AND fulfillment_status='delivered' AND payment_status='verified')
 OR NOT EXISTS(SELECT 1 FROM public.shipments WHERE order_id=oid AND status='delivered' AND delivered_at IS NOT NULL)
 OR EXISTS(SELECT 1 FROM public.shipments WHERE order_id=oid AND status IN ('preparing','packed','dispatched','exception','returned')) THEN
  RETURN jsonb_build_object('deleted',false,'reason','order_fulfillment_incomplete'); END IF;
 IF EXISTS(SELECT 1 FROM public.support_cases WHERE (order_id=oid OR pair_id IN
  (SELECT pair_id FROM public.order_pair_units WHERE order_id=oid)) AND status IN ('open','investigating'))
 OR EXISTS(SELECT 1 FROM public.payment_attempts WHERE order_id=oid AND state NOT IN ('verified','rejected','expired'))
 OR NOT EXISTS(SELECT 1 FROM public.finance_sheet_sync WHERE order_id=oid AND status='synced') THEN
  RETURN jsonb_build_object('deleted',false,'reason','reconciliation_pending'); END IF;
 IF EXISTS(SELECT 1 FROM public.durable_jobs WHERE order_id=oid AND id<>jid
  AND job_kind<>'retention.cleanup' AND status IN ('pending','retry','leased'))
 OR EXISTS(SELECT 1 FROM public.print_jobs WHERE order_id=oid AND status IN ('queued','rendering')) THEN
  RETURN jsonb_build_object('deleted',false,'reason','active_jobs'); END IF;
 IF job.aggregate_type='print_artifact' AND EXISTS(SELECT 1 FROM public.print_download_grants WHERE artifact_id=job.aggregate_id AND expires_at>clock_timestamp()) THEN
  RETURN jsonb_build_object('deleted',false,'reason','active_download_grants'); END IF;
 EXECUTE format('UPDATE public.%I SET deletion_hold_reason=''retention.deleting'' WHERE id=$1',tab) USING job.aggregate_id;
 INSERT INTO public.audit_events(actor_kind,action,target_type,target_id,safe_details)
 VALUES('system','storage.deletion_authorized',job.aggregate_type,job.aggregate_id,jsonb_build_object('reason_code',approval));
 RETURN jsonb_build_object('authorized',true,'bucket',art.bucket,'object_key',art.object_key);
END $$;
REVOKE ALL ON FUNCTION public.sr_retention_prepare(uuid,integer,text) FROM PUBLIC,anon,authenticated,safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_retention_prepare(uuid,integer,text) TO safereturn_worker;
""")
    op.execute("""CREATE FUNCTION public.sr_retention_finish(jid uuid, attempt integer)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE job public.durable_jobs; pj uuid; changed uuid;
BEGIN
 SELECT * INTO job FROM public.durable_jobs WHERE id=jid AND job_kind='retention.cleanup'
 AND status='leased' AND lease_owner=public.sr_worker_id() AND attempt_count=attempt
 AND lease_until>clock_timestamp() FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Lease lost' USING ERRCODE='42501'; END IF;
 IF job.aggregate_type='print_artifact' THEN
  UPDATE public.print_artifacts SET deleted_at=clock_timestamp(),deletion_hold_reason=NULL
   WHERE id=job.aggregate_id AND deletion_hold_reason='retention.deleting' AND deleted_at IS NULL
   RETURNING id,print_job_id INTO changed,pj;
  IF changed IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.print_artifacts WHERE print_job_id=pj AND deleted_at IS NULL) THEN
   UPDATE public.print_jobs SET status='deleted' WHERE id=pj; END IF;
 ELSIF job.aggregate_type='payment_evidence' THEN
  UPDATE public.payment_evidence SET deleted_at=clock_timestamp(),deletion_hold_reason=NULL
   WHERE id=job.aggregate_id AND deletion_hold_reason='retention.deleting' AND deleted_at IS NULL RETURNING id INTO changed;
 ELSE RAISE EXCEPTION 'Invalid resource' USING ERRCODE='23514'; END IF;
 IF changed IS NOT NULL THEN
  INSERT INTO public.audit_events(actor_kind,action,target_type,target_id,safe_details)
  VALUES('system','storage.artifact_deleted',job.aggregate_type,job.aggregate_id,'{"outcome":"deleted"}'::jsonb); END IF;
END $$;
REVOKE ALL ON FUNCTION public.sr_retention_finish(uuid,integer) FROM PUBLIC,anon,authenticated,safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_retention_finish(uuid,integer) TO safereturn_worker;
""")
    op.execute("""CREATE FUNCTION public.sr_retention_admission() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE oid uuid; related uuid[];
BEGIN
 IF TG_TABLE_NAME='retention_holds' THEN
  IF NEW.released_at IS NOT NULL THEN RETURN NEW; END IF;
  IF NEW.resource_type='order' THEN oid:=NEW.resource_id;
  ELSIF NEW.resource_type='print_artifact' THEN
   SELECT j.order_id INTO oid FROM public.print_artifacts a JOIN public.print_jobs j ON j.id=a.print_job_id WHERE a.id=NEW.resource_id;
  ELSIF NEW.resource_type='payment_evidence' THEN
   SELECT p.order_id INTO oid FROM public.payment_evidence e JOIN public.payment_attempts p ON p.id=e.attempt_id WHERE e.id=NEW.resource_id;
  ELSE RETURN NEW; END IF;
 ELSIF TG_TABLE_NAME='print_download_grants' THEN
  SELECT j.order_id INTO oid FROM public.print_artifacts a JOIN public.print_jobs j ON j.id=a.print_job_id WHERE a.id=NEW.artifact_id;
 ELSIF TG_TABLE_NAME='support_cases' THEN
  SELECT array_agg(DISTINCT candidate ORDER BY candidate) INTO related FROM (
   SELECT NEW.order_id AS candidate WHERE NEW.order_id IS NOT NULL
   UNION SELECT order_id FROM public.order_pair_units WHERE pair_id=NEW.pair_id) orders;
 ELSE oid:=NEW.order_id; END IF;
 IF related IS NULL THEN related:=ARRAY[oid]; END IF;
 FOREACH oid IN ARRAY related LOOP
 PERFORM 1 FROM public.orders WHERE id=oid FOR UPDATE;
 IF EXISTS(SELECT 1 FROM public.print_artifacts a JOIN public.print_jobs j ON j.id=a.print_job_id
   WHERE j.order_id=oid AND a.deletion_hold_reason='retention.deleting')
 OR EXISTS(SELECT 1 FROM public.payment_evidence e JOIN public.payment_attempts p ON p.id=e.attempt_id
   WHERE p.order_id=oid AND e.deletion_hold_reason='retention.deleting') THEN
  RAISE EXCEPTION 'Deletion already authorized; reconciliation required' USING ERRCODE='23514'; END IF;
 END LOOP;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION public.sr_retention_admission() FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
CREATE TRIGGER sr_aa_retention_admission BEFORE INSERT ON public.retention_holds
 FOR EACH ROW EXECUTE FUNCTION public.sr_retention_admission();
CREATE TRIGGER sr_retention_job_admission BEFORE INSERT ON public.durable_jobs
 FOR EACH ROW WHEN (NEW.job_kind<>'retention.cleanup') EXECUTE FUNCTION public.sr_retention_admission();
CREATE TRIGGER sr_retention_dispute_admission BEFORE INSERT OR UPDATE OF status,order_id,pair_id ON public.support_cases
 FOR EACH ROW WHEN (NEW.status IN ('open','investigating')) EXECUTE FUNCTION public.sr_retention_admission();
CREATE TRIGGER sr_retention_download_admission BEFORE INSERT ON public.print_download_grants
 FOR EACH ROW EXECUTE FUNCTION public.sr_retention_admission();
""")


def downgrade():
    raise RuntimeError(
        "Forward recovery only; preserve deletion intents and audit history"
    )
