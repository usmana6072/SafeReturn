CREATE FUNCTION public.sr_notification_finder_details(notification uuid, attempt integer)
RETURNS TABLE (
 qr_id uuid, finder_name text, finder_email_ciphertext bytea, finder_phone_ciphertext bytea,
 finder_contact_key_version smallint, preferred_contact text, message_text_ciphertext bytea,
 message_key_version smallint, submitted_at timestamptz, latitude_ciphertext bytea,
 longitude_ciphertext bytea, location_key_version smallint, accuracy_m numeric
)
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT m.qr_id,m.finder_name::text,m.finder_email_ciphertext,m.finder_phone_ciphertext,
        m.finder_contact_key_version,m.preferred_contact::text,m.message_text_ciphertext,
        m.message_key_version,m.submitted_at,l.latitude_ciphertext,l.longitude_ciphertext,
        l.key_version,l.accuracy_m
 FROM public.notification_outbox o
 JOIN public.finder_messages m ON m.id=o.aggregate_id AND m.recipient_owner_user_id=o.recipient_user_id
 LEFT JOIN public.finder_message_locations l ON l.finder_message_id=m.id AND l.consent_at IS NOT NULL
 WHERE o.id=$1 AND o.attempt_count=$2
   AND o.event_type='finder_message.created' AND o.aggregate_type='finder_message' AND o.payload_version=1
   AND o.status='leased' AND o.lease_owner=public.sr_worker_id() AND o.lease_until>clock_timestamp()
   AND m.deleted_at IS NULL
$$;
REVOKE ALL ON FUNCTION public.sr_notification_finder_details(uuid,integer)
 FROM PUBLIC,anon,authenticated,safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_notification_finder_details(uuid,integer) TO safereturn_worker;
