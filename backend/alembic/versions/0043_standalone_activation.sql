-- Source only. Owner approved: delivered order + purchaser account, no gifting.
CREATE TABLE public.standalone_owner_release (
 singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton), enabled boolean NOT NULL DEFAULT false
);
INSERT INTO public.standalone_owner_release(singleton,enabled) VALUES(true,false);
CREATE TABLE public.standalone_activation_intents (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 logical_item_id uuid NOT NULL REFERENCES public.order_item_qr_allocations(logical_item_id) ON DELETE RESTRICT,
 actor_user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 session_id uuid NOT NULL,
 state_revision integer NOT NULL CHECK(state_revision>0),
 created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
 expires_at timestamptz NOT NULL DEFAULT statement_timestamp()+interval '5 minutes',
 consumed_at timestamptz,
 CHECK(expires_at>created_at AND expires_at<=created_at+interval '5 minutes')
);
CREATE INDEX ix_standalone_intents_actor ON public.standalone_activation_intents(actor_user_id,created_at);
CREATE TABLE public.standalone_owner_events (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 qr_id uuid NOT NULL REFERENCES public.qr_codes(id) ON DELETE RESTRICT,
 actor_user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 event_type text NOT NULL CHECK(event_type IN ('activated','owner_disabled','owner_enabled')),
 state_revision integer NOT NULL CHECK(state_revision>0),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(qr_id,state_revision)
);
CREATE TABLE public.standalone_owner_receipts (
 actor_user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 operation text NOT NULL, key_hash text NOT NULL CHECK(key_hash~'^[0-9a-f]{64}$'),
 request_hash text NOT NULL CHECK(request_hash~'^[0-9a-f]{64}$'),
 result jsonb NOT NULL CHECK(jsonb_typeof(result)='object'),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(actor_user_id,operation,key_hash)
);
CREATE UNIQUE INDEX uq_standalone_activation_once ON public.standalone_owner_events(qr_id) WHERE event_type='activated';
DO $$ DECLARE tbl text; BEGIN
 FOREACH tbl IN ARRAY ARRAY['standalone_owner_release','standalone_activation_intents','standalone_owner_events','standalone_owner_receipts'] LOOP
  EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',tbl);
  EXECUTE format('REVOKE ALL ON public.%I FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker',tbl);
 END LOOP;
END $$;
CREATE TRIGGER sr_standalone_owner_events_append BEFORE UPDATE OR DELETE ON public.standalone_owner_events FOR EACH ROW EXECUTE FUNCTION public.sr_append_only();
CREATE TRIGGER sr_standalone_owner_receipts_append BEFORE UPDATE OR DELETE ON public.standalone_owner_receipts FOR EACH ROW EXECUTE FUNCTION public.sr_append_only();

CREATE FUNCTION public.sr_standalone_owner_enabled() RETURNS boolean
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE enabled boolean;
BEGIN
 SELECT r.enabled INTO enabled FROM public.standalone_owner_release r WHERE singleton FOR SHARE;
 RETURN coalesce(enabled,false);
END $$;

CREATE FUNCTION public.sr_standalone_entitled(iid uuid) RETURNS boolean
LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT 1 FROM public.order_item_qr_allocations a JOIN public.orders o ON o.id=a.order_id
 JOIN public.typed_order_settlements t ON t.order_id=o.id JOIN public.payment_attempts p ON p.id=t.attempt_id
 JOIN public.standalone_qr_states s ON s.qr_id=a.qr_id JOIN public.qr_codes q ON q.id=a.qr_id
 WHERE a.logical_item_id=iid AND a.purchaser_user_id=public.sr_actor_id() AND o.customer_user_id=public.sr_actor_id()
 AND o.commerce_model='single_qr' AND o.order_status='placed' AND o.payment_status='verified' AND o.fulfillment_status='delivered'
 AND t.state='allocated' AND p.state='verified' AND p.amount=o.total_pkr AND p.currency_code=o.currency_code
 AND public.sr_financial_order_clear(o.id)
 AND NOT EXISTS(SELECT 1 FROM public.template_order_holds WHERE order_id=o.id)
 AND NOT EXISTS(SELECT 1 FROM public.order_item_sizes z JOIN public.order_logical_items i ON i.id=z.logical_item_id WHERE i.order_id=o.id AND NOT public.sr_template_revision_clear(z.revision_id,true))
 AND NOT EXISTS(SELECT 1 FROM public.order_cancellation_requests WHERE order_id=o.id AND status IN ('requested','investigating','approved','escalated'))
 AND EXISTS(SELECT 1 FROM public.shipment_items m JOIN public.shipments h ON h.id=m.shipment_id
 WHERE m.logical_item_id=a.logical_item_id AND h.order_id=o.id AND h.status='delivered' AND h.delivered_at IS NOT NULL AND m.packed_qa_confirmed)
 AND s.inventory_status='allocated' AND s.ownership_status='unclaimed' AND s.owner_user_id IS NULL
 AND q.pair_id IS NULL AND q.is_current AND q.public_status='unactivated' AND q.revoked_at IS NULL)
