-- BTR-01-DEV-SUPPORT-20261024 v1.1. No identity, fixtures, keys or grants seeded.
-- The NOLOGIN role is ONLY for the trusted, pinned one-account command host.
-- No membership or credential is created; runtime cannot grant or revoke roles.
DO $$ BEGIN
 IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='safereturn_support_provisioner') THEN
  CREATE ROLE safereturn_support_provisioner NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
 ELSE
  RAISE EXCEPTION 'Support command role already exists; review its privileges';
 END IF;
END $$;
GRANT USAGE ON SCHEMA public TO safereturn_support_provisioner;

CREATE TABLE public.support_dev_exception(
 change_id text PRIMARY KEY CHECK(change_id='SR-SUPPORT-DEV-84bcdd96-522d-4953-8f6c-a899dde084ba'),
 subject_id uuid NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE RESTRICT,
 grant_id uuid NOT NULL UNIQUE REFERENCES public.staff_roles(id) ON DELETE RESTRICT,
 approval_id uuid NOT NULL UNIQUE,
 packet_digest text NOT NULL CHECK(packet_digest ~ '^[a-f0-9]{64}$'),
 idempotency_key uuid NOT NULL,
 expires_at timestamptz NOT NULL CHECK(expires_at<='2026-11-07T18:59:59Z'),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 revoked_at timestamptz,
 CHECK(expires_at>created_at AND expires_at<=created_at+interval '24 hours')
);
CREATE TABLE public.support_dev_receipts(
 action text NOT NULL CHECK(action IN('grant','revoke')),
 approval_id uuid NOT NULL UNIQUE,
 idempotency_key uuid NOT NULL,
 packet_digest text NOT NULL CHECK(packet_digest ~ '^[a-f0-9]{64}$'),
 subject_id uuid NOT NULL REFERENCES public.support_dev_exception(subject_id) ON DELETE RESTRICT,
 audit_id uuid NOT NULL UNIQUE REFERENCES public.audit_events(id) ON DELETE RESTRICT,
 cipher bytea NOT NULL CHECK(octet_length(cipher)>=32),
 key_version smallint NOT NULL CHECK(key_version>0),
 PRIMARY KEY(subject_id,action), UNIQUE(subject_id,action,idempotency_key)
);
ALTER TABLE public.support_dev_exception ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.support_dev_receipts ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.support_dev_exception,public.support_dev_receipts FROM PUBLIC,anon,authenticated,service_role,safereturn_api,safereturn_worker,safereturn_support_provisioner;
CREATE TRIGGER sr_support_dev_receipt_append BEFORE UPDATE OR DELETE ON public.support_dev_receipts
 FOR EACH ROW EXECUTE FUNCTION public.sr_append_only();

CREATE FUNCTION public.sr_support_dev_immutable() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Exception history must be retained'; END IF;
 IF (NEW.change_id,NEW.subject_id,NEW.grant_id,NEW.approval_id,NEW.packet_digest,NEW.idempotency_key,NEW.expires_at,NEW.created_at)
 IS DISTINCT FROM (OLD.change_id,OLD.subject_id,OLD.grant_id,OLD.approval_id,OLD.packet_digest,OLD.idempotency_key,OLD.expires_at,OLD.created_at)
 OR OLD.revoked_at IS NOT NULL OR NEW.revoked_at IS NULL THEN RAISE EXCEPTION 'Exception is immutable except one-way revocation'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_support_dev_immutable BEFORE UPDATE OR DELETE ON public.support_dev_exception
 FOR EACH ROW EXECUTE FUNCTION public.sr_support_dev_immutable();

