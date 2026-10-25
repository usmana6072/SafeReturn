-- Admission remains disabled until all later allocation/printing/ownership gates pass.
CREATE TABLE public.single_checkout_release (
 singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
 enabled boolean NOT NULL DEFAULT false
);
INSERT INTO public.single_checkout_release(singleton) VALUES(true);
ALTER TABLE public.single_checkout_release ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.single_checkout_release FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
CREATE FUNCTION public.sr_single_checkout_enabled() RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT COALESCE((SELECT enabled FROM public.single_checkout_release WHERE singleton),false)
$$;
REVOKE ALL ON FUNCTION public.sr_single_checkout_enabled() FROM PUBLIC,anon,authenticated,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_single_checkout_enabled() TO safereturn_api;
ALTER TABLE public.orders ADD COLUMN commerce_model varchar(16) NOT NULL DEFAULT 'legacy_pair'
 CHECK(commerce_model IN ('legacy_pair','single_qr'));
ALTER TABLE public.orders ADD COLUMN payment_instructions_snapshot jsonb;
-- No account or Raast details are invented or seeded. Owner approval is a rollout prerequisite.
CREATE TABLE public.checkout_payment_instructions (
 version text PRIMARY KEY CHECK(length(version) BETWEEN 1 AND 80),
 bank_name text NOT NULL CHECK(length(bank_name) BETWEEN 1 AND 160),
 account_title text NOT NULL CHECK(length(account_title) BETWEEN 1 AND 160),
 account_number text NOT NULL CHECK(length(account_number) BETWEEN 4 AND 80),
 raast_id text NOT NULL CHECK(length(raast_id) BETWEEN 4 AND 80),
 instructions_en text NOT NULL CHECK(length(instructions_en) BETWEEN 1 AND 2000),
 instructions_ur text NOT NULL CHECK(length(instructions_ur) BETWEEN 1 AND 2000),
 approved_by uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 approved_at timestamptz NOT NULL,
 active boolean NOT NULL DEFAULT false
);
CREATE UNIQUE INDEX uq_active_checkout_instructions ON public.checkout_payment_instructions(active) WHERE active;
ALTER TABLE public.checkout_payment_instructions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.checkout_payment_instructions FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
CREATE FUNCTION public.sr_checkout_payment_instructions() RETURNS jsonb
LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT jsonb_build_object('version',version,'bank_name',bank_name,'account_title',account_title,
 'account_number',account_number,'raast_id',raast_id,'instructions_en',instructions_en,'instructions_ur',instructions_ur,'currency_code','PKR')
 FROM public.checkout_payment_instructions WHERE active FOR SHARE
$$;
REVOKE ALL ON FUNCTION public.sr_checkout_payment_instructions() FROM PUBLIC,anon,authenticated,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_checkout_payment_instructions() TO safereturn_api;
ALTER TABLE public.checkout_quotes ADD COLUMN commerce_model varchar(16) NOT NULL DEFAULT 'legacy_pair'
 CHECK(commerce_model IN ('legacy_pair','single_qr'));

