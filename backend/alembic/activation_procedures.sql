-- Only the trusted API role may invoke these fixed-search-path projections/commands.
-- No runtime membership, Auth grants, existing rows or previous migrations change.
CREATE FUNCTION public.sr_activation_rate(binding text) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF binding !~ '^[0-9a-f]{64}$' THEN RETURN false; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended('activation-peer:'||binding,0));
 IF (SELECT count(*) FROM public.audit_events WHERE action='activation.peer'
  AND request_id=binding AND occurred_at>clock_timestamp()-interval '15 minutes')>=100
 THEN RETURN false; END IF;
 INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,request_id,safe_details)
 VALUES(public.sr_actor_id(),CASE WHEN public.sr_actor_id() IS NULL THEN 'anonymous' ELSE 'customer' END,
  'activation.peer','activation',binding,jsonb_build_object('outcome','attempt'));
 RETURN true;
END $$;

CREATE FUNCTION public.sr_activation_context(token text) RETURNS jsonb
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT jsonb_build_object('status','not_activated','can_begin',true,
   'tag_type',q.tag_type,'context_ttl_seconds',900)
 FROM public.qr_codes q JOIN public.tag_pairs p ON p.id=q.pair_id
 WHERE q.public_token=token AND q.is_current AND q.public_status='unactivated'
 AND p.ownership_status='unclaimed' AND p.owner_user_id IS NULL
$$;

-- Never returns the stored verifier; API uses pair/version to compute an HMAC.
CREATE FUNCTION public.sr_activation_key_context(token text) RETURNS TABLE(pair_id uuid,key_version smallint)
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT q.pair_id,c.verifier_key_version FROM public.qr_codes q
 JOIN public.pair_activation_credentials c ON c.pair_id=q.pair_id
 WHERE public.sr_actor_id() IS NOT NULL AND q.public_token=token AND q.is_current
$$;

CREATE FUNCTION public.sr_begin_activation(token text, proof bytea, key_version integer)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE actor uuid:=public.sr_actor_id(); p public.tag_pairs%ROWTYPE;
 c public.pair_activation_credentials%ROWTYPE; unit uuid; lost uuid; ice uuid;
 iid uuid; method text; expiry timestamptz; difference integer:=0; n integer;
