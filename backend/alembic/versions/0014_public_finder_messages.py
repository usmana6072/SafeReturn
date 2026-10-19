"""Add atomic anonymous finder-message submission with optional location."""

from alembic import op

revision = "0014_public_finder_messages"
down_revision = "0013_public_contact_actions"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='5s'")
    op.execute(
        """
CREATE OR REPLACE FUNCTION public.sr_public_qr_projection(public_token text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE
    qr public.qr_codes%ROWTYPE;
    payload jsonb;
BEGIN
    SELECT * INTO qr
    FROM public.qr_codes
    WHERE qr_codes.public_token=$1 AND qr_codes.is_current;

    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    payload := jsonb_build_object(
        'tag_type', qr.tag_type,
        'status', qr.public_status,
        'locale_options', jsonb_build_array('en', 'ur')
    );

    IF qr.public_status <> 'active' THEN
        RETURN payload;
    END IF;

    IF qr.tag_type = 'lost' THEN
        payload := payload || jsonb_build_object(
            'lost_item', (
                SELECT jsonb_build_object(
                    'label', CASE WHEN published THEN item_label ELSE NULL END,
                    'description', CASE WHEN published THEN description ELSE NULL END,
                    'reward_text', CASE WHEN published THEN reward_text ELSE NULL END
                )
                FROM public.lost_item_profiles
                WHERE qr_id=qr.id
            ),
            'features', jsonb_build_object(
                'finder_form_enabled', EXISTS(SELECT 1 FROM public.lost_item_profiles WHERE qr_id=qr.id AND published),
                'whatsapp_contact_enabled', public.sr_public_whatsapp_available($1),
                'location_sharing_available', EXISTS(SELECT 1 FROM public.lost_item_profiles WHERE qr_id=qr.id AND published)
            ),
            'whatsapp_contact', jsonb_build_object(
                'action_available', public.sr_public_whatsapp_available($1),
                'disclosure_notice', 'Opening WhatsApp will reveal the owner''s chosen number.'
            )
        );
    ELSE
        SELECT payload || jsonb_build_object(
            'ice', jsonb_build_object(
                'display_name', CASE WHEN i.published AND i.publication_consent_version='ice-public-v1' THEN i.display_name ELSE NULL END,
                'blood_group', CASE WHEN i.published AND i.publication_consent_version='ice-public-v1' THEN i.blood_group ELSE NULL END,
                'medical_notes', NULL,
                'contacts', COALESCE((
                    SELECT jsonb_agg(
                        jsonb_build_object(
                            'contact_id', c.id,
                            'relationship_label', c.relationship_label,
                            'display_name', c.display_name,
                            'reveal_available', true
                        )
                        ORDER BY c.display_order, c.id
                    )
                    FROM public.ice_contacts c
                    WHERE c.ice_qr_id=qr.id
                      AND i.published
                      AND i.publication_consent_version='ice-public-v1'
                      AND c.publication_consent_at IS NOT NULL
                      AND c.publication_consent_version='ice-contact-v1'
                      AND c.published
                      AND c.removed_at IS NULL
                ), '[]'::jsonb),
                'owner_information_disclaimer', 'Owner-provided information is not medically verified.'
            )
        ) INTO payload
        FROM (SELECT 1) seed
        LEFT JOIN public.ice_profiles i ON i.qr_id=qr.id;
    END IF;

    RETURN payload;
END $$;

CREATE FUNCTION public.sr_public_finder_budget(binding text, peer text) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF binding IS NULL OR binding !~ '^[0-9a-f]{64}$'
    OR peer IS NULL OR peer !~ '^[0-9a-f]{64}$' THEN RETURN false; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended('finder-peer:'||peer,0));
 IF (SELECT count(*) FROM public.audit_events WHERE action='finder.peer'
     AND request_id=peer AND occurred_at>clock_timestamp()-interval '15 minutes')>=20 THEN
   RETURN false;
 END IF;
 INSERT INTO public.audit_events(actor_kind,action,target_type,request_id,safe_details)
 VALUES('anonymous','finder.peer','finder_message',peer,'{}'::jsonb);
 IF (SELECT count(*) FROM public.audit_events WHERE action='finder.attempt'
     AND request_id=binding AND occurred_at>clock_timestamp()-interval '15 minutes')>=5 THEN
   RETURN false;
 END IF;
 INSERT INTO public.audit_events(actor_kind,action,target_type,request_id,safe_details)
 VALUES('anonymous','finder.attempt','finder_message',binding,'{}'::jsonb);
 RETURN true;
END $$;
REVOKE ALL ON FUNCTION public.sr_public_finder_budget(text,text)
 FROM PUBLIC,anon,authenticated,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_public_finder_budget(text,text) TO safereturn_api;


CREATE FUNCTION public.sr_public_lost_qr_id(public_token text) RETURNS uuid
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$
    SELECT q.id
    FROM public.qr_codes q
    JOIN public.lost_item_profiles l ON l.qr_id=q.id
    WHERE q.public_token=$1
      AND q.tag_type='lost'
      AND q.is_current
      AND q.public_status='active'
      AND l.published
$$;
REVOKE ALL ON FUNCTION public.sr_public_lost_qr_id(text)
    FROM PUBLIC, anon, authenticated, safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_public_lost_qr_id(text) TO safereturn_api;

CREATE FUNCTION public.sr_public_submit_finder_message(
    public_token text,
    finder_name text,
    finder_email_ciphertext bytea,
    finder_phone_ciphertext bytea,
    finder_contact_key_version smallint,
    preferred_contact text,
    message_text_ciphertext bytea,
    message_key_version smallint,
    consent_version text,
    consent_at timestamptz,
    latitude_ciphertext bytea,
    longitude_ciphertext bytea,
    accuracy_m numeric,
    location_source text,
    location_consent_at timestamptz,
    location_consent_version text,
    location_key_version smallint,
    retry_key text,
    body_hash text
) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE
    qr uuid;
    owner_id uuid;
    message_id uuid;
    scope text;
    previous_hash text;
BEGIN
    SELECT q.id, p.owner_user_id
      INTO qr, owner_id
      FROM public.qr_codes q
      JOIN public.tag_pairs p ON p.id=q.pair_id
      JOIN public.lost_item_profiles l ON l.qr_id=q.id
     WHERE q.public_token=$1
       AND q.tag_type='lost'
       AND q.is_current
       AND q.public_status='active'
       AND l.published
     FOR SHARE OF q,p,l;
    IF qr IS NULL OR owner_id IS NULL THEN
        RETURN NULL;
    END IF;
    IF retry_key IS NOT NULL THEN
        scope := 'finder:' || qr::text;
        PERFORM pg_advisory_xact_lock(hashtextextended(scope || ':' || retry_key,0));
        SELECT r.request_hash INTO previous_hash FROM public.idempotency_records r
         WHERE r.actor_scope=scope AND r.operation='finder_message'
           AND r.idempotency_key=retry_key AND r.expires_at>clock_timestamp();
        IF FOUND THEN
            IF previous_hash<>body_hash THEN
                RETURN '00000000-0000-0000-0000-000000000000'::uuid;
            END IF;
            RETURN qr;
        END IF;
        DELETE FROM public.idempotency_records r WHERE r.actor_scope=scope
         AND r.operation='finder_message' AND r.idempotency_key=retry_key;
        INSERT INTO public.idempotency_records(actor_scope,operation,idempotency_key,
            request_hash,state,response_status,expires_at)
        VALUES(scope,'finder_message',retry_key,body_hash,'completed',202,
            clock_timestamp()+interval '24 hours');
    END IF;
    IF finder_email_ciphertext IS NULL AND finder_phone_ciphertext IS NULL THEN
        RETURN NULL;
    END IF;
    IF latitude_ciphertext IS NOT NULL OR longitude_ciphertext IS NOT NULL
       OR location_consent_at IS NOT NULL OR location_consent_version IS NOT NULL
       OR location_key_version IS NOT NULL THEN
        IF latitude_ciphertext IS NULL OR longitude_ciphertext IS NULL
           OR location_consent_at IS NULL OR location_consent_version IS NULL
           OR location_key_version IS NULL OR location_source <> 'browser_geolocation' THEN
            RETURN NULL;
        END IF;
    END IF;

    INSERT INTO public.finder_messages (
        qr_id, recipient_owner_user_id, finder_name,
        finder_email_ciphertext, finder_phone_ciphertext,
        finder_contact_key_version, preferred_contact,
        message_text_ciphertext, message_key_version,
        consent_version, consent_at
    ) VALUES (
        qr, owner_id, NULLIF(finder_name, ''),
        finder_email_ciphertext, finder_phone_ciphertext,
        finder_contact_key_version, preferred_contact,
        message_text_ciphertext, message_key_version,
        consent_version, consent_at
    ) RETURNING id INTO message_id;

    IF latitude_ciphertext IS NOT NULL THEN
        INSERT INTO public.finder_message_locations (
            finder_message_id, latitude_ciphertext, longitude_ciphertext,
            accuracy_m, location_source, consent_at, consent_version, key_version
        ) VALUES (
            message_id, latitude_ciphertext, longitude_ciphertext,
            accuracy_m, location_source, location_consent_at,
            location_consent_version, location_key_version
        );
    END IF;

    INSERT INTO public.notification_outbox (
        event_type, aggregate_type, aggregate_id, recipient_user_id,
        payload_version, idempotency_key
    ) VALUES (
        'finder_message.created', 'finder_message', message_id, owner_id,
        1, 'finder-message:' || message_id::text
    );
    RETURN message_id;
END $$;

REVOKE ALL ON FUNCTION public.sr_public_submit_finder_message(
    text,text,bytea,bytea,smallint,text,bytea,smallint,text,timestamptz,
    bytea,bytea,numeric,text,timestamptz,text,smallint,text,text
) FROM PUBLIC, anon, authenticated, safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_public_submit_finder_message(
    text,text,bytea,bytea,smallint,text,bytea,smallint,text,timestamptz,
    bytea,bytea,numeric,text,timestamptz,text,smallint,text,text
) TO safereturn_api;
"""
    )


def downgrade():
    raise RuntimeError("Public finder messaging is forward-only")
