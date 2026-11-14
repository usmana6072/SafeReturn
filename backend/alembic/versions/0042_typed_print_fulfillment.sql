-- Additive source only. Customer checkout release and activation remain closed.
CREATE TABLE public.typed_print_handoffs (
 event_id uuid PRIMARY KEY REFERENCES public.typed_allocation_events(id) ON DELETE RESTRICT,
 durable_job_id uuid NOT NULL UNIQUE REFERENCES public.durable_jobs(id) ON DELETE RESTRICT,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
ALTER TABLE public.typed_print_handoffs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.typed_print_handoffs FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
CREATE TRIGGER sr_typed_print_handoffs_append BEFORE UPDATE OR DELETE ON public.typed_print_handoffs
 FOR EACH ROW EXECUTE FUNCTION public.sr_append_only();

CREATE TABLE public.shipment_items (
 shipment_id uuid NOT NULL REFERENCES public.shipments(id) ON DELETE RESTRICT,
 logical_item_id uuid NOT NULL UNIQUE REFERENCES public.order_item_qr_allocations(logical_item_id) ON DELETE RESTRICT,
 print_job_id uuid NOT NULL REFERENCES public.print_jobs(id) ON DELETE RESTRICT,
 packed_qa_confirmed boolean NOT NULL DEFAULT false,
 packed_by uuid REFERENCES auth.users(id) ON DELETE RESTRICT,
 packed_at timestamptz,
 PRIMARY KEY(shipment_id,logical_item_id),
 CHECK(NOT packed_qa_confirmed OR (packed_by IS NOT NULL AND packed_at IS NOT NULL))
);
ALTER TABLE public.shipment_items ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.shipment_items FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT SELECT,INSERT ON public.shipment_items TO safereturn_api;
GRANT UPDATE(packed_qa_confirmed,packed_by,packed_at) ON public.shipment_items TO safereturn_api;
CREATE POLICY sr_shipment_items_staff ON public.shipment_items FOR ALL TO safereturn_api
 USING(public.sr_is_staff(ARRAY['operations'])) WITH CHECK(public.sr_is_staff(ARRAY['operations']));

-- Internal predicate, never a public entitlement or a token projection.
CREATE FUNCTION public.sr_typed_print_clear(oid uuid) RETURNS boolean
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 PERFORM public.sr_template_registry_gate(false);
 RETURN EXISTS(SELECT 1 FROM public.orders o JOIN public.typed_order_settlements t ON t.order_id=o.id
 JOIN public.payment_attempts a ON a.id=t.attempt_id
 WHERE o.id=oid AND o.commerce_model='single_qr' AND o.order_status='placed' AND o.payment_status='verified'
 AND t.state='allocated' AND a.state='verified' AND a.amount=o.total_pkr AND a.currency_code=o.currency_code
 AND public.sr_financial_order_clear(oid)
 AND NOT EXISTS(SELECT 1 FROM public.order_cancellation_requests c WHERE c.order_id=oid AND c.status IN ('requested','investigating','approved','escalated'))
 AND NOT EXISTS(SELECT 1 FROM public.template_order_holds WHERE order_id=oid)
 AND EXISTS(SELECT 1 FROM public.order_logical_items WHERE order_id=oid)
 AND NOT EXISTS(SELECT 1 FROM public.order_logical_items i
 LEFT JOIN public.order_item_qr_allocations x ON x.logical_item_id=i.id AND x.order_id=i.order_id
 LEFT JOIN public.qr_codes q ON q.id=x.qr_id LEFT JOIN public.standalone_qr_states s ON s.qr_id=q.id
 WHERE i.order_id=oid AND (x.qr_id IS NULL OR q.pair_id IS NOT NULL OR q.tag_type<>i.qr_type_snapshot
 OR NOT q.is_current OR q.revoked_at IS NOT NULL OR q.public_status<>'unactivated'
 OR s.inventory_status IS DISTINCT FROM 'allocated' OR s.ownership_status IS DISTINCT FROM 'unclaimed' OR s.owner_user_id IS NOT NULL))
 AND NOT EXISTS(SELECT 1 FROM public.order_item_sizes z JOIN public.order_logical_items i ON i.id=z.logical_item_id
 WHERE i.order_id=oid AND NOT public.sr_template_revision_clear(z.revision_id,true)));
END $$;

-- Extend installed bodies in place: keep OIDs, grants and the entire legacy branch.
-- Any unexpected installed definition aborts the migration instead of weakening it.
DO $patch$ DECLARE definition text; updated text; BEGIN
 SELECT pg_get_functiondef('public.sr_template_order_specs(uuid)'::regprocedure) INTO definition;
 updated:=regexp_replace(definition,E'BEGIN\\s*',$body$BEGIN
 IF EXISTS(SELECT 1 FROM public.orders WHERE id=oid AND commerce_model='single_qr') THEN
  IF NOT(public.sr_is_staff(ARRAY['operations']) OR EXISTS(SELECT 1 FROM public.orders WHERE id=oid AND customer_user_id=public.sr_actor_id())
   OR (current_setting('role',true)='safereturn_worker' AND COALESCE(public.sr_worker_id(),'')<>'')) THEN RETURN jsonb_build_object('error','FORBIDDEN'); END IF;
  IF EXISTS(SELECT 1 FROM public.template_order_holds WHERE order_id=oid)
   OR EXISTS(SELECT 1 FROM public.order_item_sizes z JOIN public.order_logical_items i ON i.id=z.logical_item_id WHERE i.order_id=oid AND NOT public.sr_template_revision_clear(z.revision_id,true))
   THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  SELECT jsonb_agg(z.print_spec_snapshot||jsonb_build_object('use_id',z.id) ORDER BY z.id) INTO value
   FROM public.order_item_sizes z JOIN public.order_logical_items i ON i.id=z.logical_item_id WHERE i.order_id=oid;
  RETURN coalesce(value,jsonb_build_object('error','CONFLICT'));
 END IF;
 $body$);
 IF updated=definition THEN RAISE EXCEPTION 'Review installed template specs'; END IF; EXECUTE updated;

 SELECT pg_get_functiondef('public.sr_print_occurrences(uuid)'::regprocedure) INTO definition;
 updated:=regexp_replace(definition,E'BEGIN\\s*',$body$BEGIN
 IF EXISTS(SELECT 1 FROM public.orders WHERE id=oid AND commerce_model='single_qr') THEN
  IF NOT(public.sr_is_staff(ARRAY['operations']) OR EXISTS(SELECT 1 FROM public.durable_jobs d WHERE d.order_id=oid AND d.job_kind IN ('print.render','allocation.finalize') AND d.status='leased' AND d.lease_owner=public.sr_worker_id() AND d.lease_until>clock_timestamp())) THEN RETURN; END IF;
  PERFORM public.sr_template_registry_gate(false);
  PERFORM 1 FROM public.orders WHERE id=oid FOR UPDATE;
  IF NOT public.sr_typed_print_clear(oid) THEN RAISE EXCEPTION 'Typed print binding unavailable' USING ERRCODE='23514'; END IF;
  RETURN QUERY SELECT z.id,q.id,i.qr_type_snapshot::text,z.copies,z.size_mm_snapshot,
   z.print_spec_snapshot->>'key',(z.print_spec_snapshot->>'version')::integer,q.public_token::text
   FROM public.order_item_sizes z JOIN public.order_logical_items i ON i.id=z.logical_item_id
   JOIN public.order_item_qr_allocations x ON x.logical_item_id=i.id JOIN public.qr_codes q ON q.id=x.qr_id
   WHERE i.order_id=oid ORDER BY z.id FOR SHARE OF q;
  RETURN;
 END IF;
 $body$);
 IF updated=definition THEN RAISE EXCEPTION 'Review installed print occurrences'; END IF; EXECUTE updated;

 SELECT pg_get_functiondef('public.sr_print_guard()'::regprocedure) INTO definition;
 updated:=regexp_replace(definition,E'BEGIN\\s*',$body$BEGIN
 IF EXISTS(SELECT 1 FROM public.orders WHERE id=NEW.order_id AND commerce_model='single_qr') THEN
  PERFORM public.sr_template_registry_gate(false);
  PERFORM 1 FROM public.orders WHERE id=NEW.order_id FOR UPDATE;
  IF TG_OP='INSERT' AND EXISTS(SELECT 1 FROM public.shipments WHERE order_id=NEW.order_id)
   THEN RAISE EXCEPTION 'Typed reprint after shipment requires packing reconciliation' USING ERRCODE='23514'; END IF;
  IF TG_OP='INSERT' AND EXISTS(SELECT 1 FROM public.shipments WHERE order_id=NEW.order_id)
   THEN RAISE EXCEPTION 'Typed reprint after shipment requires packing reconciliation' USING ERRCODE='23514'; END IF;
  IF NEW.status IN ('queued','rendering','ready','downloaded','qa_passed') AND NOT public.sr_typed_print_clear(NEW.order_id)
   THEN RAISE EXCEPTION 'Typed print requires complete clear allocation' USING ERRCODE='23514'; END IF;
  IF NEW.status IN ('rendering','ready','downloaded','qa_passed') AND EXISTS(SELECT 1 FROM public.print_jobs j WHERE j.order_id=NEW.order_id AND j.job_revision>NEW.job_revision)
   THEN RAISE EXCEPTION 'Stale print revision cannot publish' USING ERRCODE='23514'; END IF;
  IF TG_OP='UPDATE' AND (NEW.id,NEW.order_id,NEW.job_revision,NEW.template_fingerprint,NEW.render_config,NEW.created_at)
   IS DISTINCT FROM (OLD.id,OLD.order_id,OLD.job_revision,OLD.template_fingerprint,OLD.render_config,OLD.created_at)
   THEN RAISE EXCEPTION 'Print job specification is immutable' USING ERRCODE='23514'; END IF;
  RETURN NEW;
 END IF;
 $body$);
 IF updated=definition THEN RAISE EXCEPTION 'Review installed print guard'; END IF; EXECUTE updated;

END $patch$;

-- Add typed purchase snapshots to the existing withdrawal hold recorder.
DO $$ DECLARE definition text; updated text; BEGIN
 SELECT pg_get_functiondef('public.sr_template_record_holds()'::regprocedure) INTO definition;
 updated:=replace(definition,' RETURN NEW;',$body$
 IF source IS NOT NULL THEN
  INSERT INTO public.template_order_holds(order_id,source_kind,source_reference)
   SELECT o.id,TG_TABLE_NAME,source FROM public.orders o WHERE o.commerce_model='single_qr'
   AND NOT EXISTS(SELECT 1 FROM public.shipments sh WHERE sh.order_id=o.id AND sh.dispatched_at IS NOT NULL)
   AND EXISTS(SELECT 1 FROM public.order_item_sizes z JOIN public.order_logical_items i ON i.id=z.logical_item_id
    WHERE i.order_id=o.id AND NOT public.sr_template_revision_clear(z.revision_id,true))
   ON CONFLICT DO NOTHING;
 END IF;
 RETURN NEW;
 $body$);
 IF updated=definition THEN RAISE EXCEPTION 'Review installed template hold recorder'; END IF; EXECUTE updated;
END $$;

CREATE OR REPLACE FUNCTION public.sr_typed_production_gate() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM public.orders WHERE id=NEW.order_id AND commerce_model='single_qr')
 AND (TG_TABLE_NAME<>'durable_jobs' OR to_jsonb(NEW)->>'job_kind' IN ('allocation.finalize','print.render')) THEN
  PERFORM public.sr_template_registry_gate(false);
  PERFORM 1 FROM public.orders WHERE id=NEW.order_id FOR UPDATE;
  IF NOT public.sr_typed_print_clear(NEW.order_id) THEN RAISE EXCEPTION 'Typed production held' USING ERRCODE='23514'; END IF;
  IF TG_TABLE_NAME='shipments' AND EXISTS(SELECT 1 FROM public.shipments WHERE order_id=NEW.order_id)
   THEN RAISE EXCEPTION 'Typed order already has a shipment' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION public.sr_typed_fulfillment_eligible(oid uuid) RETURNS boolean
LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT public.sr_is_staff(ARRAY['operations']) AND public.sr_typed_print_clear(oid)
 AND EXISTS(SELECT 1 FROM public.print_jobs j JOIN public.print_artifacts a ON a.print_job_id=j.id
 WHERE j.order_id=oid AND j.job_revision=(SELECT max(job_revision) FROM public.print_jobs WHERE order_id=oid)
 AND j.status='qa_passed' AND a.format='pdf' AND a.deleted_at IS NULL
 AND (a.retention_until IS NULL OR a.retention_until>clock_timestamp())
 AND coalesce((SELECT q.approved AND q.artifact_sha256=a.sha256_hex FROM public.print_job_qa q
 WHERE q.print_job_id=j.id ORDER BY q.created_at DESC,q.id DESC LIMIT 1),false))
$$;

DO $$ DECLARE definition text; updated text; BEGIN
 SELECT pg_get_functiondef('public.sr_fulfillment_eligible(uuid)'::regprocedure) INTO definition;
 updated:=replace(definition,'SELECT public.sr_fulfillment_eligible_v33(oid)',
  'SELECT CASE WHEN EXISTS(SELECT 1 FROM public.orders WHERE id=oid AND commerce_model=''single_qr'') THEN public.sr_typed_fulfillment_eligible(oid) ELSE public.sr_fulfillment_eligible_v33(oid)');
 -- Close CASE before the SQL function body terminator, not inside nested subqueries.
 IF updated=definition THEN RAISE EXCEPTION 'Review installed fulfillment eligibility'; END IF;
 updated:=regexp_replace(updated,E'\\$function\\$(;?[[:space:]]*)$',E' END\n$function$\\1');
 EXECUTE updated;
