-- Task2.3D approved A–F. Offline only; no managed Auth writes or general SELECT grant.
DO $$ BEGIN
 IF NOT EXISTS(SELECT 1 FROM pg_catalog.pg_attribute WHERE attrelid='auth.sessions'::regclass
  AND attname='created_at' AND atttypid='timestamptz'::regtype AND attnum>0 AND NOT attisdropped) THEN
  RAISE EXCEPTION 'Session creation metadata requires reconciliation';
 END IF;
END $$;
CREATE TABLE public.account_security_state(
 user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE RESTRICT,
 state text NOT NULL CHECK(state IN('active','suspended')),revision integer NOT NULL CHECK(revision BETWEEN 2 AND 2147483647),
 invalidate_before timestamptz,case_id uuid NOT NULL REFERENCES public.support_cases(id) ON DELETE RESTRICT,
 updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE public.account_case_bindings(
 case_id uuid PRIMARY KEY REFERENCES public.support_cases(id) ON DELETE RESTRICT,
 subject_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 provisioned_by uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),revoked_at timestamptz,
 UNIQUE(case_id,subject_id)
);
CREATE TABLE public.security_custodians(
 user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE RESTRICT,
 verified_by uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT CHECK(verified_by<>user_id),
 evidence_id uuid NOT NULL,verified_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 expires_at timestamptz NOT NULL CHECK(expires_at>verified_at),revoked_at timestamptz
);
CREATE TABLE public.account_action_approvals(
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),case_id uuid NOT NULL,subject_id uuid NOT NULL,
 executor_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT CHECK(executor_id<>subject_id),
 approver_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT CHECK(approver_id<>executor_id AND approver_id<>subject_id),
 action text NOT NULL CHECK(action IN('suspend','restore','recovery_escalated')),
 reason_code text NOT NULL,expected_revision integer NOT NULL CHECK(expected_revision BETWEEN 1 AND 2147483646),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),expires_at timestamptz NOT NULL CHECK(expires_at>created_at),
 revoked_at timestamptz,consumed_at timestamptz,
 FOREIGN KEY(case_id,subject_id) REFERENCES public.account_case_bindings(case_id,subject_id) ON DELETE RESTRICT,
 CHECK((action='suspend' AND reason_code IN('suspected_compromise','abuse_review','security_review')) OR
       (action='restore' AND reason_code='review_cleared') OR
       (action='recovery_escalated' AND reason_code IN('factor_loss','account_access_review')))
);
CREATE UNIQUE INDEX uq_account_unused_approval ON public.account_action_approvals(case_id,subject_id,executor_id,action,reason_code,expected_revision) WHERE revoked_at IS NULL AND consumed_at IS NULL;
CREATE TABLE public.account_security_events(
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 case_id uuid NOT NULL REFERENCES public.account_case_bindings(case_id) ON DELETE RESTRICT,
 approval_id uuid NOT NULL UNIQUE REFERENCES public.account_action_approvals(id) ON DELETE RESTRICT,
 actor_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,action text NOT NULL,
 reason_code text NOT NULL,revision integer NOT NULL,from_state text NOT NULL,to_state text NOT NULL,
 occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),UNIQUE(user_id,revision)
);
CREATE TABLE public.account_lifecycle_receipts(
 scope text PRIMARY KEY CHECK(scope ~ '^[a-f0-9]{64}$'),request_hash text NOT NULL CHECK(request_hash ~ '^[a-f0-9]{64}$'),
 actor_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 approval_id uuid NOT NULL UNIQUE REFERENCES public.account_action_approvals(id) ON DELETE RESTRICT,
 event_id uuid NOT NULL UNIQUE REFERENCES public.account_security_events(id) ON DELETE RESTRICT,
 cipher bytea NOT NULL,key_version smallint NOT NULL CHECK(key_version>0)
);
DO $$ DECLARE relation text; BEGIN
 FOREACH relation IN ARRAY ARRAY['account_security_state','account_case_bindings','security_custodians','account_action_approvals','account_security_events','account_lifecycle_receipts'] LOOP
  EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',relation);
  EXECUTE format('REVOKE ALL ON public.%I FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker',relation);
 END LOOP;
 FOREACH relation IN ARRAY ARRAY['account_security_events','account_lifecycle_receipts'] LOOP
  EXECUTE format('CREATE TRIGGER sr_account_append BEFORE UPDATE OR DELETE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.sr_append_only()',relation);
 END LOOP;