CREATE FUNCTION public.sr_support_dev_state(uid uuid) RETURNS text
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE e public.support_dev_exception;
BEGIN
 IF uid IS DISTINCT FROM public.sr_actor_id() THEN RETURN 'denied'; END IF;
 PERFORM pg_advisory_xact_lock_shared(public.sr_account_lock_key(uid));
 SELECT * INTO e FROM public.support_dev_exception WHERE subject_id=uid;
 IF NOT FOUND THEN RETURN 'unregistered'; END IF;
 IF e.revoked_at IS NOT NULL OR e.expires_at<=clock_timestamp()
 OR NOT EXISTS(SELECT 1 FROM public.staff_roles r WHERE r.id=e.grant_id AND r.user_id=uid AND r.role='support' AND r.revoked_at IS NULL)
 OR EXISTS(SELECT 1 FROM public.staff_roles r WHERE r.user_id=uid AND r.role<>'support' AND r.revoked_at IS NULL)
 OR NOT EXISTS(SELECT 1 FROM auth.users u WHERE u.id=uid AND u.email='usmana6072@gmail.com'
   AND u.email_confirmed_at IS NOT NULL AND u.deleted_at IS NULL AND NOT COALESCE(u.is_anonymous,false)
   AND (u.banned_until IS NULL OR u.banned_until<=clock_timestamp()))
 THEN RETURN 'inactive'; END IF;
 RETURN 'active';
END $$;
CREATE FUNCTION public.sr_support_dev_case_allowed(assigned uuid) RETURNS boolean
LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT NOT EXISTS(SELECT 1 FROM public.support_dev_exception e WHERE e.subject_id=public.sr_actor_id())
 OR (public.sr_support_dev_state(public.sr_actor_id())='active'
     AND current_setting('safereturn.support_dev_metadata',true)='true'
     AND (assigned IS NULL OR assigned=public.sr_actor_id()))
$$;
-- Add restrictive fences only; existing authorization/abuse predicates still apply.
CREATE POLICY sr_support_dev_case_fence ON public.support_cases AS RESTRICTIVE
 FOR SELECT TO safereturn_api USING(public.sr_support_dev_case_allowed(assigned_staff_id));
CREATE POLICY sr_support_dev_history_fence ON public.support_case_events AS RESTRICTIVE
 FOR SELECT TO safereturn_api USING(public.sr_support_dev_case_allowed(public.sr_actor_id()));

CREATE FUNCTION public.sr_support_dev_command(
 op text,uid uuid,sid uuid,amr bigint,approval uuid,digest text,command_key uuid,
 expiry timestamptz,approval_expiry timestamptz,authorized_at timestamptz,receipt bytea,kv smallint
) RETURNS TABLE(grant_id uuid,expires_at timestamptz,cipher bytea,key_version smallint)
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE e public.support_dev_exception;r public.support_dev_receipts;
 gid uuid;aid uuid:=gen_random_uuid();at_time timestamptz:=clock_timestamp();previous_state text;