END $$;

CREATE FUNCTION public.sr_typed_print_handoff() RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE e public.typed_allocation_events; jid uuid;
BEGIN
 IF current_setting('role',true) IS DISTINCT FROM 'safereturn_worker' OR coalesce(public.sr_worker_id(),'')=''
 THEN RAISE EXCEPTION 'Worker required' USING ERRCODE='42501'; END IF;
 -- One bounded event per iteration; transactionally enqueue and acknowledge.
 SELECT v.* INTO e FROM public.typed_allocation_events v WHERE v.event_kind='allocation.ready'
 AND NOT EXISTS(SELECT 1 FROM public.typed_print_handoffs h WHERE h.event_id=v.id)
 AND public.sr_typed_print_clear(v.order_id) ORDER BY v.created_at,v.id FOR UPDATE OF v SKIP LOCKED LIMIT 1;
 IF e.id IS NULL THEN RETURN 0; END IF;
 PERFORM 1 FROM public.orders WHERE id=e.order_id FOR UPDATE;
 IF NOT public.sr_typed_print_clear(e.order_id) THEN RETURN 0; END IF;
 INSERT INTO public.durable_jobs(job_kind,aggregate_type,aggregate_id,order_id,idempotency_key)
 VALUES('allocation.finalize','order',e.order_id,e.order_id,'print.request:typed:'||e.id) RETURNING id INTO jid;
 INSERT INTO public.typed_print_handoffs(event_id,durable_job_id) VALUES(e.id,jid);
 INSERT INTO public.audit_events(actor_kind,action,target_type,target_id,reason,safe_details)
 VALUES('system','print.typed.handoff','order',e.order_id,'durable typed allocation handoff',jsonb_build_object('event_id',e.id));
 RETURN 1;
