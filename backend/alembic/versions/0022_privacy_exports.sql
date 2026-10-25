-- No client can provision authority. Named independent custody remains a release gate.
CREATE TABLE public.privacy_export_authorities (
 case_id uuid NOT NULL REFERENCES public.support_cases(id) ON DELETE RESTRICT,
 reviewer_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 authorized_by uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 expires_at timestamptz NOT NULL, revoked_at timestamptz,
 PRIMARY KEY(case_id,reviewer_id), CHECK(reviewer_id<>authorized_by)
);
CREATE TABLE public.privacy_exports (
 id uuid PRIMARY KEY, subject_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 case_id uuid NOT NULL REFERENCES public.support_cases(id) ON DELETE RESTRICT,
 scope text NOT NULL DEFAULT 'basic_v1' CHECK(scope='basic_v1'),
 status text NOT NULL DEFAULT 'requested' CHECK(status IN ('requested','reviewing','approved','building','ready','expired','rejected','escalated','held','retry')),
 revision integer NOT NULL DEFAULT 1 CHECK(revision>0), created_at timestamptz NOT NULL DEFAULT now(),
 manifest_id uuid NOT NULL UNIQUE, policy_version text NOT NULL DEFAULT 'basic_v1:1' CHECK(policy_version='basic_v1:1'),
 approver_id uuid REFERENCES auth.users(id) ON DELETE RESTRICT, approved_at timestamptz,
 watermark timestamptz, ready_at timestamptz, expires_at timestamptz,
 attempt integer NOT NULL DEFAULT 0 CHECK(attempt BETWEEN 0 AND 3), lease_token uuid, lease_until timestamptz,
 object_key text, key_version smallint CHECK(key_version>0), checksum text CHECK(checksum ~ '^[a-f0-9]{64}$'),
 manifest jsonb, failure_code text, snapshot_ciphertext bytea, snapshot_key_version smallint,
 CHECK(approver_id IS NULL OR approver_id<>subject_id)
);
CREATE UNIQUE INDEX sr_export_active ON public.privacy_exports(subject_id,scope)
 WHERE status IN ('requested','reviewing','approved','building','ready','held','retry');
CREATE TABLE public.privacy_export_decisions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), request_id uuid NOT NULL REFERENCES public.privacy_exports(id) ON DELETE RESTRICT,
 revision integer NOT NULL, actor_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 decision text NOT NULL CHECK(decision IN ('approve','reject','escalate')), reason_code text NOT NULL,
 manifest_id uuid NOT NULL, policy_version text NOT NULL, occurred_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(request_id,revision)
);
CREATE TRIGGER sr_export_decision_append BEFORE UPDATE OR DELETE ON public.privacy_export_decisions
 FOR EACH ROW EXECUTE FUNCTION public.sr_append_only();
CREATE TABLE public.privacy_export_grants (
 request_id uuid NOT NULL REFERENCES public.privacy_exports(id) ON DELETE RESTRICT,
 session_id uuid NOT NULL, digest text NOT NULL UNIQUE CHECK(digest ~ '^[a-f0-9]{64}$'),
 origin text NOT NULL, revision integer NOT NULL, expires_at timestamptz NOT NULL, consumed_at timestamptz,
 PRIMARY KEY(request_id,session_id)
);
ALTER TABLE public.privacy_export_authorities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.privacy_exports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.privacy_export_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.privacy_export_grants ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.privacy_export_authorities,public.privacy_exports,public.privacy_export_decisions,public.privacy_export_grants
 FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;

CREATE FUNCTION public.sr_export_authorized(cid uuid, reviewer uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT 1 FROM public.privacy_export_authorities a JOIN public.support_cases c ON c.id=a.case_id
 JOIN public.staff_roles s ON s.user_id=a.reviewer_id AND s.role='security_admin' AND s.revoked_at IS NULL
 WHERE a.case_id=cid AND a.reviewer_id=reviewer AND a.revoked_at IS NULL AND a.expires_at>now()
 AND c.case_type='privacy' AND c.status IN ('open','investigating') AND c.opened_by_user_id<>reviewer
 AND EXISTS(SELECT 1 FROM auth.users u WHERE u.id=reviewer AND u.email_confirmed_at IS NOT NULL AND u.deleted_at IS NULL AND (u.banned_until IS NULL OR u.banned_until<=now())))