BEGIN
 -- The trusted command login must itself be restricted, not a renamed admin key.
 IF NOT EXISTS(SELECT 1 FROM pg_catalog.pg_roles WHERE rolname=session_user
  AND rolname='safereturn_support_command' AND NOT rolsuper AND NOT rolbypassrls
  AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolreplication AND NOT rolinherit)
 OR EXISTS(SELECT 1 FROM pg_catalog.pg_auth_members m JOIN pg_catalog.pg_roles r ON r.oid=m.roleid
  JOIN pg_catalog.pg_roles member_role ON member_role.oid=m.member
  WHERE member_role.rolname=session_user AND r.rolname<>'safereturn_support_provisioner')
 THEN RAISE EXCEPTION 'COMMAND_LOGIN_NOT_RESTRICTED'; END IF;
 IF op NOT IN('grant','revoke') OR uid IS NULL OR sid IS NULL OR approval IS NULL OR command_key IS NULL
 OR digest IS NULL OR digest !~ '^[a-f0-9]{64}$' OR receipt IS NULL OR octet_length(receipt)<32 OR kv IS NULL OR kv<=0
 OR authorized_at IS NULL OR authorized_at>at_time OR approval_expiry IS NULL OR approval_expiry<=at_time
 OR approval_expiry>authorized_at+interval '24 hours'
 OR amr IS NULL OR to_timestamp(amr)>at_time OR to_timestamp(amr)<at_time-interval '300 seconds'
 THEN RAISE EXCEPTION 'INVALID_COMMAND_OR_ASSURANCE'; END IF;
 IF NOT pg_try_advisory_xact_lock(hashtextextended('account-lifecycle-custody',0))
 OR NOT pg_try_advisory_xact_lock(public.sr_account_lock_key(uid)) THEN RAISE EXCEPTION 'CONTENTION'; END IF;
 -- No general identity/session enumeration: exact subject and exact live session only.
 IF NOT EXISTS(SELECT 1 FROM auth.users u JOIN auth.sessions s ON s.user_id=u.id
 WHERE u.id=uid AND u.email='usmana6072@gmail.com' AND u.email_confirmed_at IS NOT NULL
 AND u.deleted_at IS NULL AND NOT COALESCE(u.is_anonymous,false)
 AND (u.banned_until IS NULL OR u.banned_until<=clock_timestamp())
 AND s.id=sid AND s.aal::text='aal2' AND (s.not_after IS NULL OR s.not_after>clock_timestamp())
 AND public.sr_account_epoch_allows(u.id,s.created_at)
 AND EXISTS(SELECT 1 FROM auth.mfa_factors f WHERE f.user_id=u.id AND f.status::text='verified' AND f.factor_type::text='totp'))
 THEN RAISE EXCEPTION 'LIVE_EMAIL_MFA_OR_ACCOUNT_DENIED'; END IF;
 SELECT * INTO e FROM public.support_dev_exception WHERE change_id='SR-SUPPORT-DEV-84bcdd96-522d-4953-8f6c-a899dde084ba' FOR UPDATE;
 IF e.subject_id IS NOT NULL AND e.subject_id<>uid THEN RAISE EXCEPTION 'WRONG_SUBJECT'; END IF;
 SELECT * INTO r FROM public.support_dev_receipts x WHERE x.subject_id=uid AND x.action=op;
 IF r.subject_id IS NOT NULL THEN
  IF r.idempotency_key<>command_key OR r.packet_digest<>digest OR r.approval_id<>approval THEN RAISE EXCEPTION 'REPLAY_CONFLICT'; END IF;
  IF op='grant' AND (e.revoked_at IS NOT NULL OR e.expires_at<=clock_timestamp()
    OR NOT EXISTS(SELECT 1 FROM public.staff_roles x WHERE x.id=e.grant_id AND x.revoked_at IS NULL))
   THEN RAISE EXCEPTION 'EXCEPTION_INACTIVE'; END IF;
  RETURN QUERY SELECT e.grant_id,e.expires_at,r.cipher,r.key_version; RETURN;
 END IF;
 IF op='grant' THEN
  IF e.subject_id IS NOT NULL THEN RAISE EXCEPTION 'EXCEPTION_ALREADY_CONSUMED'; END IF;
  IF expiry IS NULL OR expiry<=clock_timestamp() OR expiry>clock_timestamp()+interval '24 hours'
   OR expiry>'2026-11-07T18:59:59Z' OR approval_expiry>'2026-11-07T18:59:59Z'
   OR EXISTS(SELECT 1 FROM public.staff_roles x WHERE x.user_id=uid)
   THEN RAISE EXCEPTION 'EXPIRY_OR_EXISTING_STAFF_CONFLICT'; END IF;
  gid:=gen_random_uuid();
  previous_state:='absent';
  INSERT INTO public.staff_roles(id,user_id,role,granted_by,reason)
   VALUES(gid,uid,'support',uid,'BTR-01-DEV-SUPPORT-20261024 v1.1');
  INSERT INTO public.support_dev_exception(change_id,subject_id,grant_id,approval_id,packet_digest,idempotency_key,expires_at)
   VALUES('SR-SUPPORT-DEV-84bcdd96-522d-4953-8f6c-a899dde084ba',uid,gid,approval,digest,command_key,expiry);
 ELSE
  IF e.subject_id IS NULL OR e.revoked_at IS NOT NULL THEN RAISE EXCEPTION 'EXCEPTION_NOT_ACTIVE'; END IF;
  gid:=e.grant_id;
  previous_state:=CASE WHEN NOT EXISTS(SELECT 1 FROM public.staff_roles x WHERE x.id=gid AND x.revoked_at IS NULL)
   THEN 'revoked' WHEN e.expires_at<=clock_timestamp() THEN 'expired' ELSE 'active' END;
  UPDATE public.support_dev_exception SET revoked_at=clock_timestamp() WHERE subject_id=uid;
  UPDATE public.staff_roles SET revoked_at=clock_timestamp() WHERE id=gid AND user_id=uid AND role='support' AND revoked_at IS NULL;
 END IF;
 INSERT INTO public.audit_events(id,actor_user_id,actor_kind,action,target_type,target_id,request_id,reason,safe_details)
 VALUES(aid,uid,'staff','support.development.'||CASE WHEN op='grant' THEN 'granted' ELSE 'revoked' END,
 'staff_role',gid,'SR-SUPPORT-DEV-84bcdd96-522d-4953-8f6c-a899dde084ba','development_support_exception',
 jsonb_build_object('from_status',previous_state,
 'to_status',CASE WHEN op='grant' THEN 'active' ELSE 'revoked' END,'event_id',aid::text,'outcome','committed'));
 INSERT INTO public.support_dev_receipts(action,approval_id,idempotency_key,packet_digest,subject_id,audit_id,cipher,key_version)
 VALUES(op,approval,command_key,digest,uid,aid,receipt,kv);
 RETURN QUERY SELECT x.grant_id,x.expires_at,receipt,kv FROM public.support_dev_exception x WHERE x.subject_id=uid;
