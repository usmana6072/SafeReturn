-- No table/RLS/index/role grant or prior helper rewrite. Never auto-apply.
CREATE FUNCTION public.sr_qr_lifecycle_history(sid uuid,pid uuid,take integer,stamp timestamptz,eid uuid)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE p public.tag_pairs; result jsonb; actor uuid:=public.sr_actor_id();
BEGIN
 IF NOT EXISTS(SELECT 1 FROM public.sr_account_session_state(sid) s WHERE s.email_verified) THEN RETURN NULL; END IF;
 SELECT * INTO p FROM public.tag_pairs WHERE id=pid AND owner_user_id=actor AND ownership_status='active'
 AND activated_at IS NOT NULL AND revoked_at IS NULL FOR SHARE;
 IF NOT FOUND THEN RETURN NULL; END IF;
 IF take IS NULL OR take NOT BETWEEN 1 AND 101 OR (stamp IS NULL)<>(eid IS NULL) THEN RAISE EXCEPTION 'Invalid history bound'; END IF;
 SELECT jsonb_build_object('pair_id',p.id,'pair_revision',p.row_version,
 'current_tags',(SELECT coalesce(jsonb_agg(jsonb_build_object('qr_id',q.id,'tag_type',q.tag_type,'public_status',q.public_status) ORDER BY q.tag_type),'[]'::jsonb)
  FROM public.qr_codes q WHERE q.pair_id=p.id AND q.is_current),
 'items',(SELECT coalesce(jsonb_agg(to_jsonb(e) ORDER BY e.occurred_at DESC,e.event_id DESC),'[]'::jsonb) FROM (
 SELECT a.id AS event_id,CASE a.action WHEN 'pair.activated' THEN 'activation_completed'
 WHEN 'qr.owner_disabled' THEN 'owner_disabled' ELSE 'owner_enabled' END AS event_type,a.occurred_at,
 CASE WHEN a.action='pair.activated' THEN NULL ELSE q.tag_type END AS tag_type,
 CASE WHEN a.action='pair.activated' THEN NULL ELSE a.safe_details->>'from_status' END AS from_status,
 CASE WHEN a.action='pair.activated' THEN NULL ELSE a.safe_details->>'to_status' END AS to_status
 FROM public.audit_events a LEFT JOIN public.qr_codes q ON a.target_type='qr' AND q.id=a.target_id AND q.pair_id=p.id AND q.is_current
 WHERE a.actor_user_id=actor AND a.occurred_at>=p.activated_at
 AND ((a.action='pair.activated' AND a.target_type='tag_pair' AND a.target_id=p.id)
 OR (a.action IN('qr.owner_disabled','qr.owner_enabled') AND q.id IS NOT NULL))
 AND (stamp IS NULL OR (a.occurred_at,a.id)<(stamp,eid))
 ORDER BY a.occurred_at DESC,a.id DESC LIMIT take) e)) INTO result;
 RETURN result;
END $$;