$$;

CREATE FUNCTION public.sr_standalone_owner_list(sid uuid,take integer,after_id uuid) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE value jsonb;
BEGIN
 IF NOT EXISTS(SELECT 1 FROM public.sr_account_session_state(sid) WHERE email_verified) THEN RETURN NULL; END IF;
 IF take IS NULL OR take NOT BETWEEN 1 AND 101 THEN RAISE EXCEPTION 'Invalid bound'; END IF;
 SELECT coalesce(jsonb_agg(to_jsonb(r) ORDER BY r.logical_item_id),'[]'::jsonb) INTO value FROM (
 SELECT a.logical_item_id,a.qr_id,a.order_id,i.product_name_snapshot,i.qr_type_snapshot AS tag_type,
 s.ownership_status,q.public_status,s.row_version AS revision,s.activated_at,
 (public.sr_standalone_owner_enabled() AND public.sr_standalone_entitled(a.logical_item_id)) AS can_activate
 FROM public.order_item_qr_allocations a JOIN public.order_logical_items i ON i.id=a.logical_item_id
 JOIN public.standalone_qr_states s ON s.qr_id=a.qr_id JOIN public.qr_codes q ON q.id=a.qr_id
 WHERE a.purchaser_user_id=public.sr_actor_id() AND (after_id IS NULL OR a.logical_item_id>after_id)
 ORDER BY a.logical_item_id LIMIT take) r;
 RETURN jsonb_build_object('items',value,'activation_released',public.sr_standalone_owner_enabled());
END $$;

CREATE FUNCTION public.sr_standalone_begin(sid uuid,iid uuid) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a public.order_item_qr_allocations; intent public.standalone_activation_intents; revision integer;
BEGIN
 IF NOT EXISTS(SELECT 1 FROM public.sr_account_session_state(sid) WHERE email_verified) THEN RETURN NULL; END IF;
 IF NOT public.sr_standalone_owner_enabled() THEN RETURN jsonb_build_object('error','NOT_RELEASED'); END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended('standalone.begin:'||public.sr_actor_id()::text,0));
 SELECT * INTO a FROM public.order_item_qr_allocations WHERE logical_item_id=iid AND purchaser_user_id=public.sr_actor_id();
 IF NOT FOUND THEN RETURN NULL; END IF;
 PERFORM public.sr_template_registry_gate(false);
 PERFORM 1 FROM public.orders WHERE id=a.order_id FOR UPDATE;
 PERFORM 1 FROM public.qr_codes WHERE id=a.qr_id FOR UPDATE;
 SELECT row_version INTO revision FROM public.standalone_qr_states WHERE qr_id=a.qr_id FOR UPDATE;
 IF NOT public.sr_standalone_entitled(iid) THEN RETURN jsonb_build_object('error','NOT_ELIGIBLE'); END IF;
 -- Bounded durable accounting, including repeated begin requests.
 IF (SELECT count(*) FROM public.standalone_activation_intents WHERE actor_user_id=public.sr_actor_id() AND created_at>clock_timestamp()-interval '15 minutes')>=20
 THEN RETURN jsonb_build_object('error','RATE_LIMITED'); END IF;
 INSERT INTO public.standalone_activation_intents(logical_item_id,actor_user_id,session_id,state_revision)
 VALUES(iid,public.sr_actor_id(),sid,revision) RETURNING * INTO intent;
 RETURN jsonb_build_object('intent_id',intent.id,'logical_item_id',iid,'qr_id',a.qr_id,'expires_at',intent.expires_at,'method','delivered_purchaser');
