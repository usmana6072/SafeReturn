ALTER TABLE public.staff_roles DROP CONSTRAINT ck_staff_roles_role;
ALTER TABLE public.staff_roles ADD CONSTRAINT ck_staff_roles_role
 CHECK(role IN ('owner','support','operations','finance','security_admin','superadmin'));

-- The owner inherits staff authorization. MFA, recent authentication, account
-- verification, case assignment, financial rules and independent approvals remain.
CREATE OR REPLACE FUNCTION public.sr_is_staff(required_roles text[]) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT public.sr_mfa() AND EXISTS(SELECT 1 FROM public.staff_roles
 WHERE user_id=public.sr_actor_id() AND revoked_at IS NULL
   AND (role=ANY(required_roles) OR (role='owner' AND cardinality(required_roles)>0)));
$$;

-- A few authorization/approval helpers explicitly lock or check role records
-- instead of using sr_is_staff. Extend those same checks to owner while keeping
-- the existing locks and all other eligibility predicates and ACLs intact.
DO $migration$
DECLARE f record; definition text; updated text; role_name text;
BEGIN
 FOR f IN SELECT oid FROM pg_proc WHERE pronamespace='public'::regnamespace
   AND prokind='f' AND proname LIKE 'sr_%' AND proname<>'sr_is_staff'
   AND proname NOT LIKE 'sr_support_dev_%'
 LOOP
  SELECT pg_get_functiondef(f.oid) INTO definition;
  IF position('public.staff_roles' IN definition)=0 THEN CONTINUE; END IF;
  updated:=definition;
  FOREACH role_name IN ARRAY ARRAY['operations','finance','support','security_admin','superadmin'] LOOP
   updated:=replace(updated,'role='||quote_literal(role_name),
     'role IN ('||quote_literal(role_name)||',''owner'')');
  END LOOP;
  updated:=replace(updated,'role=ANY(roles)','(role=ANY(roles) OR role=''owner'')');
  IF updated<>definition THEN EXECUTE updated; END IF;
 END LOOP;
END $migration$;

-- This migration intentionally inserts no staff_roles records.
