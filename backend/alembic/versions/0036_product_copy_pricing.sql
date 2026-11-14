-- v1.4: no guessed backfill, historical order/quote snapshots remain immutable.
ALTER TABLE public.products ADD COLUMN price_per_copy numeric(12,2)
 CONSTRAINT ck_products_price_per_copy CHECK(price_per_copy BETWEEN 0 AND 9999999999.99);
ALTER TABLE public.products ADD COLUMN max_order_copies integer NOT NULL DEFAULT 100
 CONSTRAINT ck_products_max_order_copies CHECK(max_order_copies BETWEEN 1 AND 100);
-- New products require an explicit price; legacy NULL rows may be configured later.
CREATE FUNCTION public.sr_product_copy_price_required() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF NEW.price_per_copy IS NULL AND (TG_OP='INSERT' OR OLD.price_per_copy IS NOT NULL) THEN
  RAISE EXCEPTION 'Product price per copy is required' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_product_copy_price_required BEFORE INSERT OR UPDATE ON public.products
 FOR EACH ROW EXECUTE FUNCTION public.sr_product_copy_price_required();
CREATE OR REPLACE FUNCTION public.sr_checkout_catalog(ids uuid[]) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE result jsonb;
BEGIN
 IF public.sr_actor_id() IS NULL OR cardinality(ids)>50 THEN RETURN '[]'::jsonb; END IF;
 PERFORM 1 FROM public.products p WHERE p.id IN(SELECT product_id FROM public.product_variants WHERE id=ANY(ids)) ORDER BY p.id FOR SHARE OF p;
 PERFORM 1 FROM public.product_variants v WHERE v.id=ANY(ids) ORDER BY v.id FOR SHARE OF v;
 PERFORM 1 FROM public.product_categories c WHERE c.id IN(SELECT p.category_id FROM public.products p JOIN public.product_variants v ON v.product_id=p.id WHERE v.id=ANY(ids)) ORDER BY c.id FOR SHARE OF c;
 SELECT coalesce(jsonb_agg(to_jsonb(v)||jsonb_build_object('unit_price',to_char(p.price_per_copy,'FM9999999990.00'),'price_per_copy',to_char(p.price_per_copy,'FM9999999990.00'),'max_order_copies',p.max_order_copies,'product_name',p.name,'product_version',p.catalog_version,'allows_new_pair',p.allows_new_pair,'allows_existing_qr',p.allows_existing_qr)),'[]'::jsonb) INTO result
 FROM public.product_variants v JOIN public.products p ON p.id=v.product_id JOIN public.product_categories c ON c.id=p.category_id
 WHERE v.id=ANY(ids) AND v.is_active AND p.lifecycle_status='published' AND c.is_active AND c.slug='qr-stickers'
 AND v.currency_code='PKR' AND v.fulfillment_method='pdf_label' AND v.size_mm>=30;
 RETURN result;
END $$;
CREATE OR REPLACE FUNCTION public.sr_public_catalog(public_sku text DEFAULT NULL)
RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
SELECT COALESCE(jsonb_agg(card ORDER BY featured_sort_order,id),'[]'::jsonb) FROM (
 SELECT p.id,p.featured_sort_order,jsonb_build_object(
 'product_id',p.id,'slug',p.slug,'name',p.name,'description',p.description,
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
 AND v.fulfillment_method='pdf_label' AND v.size_mm>=30 AND v.currency_code='PKR')
 ) AS card FROM public.products p JOIN public.product_categories c ON c.id=p.category_id
 WHERE p.price_per_copy IS NOT NULL AND p.lifecycle_status='published' AND c.is_active AND c.slug='qr-stickers'
 AND p.allows_new_pair AND NOT p.allows_existing_qr
 AND EXISTS(SELECT 1 FROM public.product_variants v WHERE v.product_id=p.id
 AND v.is_active AND v.fulfillment_method='pdf_label' AND v.size_mm>=30 AND v.currency_code='PKR')
 AND (public_sku IS NULL OR EXISTS(SELECT 1 FROM public.product_variants v
 WHERE v.product_id=p.id AND v.sku=public_sku AND v.is_active
 AND v.fulfillment_method='pdf_label' AND v.size_mm>=30 AND v.currency_code='PKR'))
) items
$$;