$$;
CREATE FUNCTION public.sr_export_current(r public.privacy_exports) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT r.approver_id IS NOT NULL AND public.sr_export_authorized(r.case_id,r.approver_id)
 AND EXISTS(SELECT 1 FROM public.support_cases c WHERE c.id=r.case_id AND c.opened_by_user_id=r.subject_id)
 AND EXISTS(SELECT 1 FROM auth.users u WHERE u.id=r.subject_id AND u.email_confirmed_at IS NOT NULL AND u.deleted_at IS NULL AND (u.banned_until IS NULL OR u.banned_until<=now()))
 AND EXISTS(SELECT 1 FROM public.privacy_export_decisions d WHERE d.request_id=r.id AND d.actor_id=r.approver_id
 AND d.decision='approve' AND d.manifest_id=r.manifest_id AND d.policy_version=r.policy_version
 AND NOT EXISTS(SELECT 1 FROM public.privacy_export_decisions newer WHERE newer.request_id=d.request_id AND newer.revision>d.revision))
$$;
-- Recheck authorization before receipt replay under the request lock.
CREATE FUNCTION public.sr_export_preflight(rid uuid,mode text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE r public.privacy_exports;
BEGIN
 SELECT * INTO r FROM public.privacy_exports WHERE id=rid AND
 ((mode='decision' AND public.sr_is_staff(ARRAY['security_admin']) AND public.sr_export_authorized(case_id,public.sr_actor_id()))
 OR (mode='grant' AND subject_id=public.sr_actor_id())) FOR UPDATE;
 IF NOT FOUND THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
 IF mode='grant' AND (r.status<>'ready' OR r.expires_at<=now() OR NOT public.sr_export_current(r)) THEN RETURN jsonb_build_object('error','GRANT_GONE'); END IF;
 RETURN jsonb_build_object('case_id',r.case_id);
END $$;
REVOKE ALL ON FUNCTION public.sr_export_preflight(uuid,text) FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_export_preflight(uuid,text) TO safereturn_api;
-- Metadata function deliberately has no notes, subject identity, object or provider locator.
CREATE FUNCTION public.sr_export_status(r public.privacy_exports) RETURNS jsonb
LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT jsonb_build_object('request_id',r.id,'case_id',r.case_id,'status',CASE WHEN r.status='ready' AND r.expires_at<=now() THEN 'expired' ELSE r.status END,
 'revision',r.revision,'scope_version',r.scope,'manifest_version',r.policy_version,'manifest_id',r.manifest_id,
 'categories',r.manifest,'created_at',r.created_at,'ready_at',r.ready_at,'expires_at',r.expires_at)
$$;
CREATE FUNCTION public.sr_export_read(rid uuid) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE r public.privacy_exports;
BEGIN
 SELECT * INTO r FROM public.privacy_exports WHERE id=rid AND subject_id=public.sr_actor_id();
 IF NOT FOUND THEN RETURN NULL; END IF;
 RETURN public.sr_export_status(r);
END $$;
CREATE FUNCTION public.sr_export_list(lim integer, stamp timestamptz, ident uuid) RETURNS SETOF jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NOT public.sr_is_staff(ARRAY['security_admin']) OR lim NOT BETWEEN 1 AND 101 THEN RETURN; END IF;
 RETURN QUERY SELECT public.sr_export_status(r) FROM public.privacy_exports r
 WHERE public.sr_export_authorized(r.case_id,public.sr_actor_id()) AND (stamp IS NULL OR (r.created_at,r.id)<(stamp,ident))
 ORDER BY r.created_at DESC,r.id DESC LIMIT lim;
END $$;
CREATE FUNCTION public.sr_export_request(rid uuid, cid uuid, mid uuid) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE r public.privacy_exports; uid uuid:=public.sr_actor_id();
BEGIN
 IF uid IS NULL THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended(uid::text,570325));
 IF cid IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.support_cases WHERE id=cid AND opened_by_user_id=uid AND case_type='privacy' AND status IN ('open','investigating'))
 THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
 UPDATE public.privacy_exports SET status='expired',revision=revision+1 WHERE subject_id=uid AND status='ready' AND expires_at<=now();
 SELECT * INTO r FROM public.privacy_exports WHERE subject_id=uid AND status IN ('requested','reviewing','approved','building','ready','held','retry');
 IF FOUND THEN RETURN jsonb_build_object('request_id',r.id,'status',r.status,'revision',r.revision); END IF;
 IF cid IS NULL THEN cid:=gen_random_uuid(); INSERT INTO public.support_cases(id,opened_by_user_id,case_type) VALUES(cid,uid,'privacy'); END IF;
 INSERT INTO public.privacy_exports(id,subject_id,case_id,manifest_id) VALUES(rid,uid,cid,mid);
 INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id) VALUES(uid,'customer','privacy.export.requested','privacy_export',rid);
 RETURN jsonb_build_object('request_id',rid,'status','requested','revision',1);
