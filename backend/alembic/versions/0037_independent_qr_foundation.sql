-- Phase 1 only. No seeds, ownership backfill, runtime grants, or admission helpers.
ALTER TABLE public.products ADD COLUMN qr_type varchar(8)
 CONSTRAINT ck_products_qr_type CHECK(qr_type IN ('lost','ice'));
ALTER TABLE public.qr_batches ADD COLUMN generation_mode varchar(16) NOT NULL DEFAULT 'legacy_pair';
ALTER TABLE public.qr_batches ADD COLUMN qr_type varchar(8);
ALTER TABLE public.qr_batches ADD COLUMN requested_quantity integer;
ALTER TABLE public.qr_batches ADD CONSTRAINT ck_qr_batches_generation_shape CHECK (
 (generation_mode='legacy_pair' AND qr_type IS NULL AND requested_quantity IS NULL) OR
 (generation_mode='standalone' AND qr_type IS NOT NULL AND qr_type IN ('lost','ice')
 AND requested_quantity IS NOT NULL AND requested_quantity BETWEEN 1 AND 1000)
);
ALTER TABLE public.qr_codes ALTER COLUMN pair_id DROP NOT NULL;
ALTER TABLE public.qr_codes ADD COLUMN batch_id uuid
 CONSTRAINT fk_qr_codes_batch_id REFERENCES public.qr_batches(id) ON DELETE RESTRICT;
ALTER TABLE public.qr_codes ADD CONSTRAINT ck_qr_codes_identity_shape CHECK (
 (pair_id IS NOT NULL AND batch_id IS NULL) OR (pair_id IS NULL AND batch_id IS NOT NULL)
);
ALTER TABLE public.qr_codes ADD CONSTRAINT ck_qr_codes_standalone_no_replacement
 CHECK(pair_id IS NOT NULL OR (replaces_qr_id IS NULL AND is_current));
CREATE INDEX ix_standalone_qr_batch_type ON public.qr_codes(batch_id,tag_type,id) WHERE pair_id IS NULL;

CREATE TABLE public.standalone_qr_states (
 qr_id uuid PRIMARY KEY REFERENCES public.qr_codes(id) ON DELETE RESTRICT,
 owner_user_id uuid REFERENCES auth.users(id) ON DELETE RESTRICT,
 inventory_status varchar(16) NOT NULL DEFAULT 'available',
 ownership_status varchar(16) NOT NULL DEFAULT 'unclaimed',
 activated_at timestamptz, revoked_at timestamptz,
 row_version integer NOT NULL DEFAULT 1,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT ck_standalone_qr_states_inventory CHECK(inventory_status IN ('available','allocated','retired')),
 CONSTRAINT ck_standalone_qr_states_ownership CHECK(ownership_status IN ('unclaimed','active','revoked')),
 CONSTRAINT ck_standalone_qr_states_unclaimed CHECK(ownership_status<>'unclaimed' OR (owner_user_id IS NULL AND activated_at IS NULL)),
 CONSTRAINT ck_standalone_qr_states_active_owner CHECK(ownership_status<>'active' OR (owner_user_id IS NOT NULL AND activated_at IS NOT NULL AND inventory_status='allocated')),
 CONSTRAINT ck_standalone_qr_states_revocation CHECK((ownership_status='revoked')=(revoked_at IS NOT NULL)),
 CONSTRAINT ck_standalone_qr_states_version CHECK(row_version>0)
);
CREATE INDEX ix_standalone_owner ON public.standalone_qr_states(owner_user_id,ownership_status);
CREATE INDEX ix_standalone_inventory ON public.standalone_qr_states(inventory_status,qr_id);
ALTER TABLE public.standalone_qr_states ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.standalone_qr_states FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
-- Deliberately no policies or runtime EXECUTE grants in this revision.

CREATE FUNCTION public.sr_batch_identity_provenance() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF (NEW.generation_mode,NEW.qr_type,NEW.requested_quantity)
 IS DISTINCT FROM (OLD.generation_mode,OLD.qr_type,OLD.requested_quantity) THEN
  RAISE EXCEPTION 'Batch identity provenance is immutable' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_batch_identity_provenance BEFORE UPDATE ON public.qr_batches
 FOR EACH ROW EXECUTE FUNCTION public.sr_batch_identity_provenance();

CREATE FUNCTION public.sr_pair_batch_provenance() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP='UPDATE' AND NEW.batch_id IS DISTINCT FROM OLD.batch_id THEN
  RAISE EXCEPTION 'Pair batch provenance is immutable' USING ERRCODE='23514';
 END IF;
 PERFORM 1 FROM public.qr_batches WHERE id=NEW.batch_id AND generation_mode='legacy_pair' FOR SHARE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Legacy pair requires a legacy batch' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_pair_batch_provenance BEFORE INSERT OR UPDATE OF batch_id ON public.tag_pairs
 FOR EACH ROW EXECUTE FUNCTION public.sr_pair_batch_provenance();

