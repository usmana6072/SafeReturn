"""Versioned catalog and verified public-media projection; no domain row changes."""

from alembic import op

revision = "0015_public_catalog"
down_revision = "0014a_notification_delivery"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='5s'")
    for table in ("products", "product_variants", "product_categories"):
        op.execute(
            f"ALTER TABLE public.{table} ADD COLUMN catalog_version integer NOT NULL DEFAULT 1 CHECK (catalog_version>0)"
        )
    op.execute("ALTER TABLE public.product_images ADD COLUMN verified_public_url text")
    op.execute("""
CREATE FUNCTION public.sr_public_catalog(public_sku text DEFAULT NULL)
RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
SELECT COALESCE(jsonb_agg(card ORDER BY featured_sort_order,id),'[]'::jsonb) FROM (
 SELECT p.id,p.featured_sort_order,jsonb_build_object(
 'product_id',p.id,'slug',p.slug,'name',p.name,'description',p.description,
 'featured',p.is_featured,'catalog_version',p.catalog_version,
 'category',jsonb_build_object('id',c.id,'slug',c.slug,'name',c.name),
 'images',COALESCE((SELECT jsonb_agg(jsonb_build_object(
 'url',i.verified_public_url,'alt_text',i.alt_text,'is_primary',i.is_primary)
 ORDER BY i.is_primary DESC,i.sort_order,i.id) FROM public.product_images i
 WHERE i.product_id=p.id AND i.verified_public_url IS NOT NULL),'[]'::jsonb),
 'variants',(SELECT jsonb_agg(jsonb_build_object(
 'variant_id',v.id,'sku',v.sku,'name',v.name,'size_mm',v.size_mm,
 'material',v.material,'color',v.color,'currency_code',v.currency_code,
 'unit_price_pkr',to_char(v.unit_price,'FM9999999990.00'),
 'fulfillment_method',v.fulfillment_method) ORDER BY v.sort_order,v.id)
 FROM public.product_variants v WHERE v.product_id=p.id AND v.is_active
 AND v.fulfillment_method='pdf_label' AND v.size_mm>=30 AND v.currency_code='PKR')
 ) AS card FROM public.products p JOIN public.product_categories c ON c.id=p.category_id
 WHERE p.lifecycle_status='published' AND c.is_active AND c.slug='qr-stickers'
 AND p.allows_new_pair AND NOT p.allows_existing_qr
 AND EXISTS(SELECT 1 FROM public.product_variants v WHERE v.product_id=p.id
 AND v.is_active AND v.fulfillment_method='pdf_label' AND v.size_mm>=30 AND v.currency_code='PKR')
 AND (public_sku IS NULL OR EXISTS(SELECT 1 FROM public.product_variants v
 WHERE v.product_id=p.id AND v.sku=public_sku AND v.is_active
 AND v.fulfillment_method='pdf_label' AND v.size_mm>=30 AND v.currency_code='PKR'))
) items
$$;
REVOKE ALL ON FUNCTION public.sr_public_catalog(text) FROM PUBLIC,anon,authenticated,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_public_catalog(text) TO safereturn_api;
-- Unlink metadata only. No remote object deletion and no other DELETE grants.
GRANT DELETE ON public.product_images TO safereturn_api;
CREATE POLICY sr_safereturn_api_delete ON public.product_images FOR DELETE TO safereturn_api
 USING(public.sr_is_staff(ARRAY['operations','security_admin','superadmin']));
""")


def downgrade():
    raise RuntimeError("Catalog revision is forward-only")