END $$;
-- Shared locks serialize protected requests/worker admission with exclusive target changes.
-- Hash collisions only add contention; namespace is shared consistently by all helpers.
CREATE FUNCTION public.sr_account_lock_key(uid uuid) RETURNS bigint LANGUAGE sql IMMUTABLE SET search_path=pg_catalog
AS $$ SELECT hashtextextended('account-security:'||uid::text,0) $$;
CREATE FUNCTION public.sr_account_epoch_allows(uid uuid,issued_at timestamptz) RETURNS boolean
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE allowed boolean;
BEGIN
 IF uid IS NULL THEN RETURN false; END IF;
 PERFORM pg_advisory_xact_lock_shared(public.sr_account_lock_key(uid));
 SELECT EXISTS(SELECT 1 FROM auth.users u LEFT JOIN public.account_security_state a ON a.user_id=u.id
 WHERE u.id=uid AND u.email_confirmed_at IS NOT NULL AND u.deleted_at IS NULL AND NOT COALESCE(u.is_anonymous,false)
 AND (u.banned_until IS NULL OR u.banned_until<=clock_timestamp()) AND COALESCE(a.state,'active')='active'
 AND (a.invalidate_before IS NULL OR issued_at>a.invalidate_before)) INTO allowed;
 RETURN allowed;
END $$;
-- Existing signature preserved; original 0005 migration is never edited.
CREATE OR REPLACE FUNCTION public.sr_account_session_state(sid uuid)
RETURNS TABLE(email_verified boolean,mfa_active boolean)
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 PERFORM pg_advisory_xact_lock_shared(public.sr_account_lock_key(public.sr_actor_id()));
 RETURN QUERY SELECT u.email_confirmed_at IS NOT NULL,s.aal::text='aal2'
 FROM auth.users u JOIN auth.sessions s ON s.user_id=u.id
 LEFT JOIN public.account_security_state a ON a.user_id=u.id
 WHERE u.id=public.sr_actor_id() AND s.id=sid AND u.deleted_at IS NULL AND NOT COALESCE(u.is_anonymous,false)
 AND (u.banned_until IS NULL OR u.banned_until<=clock_timestamp())
 AND (s.not_after IS NULL OR s.not_after>clock_timestamp())
 AND COALESCE(a.state,'active')='active' AND (a.invalidate_before IS NULL OR s.created_at>a.invalidate_before);
END $$;
CREATE FUNCTION public.sr_lifecycle_custodian(uid uuid) RETURNS boolean
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE c public.security_custodians;
BEGIN
 SELECT * INTO c FROM public.security_custodians WHERE user_id=uid AND revoked_at IS NULL AND expires_at>clock_timestamp() FOR SHARE;
 IF NOT FOUND THEN RETURN false; END IF;
 RETURN public.sr_account_epoch_allows(uid,c.verified_at) AND EXISTS(
  SELECT 1 FROM public.staff_roles WHERE user_id=uid AND role='security_admin' AND revoked_at IS NULL);