END $$;

CREATE FUNCTION public.sr_print_worker_order_lock(oid uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF current_setting('role',true) IS DISTINCT FROM 'safereturn_worker'
 OR NOT EXISTS(SELECT 1 FROM public.durable_jobs d WHERE d.order_id=oid AND d.job_kind IN ('allocation.finalize','print.render')
  AND d.status='leased' AND d.lease_owner=public.sr_worker_id() AND d.lease_until>clock_timestamp())
 THEN RAISE EXCEPTION 'Active print lease required' USING ERRCODE='42501'; END IF;
 PERFORM public.sr_template_registry_gate(false);
 PERFORM 1 FROM public.orders WHERE id=oid FOR UPDATE;
END $$;

CREATE FUNCTION public.sr_typed_shipment_item_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE oid uuid; latest uuid;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Shipment membership is permanent' USING ERRCODE='23514'; END IF;
 PERFORM public.sr_template_registry_gate(false);
 SELECT order_id INTO oid FROM public.shipments WHERE id=NEW.shipment_id;
 PERFORM 1 FROM public.orders WHERE id=oid FOR UPDATE;
 IF TG_OP='UPDATE' AND ((NEW.shipment_id,NEW.logical_item_id,NEW.print_job_id) IS DISTINCT FROM (OLD.shipment_id,OLD.logical_item_id,OLD.print_job_id)
 OR OLD.packed_qa_confirmed OR NOT NEW.packed_qa_confirmed) THEN RAISE EXCEPTION 'Shipment membership/packing is immutable' USING ERRCODE='23514'; END IF;
 SELECT id INTO latest FROM public.print_jobs WHERE order_id=oid ORDER BY job_revision DESC LIMIT 1;
 IF NOT public.sr_typed_fulfillment_eligible(oid) OR NEW.print_job_id IS DISTINCT FROM latest
 OR NOT EXISTS(SELECT 1 FROM public.order_item_qr_allocations WHERE order_id=oid AND logical_item_id=NEW.logical_item_id)
 OR (NEW.packed_qa_confirmed AND NEW.packed_by IS DISTINCT FROM public.sr_actor_id())
 THEN RAISE EXCEPTION 'Shipment item requires latest artifact QA and permanent allocation' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_typed_shipment_item_guard BEFORE INSERT OR UPDATE OR DELETE ON public.shipment_items
 FOR EACH ROW EXECUTE FUNCTION public.sr_typed_shipment_item_guard();

CREATE FUNCTION public.sr_typed_shipment_complete() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE sid uuid; oid uuid; state text; latest uuid;
BEGIN
 IF TG_TABLE_NAME='shipments' THEN sid:=NEW.id; ELSE sid:=NEW.shipment_id; END IF;
 SELECT order_id,status INTO oid,state FROM public.shipments WHERE id=sid;
 IF NOT EXISTS(SELECT 1 FROM public.orders WHERE id=oid AND commerce_model='single_qr') THEN RETURN NULL; END IF;
 IF state IN ('preparing','packed','dispatched','delivered') THEN
  SELECT id INTO latest FROM public.print_jobs WHERE order_id=oid ORDER BY job_revision DESC LIMIT 1;
  IF NOT public.sr_typed_fulfillment_eligible(oid)
   OR (state<>'preparing' AND NOT EXISTS(SELECT 1 FROM public.orders WHERE id=oid AND fulfillment_status=state))
   OR EXISTS(SELECT 1 FROM public.order_logical_items i WHERE i.order_id=oid AND NOT EXISTS(SELECT 1 FROM public.shipment_items m WHERE m.shipment_id=sid AND m.logical_item_id=i.id))
   OR EXISTS(SELECT 1 FROM public.shipment_items m WHERE m.shipment_id=sid AND (m.print_job_id<>latest OR (state<>'preparing' AND NOT m.packed_qa_confirmed)))
   OR EXISTS(SELECT 1 FROM public.shipment_pairs WHERE shipment_id=sid)
  THEN RAISE EXCEPTION 'Typed shipment requires complete item packing and latest QA' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER sr_typed_shipment_complete AFTER INSERT OR UPDATE ON public.shipments
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_typed_shipment_complete();
CREATE CONSTRAINT TRIGGER sr_typed_shipment_items_complete AFTER INSERT OR UPDATE ON public.shipment_items
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_typed_shipment_complete();

CREATE FUNCTION public.sr_typed_shipment_status_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM public.orders WHERE id=NEW.order_id AND commerce_model='single_qr') THEN RETURN NEW; END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.status<>'preparing' THEN RAISE EXCEPTION 'Shipment starts preparing' USING ERRCODE='23514'; END IF;
 ELSIF NEW.status IS DISTINCT FROM OLD.status AND NOT (
  (OLD.status='preparing' AND NEW.status IN ('packed','exception'))
  OR (OLD.status='packed' AND NEW.status IN ('dispatched','exception'))
  OR (OLD.status='dispatched' AND NEW.status IN ('delivered','exception','returned'))
  OR (OLD.status='exception' AND NEW.status='returned')) THEN
  RAISE EXCEPTION 'Invalid typed shipment transition' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_typed_shipment_status_guard BEFORE INSERT OR UPDATE ON public.shipments
 FOR EACH ROW EXECUTE FUNCTION public.sr_typed_shipment_status_guard();