CREATE TABLE public.order_logical_items (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 order_id uuid NOT NULL REFERENCES public.orders(id) ON DELETE RESTRICT,
 product_id uuid NOT NULL REFERENCES public.products(id) ON DELETE RESTRICT,
 identity_group varchar(80) CHECK(identity_group IS NULL OR identity_group ~ '^[A-Za-z0-9_-]{1,80}$'),
 product_name_snapshot text NOT NULL,
 qr_type_snapshot varchar(8) NOT NULL CHECK(qr_type_snapshot IN ('lost','ice')),
 quantity integer NOT NULL,
 unit_price_snapshot numeric(12,2) NOT NULL CHECK(unit_price_snapshot>=0),
 line_total numeric(12,2) NOT NULL CHECK(line_total=quantity*unit_price_snapshot),
 max_copies_snapshot integer NOT NULL CHECK(max_copies_snapshot BETWEEN 1 AND 100),
 product_version_snapshot integer NOT NULL CHECK(product_version_snapshot>0),
 currency_code varchar(3) NOT NULL DEFAULT 'PKR' CHECK(currency_code='PKR'),
 created_at timestamptz NOT NULL DEFAULT now(),
 CHECK(quantity BETWEEN 1 AND max_copies_snapshot)
);
CREATE UNIQUE INDEX uq_logical_item_identity ON public.order_logical_items(order_id,product_id,coalesce(identity_group,''));
CREATE TABLE public.order_item_sizes (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 logical_item_id uuid NOT NULL REFERENCES public.order_logical_items(id) ON DELETE RESTRICT,
 variant_id uuid NOT NULL REFERENCES public.product_variants(id) ON DELETE RESTRICT,
 variant_name_snapshot text NOT NULL,
 sku_snapshot text NOT NULL,
 size_mm_snapshot numeric(7,2) NOT NULL CHECK(size_mm_snapshot BETWEEN 30 AND 100),
 material_snapshot text,
 copies integer NOT NULL CHECK(copies BETWEEN 1 AND 100),
 variant_version_snapshot integer NOT NULL CHECK(variant_version_snapshot>0),
 print_spec_snapshot jsonb NOT NULL CHECK(jsonb_typeof(print_spec_snapshot)='object'),
 revision_id uuid GENERATED ALWAYS AS ((print_spec_snapshot->>'revision_id')::uuid) STORED NOT NULL REFERENCES public.print_template_revisions(revision_id) ON DELETE RESTRICT,
 approval_id uuid GENERATED ALWAYS AS ((print_spec_snapshot->>'approval_id')::uuid) STORED NOT NULL REFERENCES public.template_qa_approvals(approval_id) ON DELETE RESTRICT,
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(logical_item_id,variant_id), UNIQUE(logical_item_id,size_mm_snapshot)
);
ALTER TABLE public.order_logical_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.order_item_sizes ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.order_logical_items,public.order_item_sizes FROM PUBLIC,anon,authenticated,safereturn_worker;
GRANT SELECT,INSERT ON public.order_logical_items,public.order_item_sizes TO safereturn_api;
CREATE POLICY sr_logical_select ON public.order_logical_items FOR SELECT TO safereturn_api
 USING(public.sr_owns_order(order_id) OR public.sr_is_staff(ARRAY['operations','finance','security_admin','superadmin']));
CREATE POLICY sr_logical_insert ON public.order_logical_items FOR INSERT TO safereturn_api
 WITH CHECK(public.sr_owns_order(order_id) AND EXISTS(SELECT 1 FROM public.orders WHERE id=order_id AND commerce_model='single_qr' AND order_status='draft'));
CREATE POLICY sr_size_select ON public.order_item_sizes FOR SELECT TO safereturn_api
 USING(EXISTS(SELECT 1 FROM public.order_logical_items i WHERE i.id=logical_item_id));
CREATE POLICY sr_size_insert ON public.order_item_sizes FOR INSERT TO safereturn_api
 WITH CHECK(EXISTS(SELECT 1 FROM public.order_logical_items i JOIN public.orders o ON o.id=i.order_id
 WHERE i.id=logical_item_id AND o.customer_user_id=public.sr_actor_id() AND o.order_status='draft' AND o.commerce_model='single_qr'));