END $$;
CREATE FUNCTION public.sr_lifecycle_context(sid uuid,amr bigint,uid uuid,cid uuid,op text,expected integer,why text,receipt_scope text,digest text)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a public.account_action_approvals;r public.account_lifecycle_receipts;current_revision integer;locked_roles integer;actor uuid:=public.sr_actor_id();
BEGIN
 IF NOT public.sr_is_staff(ARRAY['security_admin']) OR NOT EXISTS(SELECT 1 FROM public.sr_account_session_state(sid) s WHERE s.email_verified AND s.mfa_active) THEN RETURN NULL; END IF;
 IF amr IS NULL OR to_timestamp(amr)>clock_timestamp() OR to_timestamp(amr)<clock_timestamp()-interval '300 seconds' THEN RETURN jsonb_build_object('error','REAUTH_REQUIRED'); END IF;
 IF actor=uid OR uid IS NULL OR NOT EXISTS(SELECT 1 FROM auth.users WHERE id=uid AND deleted_at IS NULL AND NOT COALESCE(is_anonymous,false)) THEN RETURN NULL; END IF;
 IF NOT pg_try_advisory_xact_lock(hashtextextended('account-lifecycle-custody',0)) THEN RETURN jsonb_build_object('error','CONTENTION'); END IF;
 IF NOT pg_try_advisory_xact_lock(public.sr_account_lock_key(uid)) THEN RETURN jsonb_build_object('error','CONTENTION'); END IF;
 PERFORM 1 FROM public.support_cases WHERE id=cid AND status IN('open','investigating') FOR SHARE;
 IF NOT FOUND THEN RETURN NULL; END IF;
 PERFORM 1 FROM public.account_case_bindings WHERE case_id=cid AND subject_id=uid AND revoked_at IS NULL FOR SHARE;
 IF NOT FOUND THEN RETURN NULL; END IF;
 SELECT * INTO r FROM public.account_lifecycle_receipts WHERE scope=receipt_scope AND actor_id=actor;
 IF r.scope IS NOT NULL AND r.request_hash<>digest THEN RETURN jsonb_build_object('error','IDEMPOTENCY_KEY_REUSED'); END IF;
 SELECT * INTO a FROM public.account_action_approvals WHERE case_id=cid AND subject_id=uid AND executor_id=actor
 AND action=op AND reason_code=why AND expected_revision=expected AND revoked_at IS NULL AND expires_at>clock_timestamp()
 AND ((r.scope IS NULL AND consumed_at IS NULL AND NOT EXISTS(SELECT 1 FROM public.account_security_state st WHERE st.user_id=uid AND created_at<=st.updated_at)) OR (r.scope IS NOT NULL AND id=r.approval_id)) FOR UPDATE;
 IF NOT FOUND OR a.approver_id IN(actor,uid) OR NOT public.sr_lifecycle_custodian(a.approver_id)
 OR NOT public.sr_account_epoch_allows(actor,a.created_at) OR NOT public.sr_account_epoch_allows(a.approver_id,a.created_at) THEN RETURN NULL; END IF;
 PERFORM 1 FROM public.staff_roles WHERE user_id IN(actor,a.approver_id) AND role='security_admin' AND revoked_at IS NULL FOR SHARE;
 GET DIAGNOSTICS locked_roles=ROW_COUNT;
 IF locked_roles<>2 OR NOT public.sr_lifecycle_custodian(a.approver_id) THEN RETURN NULL; END IF;
 IF r.scope IS NOT NULL THEN RETURN jsonb_build_object('approval_id',a.id,'receipt',jsonb_build_object('cipher',encode(r.cipher,'hex'),'key_version',r.key_version)); END IF;
 SELECT COALESCE((SELECT revision FROM public.account_security_state WHERE user_id=uid),1) INTO current_revision;
 IF current_revision<>expected THEN RETURN jsonb_build_object('error','STALE_VERSION'); END IF;
 RETURN jsonb_build_object('approval_id',a.id,'receipt',NULL);