CREATE FUNCTION public.sr_typed_order_fulfillment_complete() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE o public.orders;
BEGIN
 SELECT * INTO o FROM public.orders WHERE id=NEW.id;
 IF o.commerce_model='single_qr' AND o.fulfillment_status IN ('packed','dispatched','delivered')
 AND NOT EXISTS(SELECT 1 FROM public.shipments s WHERE s.order_id=o.id AND s.status=o.fulfillment_status)
 THEN RAISE EXCEPTION 'Typed fulfillment requires matching shipment' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER sr_typed_order_fulfillment_complete AFTER INSERT OR UPDATE ON public.orders
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_typed_order_fulfillment_complete();

CREATE FUNCTION public.sr_typed_job_qa_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE oid uuid; obs jsonb:=NEW.observations;
BEGIN
 SELECT order_id INTO oid FROM public.print_jobs WHERE id=NEW.print_job_id;
 IF NOT EXISTS(SELECT 1 FROM public.orders WHERE id=oid AND commerce_model='single_qr') THEN RETURN NEW; END IF;
 PERFORM public.sr_template_registry_gate(false);
 PERFORM 1 FROM public.orders WHERE id=oid FOR UPDATE;
 IF NEW.approved AND (NOT public.sr_typed_print_clear(oid)
 OR NOT coalesce((obs->>'scan_passed')::boolean,false)
 OR NOT coalesce((obs->>'logo_quiet_zone_passed')::boolean,false)
 OR NOT coalesce((obs->>'bilingual_passed')::boolean,false)
 OR NOT coalesce((obs->>'cutting_packaging_passed')::boolean,false)
 OR NOT coalesce((obs->>'actual_scale_passed')::boolean,false)
 OR jsonb_typeof(obs->'inspected_item_ids') IS DISTINCT FROM 'array'
 OR jsonb_array_length(obs->'inspected_item_ids')<>(SELECT count(*) FROM public.order_logical_items WHERE order_id=oid)
 OR EXISTS(SELECT 1 FROM public.order_logical_items i WHERE i.order_id=oid AND NOT (obs->'inspected_item_ids' ? i.id::text))
 OR NOT EXISTS(SELECT 1 FROM public.print_artifacts a WHERE a.print_job_id=NEW.print_job_id AND a.sha256_hex=NEW.artifact_sha256 AND a.deleted_at IS NULL)
 OR EXISTS(WITH expected AS (
   SELECT i.qr_type_snapshot AS kind,z.size_mm_snapshot AS mm,sum(z.copies) AS copies
   FROM public.order_item_sizes z JOIN public.order_logical_items i ON i.id=z.logical_item_id WHERE i.order_id=oid GROUP BY 1,2),
 actual AS (SELECT r.tag_type AS kind,r.symbol_mm::numeric AS mm,sum(r.copies) AS copies
   FROM jsonb_to_recordset(obs->'observed') r(tag_type text,symbol_mm text,copies integer) GROUP BY 1,2)
 SELECT 1 FROM expected e FULL JOIN actual a USING(kind,mm) WHERE e.copies IS DISTINCT FROM a.copies))
 THEN RAISE EXCEPTION 'Typed QA requires every item, size, copy and artifact checks' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_typed_job_qa_guard BEFORE INSERT ON public.print_job_qa
 FOR EACH ROW EXECUTE FUNCTION public.sr_typed_job_qa_guard();