END $$;
CREATE FUNCTION public.sr_export_decide(rid uuid,cid uuid,expected integer,choice text,why text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE r public.privacy_exports; uid uuid:=public.sr_actor_id();
BEGIN
 IF NOT public.sr_is_staff(ARRAY['security_admin']) THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
 PERFORM 1 FROM public.support_cases WHERE id=cid FOR UPDATE;
 SELECT * INTO r FROM public.privacy_exports WHERE id=rid AND case_id=cid AND public.sr_export_authorized(cid,uid) FOR UPDATE;
 IF NOT FOUND THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
 IF r.revision<>expected THEN RETURN jsonb_build_object('error','STALE_CASE'); END IF;
 IF r.subject_id=uid OR r.status NOT IN ('requested','reviewing') THEN RETURN jsonb_build_object('error','INVALID_STATE'); END IF;
 IF choice NOT IN ('approve','reject','escalate') OR why NOT IN ('scope_reviewed','scope_not_supported','identity_review_failed','requires_review') THEN RETURN jsonb_build_object('error','INVALID_REQUEST'); END IF;
 UPDATE public.privacy_exports SET status=CASE choice WHEN 'approve' THEN 'approved' WHEN 'reject' THEN 'rejected' ELSE 'escalated' END,
 revision=revision+1,approver_id=uid,approved_at=now() WHERE id=rid RETURNING * INTO r;
 INSERT INTO public.privacy_export_decisions(request_id,revision,actor_id,decision,reason_code,manifest_id,policy_version)
 VALUES(rid,r.revision,uid,choice,why,r.manifest_id,r.policy_version);
 INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,safe_details)
 VALUES(uid,'staff','privacy.export.decided','privacy_export',rid,jsonb_build_object('version',r.revision,'reason_code',why));
 RETURN public.sr_export_status(r);
END $$;
CREATE FUNCTION public.sr_export_grant(rid uuid,sid uuid,expected integer,hash text,web_origin text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE r public.privacy_exports;
BEGIN
 SELECT * INTO r FROM public.privacy_exports WHERE id=rid AND subject_id=public.sr_actor_id() FOR UPDATE;
 IF NOT FOUND THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
 IF r.revision<>expected THEN RETURN jsonb_build_object('error','STALE_CASE'); END IF;
 IF r.status<>'ready' OR r.expires_at<=now() OR NOT public.sr_export_current(r) THEN RETURN jsonb_build_object('error','GRANT_GONE'); END IF;
 INSERT INTO public.privacy_export_grants(request_id,session_id,digest,origin,revision,expires_at)
 VALUES(rid,sid,hash,web_origin,r.revision,least(r.expires_at,now()+interval '300 seconds'))
 ON CONFLICT(request_id,session_id) DO UPDATE SET digest=excluded.digest,origin=excluded.origin,revision=excluded.revision,expires_at=excluded.expires_at,consumed_at=NULL;
 INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id) VALUES(public.sr_actor_id(),'customer','privacy.export.granted','privacy_export',rid);
 RETURN jsonb_build_object('expires_in',300);
END $$;
CREATE FUNCTION public.sr_export_consume(rid uuid,sid uuid,hash text,web_origin text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE r public.privacy_exports; g public.privacy_export_grants;
BEGIN
 SELECT * INTO r FROM public.privacy_exports WHERE id=rid AND subject_id=public.sr_actor_id() FOR UPDATE;
 IF NOT FOUND THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
 SELECT * INTO g FROM public.privacy_export_grants WHERE request_id=rid AND session_id=sid FOR UPDATE;
 IF NOT FOUND OR g.digest<>hash OR g.origin<>web_origin OR g.revision<>r.revision OR g.expires_at<=now() OR g.consumed_at IS NOT NULL
 OR r.status<>'ready' OR r.expires_at<=now() OR NOT public.sr_export_current(r) THEN RETURN jsonb_build_object('error','GRANT_GONE'); END IF;
 UPDATE public.privacy_export_grants SET consumed_at=clock_timestamp() WHERE request_id=rid AND session_id=sid;
 INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id) VALUES(public.sr_actor_id(),'customer','privacy.export.consumed','privacy_export',rid);
 RETURN jsonb_build_object('object_key',r.object_key,'key_version',r.key_version,'checksum',r.checksum,'manifest_id',r.manifest_id);
END $$;
-- Workers get only this queue, never unrestricted source-table reads.
GRANT SELECT ON public.privacy_exports TO safereturn_worker;
GRANT UPDATE(status,revision,watermark,ready_at,expires_at,attempt,lease_token,lease_until,object_key,key_version,checksum,manifest,failure_code,snapshot_ciphertext,snapshot_key_version)
 ON public.privacy_exports TO safereturn_worker;