END $$;
CREATE FUNCTION public.sr_lifecycle_apply(sid uuid,amr bigint,uid uuid,cid uuid,op text,expected integer,why text,receipt_scope text,digest text)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE snapshot jsonb;old_state text;next_state text;epoch timestamptz;observed timestamptz;eid uuid:=gen_random_uuid();aid uuid;
BEGIN
 snapshot:=public.sr_lifecycle_context(sid,amr,uid,cid,op,expected,why,receipt_scope,digest);
 IF snapshot IS NULL OR snapshot ? 'error' THEN RETURN snapshot; END IF;
 IF snapshot->'receipt'<>'null'::jsonb THEN RETURN jsonb_build_object('error','INVALID_STATE'); END IF;
 aid:=(snapshot->>'approval_id')::uuid;
 SELECT state,invalidate_before INTO old_state,epoch FROM public.account_security_state WHERE user_id=uid FOR UPDATE;
 old_state:=COALESCE(old_state,'active');next_state:=old_state;
 IF (op='suspend' AND old_state='suspended') OR (op='restore' AND old_state='active') THEN RETURN jsonb_build_object('error','INVALID_STATE'); END IF;
 IF op='suspend' AND NOT EXISTS(SELECT 1 FROM public.security_custodians c WHERE c.user_id<>uid AND public.sr_lifecycle_custodian(c.user_id)) THEN RETURN jsonb_build_object('error','LAST_CUSTODIAN'); END IF;
 observed:=clock_timestamp();
 IF op IN('suspend','restore') THEN next_state:=CASE op WHEN 'suspend' THEN 'suspended' ELSE 'active' END;epoch:=observed; END IF;
 INSERT INTO public.account_security_state(user_id,state,revision,invalidate_before,case_id,updated_at)
 VALUES(uid,next_state,expected+1,epoch,cid,observed)
 ON CONFLICT(user_id) DO UPDATE SET state=excluded.state,revision=excluded.revision,invalidate_before=excluded.invalidate_before,case_id=excluded.case_id,updated_at=excluded.updated_at;
 INSERT INTO public.account_security_events(id,user_id,case_id,approval_id,actor_id,action,reason_code,revision,from_state,to_state,occurred_at)
 VALUES(eid,uid,cid,aid,public.sr_actor_id(),op,why,expected+1,old_state,next_state,observed);
 UPDATE public.account_action_approvals SET consumed_at=observed WHERE id=aid;
 INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,safe_details)
 VALUES(public.sr_actor_id(),'staff','account.security.'||op,'account_security_event',eid,
 jsonb_build_object('from_status',old_state,'to_status',next_state,'reason_code',why,'version',expected+1,'event_id',eid));
 IF op='recovery_escalated' THEN RETURN jsonb_build_object('user_id',uid,'case_id',cid,'action',op,'revision',expected+1,'event_id',eid,'occurred_at',observed,'status','referred'); END IF;
 RETURN jsonb_build_object('user_id',uid,'case_id',cid,'action',op,'revision',expected+1,'event_id',eid,'occurred_at',observed,'state',next_state,'fresh_sign_in_required',true);
END $$;
CREATE FUNCTION public.sr_lifecycle_save_receipt(receipt_scope text,digest text,aid uuid,eid uuid,encrypted bytea,version smallint)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NOT public.sr_is_staff(ARRAY['security_admin']) OR NOT EXISTS(SELECT 1 FROM public.account_security_events e JOIN public.account_action_approvals a ON a.id=e.approval_id
 WHERE e.id=eid AND e.actor_id=public.sr_actor_id() AND a.id=aid AND a.consumed_at IS NOT NULL AND a.revoked_at IS NULL) THEN RETURN false; END IF;
 INSERT INTO public.account_lifecycle_receipts(scope,request_hash,actor_id,approval_id,event_id,cipher,key_version)
 VALUES(receipt_scope,digest,public.sr_actor_id(),aid,eid,encrypted,version);RETURN true;
END $$;
-- No runtime approval/custody provisioner. Controlled operators must hold the same
-- global lifecycle lock and subject try-lock protocol when granting/revoking evidence.
DO $$ DECLARE fn record; BEGIN
 FOR fn IN SELECT p.oid::regprocedure AS signature FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
 WHERE n.nspname='public' AND p.proname IN('sr_account_lock_key','sr_account_epoch_allows','sr_account_session_state','sr_lifecycle_custodian','sr_lifecycle_context','sr_lifecycle_apply','sr_lifecycle_save_receipt') LOOP
  EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker',fn.signature);
 END LOOP;
