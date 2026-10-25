-- Approved A–E Task 2.3C. No Auth table grant, index, mutation or profile access.
DO $$
BEGIN
 IF EXISTS (
  SELECT 1 FROM (VALUES ('id','uuid'),('created_at','timestamptz'),('email_confirmed_at','timestamptz'),
   ('deleted_at','timestamptz'),('is_anonymous','boolean'),('banned_until','timestamptz')) required(name,typ)
  WHERE NOT EXISTS (SELECT 1 FROM pg_catalog.pg_attribute a
   WHERE a.attrelid='auth.users'::regclass AND a.attname=required.name
   AND a.atttypid=required.typ::regtype AND a.attnum>0 AND NOT a.attisdropped)) THEN
  RAISE EXCEPTION 'Managed metadata requires reconciliation';
 END IF;
 IF EXISTS(SELECT 1 FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
  WHERE n.nspname='public' AND p.proname='sr_staff_directory') THEN
  RAISE EXCEPTION 'Existing directory helper requires reconciliation';
 END IF;
END $$;

CREATE FUNCTION public.sr_staff_directory(sid uuid,kind text,uid uuid,verified boolean,
 access_filter text,page_limit integer,cursor_at timestamptz,cursor_id uuid) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE observed timestamptz := statement_timestamp(); result jsonb;
BEGIN
 IF public.sr_is_staff(ARRAY['security_admin']) IS NOT TRUE OR NOT EXISTS(
  SELECT 1 FROM public.sr_account_session_state(sid) s WHERE s.email_verified AND s.mfa_active
 ) THEN RETURN NULL; END IF;
 IF kind IS NULL OR kind NOT IN('list','detail','count') OR page_limit IS NULL OR page_limit<1 OR page_limit>100
  OR (access_filter IS NOT NULL AND access_filter NOT IN('banned','not_banned'))
  OR ((cursor_at IS NULL)<>(cursor_id IS NULL))
  OR (kind<>'list' AND cursor_at IS NOT NULL) OR (kind='detail' AND uid IS NULL) THEN
  RAISE EXCEPTION 'Invalid directory bounds' USING ERRCODE='22023';
 END IF;
 -- Unique Auth PK defines registrations. Profiles/sessions cannot add or remove members.
 WITH matched AS NOT MATERIALIZED (
  SELECT u.id,u.created_at,(u.email_confirmed_at IS NOT NULL) AS email_verified,
   CASE WHEN u.banned_until>observed THEN 'banned' ELSE 'not_banned' END AS provider_access
  FROM auth.users u
  WHERE u.deleted_at IS NULL AND NOT COALESCE(u.is_anonymous,false)
   AND (uid IS NULL OR u.id=uid)
   AND (verified IS NULL OR (u.email_confirmed_at IS NOT NULL)=verified)
   AND (access_filter IS NULL OR CASE WHEN u.banned_until>observed THEN 'banned' ELSE 'not_banned' END=access_filter)
 ), bounded AS (
  SELECT * FROM matched WHERE kind<>'count' AND (cursor_at IS NULL OR (created_at,id)<(cursor_at,cursor_id))
  ORDER BY created_at DESC,id DESC
  LIMIT CASE WHEN kind='detail' THEN 1 ELSE page_limit+1 END
 ), counted AS (
  SELECT 1 FROM matched WHERE kind='count' LIMIT 1000
 )
 SELECT CASE WHEN kind='count' THEN (SELECT jsonb_build_object(
  'as_of',observed,'definition','retained_nonanonymous_auth_registrations_v1',
  'filters',jsonb_build_object('user_id',uid,'email_verified',verified,'provider_access',access_filter),
  'count',jsonb_build_object('value',count(*),'is_exact',count(*)<1000)) FROM counted)
 ELSE (SELECT jsonb_build_object('as_of',observed,'items',COALESCE(jsonb_agg(jsonb_build_object(
  'user_id',id,'registered_at',created_at,'email_verified',email_verified,'provider_access',provider_access)
  ORDER BY created_at DESC,id DESC),'[]'::jsonb)) FROM bounded) END INTO result;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION public.sr_staff_directory(uuid,text,uuid,boolean,text,integer,timestamptz,uuid)
 FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_staff_directory(uuid,text,uuid,boolean,text,integer,timestamptz,uuid) TO safereturn_api;