CREATE POLICY sr_export_worker ON public.privacy_exports TO safereturn_worker USING (current_setting('safereturn.worker_id',true)<>'') WITH CHECK(current_setting('safereturn.worker_id',true)<>'');
CREATE FUNCTION public.sr_export_page(rid uuid,token uuid,category text,after_id uuid) RETURNS TABLE(id uuid,value jsonb)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE r public.privacy_exports;
BEGIN
 SELECT * INTO r FROM public.privacy_exports WHERE privacy_exports.id=rid AND lease_token=token AND status='building' AND lease_until>clock_timestamp() AND public.sr_export_current(privacy_exports);
 IF NOT FOUND THEN RAISE EXCEPTION 'Export lease unavailable' USING ERRCODE='42501'; END IF;
 IF category='account' THEN RETURN QUERY SELECT p.user_id,jsonb_build_object('display_name',p.display_name,'locale',p.preferred_locale) FROM public.user_profiles p WHERE p.user_id=r.subject_id AND (after_id IS NULL OR p.user_id>after_id);
 ELSIF category='pairs' THEN RETURN QUERY SELECT p.id,jsonb_build_object('pair_id',p.id,'ownership_status',p.ownership_status,'activated_at',p.activated_at,'revoked_at',p.revoked_at) FROM public.tag_pairs p WHERE p.owner_user_id=r.subject_id AND (after_id IS NULL OR p.id>after_id) ORDER BY p.id LIMIT 100;
 ELSIF category='orders' THEN RETURN QUERY SELECT o.id,jsonb_build_object('order_id',o.id,'status',o.order_status,'total',o.total_pkr::text,'currency',o.currency_code,'placed_at',o.placed_at) FROM public.orders o WHERE o.customer_user_id=r.subject_id AND (after_id IS NULL OR o.id>after_id) ORDER BY o.id LIMIT 100;
 ELSIF category='items' THEN RETURN QUERY SELECT i.id,jsonb_build_object('item_id',i.id,'order_id',i.order_id,'product_id',i.product_id,'variant_id',i.variant_id,'quantity',i.quantity,'unit_price',i.unit_price_snapshot::text,'line_total',i.line_total::text,'currency',i.currency_code) FROM public.order_items i JOIN public.orders o ON o.id=i.order_id WHERE o.customer_user_id=r.subject_id AND (after_id IS NULL OR i.id>after_id) ORDER BY i.id LIMIT 100;
 ELSIF category='occurrences' THEN RETURN QUERY SELECT u.id,jsonb_build_object('item_id',u.order_item_id,'qr_id',u.qr_code_id,'tag_type',u.tag_type_snapshot,'copies',u.copies) FROM public.order_item_qr_uses u JOIN public.order_items i ON i.id=u.order_item_id JOIN public.orders o ON o.id=i.order_id WHERE o.customer_user_id=r.subject_id AND (after_id IS NULL OR u.id>after_id) ORDER BY u.id LIMIT 100;
 ELSIF category='payments' THEN RETURN QUERY SELECT p.id,jsonb_build_object('order_id',p.order_id,'state',p.state,'amount',p.amount::text,'currency',p.currency_code,'verified_at',p.verified_at) FROM public.payment_attempts p JOIN public.orders o ON o.id=p.order_id WHERE o.customer_user_id=r.subject_id AND (after_id IS NULL OR p.id>after_id) ORDER BY p.id LIMIT 100;
 ELSIF category='receipts' THEN RETURN QUERY SELECT m.id,jsonb_build_object('status',m.status,'received_at',m.submitted_at) FROM public.finder_messages m WHERE m.recipient_owner_user_id=r.subject_id AND (after_id IS NULL OR m.id>after_id) ORDER BY m.id LIMIT 100;
 ELSIF category='privacy_requests' THEN RETURN QUERY SELECT c.id,jsonb_build_object('request_id',c.id,'status',c.status,'created_at',c.created_at) FROM public.support_cases c WHERE c.opened_by_user_id=r.subject_id AND c.case_type='privacy' AND (after_id IS NULL OR c.id>after_id) ORDER BY c.id LIMIT 100;
 END IF;
END $$;
REVOKE ALL ON FUNCTION public.sr_export_authorized(uuid,uuid),public.sr_export_current(public.privacy_exports),public.sr_export_status(public.privacy_exports),public.sr_export_read(uuid),public.sr_export_list(integer,timestamptz,uuid),public.sr_export_request(uuid,uuid,uuid),public.sr_export_decide(uuid,uuid,integer,text,text),public.sr_export_grant(uuid,uuid,integer,text,text),public.sr_export_consume(uuid,uuid,text,text),public.sr_export_page(uuid,uuid,text,uuid)
 FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_export_read(uuid),public.sr_export_list(integer,timestamptz,uuid),public.sr_export_request(uuid,uuid,uuid),public.sr_export_decide(uuid,uuid,integer,text,text),public.sr_export_grant(uuid,uuid,integer,text,text),public.sr_export_consume(uuid,uuid,text,text) TO safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_export_current(public.privacy_exports),public.sr_export_page(uuid,uuid,text,uuid) TO safereturn_worker;