CREATE FUNCTION public.sr_qr_lifecycle_command(sid uuid,amr bigint,qid uuid,expected integer,wanted text,why text,scope text,digest text)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE p public.tag_pairs; q public.qr_codes; old public.idempotency_records; actor uuid:=public.sr_actor_id(); pid uuid; result jsonb;
BEGIN
 IF NOT EXISTS(SELECT 1 FROM public.sr_account_session_state(sid) s WHERE s.email_verified) THEN RETURN NULL; END IF;
 IF amr IS NULL OR amr<0 OR amr>extract(epoch FROM clock_timestamp()) OR extract(epoch FROM clock_timestamp())-amr>300 THEN RETURN jsonb_build_object('error','REAUTH_REQUIRED'); END IF;
 SELECT pair_id INTO pid FROM public.qr_codes WHERE id=qid AND is_current;
 SELECT * INTO p FROM public.tag_pairs WHERE id=pid AND owner_user_id=actor AND ownership_status='active'
 AND activated_at IS NOT NULL AND revoked_at IS NULL FOR UPDATE;
 IF NOT FOUND THEN RETURN NULL; END IF;
 PERFORM 1 FROM public.qr_codes WHERE pair_id=p.id AND is_current ORDER BY id FOR UPDATE;
 SELECT * INTO q FROM public.qr_codes WHERE id=qid AND pair_id=p.id AND is_current;
 IF NOT FOUND THEN RETURN NULL; END IF;
 IF (SELECT count(*) FROM public.qr_codes WHERE pair_id=p.id AND is_current)<>2
 OR NOT EXISTS(SELECT 1 FROM public.qr_codes WHERE pair_id=p.id AND is_current AND tag_type='lost')
 OR NOT EXISTS(SELECT 1 FROM public.qr_codes WHERE pair_id=p.id AND is_current AND tag_type='ice') THEN RETURN jsonb_build_object('error','INVALID_STATE'); END IF;
 IF q.public_status NOT IN('active','owner_disabled') THEN RETURN jsonb_build_object('error','INVALID_STATE'); END IF;
 IF scope IS NULL OR digest IS NULL OR scope !~ '^[0-9a-f]{64}$' OR digest !~ '^[0-9a-f]{64}$' THEN RAISE EXCEPTION 'Invalid command scope'; END IF;
 -- Parent lock serializes same-resource keys and shared sibling revision checks.
 SELECT * INTO old FROM public.idempotency_records WHERE actor_scope=actor::text AND actor_user_id=actor
 AND operation='qr.public_status:'||qid::text AND idempotency_key=scope FOR UPDATE;
 IF FOUND THEN
  IF old.request_hash<>digest THEN RETURN jsonb_build_object('error','IDEMPOTENCY_KEY_REUSED'); END IF;
  RETURN jsonb_build_object('receipt',jsonb_build_object('cipher',encode(old.response_body_ciphertext,'hex'),'key_version',old.response_key_version));
 END IF;
 IF expected IS NULL OR wanted IS NULL OR why IS NULL THEN RETURN jsonb_build_object('error','INVALID_STATE'); END IF;
 IF expected<>p.row_version THEN RETURN jsonb_build_object('error','VERSION_MISMATCH'); END IF;
 IF expected<1 OR expected>=2147483647 OR wanted NOT IN('active','owner_disabled') OR q.public_status=wanted
 OR (wanted='owner_disabled' AND why<>'temporary') OR (wanted='active' AND why<>'resume') THEN RETURN jsonb_build_object('error','INVALID_STATE'); END IF;
 UPDATE public.qr_codes SET public_status=wanted,updated_at=clock_timestamp() WHERE id=q.id;
 UPDATE public.tag_pairs SET row_version=row_version+1,updated_at=clock_timestamp() WHERE id=p.id;
 INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,request_id,reason,safe_details)
 VALUES(actor,'customer',CASE WHEN wanted='owner_disabled' THEN 'qr.owner_disabled' ELSE 'qr.owner_enabled' END,
 'qr',q.id,scope,'owner public availability',jsonb_build_object('from_status',q.public_status,'to_status',wanted,'version',p.row_version+1,'outcome','success'));
 result:=jsonb_build_object('pair_id',p.id,'qr_id',q.id,'tag_type',q.tag_type,'public_status',wanted,'pair_revision',p.row_version+1);
 RETURN result;
END $$;

CREATE FUNCTION public.sr_qr_lifecycle_save(sid uuid,amr bigint,qid uuid,scope text,digest text,cipher bytea,kv smallint)
RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE actor uuid:=public.sr_actor_id();
BEGIN
 IF NOT EXISTS(SELECT 1 FROM public.sr_account_session_state(sid) s WHERE s.email_verified)
 OR amr IS NULL OR amr<0 OR amr>extract(epoch FROM clock_timestamp()) OR extract(epoch FROM clock_timestamp())-amr>300 THEN RETURN false; END IF;
 IF scope IS NULL OR digest IS NULL OR scope !~ '^[0-9a-f]{64}$' OR digest !~ '^[0-9a-f]{64}$' OR kv IS NULL OR kv<1 OR cipher IS NULL OR octet_length(cipher)<32 THEN RETURN false; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.qr_codes q JOIN public.tag_pairs p ON p.id=q.pair_id
 WHERE q.id=qid AND q.is_current AND p.owner_user_id=actor AND p.ownership_status='active' AND p.revoked_at IS NULL
 AND q.public_status IN('active','owner_disabled')) THEN RETURN false; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.audit_events WHERE actor_user_id=actor AND target_type='qr' AND target_id=qid
 AND request_id=scope AND action IN('qr.owner_disabled','qr.owner_enabled')) THEN RETURN false; END IF;
 INSERT INTO public.idempotency_records(actor_scope,actor_user_id,operation,idempotency_key,request_hash,state,response_status,response_body_ciphertext,response_key_version,expires_at)
 VALUES(actor::text,actor,'qr.public_status:'||qid::text,scope,digest,'completed',200,cipher,kv,clock_timestamp()+interval '1 day');
 RETURN true;
END $$;
REVOKE ALL ON FUNCTION public.sr_qr_lifecycle_history(uuid,uuid,integer,timestamptz,uuid) FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
REVOKE ALL ON FUNCTION public.sr_qr_lifecycle_command(uuid,bigint,uuid,integer,text,text,text,text) FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
REVOKE ALL ON FUNCTION public.sr_qr_lifecycle_save(uuid,bigint,uuid,text,text,bytea,smallint) FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_qr_lifecycle_history(uuid,uuid,integer,timestamptz,uuid) TO safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_qr_lifecycle_command(uuid,bigint,uuid,integer,text,text,text,text) TO safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_qr_lifecycle_save(uuid,bigint,uuid,text,text,bytea,smallint) TO safereturn_api;
