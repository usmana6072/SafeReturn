CREATE UNIQUE INDEX uq_shipment_delivered_email ON public.notification_outbox(aggregate_id)
 WHERE event_type='shipment.delivered';

DO $$ DECLARE definition text; BEGIN
 SELECT pg_get_functiondef('public.sr_outbox_relation()'::regprocedure) INTO definition;
 IF position('Notification event identity/payload is immutable' IN definition)=0 THEN
  RAISE EXCEPTION 'Unexpected outbox guard';
 END IF;
 EXECUTE replace(definition, E'BEGIN\n', $guard$BEGIN
 IF NEW.event_type='shipment.delivered' AND NOT EXISTS (
  SELECT 1 FROM public.shipments s JOIN public.orders o ON o.id=s.order_id
  WHERE s.id=NEW.aggregate_id AND NEW.aggregate_type='shipment' AND s.status='delivered'
    AND o.customer_user_id=NEW.recipient_user_id AND NEW.payload_version=1
    AND NEW.payload_ciphertext IS NOT NULL AND NEW.payload_key_version>0
 ) THEN RAISE EXCEPTION 'Delivery notification must match delivered shipment/customer' USING ERRCODE='23514'; END IF;
$guard$);
END $$;

CREATE FUNCTION public.sr_shipment_notification_recipient(
 notification uuid, attempt integer, snapshot bytea DEFAULT NULL, key_version smallint DEFAULT NULL
) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE recipient text;
BEGIN
 SELECT u.email INTO recipient FROM public.notification_outbox n
 JOIN public.shipments s ON s.id=n.aggregate_id AND s.status='delivered'
 JOIN public.orders o ON o.id=s.order_id AND o.customer_user_id=n.recipient_user_id
 JOIN auth.users u ON u.id=o.customer_user_id
 WHERE n.id=$1 AND n.attempt_count=$2 AND n.event_type='shipment.delivered'
   AND n.aggregate_type='shipment' AND n.payload_version=1 AND n.status='leased'
   AND n.lease_owner=public.sr_worker_id() AND n.lease_until>clock_timestamp()
   AND u.deleted_at IS NULL AND u.email_confirmed_at IS NOT NULL
   AND NOT COALESCE(u.is_anonymous,false) AND (u.banned_until IS NULL OR u.banned_until<=clock_timestamp())
 FOR UPDATE OF n;
 IF recipient IS NULL THEN RETURN NULL; END IF;
 IF $3 IS NOT NULL OR $4 IS NOT NULL THEN
  IF $3 IS NULL OR octet_length($3)<32 OR $4 IS NULL OR $4<=0 THEN
   RAISE EXCEPTION 'Invalid encrypted recipient' USING ERRCODE='23514';
  END IF;
  UPDATE public.notification_outbox SET recipient_email_snapshot_ciphertext=$3,recipient_email_key_version=$4
  WHERE id=$1 AND recipient_email_snapshot_ciphertext IS NULL AND recipient_email_key_version IS NULL;
 END IF;
 RETURN recipient;
END $$;
REVOKE ALL ON FUNCTION public.sr_shipment_notification_recipient(uuid,integer,bytea,smallint)
 FROM PUBLIC,anon,authenticated,safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_shipment_notification_recipient(uuid,integer,bytea,smallint) TO safereturn_worker;