END $$;

CREATE FUNCTION public.sr_standalone_confirm(sid uuid,intent_id uuid,kh text,rh text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a public.order_item_qr_allocations; i public.standalone_activation_intents; s public.standalone_qr_states;
 old public.standalone_owner_receipts; result jsonb;
BEGIN
 IF NOT EXISTS(SELECT 1 FROM public.sr_account_session_state(sid) WHERE email_verified) THEN RETURN NULL; END IF;
 IF NOT public.sr_standalone_owner_enabled() THEN RETURN jsonb_build_object('error','NOT_RELEASED'); END IF;
 IF kh IS NULL OR rh IS NULL OR kh!~'^[0-9a-f]{64}$' OR rh!~'^[0-9a-f]{64}$' THEN RAISE EXCEPTION 'Invalid receipt'; END IF;
 SELECT * INTO i FROM public.standalone_activation_intents WHERE id=intent_id AND actor_user_id=public.sr_actor_id() AND session_id=sid;
 IF NOT FOUND THEN RETURN NULL; END IF;
 SELECT * INTO a FROM public.order_item_qr_allocations WHERE logical_item_id=i.logical_item_id AND purchaser_user_id=public.sr_actor_id();
 IF NOT FOUND THEN RETURN NULL; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended('standalone.confirm:'||public.sr_actor_id()::text||':'||kh,0));
 PERFORM public.sr_template_registry_gate(false);
 PERFORM 1 FROM public.orders WHERE id=a.order_id FOR UPDATE;
 PERFORM 1 FROM public.qr_codes WHERE id=a.qr_id FOR UPDATE;
 SELECT * INTO s FROM public.standalone_qr_states WHERE qr_id=a.qr_id FOR UPDATE;
 SELECT * INTO i FROM public.standalone_activation_intents WHERE id=intent_id FOR UPDATE;
 SELECT * INTO old FROM public.standalone_owner_receipts WHERE actor_user_id=public.sr_actor_id() AND operation='activate' AND key_hash=kh;
 IF FOUND THEN
  IF old.request_hash<>rh THEN RETURN jsonb_build_object('error','IDEMPOTENCY_KEY_REUSED'); END IF;
  RETURN old.result;
 END IF;
 IF i.consumed_at IS NOT NULL OR i.expires_at<=clock_timestamp() OR i.state_revision<>s.row_version OR NOT public.sr_standalone_entitled(i.logical_item_id)
 THEN RETURN jsonb_build_object('error','NOT_ELIGIBLE'); END IF;
 UPDATE public.standalone_qr_states SET owner_user_id=public.sr_actor_id(),ownership_status='active',activated_at=clock_timestamp(),row_version=row_version+1 WHERE qr_id=a.qr_id RETURNING * INTO s;
 UPDATE public.qr_codes SET public_status='active',updated_at=clock_timestamp() WHERE id=a.qr_id;
 IF EXISTS(SELECT 1 FROM public.qr_codes WHERE id=a.qr_id AND tag_type='lost') THEN
  INSERT INTO public.lost_item_profiles(qr_id) VALUES(a.qr_id);
  INSERT INTO public.tag_contact_preferences(qr_id) VALUES(a.qr_id);
 ELSE INSERT INTO public.ice_profiles(qr_id) VALUES(a.qr_id); END IF;
 UPDATE public.standalone_activation_intents SET consumed_at=clock_timestamp() WHERE id=i.id;
 INSERT INTO public.standalone_owner_events(qr_id,actor_user_id,event_type,state_revision) VALUES(a.qr_id,public.sr_actor_id(),'activated',s.row_version);
 INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,reason,safe_details)
 VALUES(public.sr_actor_id(),'customer','qr.standalone.activated','qr',a.qr_id,'delivered purchaser entitlement',jsonb_build_object('revision',s.row_version));
 result:=jsonb_build_object('qr_id',a.qr_id,'logical_item_id',a.logical_item_id,'status','active','revision',s.row_version,'activated_at',s.activated_at);
 INSERT INTO public.standalone_owner_receipts(actor_user_id,operation,key_hash,request_hash,result) VALUES(public.sr_actor_id(),'activate',kh,rh,result);
 RETURN result;
