"""Scoped support revisions and append-only encrypted case history; no erasure powers."""

from alembic import op

revision = "0021_support_case_console"
down_revision = "0020_notification_operations"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='5s'")
    op.execute("""
ALTER TABLE public.support_cases
 ADD COLUMN case_revision integer NOT NULL DEFAULT 1 CHECK(case_revision>0),
 ADD COLUMN priority varchar(10) NOT NULL DEFAULT 'normal' CHECK(priority IN ('low','normal','high','urgent')),
 ADD COLUMN description_format smallint NOT NULL DEFAULT 0 CHECK(description_format IN (0,1));
CREATE TABLE public.support_case_events (
 id uuid PRIMARY KEY, case_id uuid NOT NULL REFERENCES public.support_cases(id) ON DELETE RESTRICT,
 case_revision integer NOT NULL CHECK(case_revision>0), actor_staff_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 event_type text NOT NULL CHECK(event_type IN ('created','claimed','updated')),
 from_status text, to_status text NOT NULL CHECK(to_status IN ('open','investigating','resolved','closed')),
 priority varchar(10) NOT NULL CHECK(priority IN ('low','normal','high','urgent')),
 note_ciphertext bytea, note_key_version smallint, created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(case_id,case_revision),
 CHECK((note_ciphertext IS NULL AND note_key_version IS NULL) OR
 (note_ciphertext IS NOT NULL AND octet_length(note_ciphertext)>=32 AND note_key_version IS NOT NULL AND note_key_version>0))
);
ALTER TABLE public.support_case_events ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.support_case_events FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT SELECT ON public.support_case_events TO safereturn_api;
CREATE POLICY sr_case_event_read ON public.support_case_events FOR SELECT TO safereturn_api USING
 (public.sr_is_staff(ARRAY['support']) AND EXISTS(SELECT 1 FROM public.support_cases c
 WHERE c.id=case_id AND c.assigned_staff_id=public.sr_actor_id()));
CREATE TRIGGER sr_case_event_append BEFORE UPDATE OR DELETE ON public.support_case_events
 FOR EACH ROW EXECUTE FUNCTION public.sr_append_only();
-- Finder holds also serialize with linked case closure. Existing order/artifact
-- admission remains unchanged; no hold-writing permission is added.
CREATE FUNCTION public.sr_support_finder_hold_lock() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE pid uuid;
BEGIN
 IF NEW.resource_type='finder_message' AND NEW.released_at IS NULL THEN
  SELECT q.pair_id INTO pid FROM public.finder_messages m JOIN public.qr_codes q ON q.id=m.qr_id WHERE m.id=NEW.resource_id;
  PERFORM 1 FROM public.orders o WHERE o.id IN (SELECT u.order_id FROM public.order_pair_units u WHERE u.pair_id=pid) ORDER BY o.id FOR UPDATE;
  PERFORM 1 FROM public.tag_pairs WHERE id=pid FOR UPDATE;
 END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION public.sr_support_finder_hold_lock() FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
CREATE TRIGGER sr_ab_support_finder_hold BEFORE INSERT OR UPDATE ON public.retention_holds
 FOR EACH ROW EXECUTE FUNCTION public.sr_support_finder_hold_lock();
CREATE FUNCTION public.sr_support_context(case_id uuid) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE c public.support_cases; held boolean;
BEGIN
 IF NOT public.sr_is_staff(ARRAY['support']) THEN RETURN NULL; END IF;
 SELECT * INTO c FROM public.support_cases WHERE id=$1 AND assigned_staff_id=public.sr_actor_id();
 IF NOT FOUND THEN RETURN NULL; END IF;
 WITH linked_orders AS (SELECT c.order_id AS id WHERE c.order_id IS NOT NULL
 UNION SELECT u.order_id FROM public.order_pair_units u WHERE u.pair_id=c.pair_id)
 SELECT EXISTS(SELECT 1 FROM public.retention_holds h WHERE h.released_at IS NULL AND (
 (h.resource_type='order' AND h.resource_id IN (SELECT id FROM linked_orders)) OR
 (h.resource_type='print_artifact' AND EXISTS(SELECT 1 FROM public.print_artifacts a JOIN public.print_jobs j ON j.id=a.print_job_id
 WHERE a.id=h.resource_id AND j.order_id IN (SELECT id FROM linked_orders))) OR
 (h.resource_type='payment_evidence' AND EXISTS(SELECT 1 FROM public.payment_evidence e JOIN public.payment_attempts p ON p.id=e.attempt_id
 WHERE e.id=h.resource_id AND p.order_id IN (SELECT id FROM linked_orders))) OR
 (h.resource_type='finder_message' AND EXISTS(SELECT 1 FROM public.finder_messages m JOIN public.qr_codes q ON q.id=m.qr_id
 WHERE m.id=h.resource_id AND (q.pair_id=c.pair_id OR q.pair_id IN
 (SELECT u.pair_id FROM public.order_pair_units u WHERE u.order_id IN (SELECT id FROM linked_orders))))))) INTO held;
 RETURN jsonb_build_object('has_active_hold',held,'account_deletion_request',EXISTS(SELECT 1 FROM public.audit_events a
 WHERE a.target_type='support_case' AND a.target_id=c.id AND a.action='account.deletion.requested'));
END $$;
CREATE FUNCTION public.sr_support_create(case_id uuid, kind text, urgency text, pair_ref uuid, order_ref uuid,
 description bytea, key_version smallint, event_id uuid, request_tag text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NOT public.sr_is_staff(ARRAY['support']) THEN RAISE EXCEPTION 'Denied' USING ERRCODE='42501'; END IF;
 IF kind IS NULL OR kind NOT IN ('activation','lost_tag','payment','privacy','ownership_dispute','other')
 OR urgency IS NULL OR urgency NOT IN ('low','normal','high','urgent') OR description IS NULL OR octet_length(description)<32
 OR key_version IS NULL OR key_version<=0 THEN RETURN jsonb_build_object('error','INVALID_REQUEST'); END IF;
 IF (pair_ref IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.tag_pairs WHERE id=pair_ref))
 OR (order_ref IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.orders WHERE id=order_ref))
 OR (pair_ref IS NOT NULL AND order_ref IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.order_pair_units WHERE pair_id=pair_ref AND order_id=order_ref))
 THEN RETURN jsonb_build_object('error','INVALID_CONTEXT'); END IF;
 INSERT INTO public.support_cases(id,case_type,priority,pair_id,order_id,opened_by_user_id,assigned_staff_id,description_ciphertext,description_key_version,description_format)
 VALUES(case_id,kind,urgency,pair_ref,order_ref,public.sr_actor_id(),public.sr_actor_id(),description,key_version,1);
 INSERT INTO public.support_case_events(id,case_id,case_revision,actor_staff_id,event_type,to_status,priority)
 VALUES(event_id,case_id,1,public.sr_actor_id(),'created','open',urgency);
 INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,request_id,reason,safe_details)
 VALUES(public.sr_actor_id(),'staff','support_case.created','support_case',case_id,request_tag,'staff_case_intake',jsonb_build_object('version',1,'to_status','open'));
 RETURN jsonb_build_object('id',case_id,'status','open','case_revision',1);
END $$;
CREATE FUNCTION public.sr_support_change(case_id uuid, expected integer, action_name text, next_status text, urgency text,
 event_id uuid, note bytea, key_version smallint, request_tag text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE c public.support_cases; new_status text; new_priority text; revision integer; context jsonb;
BEGIN
 IF NOT public.sr_is_staff(ARRAY['support']) THEN RAISE EXCEPTION 'Denied' USING ERRCODE='42501'; END IF;
 SELECT * INTO c FROM public.support_cases WHERE id=$1 AND (assigned_staff_id IS NULL OR assigned_staff_id=public.sr_actor_id());
 IF NOT FOUND THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
 -- Same order-first lock as retention/print admission. References are immutable through this API.
 PERFORM 1 FROM public.orders o WHERE o.id=c.order_id OR o.id IN
 (SELECT u.order_id FROM public.order_pair_units u WHERE u.pair_id=c.pair_id) ORDER BY o.id FOR UPDATE;
 PERFORM 1 FROM public.tag_pairs p WHERE p.id=c.pair_id OR p.id IN
 (SELECT u.pair_id FROM public.order_pair_units u WHERE u.order_id=c.order_id) ORDER BY p.id FOR UPDATE;
 SELECT * INTO c FROM public.support_cases WHERE id=$1 AND (assigned_staff_id IS NULL OR assigned_staff_id=public.sr_actor_id()) FOR UPDATE;
 IF NOT FOUND THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
 IF expected IS NULL OR c.case_revision<>expected THEN RETURN jsonb_build_object('error','STALE_CASE'); END IF;
 IF c.status='closed' THEN RETURN jsonb_build_object('error','CASE_CLOSED'); END IF;
 IF action_name='claim' THEN
  IF c.assigned_staff_id IS NOT NULL OR c.status NOT IN ('open','investigating') OR next_status IS NOT NULL OR urgency IS NOT NULL OR note IS NOT NULL
  THEN RETURN jsonb_build_object('error','CLAIM_NOT_ALLOWED'); END IF;
  UPDATE public.support_cases SET assigned_staff_id=public.sr_actor_id(),case_revision=case_revision+1 WHERE id=$1 RETURNING case_revision INTO revision;
  new_status:=c.status;new_priority:=c.priority;
 ELSIF action_name='update' THEN
  IF c.assigned_staff_id IS DISTINCT FROM public.sr_actor_id() THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
  new_status:=coalesce(next_status,c.status);new_priority:=coalesce(urgency,c.priority);
  IF new_priority NOT IN ('low','normal','high','urgent') OR new_status NOT IN ('open','investigating','resolved','closed')
  OR (note IS NOT NULL AND (octet_length(note)<32 OR key_version IS NULL OR key_version<=0))
  OR (note IS NULL AND key_version IS NOT NULL) THEN RETURN jsonb_build_object('error','INVALID_REQUEST'); END IF;
  IF new_status<>c.status AND NOT ((c.status='open' AND new_status='investigating') OR
  (c.status='investigating' AND new_status='resolved') OR (c.status='resolved' AND new_status='closed')) THEN RETURN jsonb_build_object('error','INVALID_TRANSITION'); END IF;
  context:=public.sr_support_context(c.id);
  IF new_status IN ('resolved','closed') AND new_status<>c.status AND
   (c.case_type IN ('payment','privacy','ownership_dispute') OR coalesce((context->>'has_active_hold')::boolean,true))
  THEN RETURN jsonb_build_object('error','ESCALATION_REQUIRED'); END IF;
  IF new_status=c.status AND new_priority=c.priority AND note IS NULL THEN RETURN jsonb_build_object('error','NO_CHANGE'); END IF;
  UPDATE public.support_cases SET status=new_status,priority=new_priority,case_revision=case_revision+1,
   closed_at=CASE WHEN new_status='closed' THEN clock_timestamp() ELSE closed_at END WHERE id=$1 RETURNING case_revision INTO revision;
 ELSE RETURN jsonb_build_object('error','INVALID_REQUEST'); END IF;
 INSERT INTO public.support_case_events(id,case_id,case_revision,actor_staff_id,event_type,from_status,to_status,priority,note_ciphertext,note_key_version)
 VALUES(event_id,case_id,revision,public.sr_actor_id(),CASE WHEN action_name='claim' THEN 'claimed' ELSE 'updated' END,c.status,new_status,new_priority,note,key_version);
 INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,request_id,reason,safe_details)
 VALUES(public.sr_actor_id(),'staff','support_case.changed','support_case',case_id,request_tag,'support_case_'||action_name,
 jsonb_build_object('version',revision,'from_status',c.status,'to_status',new_status));
 RETURN jsonb_build_object('id',case_id,'status',new_status,'case_revision',revision);
END $$;
REVOKE ALL ON FUNCTION public.sr_support_context(uuid),public.sr_support_create(uuid,text,text,uuid,uuid,bytea,smallint,uuid,text),
 public.sr_support_change(uuid,integer,text,text,text,uuid,bytea,smallint,text) FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_support_context(uuid),public.sr_support_create(uuid,text,text,uuid,uuid,bytea,smallint,uuid,text),
 public.sr_support_change(uuid,integer,text,text,text,uuid,bytea,smallint,text) TO safereturn_api;
""")


def downgrade():
    raise RuntimeError("Forward-only support case history")
