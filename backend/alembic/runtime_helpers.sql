-- Frozen role/policy helpers for 0003. Only the trusted API/worker may execute.
CREATE ROLE safereturn_api NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE safereturn_worker NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
-- Passwords are provisioned separately into ignored environment configuration.
CREATE ROLE safereturn_api_login LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE safereturn_worker_login LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT safereturn_api TO safereturn_api_login;
GRANT safereturn_worker TO safereturn_worker_login;
DO $$ BEGIN
 EXECUTE pg_catalog.format('GRANT safereturn_api TO %I',current_user);
 EXECUTE pg_catalog.format('GRANT safereturn_worker TO %I',current_user);
END $$;
GRANT USAGE ON SCHEMA public TO safereturn_api,safereturn_worker;

CREATE FUNCTION public.sr_actor_id() RETURNS uuid LANGUAGE sql STABLE SET search_path=pg_catalog
AS $$ SELECT NULLIF(pg_catalog.current_setting('safereturn.actor_id',true),'')::uuid $$;
CREATE FUNCTION public.sr_mfa() RETURNS boolean LANGUAGE sql STABLE SET search_path=pg_catalog
AS $$ SELECT COALESCE(pg_catalog.current_setting('safereturn.mfa_verified',true)='true',false) $$;
CREATE FUNCTION public.sr_worker_id() RETURNS text LANGUAGE sql STABLE SET search_path=pg_catalog
AS $$ SELECT NULLIF(pg_catalog.current_setting('safereturn.worker_id',true),'') $$;
CREATE FUNCTION public.sr_submission_id() RETURNS uuid LANGUAGE sql STABLE SET search_path=pg_catalog
AS $$ SELECT NULLIF(pg_catalog.current_setting('safereturn.submission_id',true),'')::uuid $$;
CREATE FUNCTION public.sr_scan_binding() RETURNS text LANGUAGE sql STABLE SET search_path=pg_catalog
AS $$ SELECT NULLIF(pg_catalog.current_setting('safereturn.scan_binding',true),'') $$;

CREATE FUNCTION public.sr_is_staff(required_roles text[]) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT public.sr_mfa() AND EXISTS (SELECT 1 FROM public.staff_roles
 WHERE user_id=public.sr_actor_id() AND revoked_at IS NULL AND role=ANY(required_roles))
$$;
CREATE FUNCTION public.sr_owns_pair(pid uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS (SELECT 1 FROM public.tag_pairs WHERE id=pid AND owner_user_id=public.sr_actor_id())
$$;
CREATE FUNCTION public.sr_owns_qr(qid uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS (SELECT 1 FROM public.qr_codes q JOIN public.tag_pairs p ON p.id=q.pair_id
 WHERE q.id=qid AND p.owner_user_id=public.sr_actor_id())
$$;
CREATE FUNCTION public.sr_owns_order(oid uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS (SELECT 1 FROM public.orders WHERE id=oid AND customer_user_id=public.sr_actor_id())
$$;
CREATE FUNCTION public.sr_entitled_pair(pid uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS (SELECT 1 FROM public.order_pair_units u JOIN public.orders o ON o.id=u.order_id
 WHERE u.pair_id=pid AND u.status IN ('reserved','allocated') AND o.customer_user_id=public.sr_actor_id())
$$;
CREATE FUNCTION public.sr_can_message(mid uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS (SELECT 1 FROM public.finder_messages WHERE id=mid AND
 (recipient_owner_user_id=public.sr_actor_id() OR
  (id=public.sr_submission_id() AND submitted_at=pg_catalog.transaction_timestamp())))
$$;
CREATE FUNCTION public.sr_scan_pair(pid uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT public.sr_actor_id() IS NOT NULL AND EXISTS (
 SELECT 1 FROM public.scan_contexts s JOIN public.qr_codes q ON q.id=s.qr_code_id
 WHERE q.pair_id=pid AND s.session_binding_digest=public.sr_scan_binding()
 AND s.bound_actor_user_id=public.sr_actor_id() AND s.expires_at>pg_catalog.now())
$$;
CREATE FUNCTION public.sr_worker_print(jid uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS (SELECT 1 FROM public.durable_jobs WHERE print_job_id=jid AND job_kind='print.render'
 AND status='leased' AND lease_owner=public.sr_worker_id() AND lease_until>pg_catalog.now())
$$;
CREATE FUNCTION public.sr_worker_cleanup(kind text,rid uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS (SELECT 1 FROM public.durable_jobs WHERE job_kind='retention.cleanup'
 AND aggregate_type=kind AND aggregate_id=rid AND status='leased'
 AND lease_owner=public.sr_worker_id() AND lease_until>pg_catalog.now())
$$;
CREATE FUNCTION public.sr_worker_order(oid uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS (SELECT 1 FROM public.durable_jobs WHERE order_id=oid AND status='leased'
 AND lease_owner=public.sr_worker_id() AND lease_until>pg_catalog.now())
$$;
