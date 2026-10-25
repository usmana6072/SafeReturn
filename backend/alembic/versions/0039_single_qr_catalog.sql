ALTER TABLE public.products ADD COLUMN commerce_model varchar(16) NOT NULL DEFAULT 'legacy_pair';
ALTER TABLE public.products ADD CONSTRAINT ck_products_commerce_model CHECK (
 commerce_model IN ('legacy_pair','single_qr') AND (commerce_model<>'single_qr' OR qr_type IS NOT NULL));
CREATE FUNCTION public.sr_product_model_immutable() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NEW.commerce_model IS DISTINCT FROM OLD.commerce_model THEN
  RAISE EXCEPTION 'Product commerce model is immutable' USING ERRCODE='23514';
 END IF;
 IF OLD.commerce_model='legacy_pair' AND NEW.qr_type IS DISTINCT FROM OLD.qr_type THEN
  RAISE EXCEPTION 'Legacy product identity model is preserved' USING ERRCODE='23514';
 END IF;
 IF NEW.qr_type IS DISTINCT FROM OLD.qr_type AND (OLD.lifecycle_status<>'draft' OR EXISTS(SELECT 1 FROM public.order_items WHERE product_id=OLD.id)) THEN
  RAISE EXCEPTION 'Referenced or published product type is immutable' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_product_model_immutable BEFORE UPDATE ON public.products FOR EACH ROW EXECUTE FUNCTION public.sr_product_model_immutable();
CREATE FUNCTION public.sr_template_catalog_type_eligible(vid uuid,kind text) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM public.template_registry_sources WHERE variant_id=vid) THEN RETURN NULL; END IF;
 RETURN EXISTS(SELECT 1 FROM public.print_template_variant_bindings WHERE variant_id=vid AND tag_type=kind AND is_active
  AND public.sr_template_revision_clear(revision_id,false));
END $$;
REVOKE ALL ON FUNCTION public.sr_product_model_immutable(),public.sr_template_catalog_type_eligible(uuid,text) FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_template_catalog_type_eligible(uuid,text) TO safereturn_api;
-- Typed products stay out of legacy customer sale/quote paths until Phase 4.
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
 WHERE p.commerce_model='legacy_pair' AND v.id=ANY(ids) AND v.is_active AND p.lifecycle_status='published' AND c.is_active AND c.slug='qr-stickers'
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
 WHERE p.commerce_model='legacy_pair' AND p.price_per_copy IS NOT NULL AND p.lifecycle_status='published' AND c.is_active AND c.slug='qr-stickers'
 AND p.allows_new_pair AND NOT p.allows_existing_qr
 AND EXISTS(SELECT 1 FROM public.product_variants v WHERE v.product_id=p.id
 AND v.is_active AND v.fulfillment_method='pdf_label' AND v.size_mm>=30 AND v.currency_code='PKR')
 AND (public_sku IS NULL OR EXISTS(SELECT 1 FROM public.product_variants v
 WHERE v.product_id=p.id AND v.sku=public_sku AND v.is_active
 AND v.fulfillment_method='pdf_label' AND v.size_mm>=30 AND v.currency_code='PKR'))
) items
$$;

-- Protect published typed catalog even from direct runtime table writers.
CREATE FUNCTION public.sr_single_catalog_complete() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE pid uuid; p public.products;
BEGIN
 IF TG_TABLE_NAME='products' THEN pid:=NEW.id;
 ELSIF TG_OP='DELETE' THEN pid:=OLD.product_id;
 ELSE pid:=NEW.product_id; END IF;
 SELECT * INTO p FROM public.products WHERE id=pid FOR UPDATE;
 IF NOT FOUND OR p.commerce_model<>'single_qr' OR p.lifecycle_status<>'published' THEN RETURN NULL; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.product_categories WHERE id=p.category_id AND is_active AND slug='qr-stickers')
  OR (SELECT count(*) FROM public.product_images WHERE product_id=pid AND is_primary AND verified_public_url IS NOT NULL)<>1
  OR NOT EXISTS(SELECT 1 FROM public.product_variants WHERE product_id=pid AND is_active)
  OR EXISTS(SELECT 1 FROM public.product_variants WHERE product_id=pid AND is_active AND
   (size_mm IS NULL OR size_mm<30 OR currency_code<>'PKR' OR fulfillment_method<>'pdf_label'
    OR public.sr_template_catalog_type_eligible(id,p.qr_type) IS NOT TRUE))
  OR EXISTS(SELECT 1 FROM public.product_variants WHERE product_id=pid AND is_active GROUP BY size_mm HAVING count(*)>1)
 THEN RAISE EXCEPTION 'Typed product publication requires unique approved sizes and one verified main image' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER sr_single_product_complete AFTER INSERT OR UPDATE ON public.products
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_single_catalog_complete();
CREATE CONSTRAINT TRIGGER sr_single_variant_complete AFTER INSERT OR UPDATE OR DELETE ON public.product_variants
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_single_catalog_complete();
CREATE CONSTRAINT TRIGGER sr_single_image_complete AFTER INSERT OR UPDATE OR DELETE ON public.product_images
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_single_catalog_complete();
REVOKE ALL ON FUNCTION public.sr_single_catalog_complete() FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