END $$;

-- Activation cannot be forged by old inventory UPDATE grants or a partial write.
CREATE FUNCTION public.sr_standalone_owner_consistency() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE s public.standalone_qr_states;
BEGIN
 SELECT * INTO s FROM public.standalone_qr_states WHERE qr_id=NEW.qr_id;
 IF s.ownership_status='active' AND (NOT EXISTS(SELECT 1 FROM public.order_item_qr_allocations WHERE qr_id=s.qr_id AND purchaser_user_id=s.owner_user_id)
 OR NOT EXISTS(SELECT 1 FROM public.standalone_owner_events WHERE qr_id=s.qr_id AND actor_user_id=s.owner_user_id AND event_type='activated')
 OR NOT EXISTS(SELECT 1 FROM public.qr_codes WHERE id=s.qr_id AND public_status IN ('active','owner_disabled','admin_suspended')))
 THEN RAISE EXCEPTION 'Standalone owner requires permanent entitlement and activation history' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER sr_standalone_owner_consistency AFTER INSERT OR UPDATE ON public.standalone_qr_states DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_standalone_owner_consistency();

REVOKE ALL ON FUNCTION public.sr_standalone_owner_enabled(),public.sr_standalone_entitled(uuid),public.sr_standalone_owner_list(uuid,integer,uuid),public.sr_standalone_begin(uuid,uuid),public.sr_standalone_confirm(uuid,uuid,text,text),public.sr_standalone_owner_consistency()
 FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_standalone_owner_list(uuid,integer,uuid),public.sr_standalone_begin(uuid,uuid),public.sr_standalone_confirm(uuid,uuid,text,text) TO safereturn_api;

CREATE FUNCTION public.sr_standalone_history(sid uuid,qid uuid,take integer,after_revision integer) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE value jsonb;
BEGIN
 IF NOT EXISTS(SELECT 1 FROM public.sr_account_session_state(sid) WHERE email_verified)
 OR NOT EXISTS(SELECT 1 FROM public.standalone_qr_states WHERE qr_id=qid AND owner_user_id=public.sr_actor_id()) THEN RETURN NULL; END IF;
 IF take IS NULL OR take NOT BETWEEN 1 AND 100 THEN RAISE EXCEPTION 'Invalid history bound'; END IF;
 SELECT coalesce(jsonb_agg(to_jsonb(r) ORDER BY state_revision DESC),'[]'::jsonb) INTO value FROM (
 SELECT id AS event_id,event_type,state_revision,created_at FROM public.standalone_owner_events
 WHERE qr_id=qid AND (after_revision IS NULL OR state_revision<after_revision) ORDER BY state_revision DESC LIMIT take) r;
 RETURN jsonb_build_object('qr_id',qid,'items',value,'next_revision',CASE WHEN jsonb_array_length(value)=take THEN (value->(take-1)->>'state_revision')::integer ELSE NULL END);
END $$;