CREATE FUNCTION public.sr_item_snapshot_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE oid uuid; o public.orders; p public.products; i public.order_logical_items; v public.product_variants;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Item snapshots are append only' USING ERRCODE='23514'; END IF;
 IF TG_TABLE_NAME='order_logical_items' THEN oid:=NEW.order_id;
 ELSE SELECT * INTO i FROM public.order_logical_items WHERE id=NEW.logical_item_id; oid:=i.order_id; END IF;
 SELECT * INTO o FROM public.orders WHERE id=oid FOR UPDATE;
 IF o.id IS NULL OR o.commerce_model<>'single_qr' OR o.order_status<>'draft' OR o.placed_at IS NOT NULL
 THEN RAISE EXCEPTION 'Item requires draft typed order' USING ERRCODE='23514'; END IF;
 IF TG_TABLE_NAME='order_logical_items' THEN
  SELECT * INTO p FROM public.products WHERE id=NEW.product_id FOR SHARE;
  IF p.id IS NULL OR p.commerce_model<>'single_qr' OR p.lifecycle_status<>'published' OR p.qr_type<>NEW.qr_type_snapshot
   OR (p.name,p.price_per_copy,p.max_order_copies,p.catalog_version) IS DISTINCT FROM
      (NEW.product_name_snapshot,NEW.unit_price_snapshot,NEW.max_copies_snapshot,NEW.product_version_snapshot)
  THEN RAISE EXCEPTION 'Item product/type mismatch' USING ERRCODE='23514'; END IF;
 ELSE
  SELECT * INTO v FROM public.product_variants WHERE id=NEW.variant_id AND product_id=i.product_id FOR SHARE;
  IF v.id IS NULL OR NOT v.is_active OR
   (v.name,v.sku,v.size_mm,v.material,v.catalog_version) IS DISTINCT FROM
   (NEW.variant_name_snapshot,NEW.sku_snapshot,NEW.size_mm_snapshot,NEW.material_snapshot,NEW.variant_version_snapshot)
   OR NEW.print_spec_snapshot->>'tag_type' IS DISTINCT FROM i.qr_type_snapshot
   OR NEW.print_spec_snapshot IS DISTINCT FROM (public.sr_template_resolve(NEW.variant_id,jsonb_build_array(jsonb_build_object('tag_type',i.qr_type_snapshot)))->0)
  THEN RAISE EXCEPTION 'Size product/type/approval mismatch' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_logical_snapshot BEFORE INSERT OR UPDATE OR DELETE ON public.order_logical_items
 FOR EACH ROW EXECUTE FUNCTION public.sr_item_snapshot_guard();
CREATE TRIGGER sr_size_snapshot BEFORE INSERT OR UPDATE OR DELETE ON public.order_item_sizes
 FOR EACH ROW EXECUTE FUNCTION public.sr_item_snapshot_guard();

CREATE FUNCTION public.sr_item_order_model_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP='UPDATE' AND NEW.commerce_model IS DISTINCT FROM OLD.commerce_model THEN
  RAISE EXCEPTION 'Order commerce model is immutable' USING ERRCODE='23514'; END IF;
 IF TG_OP='UPDATE' AND NEW.payment_instructions_snapshot IS DISTINCT FROM OLD.payment_instructions_snapshot THEN
  RAISE EXCEPTION 'Payment instruction snapshot is immutable' USING ERRCODE='23514'; END IF;
 IF NEW.commerce_model='single_qr' THEN
  IF TG_OP='INSERT' AND NOT public.sr_single_checkout_enabled() THEN
   RAISE EXCEPTION 'Single checkout is not released' USING ERRCODE='23514'; END IF;
  IF NEW.payment_instructions_snapshot IS NULL THEN RAISE EXCEPTION 'Official payment instructions required' USING ERRCODE='23514'; END IF;
  IF NEW.payment_status IN ('verified','refunded') OR NEW.fulfillment_status<>'unallocated' THEN
   RAISE EXCEPTION 'Typed settlement/allocation is not released' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_item_order_model BEFORE INSERT OR UPDATE ON public.orders
 FOR EACH ROW EXECUTE FUNCTION public.sr_item_order_model_guard();