-- Preserve legacy locking, immutable identity and replacement semantics.
CREATE OR REPLACE FUNCTION public.sr_guard_qr() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP='DELETE' THEN
  IF OLD.pair_id IS NULL THEN
   RAISE EXCEPTION 'Standalone identity history cannot be deleted' USING ERRCODE='23514';
  END IF;
  PERFORM 1 FROM public.tag_pairs WHERE id=OLD.pair_id FOR UPDATE;
  RETURN OLD;
 END IF;
 IF NEW.pair_id IS NOT NULL THEN
  PERFORM 1 FROM public.tag_pairs WHERE id=NEW.pair_id FOR UPDATE;
 ELSE
  PERFORM 1 FROM public.qr_batches WHERE id=NEW.batch_id
   AND generation_mode='standalone' AND qr_type=NEW.tag_type FOR SHARE;
  IF NOT FOUND THEN RAISE EXCEPTION 'Standalone QR requires matching typed batch' USING ERRCODE='23514'; END IF;
 END IF;
 IF TG_OP='UPDATE' AND
  (NEW.id,NEW.pair_id,NEW.batch_id,NEW.tag_type,NEW.public_token,NEW.serial_number,NEW.replaces_qr_id)
  IS DISTINCT FROM
  (OLD.id,OLD.pair_id,OLD.batch_id,OLD.tag_type,OLD.public_token,OLD.serial_number,OLD.replaces_qr_id) THEN
  RAISE EXCEPTION 'QR identity fields are immutable' USING ERRCODE='23514';
 END IF;
 IF NEW.replaces_qr_id IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM public.qr_codes q WHERE q.id=NEW.replaces_qr_id
   AND q.pair_id=NEW.pair_id AND q.tag_type=NEW.tag_type
   AND NOT q.is_current AND q.public_status='revoked'
 ) THEN RAISE EXCEPTION 'Invalid QR replacement relationship' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.sr_check_pair() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE pid uuid; n integer;
BEGIN
 IF TG_TABLE_NAME='tag_pairs' THEN pid:=NEW.id;
 ELSIF TG_OP='DELETE' THEN pid:=OLD.pair_id;
 ELSE pid:=NEW.pair_id; END IF;
 IF pid IS NULL THEN RETURN NULL; END IF;
 PERFORM 1 FROM public.tag_pairs WHERE id=pid FOR UPDATE;
 IF NOT FOUND THEN RETURN NULL; END IF;
 SELECT count(*) INTO n FROM public.qr_codes WHERE pair_id=pid AND is_current;
 IF n<>2 THEN RAISE EXCEPTION 'Pair requires one current Lost and one current ICE QR' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $$;

CREATE FUNCTION public.sr_standalone_state_history() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Standalone state history cannot be deleted' USING ERRCODE='23514'; END IF;
 IF TG_OP='UPDATE' AND (NEW.qr_id,NEW.created_at) IS DISTINCT FROM (OLD.qr_id,OLD.created_at) THEN
  RAISE EXCEPTION 'Cannot move standalone state history' USING ERRCODE='23514';
 END IF;
 PERFORM 1 FROM public.qr_codes WHERE id=NEW.qr_id AND pair_id IS NULL FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Standalone state requires standalone QR' USING ERRCODE='23514'; END IF;
 IF TG_OP='UPDATE' THEN
  IF NEW.row_version<>OLD.row_version+1 THEN RAISE EXCEPTION 'Standalone state revision must increment once' USING ERRCODE='23514'; END IF;
  NEW.updated_at:=clock_timestamp();
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_standalone_state_history BEFORE INSERT OR UPDATE OR DELETE ON public.standalone_qr_states
 FOR EACH ROW EXECUTE FUNCTION public.sr_standalone_state_history();

CREATE FUNCTION public.sr_standalone_correspondence() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE qid uuid; q public.qr_codes; s public.standalone_qr_states;
BEGIN
 IF TG_TABLE_NAME='qr_codes' THEN
  IF TG_OP='DELETE' THEN qid:=OLD.id; ELSE qid:=NEW.id; END IF;
 ELSE
  IF TG_OP='DELETE' THEN qid:=OLD.qr_id; ELSE qid:=NEW.qr_id; END IF;
 END IF;
 SELECT * INTO q FROM public.qr_codes WHERE id=qid FOR UPDATE;
 IF NOT FOUND THEN RETURN NULL; END IF;
 SELECT * INTO s FROM public.standalone_qr_states WHERE qr_id=qid;
 IF q.pair_id IS NOT NULL THEN
  IF FOUND THEN RAISE EXCEPTION 'Legacy QR cannot have standalone state' USING ERRCODE='23514'; END IF;
 ELSIF s.qr_id IS NULL THEN
  RAISE EXCEPTION 'Standalone QR requires one state row' USING ERRCODE='23514';
 ELSIF (q.public_status IN ('active','owner_disabled') AND s.ownership_status<>'active')
  OR ((q.public_status='revoked')<>(s.ownership_status='revoked')) THEN
  RAISE EXCEPTION 'Standalone public status requires matching ownership state' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER sr_qr_standalone_state AFTER INSERT OR UPDATE OR DELETE ON public.qr_codes
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_standalone_correspondence();
CREATE CONSTRAINT TRIGGER sr_state_standalone_qr AFTER INSERT OR UPDATE OR DELETE ON public.standalone_qr_states
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_standalone_correspondence();

REVOKE ALL ON FUNCTION public.sr_batch_identity_provenance(),public.sr_pair_batch_provenance(),
 public.sr_standalone_state_history(),public.sr_standalone_correspondence()
 FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
-- Existing exact-two triggers and global token/serial/current-pair/replacement uniqueness remain.

-- Keep standalone scan admission closed until owner/public compatibility ships.
-- Preserve the current legacy projection body and its existing ACL.
CREATE OR REPLACE FUNCTION public.sr_public_qr_projection(public_token text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE
    qr public.qr_codes%ROWTYPE;
    payload jsonb;
BEGIN
    SELECT * INTO qr
    FROM public.qr_codes
    WHERE qr_codes.public_token=$1 AND qr_codes.is_current AND qr_codes.pair_id IS NOT NULL;

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
