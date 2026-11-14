-- Task5.7C opt-in projection only. No table grants, Auth administration or writers.
CREATE FUNCTION public.sr_staff_account_state(sid uuid,uid uuid) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE result jsonb;
BEGIN
 IF public.sr_is_staff(ARRAY['security_admin']) IS NOT TRUE OR NOT EXISTS(
 SELECT 1 FROM public.sr_account_session_state(sid) s WHERE s.email_verified AND s.mfa_active) THEN RETURN NULL; END IF;
 SELECT jsonb_build_object('status','ready','state',COALESCE(a.state,'active'),
 'revision',COALESCE(a.revision,1),'as_of',clock_timestamp()) INTO result
 FROM auth.users u LEFT JOIN public.account_security_state a ON a.user_id=u.id
 WHERE u.id=uid AND u.deleted_at IS NULL AND NOT COALESCE(u.is_anonymous,false);
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION public.sr_staff_account_state(uuid,uuid) FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_staff_account_state(uuid,uuid) TO safereturn_api;