END $$;

CREATE FUNCTION public.sr_support_dev_grant(uid uuid,sid uuid,amr bigint,approval uuid,digest text,command_key uuid,
 expiry timestamptz,approval_expiry timestamptz,authorized_at timestamptz,receipt bytea,kv smallint)
RETURNS TABLE(grant_id uuid,expires_at timestamptz,cipher bytea,key_version smallint)
LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT * FROM public.sr_support_dev_command('grant',uid,sid,amr,approval,digest,command_key,expiry,approval_expiry,authorized_at,receipt,kv)
$$;
CREATE FUNCTION public.sr_support_dev_revoke(uid uuid,sid uuid,amr bigint,approval uuid,digest text,command_key uuid,
 expiry timestamptz,approval_expiry timestamptz,authorized_at timestamptz,receipt bytea,kv smallint)
RETURNS TABLE(grant_id uuid,expires_at timestamptz,cipher bytea,key_version smallint)
LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT * FROM public.sr_support_dev_command('revoke',uid,sid,amr,approval,digest,command_key,expiry,approval_expiry,authorized_at,receipt,kv)
$$;
REVOKE ALL ON FUNCTION public.sr_support_dev_immutable(),public.sr_support_dev_state(uuid),public.sr_support_dev_case_allowed(uuid),
 public.sr_support_dev_command(text,uuid,uuid,bigint,uuid,text,uuid,timestamptz,timestamptz,timestamptz,bytea,smallint),
 public.sr_support_dev_grant(uuid,uuid,bigint,uuid,text,uuid,timestamptz,timestamptz,timestamptz,bytea,smallint),
 public.sr_support_dev_revoke(uuid,uuid,bigint,uuid,text,uuid,timestamptz,timestamptz,timestamptz,bytea,smallint)
 FROM PUBLIC,anon,authenticated,service_role,safereturn_api,safereturn_worker,safereturn_support_provisioner;
GRANT EXECUTE ON FUNCTION public.sr_support_dev_state(uuid),public.sr_support_dev_case_allowed(uuid) TO safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_support_dev_grant(uuid,uuid,bigint,uuid,text,uuid,timestamptz,timestamptz,timestamptz,bytea,smallint),
 public.sr_support_dev_revoke(uuid,uuid,bigint,uuid,text,uuid,timestamptz,timestamptz,timestamptz,bytea,smallint) TO safereturn_support_provisioner;
