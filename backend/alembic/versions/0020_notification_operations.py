"""Narrow canonical notification metadata/retry delegation; no broad RLS grants."""

from alembic import op

revision = "0020_notification_operations"
down_revision = "0019_retention_recovery"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='5s'")
    op.execute(r"""
CREATE FUNCTION public.sr_notification_safe_code(code text) RETURNS text
LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT CASE WHEN $1 IS NULL THEN NULL WHEN $1 IN
 ('provider_network','provider_invalid_response','provider_not_configured','recipient_unavailable',
 'recipient_decryption_failed','invalid_recipient','attempts_exhausted','idempotency_window_expired')
 OR $1 ~ '^provider_http_[1-5][0-9]{2}$' THEN $1 ELSE 'provider_failure' END
$$;
CREATE FUNCTION public.sr_notification_retry_gate(event_id uuid, budget integer) RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT CASE
 WHEN o.status<>'dead' THEN 'not_dead'
 WHEN o.event_type<>'finder_message.created' OR o.aggregate_type<>'finder_message' OR o.payload_version<>1 THEN 'unsupported_event'
 WHEN o.attempt_count<1 OR o.attempt_count >= $2 THEN 'attempt_budget_exhausted'
 WHEN NOT EXISTS(SELECT 1 FROM public.notification_attempts a WHERE a.outbox_id=o.id)
   OR (SELECT min(a.attempted_at) FROM public.notification_attempts a WHERE a.outbox_id=o.id)<=now()-interval '23 hours' THEN 'manual_review_required'
 WHEN EXISTS(SELECT 1 FROM public.notification_attempts a WHERE a.outbox_id=o.id AND a.outcome='success') THEN 'already_accepted'
 WHEN o.last_error_code IS NULL OR NOT (o.last_error_code IN
 ('provider_network','provider_invalid_response','provider_not_configured','recipient_unavailable','provider_http_401','provider_http_403','provider_http_408','provider_http_409','provider_http_429')
 OR o.last_error_code ~ '^provider_http_5[0-9]{2}$') THEN 'manual_review_required'
 WHEN NOT EXISTS(SELECT 1 FROM public.finder_messages m JOIN auth.users u ON u.id=m.recipient_owner_user_id
 WHERE m.id=o.aggregate_id AND m.recipient_owner_user_id=o.recipient_user_id AND m.deleted_at IS NULL
 AND u.deleted_at IS NULL AND u.email_confirmed_at IS NOT NULL AND u.email IS NOT NULL
 AND NOT COALESCE(u.is_anonymous,false) AND (u.banned_until IS NULL OR u.banned_until<=now())) THEN 'recipient_unavailable'
 ELSE NULL END FROM public.notification_outbox o WHERE o.id=$1
$$;
CREATE FUNCTION public.sr_notification_metadata(lim integer, stamp timestamptz, ident uuid,
 filter_status text, event_id uuid, attempt_lim integer, before_attempt integer, budget integer) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE result jsonb;
BEGIN
 IF NOT public.sr_is_staff(ARRAY['operations','security_admin']) THEN RAISE EXCEPTION 'Denied' USING ERRCODE='42501'; END IF;
 IF lim IS NULL OR attempt_lim IS NULL OR budget IS NULL OR lim NOT BETWEEN 1 AND 101 OR attempt_lim NOT BETWEEN 1 AND 100 OR budget NOT BETWEEN 1 AND 100 THEN RAISE EXCEPTION 'Invalid bounds' USING ERRCODE='22023'; END IF;
 SELECT coalesce(jsonb_agg(jsonb_build_object(
 'id',o.id,'event_type',CASE WHEN o.event_type='finder_message.created' THEN o.event_type ELSE 'unsupported' END,
 'status',o.status,'attempt_count',o.attempt_count,'created_at',o.created_at,'next_attempt_at',o.next_attempt_at,
 'lease_until',o.lease_until,'sent_at',o.sent_at,'last_error_code',public.sr_notification_safe_code(o.last_error_code),
 'first_attempt_at',(SELECT min(a.attempted_at) FROM public.notification_attempts a WHERE a.outbox_id=o.id),
 'due_lag_seconds',CASE WHEN o.status IN ('pending','retry') THEN greatest(0,floor(extract(epoch FROM now()-o.next_attempt_at))) ELSE NULL END,
 'retry_blocked_reason',public.sr_notification_retry_gate(o.id,budget),
 'attempts',CASE WHEN event_id IS NOT NULL THEN (SELECT coalesce(jsonb_agg(to_jsonb(a) ORDER BY a.attempt_number DESC),'[]'::jsonb) FROM
 (SELECT attempt_number,outcome,attempted_at,finished_at,public.sr_notification_safe_code(error_code) AS error_code FROM public.notification_attempts
 WHERE outbox_id=o.id AND (before_attempt IS NULL OR attempt_number<before_attempt) ORDER BY attempt_number DESC LIMIT attempt_lim) a) ELSE NULL END,
 'next_attempt_before',CASE WHEN event_id IS NOT NULL THEN (SELECT min(a.attempt_number) FROM
 (SELECT attempt_number FROM public.notification_attempts WHERE outbox_id=o.id AND (before_attempt IS NULL OR attempt_number<before_attempt)
 ORDER BY attempt_number DESC LIMIT attempt_lim) a HAVING count(*)=attempt_lim) ELSE NULL END
 ) ORDER BY o.created_at DESC,o.id DESC),'[]'::jsonb) INTO result
 FROM (SELECT * FROM public.notification_outbox WHERE (filter_status IS NULL OR status=filter_status)
 AND (event_id IS NULL OR id=event_id) AND (stamp IS NULL OR (created_at,id)<(stamp,ident))
 ORDER BY created_at DESC,id DESC LIMIT lim) o;
 RETURN result;
END $$;
CREATE FUNCTION public.sr_notification_retry(event_id uuid, expected integer, budget integer, reason_code text, request_tag text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE o public.notification_outbox; blocked text;
BEGIN
 IF NOT public.sr_is_staff(ARRAY['operations','security_admin']) THEN RAISE EXCEPTION 'Denied' USING ERRCODE='42501'; END IF;
 IF expected IS NULL OR budget IS NULL OR reason_code IS NULL OR expected<1 OR budget NOT BETWEEN 1 AND 100
 OR reason_code NOT IN ('provider_recovered','recipient_reverified') OR (request_tag IS NOT NULL AND request_tag !~ '^[0-9a-f]{32}$') THEN RETURN jsonb_build_object('error','INVALID_REQUEST'); END IF;
 SELECT * INTO o FROM public.notification_outbox WHERE id=event_id FOR UPDATE;
 IF NOT FOUND THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
 IF o.attempt_count<>expected THEN RETURN jsonb_build_object('error','STALE_ATTEMPT'); END IF;
 blocked:=public.sr_notification_retry_gate(event_id,budget);
 IF blocked IS NOT NULL THEN RETURN jsonb_build_object('error','RETRY_NOT_ALLOWED'); END IF;
 UPDATE public.notification_outbox SET status='retry',next_attempt_at=clock_timestamp() WHERE id=event_id;
 INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,request_id,reason,safe_details)
 VALUES(public.sr_actor_id(),'staff','notification.retry','notification_outbox',event_id,request_tag,reason_code,
 jsonb_build_object('from_status','dead','to_status','retry','version',expected,'reason_code',reason_code));
 RETURN jsonb_build_object('id',event_id,'status','retry','expected_attempt_count',expected);
END $$;
REVOKE ALL ON FUNCTION public.sr_notification_safe_code(text), public.sr_notification_retry_gate(uuid,integer),
 public.sr_notification_metadata(integer,timestamptz,uuid,text,uuid,integer,integer,integer),
 public.sr_notification_retry(uuid,integer,integer,text,text) FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_notification_metadata(integer,timestamptz,uuid,text,uuid,integer,integer,integer),
 public.sr_notification_retry(uuid,integer,integer,text,text) TO safereturn_api;
""")


def downgrade():
    raise RuntimeError("Forward-only notification operations")