END $$;
GRANT EXECUTE ON FUNCTION public.sr_account_session_state(uuid),public.sr_lifecycle_context(uuid,bigint,uuid,uuid,text,integer,text,text,text),public.sr_lifecycle_apply(uuid,bigint,uuid,uuid,text,integer,text,text,text),public.sr_lifecycle_save_receipt(text,text,uuid,uuid,bytea,smallint) TO safereturn_api;
-- Staff print grants have creation timestamps. Old grants remain stored but unusable.
ALTER POLICY sr_print_grant_select ON public.print_download_grants USING(granted_to=public.sr_actor_id() AND public.sr_is_staff(ARRAY['operations']) AND public.sr_account_epoch_allows(granted_to,created_at));
ALTER POLICY sr_print_grant_insert ON public.print_download_grants WITH CHECK(granted_to=public.sr_actor_id() AND public.sr_is_staff(ARRAY['operations']) AND expires_at<=clock_timestamp()+interval '5 minutes' AND public.sr_account_epoch_allows(granted_to,created_at));
ALTER POLICY sr_print_grant_use ON public.print_download_grants USING(granted_to=public.sr_actor_id() AND public.sr_is_staff(ARRAY['operations']) AND used_at IS NULL AND expires_at>clock_timestamp() AND public.sr_account_epoch_allows(granted_to,created_at)) WITH CHECK(granted_to=public.sr_actor_id() AND public.sr_is_staff(ARRAY['operations']) AND public.sr_account_epoch_allows(granted_to,created_at));
GRANT EXECUTE ON FUNCTION public.sr_account_epoch_allows(uuid,timestamptz) TO safereturn_api,safereturn_worker;
-- Preserve function OIDs/signatures: existing callers and cached dependencies
-- must not retain an unguarded renamed implementation.
CREATE OR REPLACE FUNCTION public.sr_export_authorized(cid uuid, reviewer uuid) RETURNS boolean
LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT 1 FROM public.privacy_export_authorities a JOIN public.support_cases c ON c.id=a.case_id
 JOIN public.staff_roles s ON s.user_id=a.reviewer_id AND s.role='security_admin' AND s.revoked_at IS NULL
 WHERE a.case_id=cid AND a.reviewer_id=reviewer AND a.revoked_at IS NULL AND a.expires_at>now()
 AND c.case_type='privacy' AND c.status IN ('open','investigating') AND c.opened_by_user_id<>reviewer
 AND EXISTS(SELECT 1 FROM auth.users u WHERE u.id=reviewer AND u.email_confirmed_at IS NOT NULL AND u.deleted_at IS NULL AND (u.banned_until IS NULL OR u.banned_until<=now()))
 AND public.sr_account_epoch_allows(reviewer,NULL) AND public.sr_account_epoch_allows(a.authorized_by,NULL))
$$;
-- Authority rows lack issuance timestamps: after either principal invalidation,
-- deny this old authority; no guessed issuance time or automatic reapproval.
CREATE OR REPLACE FUNCTION public.sr_export_current(r public.privacy_exports) RETURNS boolean
LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT r.approver_id IS NOT NULL AND public.sr_export_authorized(r.case_id,r.approver_id)
 AND EXISTS(SELECT 1 FROM public.support_cases c WHERE c.id=r.case_id AND c.opened_by_user_id=r.subject_id)
 AND EXISTS(SELECT 1 FROM auth.users u WHERE u.id=r.subject_id AND u.email_confirmed_at IS NOT NULL AND u.deleted_at IS NULL AND (u.banned_until IS NULL OR u.banned_until<=now()))
 AND EXISTS(SELECT 1 FROM public.privacy_export_decisions d WHERE d.request_id=r.id AND d.actor_id=r.approver_id
 AND d.decision='approve' AND d.manifest_id=r.manifest_id AND d.policy_version=r.policy_version
 AND NOT EXISTS(SELECT 1 FROM public.privacy_export_decisions newer WHERE newer.request_id=d.request_id AND newer.revision>d.revision))
 AND public.sr_account_epoch_allows(r.subject_id,r.created_at) AND public.sr_account_epoch_allows(r.approver_id,r.approved_at)