CREATE FUNCTION public.sr_standalone_availability(sid uuid,qid uuid,expected integer,wanted text,kh text,rh text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE s public.standalone_qr_states; q public.qr_codes; old public.standalone_owner_receipts; result jsonb; oid uuid;
BEGIN
 IF NOT EXISTS(SELECT 1 FROM public.sr_account_session_state(sid) WHERE email_verified) THEN RETURN NULL; END IF;
 IF kh IS NULL OR rh IS NULL OR kh!~'^[0-9a-f]{64}$' OR rh!~'^[0-9a-f]{64}$' THEN RAISE EXCEPTION 'Invalid receipt'; END IF;
 SELECT order_id INTO oid FROM public.order_item_qr_allocations WHERE qr_id=qid AND purchaser_user_id=public.sr_actor_id();
 IF NOT FOUND THEN RETURN NULL; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended('standalone.availability:'||public.sr_actor_id()::text||':'||kh,0));
 PERFORM 1 FROM public.orders WHERE id=oid FOR UPDATE;
 SELECT * INTO q FROM public.qr_codes WHERE id=qid FOR UPDATE;
 SELECT * INTO s FROM public.standalone_qr_states WHERE qr_id=qid AND owner_user_id=public.sr_actor_id() AND ownership_status='active' FOR UPDATE;
 IF NOT FOUND THEN RETURN NULL; END IF;
 SELECT * INTO old FROM public.standalone_owner_receipts WHERE actor_user_id=public.sr_actor_id() AND operation='availability:'||qid::text AND key_hash=kh;
 IF FOUND THEN
  IF old.request_hash<>rh THEN RETURN jsonb_build_object('error','IDEMPOTENCY_KEY_REUSED'); END IF;
  RETURN old.result;
 END IF;
 IF expected IS DISTINCT FROM s.row_version THEN RETURN jsonb_build_object('error','VERSION_MISMATCH'); END IF;
 IF wanted IS NULL OR wanted NOT IN ('active','owner_disabled') OR q.public_status NOT IN ('active','owner_disabled') OR wanted=q.public_status
 OR NOT q.is_current OR q.revoked_at IS NOT NULL THEN RETURN jsonb_build_object('error','NOT_ELIGIBLE'); END IF;
 IF wanted='active' AND (NOT public.sr_standalone_owner_enabled() OR NOT public.sr_financial_order_clear(oid)) THEN RETURN jsonb_build_object('error','NOT_ELIGIBLE'); END IF;
 UPDATE public.qr_codes SET public_status=wanted,updated_at=clock_timestamp() WHERE id=qid;
 UPDATE public.standalone_qr_states SET row_version=row_version+1 WHERE qr_id=qid RETURNING * INTO s;
 INSERT INTO public.standalone_owner_events(qr_id,actor_user_id,event_type,state_revision) VALUES(qid,public.sr_actor_id(),CASE wanted WHEN 'active' THEN 'owner_enabled' ELSE 'owner_disabled' END,s.row_version);
 INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,reason,safe_details)
 VALUES(public.sr_actor_id(),'customer','qr.standalone.availability','qr',qid,'owner public availability',jsonb_build_object('from_status',q.public_status,'to_status',wanted,'revision',s.row_version));
 result:=jsonb_build_object('qr_id',qid,'public_status',wanted,'revision',s.row_version);
 INSERT INTO public.standalone_owner_receipts(actor_user_id,operation,key_hash,request_hash,result) VALUES(public.sr_actor_id(),'availability:'||qid::text,kh,rh,result);
 RETURN result;
END $$;

CREATE OR REPLACE FUNCTION public.sr_owns_qr(qid uuid) RETURNS boolean
LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT 1 FROM public.qr_codes q JOIN public.tag_pairs p ON p.id=q.pair_id WHERE q.id=qid AND p.owner_user_id=public.sr_actor_id())
 OR EXISTS(SELECT 1 FROM public.standalone_qr_states s JOIN public.qr_codes q ON q.id=s.qr_id
 WHERE s.qr_id=qid AND s.owner_user_id=public.sr_actor_id() AND s.ownership_status='active' AND q.pair_id IS NULL AND q.is_current AND q.revoked_at IS NULL)
$$;