CREATE FUNCTION public.sr_check_item_order(oid uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE o public.orders; subtotal numeric;
BEGIN
 SELECT * INTO o FROM public.orders WHERE id=oid FOR UPDATE;
 IF o.id IS NULL OR o.commerce_model<>'single_qr' THEN RETURN; END IF;
 IF EXISTS(SELECT 1 FROM public.order_items WHERE order_id=oid)
  OR EXISTS(SELECT 1 FROM public.order_pair_units WHERE order_id=oid)
 THEN RAISE EXCEPTION 'Cannot mix purchase models' USING ERRCODE='23514'; END IF;
 IF o.placed_at IS NULL THEN RETURN; END IF;
 SELECT sum(line_total) INTO subtotal FROM public.order_logical_items WHERE order_id=oid;
 IF subtotal IS NULL OR subtotal<>o.subtotal_pkr OR o.currency_code<>'PKR'
  OR NOT EXISTS(SELECT 1 FROM public.order_shipping_snapshots WHERE order_id=oid)
  OR EXISTS(SELECT 1 FROM public.order_logical_items i WHERE i.order_id=oid AND
   (i.currency_code<>o.currency_code OR i.quantity<>COALESCE((SELECT sum(copies) FROM public.order_item_sizes WHERE logical_item_id=i.id),0)))
 THEN RAISE EXCEPTION 'Typed purchase quantities, amounts or shipping incomplete' USING ERRCODE='23514'; END IF;
END $$;
CREATE FUNCTION public.sr_item_complete() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE oid uuid;
BEGIN
 IF TG_TABLE_NAME='order_logical_items' THEN oid:=NEW.order_id;
 ELSE SELECT order_id INTO oid FROM public.order_logical_items WHERE id=NEW.logical_item_id; END IF;
 PERFORM public.sr_check_item_order(oid); RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER sr_logical_complete AFTER INSERT ON public.order_logical_items
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_item_complete();
CREATE CONSTRAINT TRIGGER sr_size_complete AFTER INSERT ON public.order_item_sizes
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_item_complete();

CREATE OR REPLACE FUNCTION public.sr_product_model_immutable() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NEW.commerce_model IS DISTINCT FROM OLD.commerce_model OR
  (NEW.qr_type IS DISTINCT FROM OLD.qr_type AND
   (OLD.commerce_model='legacy_pair' OR OLD.lifecycle_status<>'draft'
    OR EXISTS(SELECT 1 FROM public.order_items WHERE product_id=OLD.id)
    OR EXISTS(SELECT 1 FROM public.order_logical_items WHERE product_id=OLD.id)))
 THEN RAISE EXCEPTION 'Product identity model is immutable' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION public.sr_item_checkout_catalog(ids uuid[]) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE result jsonb;
BEGIN
 IF public.sr_actor_id() IS NULL OR NOT public.sr_single_checkout_enabled() OR cardinality(ids)>50 THEN RETURN '[]'::jsonb; END IF;
 PERFORM 1 FROM public.products p WHERE p.id IN(SELECT product_id FROM public.product_variants WHERE id=ANY(ids)) ORDER BY p.id FOR SHARE OF p;
 PERFORM 1 FROM public.product_variants v WHERE v.id=ANY(ids) ORDER BY v.id FOR SHARE OF v;
 PERFORM 1 FROM public.product_categories c WHERE c.id IN(SELECT p.category_id FROM public.products p JOIN public.product_variants v ON v.product_id=p.id WHERE v.id=ANY(ids)) ORDER BY c.id FOR SHARE OF c;
 SELECT COALESCE(jsonb_agg(to_jsonb(v)||jsonb_build_object('price_per_copy',to_char(p.price_per_copy,'FM9999999990.00'),
  'max_order_copies',p.max_order_copies,'qr_type',p.qr_type,'product_name',p.name,'product_version',p.catalog_version)),'[]'::jsonb) INTO result
 FROM public.product_variants v JOIN public.products p ON p.id=v.product_id JOIN public.product_categories c ON c.id=p.category_id
 WHERE v.id=ANY(ids) AND p.commerce_model='single_qr' AND p.lifecycle_status='published' AND p.price_per_copy IS NOT NULL
 AND c.is_active AND c.slug='qr-stickers' AND v.is_active AND v.currency_code='PKR' AND v.fulfillment_method='pdf_label'
 AND v.size_mm BETWEEN 30 AND 100 AND public.sr_template_catalog_type_eligible(v.id,p.qr_type) IS TRUE
 AND EXISTS(SELECT 1 FROM public.product_images WHERE product_id=p.id AND is_primary AND verified_public_url IS NOT NULL);
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION public.sr_item_checkout_catalog(uuid[]) FROM PUBLIC,anon,authenticated,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_item_checkout_catalog(uuid[]) TO safereturn_api;
CREATE FUNCTION public.sr_legacy_item_model_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM public.orders WHERE id=NEW.order_id AND commerce_model='legacy_pair')
  OR NOT EXISTS(SELECT 1 FROM public.products WHERE id=NEW.product_id AND commerce_model='legacy_pair')
 THEN RAISE EXCEPTION 'Legacy item requires legacy order and product' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_legacy_item_model BEFORE INSERT OR UPDATE ON public.order_items
 FOR EACH ROW EXECUTE FUNCTION public.sr_legacy_item_model_guard();