BEGIN
 IF actor IS NULL THEN RETURN jsonb_build_object('_status',403); END IF;
 -- Serialize actor attempts across all API processes; failed decisions commit their audit.
 PERFORM pg_advisory_xact_lock(hashtextextended('activation-attempt:'||actor::text,0));
 IF (SELECT count(*) FROM public.audit_events WHERE actor_user_id=actor
     AND action='activation.attempt' AND occurred_at>clock_timestamp()-interval '15 minutes')>=20
 THEN RETURN jsonb_build_object('_status',429); END IF;
 INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,safe_details)
 VALUES(actor,'customer','activation.attempt','activation',jsonb_build_object('outcome','attempt'));
 SELECT t.* INTO p FROM public.tag_pairs t JOIN public.qr_codes q ON q.pair_id=t.id
 WHERE q.public_token=token AND q.is_current AND q.public_status='unactivated' FOR UPDATE OF t;
 IF NOT FOUND OR p.owner_user_id IS NOT NULL OR p.ownership_status<>'unclaimed'
 OR p.revoked_at IS NOT NULL OR p.inventory_status NOT IN ('qa_passed','reserved','packed','shipped','delivered')
 THEN RETURN jsonb_build_object('_status',409); END IF;
 SELECT id INTO lost FROM public.qr_codes WHERE pair_id=p.id AND is_current AND tag_type='lost' AND public_status='unactivated';
 SELECT id INTO ice FROM public.qr_codes WHERE pair_id=p.id AND is_current AND tag_type='ice' AND public_status='unactivated';
 IF lost IS NULL OR ice IS NULL THEN RETURN jsonb_build_object('_status',409); END IF;
 SELECT * INTO c FROM public.pair_activation_credentials WHERE pair_id=p.id FOR UPDATE;
 IF NOT FOUND OR c.status NOT IN ('unused','locked') THEN RETURN jsonb_build_object('_status',409); END IF;
 IF c.locked_until>clock_timestamp() THEN RETURN jsonb_build_object('_status',429); END IF;
 IF c.status='locked' THEN
  UPDATE public.pair_activation_credentials SET status='unused',locked_until=NULL,failed_attempts=0 WHERE pair_id=p.id;
 END IF;
 -- Lock authoritative order and allocation, not a submitted owner/order ID.
 SELECT u.id INTO unit FROM public.order_pair_units u JOIN public.orders o ON o.id=u.order_id
 WHERE u.pair_id=p.id AND u.status='allocated' AND o.customer_user_id=actor
 AND o.payment_status='verified' AND o.order_status IN ('placed','processing','fulfilled')
 FOR SHARE OF u,o;
 IF unit IS NOT NULL THEN method:='order_entitlement';
 ELSE
  -- Do not use variable-time bytea equality for the verifier.
  IF proof IS NULL OR octet_length(proof)<>32 OR octet_length(c.secret_verifier)<>32
     OR key_version IS DISTINCT FROM c.verifier_key_version THEN difference:=1;
  ELSE
   FOR n IN 0..31 LOOP difference:=difference | (get_byte(proof,n) # get_byte(c.secret_verifier,n)); END LOOP;
  END IF;
  -- A credential cannot steal a pair reserved/allocated to another customer.
  IF difference<>0 OR EXISTS(SELECT 1 FROM public.order_pair_units u JOIN public.orders o ON o.id=u.order_id
      WHERE u.pair_id=p.id AND u.status IN ('reserved','allocated') AND o.customer_user_id<>actor)
  THEN
   UPDATE public.pair_activation_credentials SET failed_attempts=failed_attempts+1,
    status=CASE WHEN failed_attempts+1>=5 THEN 'locked' ELSE 'unused' END,
    locked_until=CASE WHEN failed_attempts+1>=5 THEN clock_timestamp()+interval '15 minutes' ELSE NULL END
   WHERE pair_id=p.id;
   RETURN jsonb_build_object('_status',409);
  END IF;
  method:='concealed_credential';
 END IF;
 expiry:=clock_timestamp()+interval '15 minutes';
 INSERT INTO public.activation_intents(actor_user_id,pair_id,lost_qr_id,ice_qr_id,method,
   order_pair_unit_id,verifier_key_version,expires_at)
 VALUES(actor,p.id,lost,ice,method,unit,CASE WHEN unit IS NULL THEN c.verifier_key_version ELSE NULL END,expiry)
 RETURNING id INTO iid;
 RETURN jsonb_build_object('_status',201,'intent_id',iid,'pair_id',p.id,'lost_qr_id',lost,
   'ice_qr_id',ice,'expires_at',expiry,'method',method);
END $$;

CREATE FUNCTION public.sr_confirm_activation(iid uuid, idem text, request_digest text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE actor uuid:=public.sr_actor_id(); i public.activation_intents%ROWTYPE;
 p public.tag_pairs%ROWTYPE; c public.pair_activation_credentials%ROWTYPE;
 previous public.idempotency_records%ROWTYPE; result jsonb; at_time timestamptz;
BEGIN
 IF actor IS NULL THEN RETURN jsonb_build_object('_status',403); END IF;
 IF length(idem) NOT BETWEEN 8 AND 160 OR request_digest !~ '^[0-9a-f]{64}$'
 THEN RETURN jsonb_build_object('_status',400); END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended(actor::text||':activation:'||idem,0));
 SELECT * INTO previous FROM public.idempotency_records WHERE actor_scope=actor::text
 AND operation='pair.activate' AND idempotency_key=idem FOR UPDATE;
 IF FOUND THEN
  IF previous.request_hash<>request_digest THEN RETURN jsonb_build_object('_status',409); END IF;
  IF previous.response_status<>201 THEN RETURN jsonb_build_object('_status',previous.response_status); END IF;
  SELECT * INTO i FROM public.activation_intents WHERE id=iid AND actor_user_id=actor AND state='consumed';
  SELECT * INTO p FROM public.tag_pairs WHERE id=i.pair_id;
  RETURN jsonb_build_object('_status',201,'pair_id',i.pair_id,'status','active','activated_at',p.activated_at,
   'qr_codes',jsonb_build_array(jsonb_build_object('qr_id',i.lost_qr_id,'tag_type','lost'),jsonb_build_object('qr_id',i.ice_qr_id,'tag_type','ice')));
 END IF;
 -- Read identity first, then lock pair before intent to use one lock order across claims.
 SELECT * INTO i FROM public.activation_intents WHERE id=iid AND actor_user_id=actor;
 SELECT * INTO p FROM public.tag_pairs WHERE id=i.pair_id FOR UPDATE;
 SELECT * INTO i FROM public.activation_intents WHERE id=iid AND actor_user_id=actor FOR UPDATE;
 result:=jsonb_build_object('_status',409);
 IF i.id IS NOT NULL AND i.state='pending' AND i.expires_at>clock_timestamp()
 AND p.owner_user_id IS NULL AND p.ownership_status='unclaimed' AND p.revoked_at IS NULL
 AND p.inventory_status IN ('qa_passed','reserved','packed','shipped','delivered') THEN
  SELECT * INTO c FROM public.pair_activation_credentials WHERE pair_id=p.id FOR UPDATE;
  -- Recheck paid allocation and lock it until commit. Refunded/cancelled orders fail closed.
  IF i.method='order_entitlement' THEN
   PERFORM 1 FROM public.order_pair_units u JOIN public.orders o ON o.id=u.order_id
   WHERE u.id=i.order_pair_unit_id AND u.pair_id=p.id AND u.status='allocated'
    AND o.customer_user_id=actor AND o.payment_status='verified'
    AND o.order_status IN ('placed','processing','fulfilled') FOR SHARE OF u,o;
  ELSE
   PERFORM 1 WHERE c.verifier_key_version=i.verifier_key_version AND NOT EXISTS(
    SELECT 1 FROM public.order_pair_units u JOIN public.orders o ON o.id=u.order_id
    WHERE u.pair_id=p.id AND u.status IN ('reserved','allocated') AND o.customer_user_id<>actor);
  END IF;
  IF FOUND AND c.status='unused' AND (c.locked_until IS NULL OR c.locked_until<=clock_timestamp())
   AND EXISTS(SELECT 1 FROM public.qr_codes WHERE id=i.lost_qr_id AND pair_id=p.id AND tag_type='lost' AND is_current AND public_status='unactivated')
   AND EXISTS(SELECT 1 FROM public.qr_codes WHERE id=i.ice_qr_id AND pair_id=p.id AND tag_type='ice' AND is_current AND public_status='unactivated') THEN
   at_time:=clock_timestamp();
   -- Consume while the old unclaimed state still satisfies the existing binding trigger.
   UPDATE public.activation_intents SET state='consumed',consumed_at=at_time WHERE id=i.id;
   UPDATE public.pair_activation_credentials SET status='consumed',consumed_at=at_time,locked_until=NULL WHERE pair_id=p.id;
   UPDATE public.tag_pairs SET owner_user_id=actor,ownership_status='active',activated_at=at_time,
    row_version=row_version+1,updated_at=at_time WHERE id=p.id;
   UPDATE public.qr_codes SET public_status='active',updated_at=at_time WHERE id IN(i.lost_qr_id,i.ice_qr_id);
   -- Profile publication/consent rows are intentionally untouched.
   INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,safe_details)
    VALUES(actor,'customer','pair.activated','tag_pair',p.id,jsonb_build_object('outcome','success'));
   INSERT INTO public.notification_outbox(event_type,aggregate_type,aggregate_id,recipient_user_id,idempotency_key)
    VALUES('pair.activated','tag_pair',p.id,actor,'pair.activated:'||p.id::text);
   result:=jsonb_build_object('_status',201,'pair_id',p.id,'status','active','activated_at',at_time,
    'qr_codes',jsonb_build_array(jsonb_build_object('qr_id',i.lost_qr_id,'tag_type','lost'),jsonb_build_object('qr_id',i.ice_qr_id,'tag_type','ice')));
  END IF;
 END IF;
 -- Both success and ineligible decisions are stable; no private response plaintext is stored.
 INSERT INTO public.idempotency_records(actor_scope,actor_user_id,operation,idempotency_key,
  request_hash,state,response_status,expires_at)
 VALUES(actor::text,actor,'pair.activate',idem,request_digest,'completed',(result->>'_status')::integer,clock_timestamp()+interval '1 day');
 RETURN result;
END $$;

REVOKE ALL ON FUNCTION public.sr_activation_context(text),public.sr_activation_key_context(text),
 public.sr_begin_activation(text,bytea,integer),public.sr_confirm_activation(uuid,text,text),public.sr_activation_rate(text)
 FROM PUBLIC,anon,authenticated,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_activation_context(text),public.sr_activation_key_context(text),
 public.sr_begin_activation(text,bytea,integer),public.sr_confirm_activation(uuid,text,text),public.sr_activation_rate(text) TO safereturn_api;
-- Runtime callers cannot manufacture a concealed-credential intent without the verifier check.
REVOKE INSERT ON public.activation_intents FROM safereturn_api;