DO $$ DECLARE definition text; updated text; BEGIN
 SELECT pg_get_functiondef('public.sr_lock_profile_qr(uuid,text)'::regprocedure) INTO definition;
 updated:=regexp_replace(definition,E'BEGIN\\s*',$body$BEGIN
 IF EXISTS(SELECT 1 FROM public.qr_codes WHERE id=qid AND pair_id IS NULL) THEN
  IF public.sr_actor_id() IS NULL OR purpose NOT IN ('lost','ice') OR NOT public.sr_owns_qr(qid) THEN RETURN false; END IF;
  PERFORM 1 FROM public.qr_codes WHERE id=qid AND tag_type=purpose AND is_current AND public_status<>'revoked' FOR UPDATE;
  IF NOT FOUND THEN RETURN false; END IF;
  PERFORM 1 FROM public.standalone_qr_states WHERE qr_id=qid AND owner_user_id=public.sr_actor_id() AND ownership_status='active' FOR SHARE;
  RETURN FOUND;
 END IF;
 $body$);
 IF updated=definition THEN RAISE EXCEPTION 'Review installed profile owner lock'; END IF; EXECUTE updated;
 SELECT pg_get_functiondef('public.sr_typed_print_clear(uuid)'::regprocedure) INTO definition;
 updated:=replace(definition,'q.public_status<>''unactivated''','q.public_status NOT IN (''unactivated'',''active'',''owner_disabled'')');
 updated:=replace(updated,'s.ownership_status IS DISTINCT FROM ''unclaimed'' OR s.owner_user_id IS NOT NULL',
  'NOT ((s.ownership_status=''unclaimed'' AND s.owner_user_id IS NULL) OR (s.ownership_status=''active'' AND s.owner_user_id=x.purchaser_user_id))');
 IF updated=definition THEN RAISE EXCEPTION 'Review installed typed print owner predicate'; END IF; EXECUTE updated;
END $$;

REVOKE ALL ON FUNCTION public.sr_standalone_history(uuid,uuid,integer,integer),public.sr_standalone_availability(uuid,uuid,integer,text,text,text) FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_standalone_history(uuid,uuid,integer,integer),public.sr_standalone_availability(uuid,uuid,integer,text,text,text) TO safereturn_api;

CREATE FUNCTION public.sr_standalone_public_clear(qid uuid) RETURNS boolean
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE uid uuid;
BEGIN
 IF NOT public.sr_standalone_owner_enabled() THEN RETURN false; END IF;
 SELECT owner_user_id INTO uid FROM public.standalone_qr_states WHERE qr_id=qid AND ownership_status='active' AND inventory_status='allocated';
 IF uid IS NULL OR NOT public.sr_account_epoch_allows(uid,clock_timestamp()) THEN RETURN false; END IF;
 PERFORM 1 FROM public.qr_codes q JOIN public.standalone_qr_states s ON s.qr_id=q.id
 WHERE q.id=qid AND q.pair_id IS NULL AND q.is_current AND q.public_status='active' AND q.revoked_at IS NULL
 AND s.owner_user_id=uid AND s.ownership_status='active' FOR SHARE OF q,s;
 RETURN FOUND;
END $$;

