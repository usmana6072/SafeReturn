"""Owner-scoped immutable checkout quotes and narrow exclusive pair reservation."""

from alembic import op

revision = "0016_checkout_quotes"
down_revision = "0015_public_catalog"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='5s'")
    op.execute("""
CREATE TABLE public.checkout_quotes (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 customer_user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 payload jsonb NOT NULL CHECK (jsonb_typeof(payload)='object'),
 address_ciphertext bytea NOT NULL CHECK(octet_length(address_ciphertext)>0),
 address_key_version smallint NOT NULL CHECK(address_key_version>0),
 subtotal_pkr numeric(12,2) NOT NULL CHECK(subtotal_pkr>=0),
 shipping_pkr numeric(12,2) NOT NULL CHECK(shipping_pkr>=0),
 tax_pkr numeric(12,2) NOT NULL CHECK(tax_pkr>=0),
 total_pkr numeric(12,2) NOT NULL CHECK(total_pkr=subtotal_pkr+shipping_pkr+tax_pkr),
 currency_code varchar(3) NOT NULL DEFAULT 'PKR' CHECK(currency_code='PKR'),
 expires_at timestamptz NOT NULL,
 status text NOT NULL DEFAULT 'open' CHECK(status IN('open','confirmed','expired','cancelled')),
 order_id uuid UNIQUE REFERENCES public.orders(id) ON DELETE RESTRICT,
 created_at timestamptz NOT NULL DEFAULT now(),
 CHECK(expires_at>created_at),
 CHECK((status='confirmed')=(order_id IS NOT NULL))
);
CREATE INDEX idx_checkout_quotes_customer ON public.checkout_quotes(customer_user_id,created_at);
ALTER TABLE public.checkout_quotes ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.checkout_quotes FROM PUBLIC,anon,authenticated,safereturn_worker;
GRANT SELECT,INSERT,UPDATE ON public.checkout_quotes TO safereturn_api;
CREATE POLICY sr_quote_select ON public.checkout_quotes FOR SELECT TO safereturn_api USING(customer_user_id=public.sr_actor_id());
CREATE POLICY sr_quote_insert ON public.checkout_quotes FOR INSERT TO safereturn_api WITH CHECK(customer_user_id=public.sr_actor_id() AND status='open' AND order_id IS NULL);
CREATE POLICY sr_quote_update ON public.checkout_quotes FOR UPDATE TO safereturn_api USING(customer_user_id=public.sr_actor_id()) WITH CHECK(customer_user_id=public.sr_actor_id());
CREATE FUNCTION public.sr_quote_immutable() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Quote history cannot be deleted' USING ERRCODE='23514'; END IF;
 IF (to_jsonb(NEW)-'status'-'order_id') IS DISTINCT FROM (to_jsonb(OLD)-'status'-'order_id')
 OR OLD.status<>'open' OR NEW.status NOT IN('confirmed','expired','cancelled') THEN
 RAISE EXCEPTION 'Quote snapshot is immutable' USING ERRCODE='23514'; END IF;
 IF NEW.order_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.orders WHERE id=NEW.order_id AND customer_user_id=NEW.customer_user_id AND placed_at IS NOT NULL AND total_pkr=NEW.total_pkr) THEN
 RAISE EXCEPTION 'Quote order mismatch' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_quote_immutable BEFORE UPDATE OR DELETE ON public.checkout_quotes FOR EACH ROW EXECUTE FUNCTION public.sr_quote_immutable();
CREATE FUNCTION public.sr_checkout_catalog(ids uuid[]) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE result jsonb;
BEGIN
 IF public.sr_actor_id() IS NULL OR cardinality(ids)>50 THEN RETURN '[]'::jsonb; END IF;
 PERFORM 1 FROM public.products p WHERE p.id IN(SELECT product_id FROM public.product_variants WHERE id=ANY(ids)) ORDER BY p.id FOR SHARE OF p;
 PERFORM 1 FROM public.product_variants v WHERE v.id=ANY(ids) ORDER BY v.id FOR SHARE OF v;
 PERFORM 1 FROM public.product_categories c WHERE c.id IN(SELECT p.category_id FROM public.products p JOIN public.product_variants v ON v.product_id=p.id WHERE v.id=ANY(ids)) ORDER BY c.id FOR SHARE OF c;
 SELECT coalesce(jsonb_agg(to_jsonb(v)||jsonb_build_object('unit_price',to_char(v.unit_price,'FM9999999990.00'),'product_name',p.name,'product_version',p.catalog_version,'allows_new_pair',p.allows_new_pair,'allows_existing_qr',p.allows_existing_qr)),'[]'::jsonb) INTO result
 FROM public.product_variants v JOIN public.products p ON p.id=v.product_id JOIN public.product_categories c ON c.id=p.category_id
 WHERE v.id=ANY(ids) AND v.is_active AND p.lifecycle_status='published' AND c.is_active AND c.slug='qr-stickers'
 AND v.currency_code='PKR' AND v.fulfillment_method='pdf_label' AND v.size_mm>=30;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION public.sr_checkout_catalog(uuid[]) FROM PUBLIC,anon,authenticated,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_checkout_catalog(uuid[]) TO safereturn_api;
CREATE FUNCTION public.sr_checkout_capacity() RETURNS integer LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT count(*)::integer FROM (SELECT p.id FROM public.tag_pairs p
 WHERE public.sr_actor_id() IS NOT NULL AND p.ownership_status='unclaimed' AND p.inventory_status='qa_passed'
 AND NOT EXISTS(SELECT 1 FROM public.order_pair_units u WHERE u.pair_id=p.id AND u.status IN('reserved','allocated'))
 AND (SELECT count(*) FROM public.qr_codes q WHERE q.pair_id=p.id AND q.is_current AND q.public_status='unactivated')=2
 AND EXISTS(SELECT 1 FROM public.pair_activation_credentials a WHERE a.pair_id=p.id AND a.status='unused') LIMIT 100) available
$$;
CREATE FUNCTION public.sr_checkout_reserve(qid uuid,oid uuid,unit_id uuid,hold_minutes integer)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE pid uuid; lost uuid; ice uuid; until_time timestamptz;
BEGIN
 IF hold_minutes NOT BETWEEN 5 AND 120 OR NOT EXISTS(SELECT 1 FROM public.checkout_quotes q JOIN public.orders o ON o.id=oid
 WHERE q.id=qid AND q.customer_user_id=public.sr_actor_id() AND o.customer_user_id=q.customer_user_id
 AND q.status='open' AND q.expires_at>clock_timestamp() AND q.payload->>'new_pair_count'='1' AND (q.payload->>'reservation_minutes')::integer=hold_minutes AND o.order_status='draft' AND o.placed_at IS NULL
 AND o.total_pkr=q.total_pkr AND o.payment_status='awaiting_transfer' AND o.fulfillment_status='unallocated') THEN
 RAISE EXCEPTION 'Checkout reservation unavailable' USING ERRCODE='23514'; END IF;
 PERFORM 1 FROM public.orders WHERE id=oid FOR UPDATE;
 IF EXISTS(SELECT 1 FROM public.order_pair_units WHERE order_id=oid) THEN
 RAISE EXCEPTION 'One pair per checkout' USING ERRCODE='23514'; END IF;
 SELECT p.id INTO pid FROM public.tag_pairs p
 WHERE p.ownership_status='unclaimed' AND p.inventory_status='qa_passed'
 AND NOT EXISTS(SELECT 1 FROM public.order_pair_units u WHERE u.pair_id=p.id AND u.status IN('reserved','allocated'))
 AND (SELECT count(*) FROM public.qr_codes q WHERE q.pair_id=p.id AND q.is_current AND q.public_status='unactivated')=2
 AND EXISTS(SELECT 1 FROM public.pair_activation_credentials a WHERE a.pair_id=p.id AND a.status='unused')
 ORDER BY p.id FOR UPDATE OF p SKIP LOCKED LIMIT 1;
 IF pid IS NULL THEN RETURN NULL; END IF;
 SELECT id INTO lost FROM public.qr_codes WHERE pair_id=pid AND is_current AND tag_type='lost' AND public_status='unactivated' FOR SHARE;
 SELECT id INTO ice FROM public.qr_codes WHERE pair_id=pid AND is_current AND tag_type='ice' AND public_status='unactivated' FOR SHARE;
 IF lost IS NULL OR ice IS NULL THEN RETURN NULL; END IF;
 until_time=clock_timestamp()+make_interval(mins=>hold_minutes);
 INSERT INTO public.order_pair_units(id,order_id,pair_id,reserved_until) VALUES(unit_id,oid,pid,until_time);
 UPDATE public.tag_pairs SET inventory_status='reserved' WHERE id=pid;
 RETURN jsonb_build_object('unit_id',unit_id,'lost',lost,'ice',ice,'reserved_until',until_time);
END $$;
REVOKE ALL ON FUNCTION public.sr_quote_immutable() FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
REVOKE ALL ON FUNCTION public.sr_checkout_capacity(),public.sr_checkout_reserve(uuid,uuid,uuid,integer) FROM PUBLIC,anon,authenticated,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_checkout_capacity(),public.sr_checkout_reserve(uuid,uuid,uuid,integer) TO safereturn_api;
""")


def downgrade():
    raise RuntimeError(
        "Checkout migration is forward-only; rehearse transactional rollback"
    )
