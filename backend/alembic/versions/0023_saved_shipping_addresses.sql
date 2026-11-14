-- Reviewed forward-only proposal. Application requires separate authorization.
ALTER TABLE public.shipping_addresses
 ADD COLUMN is_saved boolean NOT NULL DEFAULT false,
 ADD COLUMN version integer NOT NULL DEFAULT 1 CHECK(version > 0),
 ADD CONSTRAINT uq_shipping_address_owner UNIQUE(customer_user_id,id);

CREATE TABLE public.shipping_address_books (
 customer_user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE RESTRICT,
 version integer NOT NULL CHECK(version > 0),
 default_address_id uuid,
 FOREIGN KEY(customer_user_id,default_address_id)
 REFERENCES public.shipping_addresses(customer_user_id,id) ON DELETE RESTRICT
);
ALTER TABLE public.shipping_address_books ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.shipping_address_books FROM PUBLIC,anon,authenticated;
GRANT SELECT,INSERT,UPDATE ON public.shipping_address_books TO safereturn_api;
CREATE POLICY sr_address_book_owner ON public.shipping_address_books TO safereturn_api
 USING(customer_user_id=public.sr_actor_id())
 WITH CHECK(customer_user_id=public.sr_actor_id());
GRANT DELETE ON public.shipping_addresses TO safereturn_api;
CREATE POLICY sr_saved_address_delete ON public.shipping_addresses FOR DELETE TO safereturn_api
 USING(customer_user_id=public.sr_actor_id() AND is_saved);

-- Protect old checkout source ciphertext and all referenced saved rows, even from
-- a mistaken future writer; FK checks additionally serialize reference inserts.
CREATE FUNCTION public.sr_saved_address_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF NOT OLD.is_saved OR
   EXISTS(SELECT 1 FROM public.order_shipping_snapshots WHERE source_address_id=OLD.id) OR
   EXISTS(SELECT 1 FROM public.shipments WHERE shipping_address_id=OLD.id) THEN
   RAISE EXCEPTION 'Shipping source is protected' USING ERRCODE='23514';
 END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; END IF;
 IF (NEW.id,NEW.customer_user_id,NEW.is_saved) IS DISTINCT FROM
   (OLD.id,OLD.customer_user_id,OLD.is_saved) THEN
   RAISE EXCEPTION 'Shipping source identity is protected' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_saved_address_guard BEFORE UPDATE OR DELETE ON public.shipping_addresses
 FOR EACH ROW EXECUTE FUNCTION public.sr_saved_address_guard();

CREATE FUNCTION public.sr_saved_default_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF NEW.default_address_id IS NOT NULL AND NOT EXISTS(
   SELECT 1 FROM public.shipping_addresses WHERE id=NEW.default_address_id
   AND customer_user_id=NEW.customer_user_id AND is_saved) THEN
   RAISE EXCEPTION 'Saved default required' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_saved_default_guard BEFORE INSERT OR UPDATE ON public.shipping_address_books
 FOR EACH ROW EXECUTE FUNCTION public.sr_saved_default_guard();