CREATE FUNCTION public.sr_item_payment_gate() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NEW.state IN ('verified','refunded') AND EXISTS(SELECT 1 FROM public.orders WHERE id=NEW.order_id AND commerce_model='single_qr') THEN
  RAISE EXCEPTION 'Typed verified allocation is not released' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_item_payment_gate BEFORE INSERT OR UPDATE ON public.payment_attempts
 FOR EACH ROW EXECUTE FUNCTION public.sr_item_payment_gate();
CREATE FUNCTION public.sr_item_quote_model_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF COALESCE(NEW.payload->>'commerce_model','legacy_pair')<>NEW.commerce_model THEN
  RAISE EXCEPTION 'Quote commerce model mismatch' USING ERRCODE='23514'; END IF;
 IF NEW.commerce_model='single_qr' AND NOT public.sr_single_checkout_enabled() THEN
  RAISE EXCEPTION 'Single checkout is not released' USING ERRCODE='23514'; END IF;
 IF NEW.order_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.orders WHERE id=NEW.order_id AND commerce_model=NEW.commerce_model) THEN
  RAISE EXCEPTION 'Quote/order commerce model mismatch' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_item_quote_model BEFORE INSERT OR UPDATE ON public.checkout_quotes
 FOR EACH ROW EXECUTE FUNCTION public.sr_item_quote_model_guard();
REVOKE ALL ON FUNCTION public.sr_item_snapshot_guard(),public.sr_item_order_model_guard(),public.sr_check_item_order(uuid),public.sr_item_complete()
 FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
REVOKE ALL ON FUNCTION public.sr_legacy_item_model_guard(),public.sr_item_payment_gate(),public.sr_item_quote_model_guard()
 FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;

-- Frozen legacy completion body retained, with explicit model dispatch.
CREATE OR REPLACE FUNCTION public.sr_check_order() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE oid uuid; o public.orders%ROWTYPE; subtotal numeric;
BEGIN
 IF TG_TABLE_NAME='orders' THEN
  oid:=NEW.id;
 ELSIF TG_TABLE_NAME='order_item_qr_uses' THEN
  IF TG_OP='DELETE' THEN
   SELECT order_id INTO oid FROM public.order_items WHERE id=OLD.order_item_id;
  ELSE SELECT order_id INTO oid FROM public.order_items WHERE id=NEW.order_item_id; END IF;
 ELSE
  IF TG_OP='DELETE' THEN oid:=OLD.order_id; ELSE oid:=NEW.order_id; END IF;
 END IF;
 SELECT * INTO o FROM public.orders WHERE id=oid FOR UPDATE;
 IF o.commerce_model='single_qr' THEN PERFORM public.sr_check_item_order(oid); RETURN NULL; END IF;
 IF NOT FOUND OR o.placed_at IS NULL THEN RETURN NULL; END IF;
 SELECT sum(line_total) INTO subtotal FROM public.order_items WHERE order_id=oid;
 IF subtotal IS NULL OR subtotal <> o.subtotal_pkr OR NOT EXISTS (
  SELECT 1 FROM public.order_shipping_snapshots WHERE order_id=oid
 ) THEN RAISE EXCEPTION 'Placed order requires matching lines and shipping snapshot' USING ERRCODE='23514'; END IF;
 IF EXISTS (
  SELECT 1 FROM public.order_items i WHERE i.order_id=oid AND
   (i.currency_code <> o.currency_code OR i.quantity <> COALESCE((
    SELECT sum(u.copies) FROM public.order_item_qr_uses u WHERE u.order_item_id=i.id
   ),0))
 ) THEN RAISE EXCEPTION 'Order copy quantities or currency mismatch' USING ERRCODE='23514'; END IF;
 IF EXISTS (
  SELECT 1 FROM public.order_pair_units p WHERE p.order_id=oid AND
   (NOT EXISTS (SELECT 1 FROM public.order_item_qr_uses u WHERE u.pair_unit_id=p.id AND u.tag_type_snapshot='lost')
    OR NOT EXISTS (SELECT 1 FROM public.order_item_qr_uses u WHERE u.pair_unit_id=p.id AND u.tag_type_snapshot='ice'))
 ) THEN RAISE EXCEPTION 'New pair requires both Lost and ICE copies' USING ERRCODE='23514'; END IF;
 IF o.payment_status='verified' AND NOT EXISTS (
  SELECT 1 FROM public.payment_attempts p WHERE p.order_id=oid AND p.state='verified'
   AND p.amount=o.total_pkr AND p.currency_code=o.currency_code
 ) THEN RAISE EXCEPTION 'Order payment status requires matching verified attempt' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $$;