$$;
-- Worker RLS applies the same subject/approval epoch to claim/snapshot/complete.
-- Stored request/approval/grant/completed history is never removed or reset.
ALTER POLICY sr_export_worker ON public.privacy_exports USING(current_setting('safereturn.worker_id',true)<>'' AND public.sr_export_current(privacy_exports)) WITH CHECK(current_setting('safereturn.worker_id',true)<>'' AND public.sr_export_current(privacy_exports));
CREATE OR REPLACE FUNCTION public.sr_mfg_authorized(bid uuid) RETURNS boolean
LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT 1 FROM public.manufacturing_approvals a JOIN public.manufacturing_sources s ON s.batch_id=a.batch_id
 WHERE a.batch_id=bid AND a.revoked_at IS NULL AND a.executor<>a.approver
 AND a.manifest_sha256=s.manifest_sha256 AND a.printer_key_fingerprint=s.printer_key_fingerprint
 AND EXISTS(SELECT 1 FROM public.staff_roles WHERE user_id=a.executor AND role='operations' AND revoked_at IS NULL)
 AND EXISTS(SELECT 1 FROM public.staff_roles WHERE user_id=a.approver AND role='security_admin' AND revoked_at IS NULL)
 AND public.sr_account_epoch_allows(a.executor,a.created_at) AND public.sr_account_epoch_allows(a.approver,a.created_at)
 AND NOT EXISTS(SELECT 1 FROM public.manufacturing_exports j WHERE j.batch_id=bid AND (NOT public.sr_account_epoch_allows(a.executor,j.created_at) OR NOT public.sr_account_epoch_allows(a.approver,j.created_at))))
$$;
-- Claim/finish/context/download/handoff already call sr_mfg_authorized. Both
-- authority principals now hold shared transaction locks through admission.
REVOKE ALL ON FUNCTION public.sr_export_authorized(uuid,uuid),public.sr_export_current(public.privacy_exports),public.sr_mfg_authorized(uuid) FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_export_current(public.privacy_exports) TO safereturn_worker;

-- Financial case grants have created_at; preserved history is denied after
-- finance recipient/provisioner invalidation without rewriting any grant or role.
CREATE OR REPLACE FUNCTION public.sr_financial_case_context(cid uuid,deciding boolean,reference uuid) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE uid uuid:=public.sr_actor_id(); b public.financial_case_bindings; c public.support_cases;
 o public.orders; a public.payment_attempts; g public.financial_case_authorities; review jsonb; verifiers jsonb;