-- Keep the exact public consent/field allowlist and legacy projection body.
DO $$ DECLARE definition text; updated text; signature text; BEGIN
 SELECT pg_get_functiondef('public.sr_public_qr_projection(text)'::regprocedure) INTO definition;
 updated:=replace(definition,'AND qr_codes.pair_id IS NOT NULL','');
 IF updated=definition THEN RAISE EXCEPTION 'Review installed legacy projection filter'; END IF;
 updated:=replace(updated,'    payload := jsonb_build_object(',$body$
    IF qr.pair_id IS NULL THEN
      IF NOT public.sr_standalone_owner_enabled() THEN RETURN NULL; END IF;
      IF qr.public_status='active' AND NOT public.sr_standalone_public_clear(qr.id) THEN
       RETURN jsonb_build_object('tag_type',qr.tag_type,'status','admin_suspended','locale_options',jsonb_build_array('en','ur'));
      END IF;
    END IF;
    payload := jsonb_build_object($body$);
 EXECUTE updated;

 FOREACH signature IN ARRAY ARRAY['public.sr_public_ice_contact(text,uuid)','public.sr_public_whatsapp_link(text)'] LOOP
  SELECT pg_get_functiondef(signature::regprocedure) INTO definition;
  updated:=regexp_replace(definition,E'BEGIN\\s*',$body$BEGIN
   IF EXISTS(SELECT 1 FROM public.qr_codes x WHERE x.public_token=$1 AND x.pair_id IS NULL AND NOT public.sr_standalone_public_clear(x.id)) THEN RETURN NULL; END IF;
  $body$);
  IF updated=definition THEN RAISE EXCEPTION 'Review installed public contact projection'; END IF; EXECUTE updated;
 END LOOP;

 SELECT pg_get_functiondef('public.sr_public_lost_qr_id(text)'::regprocedure) INTO definition;
 updated:=replace(definition,'AND l.published','AND l.published AND (q.pair_id IS NOT NULL OR public.sr_standalone_public_clear(q.id))');
 IF updated=definition THEN RAISE EXCEPTION 'Review installed finder identity projection'; END IF; EXECUTE updated;

 SELECT pg_get_functiondef('public.sr_public_submit_finder_message(text,text,bytea,bytea,smallint,text,bytea,smallint,text,timestamp with time zone,bytea,bytea,numeric,text,timestamp with time zone,text,smallint,text,text)'::regprocedure) INTO definition;
 updated:=replace(definition,'    SELECT q.id, p.owner_user_id',$body$
    IF EXISTS(SELECT 1 FROM public.qr_codes x WHERE x.public_token=$1 AND x.pair_id IS NULL) THEN
     SELECT q.id,s.owner_user_id INTO qr,owner_id FROM public.qr_codes q
     JOIN public.standalone_qr_states s ON s.qr_id=q.id JOIN public.lost_item_profiles l ON l.qr_id=q.id
     WHERE q.public_token=$1 AND q.tag_type='lost' AND l.published AND public.sr_standalone_public_clear(q.id) FOR SHARE OF q,s,l;
    ELSE
    SELECT q.id, p.owner_user_id$body$);
 IF position('FOR UPDATE OF p FOR SHARE OF q,l;' IN updated)=0 THEN
  RAISE EXCEPTION 'Review installed finder submission lock clause';
 END IF;
 updated:=replace(updated,'FOR UPDATE OF p FOR SHARE OF q,l;','FOR UPDATE OF p FOR SHARE OF q,l; END IF;');
 IF updated=definition THEN RAISE EXCEPTION 'Review installed finder submission'; END IF; EXECUTE updated;

 SELECT pg_get_functiondef('public.sr_finder_guard()'::regprocedure) INTO definition;
 updated:=regexp_replace(definition,E'BEGIN\\s*',$body$BEGIN
 IF TG_OP='INSERT' AND EXISTS(SELECT 1 FROM public.qr_codes WHERE id=NEW.qr_id AND pair_id IS NULL) THEN
  IF NOT public.sr_standalone_public_clear(NEW.qr_id) OR NOT EXISTS(
   SELECT 1 FROM public.standalone_qr_states s JOIN public.qr_codes q ON q.id=s.qr_id JOIN public.lost_item_profiles l ON l.qr_id=q.id
   WHERE s.qr_id=NEW.qr_id AND s.owner_user_id=NEW.recipient_owner_user_id AND q.tag_type='lost' AND l.published)
   THEN RAISE EXCEPTION 'Message requires active standalone owner' USING ERRCODE='23514'; END IF;
  NEW.submitted_at:=transaction_timestamp(); RETURN NEW;
 END IF;
 $body$);
 IF updated=definition THEN RAISE EXCEPTION 'Review installed finder recipient guard'; END IF; EXECUTE updated;
END $$;
REVOKE ALL ON FUNCTION public.sr_standalone_public_clear(uuid) FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;

CREATE FUNCTION public.sr_standalone_products(qid uuid) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE value jsonb;
BEGIN
 IF NOT public.sr_owns_qr(qid) THEN RETURN NULL; END IF;
 SELECT coalesce(jsonb_agg(jsonb_build_object('product_name_snapshot',i.product_name_snapshot,'variant_name_snapshot',z.variant_name_snapshot,'copies',z.copies) ORDER BY z.id),'[]'::jsonb) INTO value
 FROM public.order_item_qr_allocations a JOIN public.order_logical_items i ON i.id=a.logical_item_id JOIN public.order_item_sizes z ON z.logical_item_id=i.id
 WHERE a.qr_id=qid AND a.purchaser_user_id=public.sr_actor_id();
 RETURN value;
END $$;
REVOKE ALL ON FUNCTION public.sr_standalone_products(uuid) FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_standalone_products(uuid) TO safereturn_api;

CREATE FUNCTION public.sr_standalone_support(sid uuid,cid uuid) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE oid uuid; value jsonb;
BEGIN
 IF NOT public.sr_is_staff(ARRAY['support']) OR NOT public.sr_mfa()
 OR NOT EXISTS(SELECT 1 FROM public.sr_account_session_state(sid) WHERE email_verified AND mfa_active) THEN RETURN NULL; END IF;
 PERFORM 1 FROM public.staff_roles WHERE user_id=public.sr_actor_id() AND role='support' AND revoked_at IS NULL FOR SHARE;
 IF NOT FOUND THEN RETURN NULL; END IF;
 SELECT order_id INTO oid FROM public.support_cases WHERE id=cid AND assigned_staff_id=public.sr_actor_id() FOR SHARE;
 IF oid IS NULL THEN RETURN NULL; END IF;
 SELECT coalesce(jsonb_agg(jsonb_build_object('logical_item_id',a.logical_item_id,'qr_id',a.qr_id,'tag_type',i.qr_type_snapshot,'ownership_status',s.ownership_status,'public_status',q.public_status,'revision',s.row_version) ORDER BY a.logical_item_id),'[]'::jsonb)
 INTO value FROM public.order_item_qr_allocations a JOIN public.order_logical_items i ON i.id=a.logical_item_id JOIN public.qr_codes q ON q.id=a.qr_id JOIN public.standalone_qr_states s ON s.qr_id=q.id WHERE a.order_id=oid;
 INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,reason,safe_details)
 VALUES(public.sr_actor_id(),'staff','support.standalone.read','support_case',cid,'assigned order investigation','{}'::jsonb);
 RETURN jsonb_build_object('case_id',cid,'order_id',oid,'items',value);
