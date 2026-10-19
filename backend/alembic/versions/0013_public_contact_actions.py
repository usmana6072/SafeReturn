"""Add protected ICE reveal and explicit WhatsApp link projections."""

from alembic import op

revision = "0013_public_contact_actions"
down_revision = "0012_public_qr_projection"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='5s'")
    op.execute(
        """
CREATE FUNCTION public.sr_public_ice_contact(public_token text, contact uuid) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE
    result jsonb;
    state text;
BEGIN
    SELECT q.public_status INTO state FROM public.qr_codes q
    WHERE q.public_token=$1 AND q.is_current AND q.tag_type='ice' FOR SHARE;
    IF NOT FOUND THEN RETURN NULL; END IF;
    IF state<>'active' THEN RETURN jsonb_build_object('unavailable',true); END IF;
    SELECT jsonb_build_object(
        'qr_id', q.id,
        'ciphertext', encode(c.phone_ciphertext,'base64'),
        'key_version', c.phone_key_version
    ) INTO result
    FROM public.qr_codes q
    JOIN public.ice_profiles i ON i.qr_id=q.id
    JOIN public.ice_contacts c ON c.ice_qr_id=q.id
    WHERE q.public_token=$1
      AND q.tag_type='ice'
      AND q.is_current
      AND q.public_status='active'
      AND i.published AND i.publication_consent_version='ice-public-v1'
      AND c.id=$2
      AND c.published
      AND c.publication_consent_at IS NOT NULL
      AND c.publication_consent_version='ice-contact-v1'
      AND c.removed_at IS NULL
    FOR SHARE OF q,i,c;
    RETURN result;
END $$;

CREATE FUNCTION public.sr_public_whatsapp_link(public_token text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE
    result jsonb;
    state text;
BEGIN
    SELECT jsonb_build_object(
        'qr_id', q.id,
        'ciphertext', encode(p.whatsapp_phone_ciphertext,'base64'),
        'key_version', p.whatsapp_phone_key_version
    ) INTO result
    FROM public.qr_codes q
    JOIN public.lost_item_profiles l ON l.qr_id=q.id
    JOIN public.tag_contact_preferences p ON p.qr_id=q.id
    WHERE q.public_token=$1
      AND q.tag_type='lost'
      AND q.is_current
      AND q.public_status='active'
      AND l.published
      AND p.whatsapp_enabled
      AND p.whatsapp_phone_ciphertext IS NOT NULL
      AND p.whatsapp_consent_at IS NOT NULL
      AND p.whatsapp_consent_version='wa-public-v1'
    FOR SHARE OF q,l,p;
    RETURN result;
END $$;

CREATE FUNCTION public.sr_public_contact_budget(peer text, tag text, contact text) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF peer IS NULL OR tag IS NULL OR contact IS NULL OR peer !~ '^[0-9a-f]{64}$' OR tag !~ '^[0-9a-f]{64}$' OR contact !~ '^[0-9a-f]{64}$' THEN RETURN false; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended('contact-peer:'||peer,0));
 IF (SELECT count(*) FROM public.audit_events WHERE action='contact.peer' AND request_id=peer AND occurred_at>clock_timestamp()-interval '15 minutes')>=20 THEN RETURN false; END IF;
 INSERT INTO public.audit_events(actor_kind,action,target_type,request_id,safe_details) VALUES('anonymous','contact.peer','contact',peer,'{}'::jsonb);
 IF (SELECT count(*) FROM public.audit_events WHERE action='contact.tag' AND request_id=tag AND occurred_at>clock_timestamp()-interval '15 minutes')>=10 THEN RETURN false; END IF;
 INSERT INTO public.audit_events(actor_kind,action,target_type,request_id,safe_details) VALUES('anonymous','contact.tag','contact',tag,'{}'::jsonb);
 IF (SELECT count(*) FROM public.audit_events WHERE action='contact.member' AND request_id=contact AND occurred_at>clock_timestamp()-interval '15 minutes')>=5 THEN RETURN false; END IF;
 INSERT INTO public.audit_events(actor_kind,action,target_type,request_id,safe_details) VALUES('anonymous','contact.member','contact',contact,'{}'::jsonb);
 RETURN true;
END $$;

CREATE FUNCTION public.sr_public_contact_proof(proof text) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF proof IS NULL OR proof !~ '^[0-9a-f]{64}$' THEN RETURN false; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended('contact-proof:'||proof,0));
 IF EXISTS(SELECT 1 FROM public.audit_events WHERE action='contact.proof' AND request_id=proof) THEN RETURN false; END IF;
 INSERT INTO public.audit_events(actor_kind,action,target_type,request_id,safe_details) VALUES('anonymous','contact.proof','contact',proof,'{}'::jsonb);
 RETURN true;
END $$;

CREATE FUNCTION public.sr_public_whatsapp_available(token text) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT 1 FROM public.qr_codes q JOIN public.lost_item_profiles l ON l.qr_id=q.id
 JOIN public.tag_contact_preferences p ON p.qr_id=q.id
 WHERE q.public_token=$1 AND q.is_current AND q.tag_type='lost' AND q.public_status='active'
 AND l.published AND p.whatsapp_enabled AND p.whatsapp_phone_ciphertext IS NOT NULL
 AND p.whatsapp_consent_at IS NOT NULL AND p.whatsapp_consent_version='wa-public-v1');
$$;
REVOKE ALL ON FUNCTION public.sr_public_contact_budget(text,text,text),public.sr_public_contact_proof(text),public.sr_public_whatsapp_available(text) FROM PUBLIC,anon,authenticated,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_public_contact_budget(text,text,text),public.sr_public_contact_proof(text),public.sr_public_whatsapp_available(text) TO safereturn_api;

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
                'finder_form_enabled', false,
                'whatsapp_contact_enabled', public.sr_public_whatsapp_available($1),
                'location_sharing_available', false
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

REVOKE ALL ON FUNCTION public.sr_public_ice_contact(text,uuid) FROM PUBLIC, anon, authenticated, safereturn_worker;
REVOKE ALL ON FUNCTION public.sr_public_whatsapp_link(text) FROM PUBLIC, anon, authenticated, safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_public_ice_contact(text,uuid) TO safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_public_whatsapp_link(text) TO safereturn_api;
"""
    )


def downgrade():
    raise RuntimeError("Public contact actions are forward-only")