DO $$ DECLARE signature text; definition text; updated text; BEGIN
 FOREACH signature IN ARRAY ARRAY['public.sr_item_order_model_guard()','public.sr_typed_settlement_complete(uuid)'] LOOP
  SELECT pg_get_functiondef(signature::regprocedure) INTO definition;
  updated:=replace(definition,'''unallocated'',''allocated'',''exception''','''unallocated'',''allocated'',''packed'',''dispatched'',''delivered'',''exception''');
  updated:=replace(updated,'''allocated'',''exception''','''allocated'',''packed'',''dispatched'',''delivered'',''exception''');
  IF updated=definition THEN RAISE EXCEPTION 'Review installed typed status guard'; END IF; EXECUTE updated;
 END LOOP;
END $$;

REVOKE ALL ON FUNCTION public.sr_typed_print_clear(uuid),public.sr_typed_fulfillment_eligible(uuid),
 public.sr_typed_print_handoff(),public.sr_typed_shipment_item_guard(),public.sr_typed_shipment_complete(),
 public.sr_typed_order_fulfillment_complete(),public.sr_typed_job_qa_guard(),public.sr_print_worker_order_lock(uuid)
 ,public.sr_typed_shipment_status_guard()
 FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_typed_print_handoff() TO safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_print_worker_order_lock(uuid) TO safereturn_worker;