END $$;
REVOKE ALL ON FUNCTION public.sr_standalone_support(uuid,uuid) FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_standalone_support(uuid,uuid) TO safereturn_api;

-- Export only own safe identifiers/status and immutable purchase snapshots.
-- Existing export lease, reviewer authority and third-party omissions stay intact.
DO $$ DECLARE definition text; updated text; BEGIN
 SELECT pg_get_functiondef('public.sr_export_page(uuid,uuid,text,uuid)'::regprocedure) INTO definition;
 updated:=replace(definition,' IF category=''account'' THEN',$body$
 IF category='independent_qr' THEN
  RETURN QUERY SELECT s.qr_id,jsonb_build_object('qr_id',s.qr_id,'ownership_status',s.ownership_status,'activated_at',s.activated_at,'revision',s.row_version)
  FROM public.standalone_qr_states s WHERE s.owner_user_id=r.subject_id AND (after_id IS NULL OR s.qr_id>after_id) ORDER BY s.qr_id LIMIT 100;
 ELSIF category='logical_items' THEN
  RETURN QUERY SELECT i.id,jsonb_build_object('item_id',i.id,'order_id',i.order_id,'qr_type',i.qr_type_snapshot,'quantity',i.quantity,'unit_price',i.unit_price_snapshot::text,'total',i.line_total::text,'currency',i.currency_code)
  FROM public.order_logical_items i JOIN public.orders o ON o.id=i.order_id WHERE o.customer_user_id=r.subject_id AND (after_id IS NULL OR i.id>after_id) ORDER BY i.id LIMIT 100;
 ELSIF category='item_sizes' THEN
  RETURN QUERY SELECT z.id,jsonb_build_object('item_id',z.logical_item_id,'size_mm',z.size_mm_snapshot::text,'copies',z.copies)
  FROM public.order_item_sizes z JOIN public.order_logical_items i ON i.id=z.logical_item_id JOIN public.orders o ON o.id=i.order_id
  WHERE o.customer_user_id=r.subject_id AND (after_id IS NULL OR z.id>after_id) ORDER BY z.id LIMIT 100;
 ELSIF category='independent_history' THEN
  RETURN QUERY SELECT e.id,jsonb_build_object('qr_id',e.qr_id,'event_type',e.event_type,'revision',e.state_revision,'occurred_at',e.created_at)
  FROM public.standalone_owner_events e WHERE e.actor_user_id=r.subject_id AND (after_id IS NULL OR e.id>after_id) ORDER BY e.id LIMIT 100;
 ELSIF category='account' THEN$body$);
 IF updated=definition THEN RAISE EXCEPTION 'Review installed export projection'; END IF; EXECUTE updated;
END $$;
