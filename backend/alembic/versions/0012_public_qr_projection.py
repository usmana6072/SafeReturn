"""Expose an allowlisted anonymous QR projection through one definer function."""

from alembic import op

revision = "0012_public_qr_projection"
down_revision = "0011_profile_owner_locks"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='5s'")
    op.execute(
        """
CREATE FUNCTION public.sr_public_qr_projection(public_token text) RETURNS jsonb
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
                'whatsapp_contact_enabled', COALESCE((
                    SELECT whatsapp_enabled AND whatsapp_consent_at IS NOT NULL
                           AND whatsapp_consent_version='wa-public-v1'
                           AND whatsapp_phone_ciphertext IS NOT NULL
                    FROM public.tag_contact_preferences
                    WHERE qr_id=qr.id
                ), false),
                'location_sharing_available', false
            ),
            'whatsapp_contact', jsonb_build_object(
                'action_available', false,
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
CREATE FUNCTION public.sr_public_scan_rate(binding text) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF binding IS NULL OR binding !~ '^[0-9a-f]{64}$' THEN RETURN false; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended('public-scan-peer:'||binding,0));
 IF (SELECT count(*) FROM public.audit_events WHERE action='public.scan'
     AND request_id=binding AND occurred_at>clock_timestamp()-interval '15 minutes')>=100
 THEN RETURN false; END IF;
 INSERT INTO public.audit_events(actor_kind,action,target_type,request_id,safe_details)
 VALUES('anonymous','public.scan','qr',binding,jsonb_build_object('outcome','attempt'));
 RETURN true;
END $$;
REVOKE ALL ON FUNCTION public.sr_public_scan_rate(text) FROM PUBLIC, anon, authenticated, safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_public_scan_rate(text) TO safereturn_api;
REVOKE ALL ON FUNCTION public.sr_public_qr_projection(text) FROM PUBLIC, anon, authenticated, safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_public_qr_projection(text) TO safereturn_api;
"""
    )


def downgrade():
    raise RuntimeError("Public QR projection is forward-only")
