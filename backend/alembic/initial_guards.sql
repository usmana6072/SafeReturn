-- This file is a frozen part of revision 0001; do not edit after sharing.
CREATE FUNCTION public.sr_touch_updated_at() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
BEGIN NEW.updated_at := now(); RETURN NEW; END $$;

-- Immediate parent locks serialize child mutations, including transactions that
-- began before a competing activation/replacement committed. Identity fields
-- cannot be moved between pairs or purposes and invalidate existing profiles.
CREATE FUNCTION public.sr_guard_qr() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
BEGIN
 IF TG_OP = 'DELETE' THEN
  PERFORM 1 FROM public.tag_pairs WHERE id = OLD.pair_id FOR UPDATE;
  RETURN OLD;
 END IF;
 PERFORM 1 FROM public.tag_pairs WHERE id = NEW.pair_id FOR UPDATE;
 IF TG_OP = 'UPDATE' AND
    (NEW.id, NEW.pair_id, NEW.tag_type, NEW.public_token, NEW.serial_number, NEW.replaces_qr_id)
    IS DISTINCT FROM
    (OLD.id, OLD.pair_id, OLD.tag_type, OLD.public_token, OLD.serial_number, OLD.replaces_qr_id) THEN
  RAISE EXCEPTION 'QR identity fields are immutable' USING ERRCODE = '23514';
 END IF;
 IF NEW.replaces_qr_id IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM public.qr_codes q WHERE q.id = NEW.replaces_qr_id
    AND q.pair_id = NEW.pair_id AND q.tag_type = NEW.tag_type
    AND NOT q.is_current AND q.public_status = 'revoked'
 ) THEN
  RAISE EXCEPTION 'Invalid QR replacement relationship' USING ERRCODE = '23514';
 END IF;
 RETURN NEW;
END $$;

CREATE TRIGGER sr_guard_qr BEFORE INSERT OR UPDATE OR DELETE ON public.qr_codes
FOR EACH ROW EXECUTE FUNCTION public.sr_guard_qr();

CREATE FUNCTION public.sr_check_pair() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE pid uuid; n integer;
BEGIN
 IF TG_TABLE_NAME = 'tag_pairs' THEN pid := NEW.id;
 ELSIF TG_OP = 'DELETE' THEN pid := OLD.pair_id;
 ELSE pid := NEW.pair_id;
 END IF;
 PERFORM 1 FROM public.tag_pairs WHERE id = pid FOR UPDATE;
 IF NOT FOUND THEN RETURN NULL; END IF;
 SELECT count(*) INTO n FROM public.qr_codes WHERE pair_id = pid AND is_current;
 -- The type CHECK and partial uniqueness imply one lost and one ice when n=2.
 IF n <> 2 THEN
  RAISE EXCEPTION 'Pair requires one current Lost and one current ICE QR' USING ERRCODE = '23514';
 END IF;
 RETURN NULL;
END $$;

CREATE CONSTRAINT TRIGGER sr_pair_exactly_two
AFTER INSERT OR UPDATE ON public.tag_pairs DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION public.sr_check_pair();

CREATE CONSTRAINT TRIGGER sr_qr_exactly_two
AFTER INSERT OR UPDATE OR DELETE ON public.qr_codes DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION public.sr_check_pair();

CREATE FUNCTION public.sr_profile_type() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE purpose text;
BEGIN
 SELECT tag_type INTO purpose FROM public.qr_codes WHERE id = NEW.qr_id FOR SHARE;
 IF purpose IS DISTINCT FROM TG_ARGV[0] THEN
  RAISE EXCEPTION 'Profile purpose does not match QR identity' USING ERRCODE = '23514';
 END IF;
 RETURN NEW;
END $$;

CREATE TRIGGER sr_lost_profile_type BEFORE INSERT OR UPDATE ON public.lost_item_profiles
FOR EACH ROW EXECUTE FUNCTION public.sr_profile_type('lost');
CREATE TRIGGER sr_ice_profile_type BEFORE INSERT OR UPDATE ON public.ice_profiles
FOR EACH ROW EXECUTE FUNCTION public.sr_profile_type('ice');
CREATE TRIGGER sr_whatsapp_type BEFORE INSERT OR UPDATE ON public.tag_contact_preferences
FOR EACH ROW EXECUTE FUNCTION public.sr_profile_type('lost');