BEGIN
 IF NOT public.sr_is_staff(ARRAY['finance']) OR NOT EXISTS(SELECT 1 FROM public.financial_case_authorities
   WHERE case_id=cid AND finance_user_id=uid AND can_review AND revoked_at IS NULL AND public.sr_account_epoch_allows(finance_user_id,created_at) AND public.sr_account_epoch_allows(provisioned_by,created_at)) THEN RETURN NULL; END IF;
 SELECT * INTO b FROM public.financial_case_bindings WHERE case_id=cid;
 IF NOT FOUND THEN RETURN NULL; END IF;
 SELECT * INTO o FROM public.orders WHERE id=b.order_id FOR UPDATE;
 PERFORM 1 FROM public.payment_attempts WHERE order_id=o.id ORDER BY id FOR UPDATE;
 PERFORM 1 FROM public.order_pair_units WHERE order_id=o.id ORDER BY id FOR UPDATE;
 PERFORM 1 FROM public.tag_pairs WHERE id IN(SELECT pair_id FROM public.order_pair_units WHERE order_id=o.id) ORDER BY id FOR UPDATE;
 SELECT * INTO c FROM public.support_cases WHERE id=cid FOR UPDATE;
 SELECT * INTO g FROM public.financial_case_authorities WHERE case_id=cid AND finance_user_id=uid AND can_review AND revoked_at IS NULL AND public.sr_account_epoch_allows(finance_user_id,created_at) AND public.sr_account_epoch_allows(provisioned_by,created_at) FOR UPDATE;
 IF NOT FOUND OR c.case_type<>'payment' OR c.order_id IS DISTINCT FROM b.order_id OR
  (c.pair_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.order_pair_units WHERE order_id=o.id AND pair_id=c.pair_id)) THEN RETURN NULL; END IF;
 SELECT * INTO a FROM public.payment_attempts WHERE id=b.attempt_id AND order_id=o.id;
 IF NOT FOUND THEN RETURN NULL; END IF;
 SELECT COALESCE(jsonb_agg(DISTINCT reviewed_by),'[]'::jsonb) INTO verifiers FROM public.payment_reviews WHERE attempt_id=a.id AND decision='verify' AND bank_verified;
 IF deciding AND (NOT g.can_decide OR g.provisioned_by=uid OR verifiers ? uid::text) THEN RETURN NULL; END IF;
 IF reference IS NOT NULL THEN
  SELECT jsonb_build_object('id',id,'decision',decision,'bank_verified',bank_verified) INTO review FROM public.payment_reviews WHERE id=reference AND attempt_id=a.id;
 END IF;
 RETURN jsonb_build_object('case',jsonb_build_object('id',c.id,'type',c.case_type,'status',c.status,'revision',c.case_revision),
  'order',jsonb_build_object('id',o.id,'revision',o.revision,'payment_status',o.payment_status,'amount',o.total_pkr::text,'currency',o.currency_code),
  'attempt',jsonb_build_object('id',a.id,'state',a.state,'amount',a.amount::text,'currency',a.currency_code,'verified_at',a.verified_at),
  'authority',jsonb_build_object('can_review',g.can_review,'can_decide',g.can_decide,'provisioned_by',g.provisioned_by,'revoked',false),
  'verified_reviewers',verifiers,'review_reference',review,'fence_active',NOT public.sr_financial_order_clear(o.id),
  'shipments',COALESCE((SELECT jsonb_agg(jsonb_build_object('id',id,'status',status,'dispatched_at',dispatched_at) ORDER BY id) FROM public.shipments WHERE order_id=o.id),'[]'::jsonb),
  'has_active_hold',EXISTS(SELECT 1 FROM public.retention_holds h WHERE h.released_at IS NULL AND (
    (h.resource_type='order' AND h.resource_id=o.id) OR (h.resource_type='payment_evidence' AND EXISTS(SELECT 1 FROM public.payment_evidence e WHERE e.id=h.resource_id AND e.attempt_id=a.id)) OR
    (h.resource_type='print_artifact' AND EXISTS(SELECT 1 FROM public.print_artifacts ar JOIN public.print_jobs j ON j.id=ar.print_job_id WHERE ar.id=h.resource_id AND j.order_id=o.id)))));
END $$;

-- Fence old subject requests before decision/replay, not just at download.
CREATE OR REPLACE FUNCTION public.sr_export_preflight(rid uuid,mode text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE r public.privacy_exports;
BEGIN
 SELECT * INTO r FROM public.privacy_exports WHERE id=rid AND
 public.sr_account_epoch_allows(subject_id,created_at) AND ((mode='decision' AND public.sr_is_staff(ARRAY['security_admin']) AND public.sr_export_authorized(case_id,public.sr_actor_id()))
 OR (mode='grant' AND subject_id=public.sr_actor_id())) FOR UPDATE;
 IF NOT FOUND THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
 IF mode='grant' AND (r.status<>'ready' OR r.expires_at<=now() OR NOT public.sr_export_current(r)) THEN RETURN jsonb_build_object('error','GRANT_GONE'); END IF;
 RETURN jsonb_build_object('case_id',r.case_id);
END $$;

-- Fence old subject requests before decision/replay, not just at download.
CREATE OR REPLACE FUNCTION public.sr_export_decide(rid uuid,cid uuid,expected integer,choice text,why text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE r public.privacy_exports; uid uuid:=public.sr_actor_id();
BEGIN
 IF NOT public.sr_is_staff(ARRAY['security_admin']) THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
 PERFORM 1 FROM public.support_cases WHERE id=cid FOR UPDATE;
 SELECT * INTO r FROM public.privacy_exports WHERE id=rid AND case_id=cid AND public.sr_account_epoch_allows(subject_id,created_at) AND public.sr_export_authorized(cid,uid) FOR UPDATE;
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