-- Public typed admission is controlled by the disabled release row.
CREATE OR REPLACE FUNCTION public.sr_public_catalog(public_sku text DEFAULT NULL)
RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
SELECT COALESCE(jsonb_agg(card ORDER BY featured_sort_order,id),'[]'::jsonb) FROM (
 SELECT p.id,p.featured_sort_order,jsonb_build_object(
 'commerce_model',p.commerce_model,'qr_type',p.qr_type,'product_id',p.id,'slug',p.slug,'name',p.name,'description',p.description,
 'price_per_copy',to_char(p.price_per_copy,'FM9999999990.00'),'max_order_copies',p.max_order_copies,
 'featured',p.is_featured,'catalog_version',p.catalog_version,
 'category',jsonb_build_object('id',c.id,'slug',c.slug,'name',c.name),
 'images',COALESCE((SELECT jsonb_agg(jsonb_build_object(
 'url',i.verified_public_url,'alt_text',i.alt_text,'is_primary',i.is_primary)
 ORDER BY i.is_primary DESC,i.sort_order,i.id) FROM public.product_images i
 WHERE i.product_id=p.id AND i.verified_public_url IS NOT NULL),'[]'::jsonb),
 'variants',(SELECT jsonb_agg(jsonb_build_object(
 'variant_id',v.id,'sku',v.sku,'name',v.name,'size_mm',v.size_mm,
 'material',v.material,'color',v.color,'currency_code',v.currency_code,
 'unit_price_pkr',to_char(p.price_per_copy,'FM9999999990.00'),
 'fulfillment_method',v.fulfillment_method) ORDER BY v.sort_order,v.id)
 FROM public.product_variants v WHERE v.product_id=p.id AND v.is_active
 AND v.fulfillment_method='pdf_label' AND v.size_mm>=30 AND v.currency_code='PKR' AND (p.commerce_model='legacy_pair' OR (v.size_mm<=100 AND public.sr_template_catalog_type_eligible(v.id,p.qr_type) IS TRUE)))
 ) AS card FROM public.products p JOIN public.product_categories c ON c.id=p.category_id
 WHERE (p.commerce_model='legacy_pair' OR (p.commerce_model='single_qr' AND public.sr_single_checkout_enabled() AND EXISTS(SELECT 1 FROM public.product_images WHERE product_id=p.id AND is_primary AND verified_public_url IS NOT NULL))) AND p.price_per_copy IS NOT NULL AND p.lifecycle_status='published' AND c.is_active AND c.slug='qr-stickers'
 AND (p.commerce_model='single_qr' OR (p.allows_new_pair AND NOT p.allows_existing_qr))
 AND EXISTS(SELECT 1 FROM public.product_variants v WHERE v.product_id=p.id
 AND v.is_active AND v.fulfillment_method='pdf_label' AND v.size_mm>=30 AND v.currency_code='PKR' AND (p.commerce_model='legacy_pair' OR (v.size_mm<=100 AND public.sr_template_catalog_type_eligible(v.id,p.qr_type) IS TRUE)))
 AND (public_sku IS NULL OR EXISTS(SELECT 1 FROM public.product_variants v
 WHERE v.product_id=p.id AND v.sku=public_sku AND v.is_active
 AND v.fulfillment_method='pdf_label' AND v.size_mm>=30 AND v.currency_code='PKR' AND (p.commerce_model='legacy_pair' OR (v.size_mm<=100 AND public.sr_template_catalog_type_eligible(v.id,p.qr_type) IS TRUE))))
) items
$$;
