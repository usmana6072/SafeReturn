"""Narrow operations eligibility without exposing finance rows; shipment commit guard."""

from alembic import op

revision = "0018_fulfillment_eligibility"
down_revision = "0017_print_download_grants"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='5s'")
    op.execute("""CREATE OR REPLACE FUNCTION public.sr_shipment_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE oid uuid; sid uuid; p uuid;
BEGIN
 IF TG_TABLE_NAME='shipments' THEN
  oid:=NEW.order_id;
  IF TG_OP='UPDATE' AND (NEW.id,NEW.order_id,NEW.shipping_address_id) IS DISTINCT FROM
      (OLD.id,OLD.order_id,OLD.shipping_address_id) THEN
   RAISE EXCEPTION 'Shipment identity is immutable' USING ERRCODE='23514';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM public.order_shipping_snapshots WHERE order_id=oid AND source_address_id=NEW.shipping_address_id) THEN
   RAISE EXCEPTION 'Shipment must use purchase shipping snapshot' USING ERRCODE='23514';
  END IF;
 ELSE
  SELECT order_id INTO oid FROM public.shipments WHERE id=NEW.shipment_id;
  p:=NEW.pair_id;
  IF TG_OP='UPDATE' AND (NEW.shipment_id,NEW.pair_id) IS DISTINCT FROM (OLD.shipment_id,OLD.pair_id) THEN
   RAISE EXCEPTION 'Shipment pair membership is immutable' USING ERRCODE='23514';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM public.order_pair_units WHERE order_id=oid AND pair_id=p AND status='allocated') THEN
   RAISE EXCEPTION 'Shipment pair is not allocated to this order' USING ERRCODE='23514';
  END IF;
  IF NEW.packed_qa_confirmed AND NOT COALESCE((
   SELECT approved FROM public.pair_print_qa WHERE pair_id=p ORDER BY qa_round DESC LIMIT 1
  ),false) THEN RAISE EXCEPTION 'Packing requires latest physical QA approval' USING ERRCODE='23514'; END IF;
 END IF;
 IF TG_TABLE_NAME='shipments' THEN
  IF TG_OP='UPDATE' THEN
   IF (NEW.status='exception' AND OLD.status IN ('preparing','packed','dispatched')) OR
      (NEW.status='returned' AND OLD.status IN ('dispatched','exception')) THEN RETURN NEW; END IF;
  END IF;
 END IF;
 PERFORM 1 FROM public.orders o JOIN public.payment_attempts a ON a.order_id=o.id
 WHERE o.id=oid AND o.payment_status='verified' AND o.placed_at IS NOT NULL
  AND a.state='verified' AND a.amount=o.total_pkr AND a.currency_code=o.currency_code FOR UPDATE OF o;
 IF NOT FOUND THEN RAISE EXCEPTION 'Shipment requires verified paid order' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
""")
    op.execute("""CREATE FUNCTION public.sr_fulfillment_eligible(oid uuid) RETURNS boolean
      LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
      SELECT public.sr_is_staff(ARRAY['operations']) AND EXISTS(SELECT 1 FROM public.orders o WHERE o.id=oid AND o.order_status='placed' AND o.placed_at IS NOT NULL AND o.payment_status='verified'
 AND EXISTS(SELECT 1 FROM public.payment_attempts a WHERE a.order_id=o.id AND a.state='verified' AND a.amount=o.total_pkr AND a.currency_code=o.currency_code)
 AND EXISTS(SELECT 1 FROM public.order_pair_units u WHERE u.order_id=o.id)
 AND NOT EXISTS(SELECT 1 FROM public.order_pair_units u WHERE u.order_id=o.id AND (u.status<>'allocated' OR NOT coalesce((SELECT q.approved FROM public.pair_print_qa q WHERE q.pair_id=u.pair_id ORDER BY q.qa_round DESC LIMIT 1),false)))
 AND EXISTS(SELECT 1 FROM public.print_jobs j JOIN public.print_artifacts a ON a.print_job_id=j.id
  WHERE j.order_id=o.id AND j.job_revision=(SELECT max(j2.job_revision) FROM public.print_jobs j2 WHERE j2.order_id=o.id)
  AND j.status='qa_passed' AND a.format='pdf' AND a.deleted_at IS NULL AND (a.retention_until IS NULL OR a.retention_until>clock_timestamp())
  AND coalesce((SELECT q.approved AND q.artifact_sha256=a.sha256_hex FROM public.print_job_qa q WHERE q.print_job_id=j.id ORDER BY q.created_at DESC,q.id DESC LIMIT 1),false))
 AND NOT EXISTS(SELECT 1 FROM public.order_item_qr_uses u JOIN public.order_items i ON i.id=u.order_item_id
   LEFT JOIN public.qr_codes q ON q.id=u.qr_code_id LEFT JOIN public.tag_pairs p ON p.id=q.pair_id
   LEFT JOIN public.order_pair_units pu ON pu.id=u.pair_unit_id
   WHERE i.order_id=o.id AND (q.id IS NULL OR NOT q.is_current OR q.public_status NOT IN ('unactivated','active')
   OR q.revoked_at IS NOT NULL OR p.revoked_at IS NOT NULL OR p.ownership_status IN ('disputed','revoked','transfer_pending') OR p.inventory_status='rejected'
   OR (p.owner_user_id IS NOT NULL AND p.owner_user_id<>o.customer_user_id)
   OR pu.pair_id IS DISTINCT FROM q.pair_id)))
      $$;
      REVOKE ALL ON FUNCTION public.sr_fulfillment_eligible(uuid) FROM PUBLIC,anon,authenticated;
      GRANT EXECUTE ON FUNCTION public.sr_fulfillment_eligible(uuid) TO safereturn_api;
      CREATE FUNCTION public.sr_fulfillment_complete() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
      DECLARE sid uuid; oid uuid; state text;
      BEGIN
       IF TG_TABLE_NAME='shipments' THEN sid:=NEW.id; ELSIF TG_OP='DELETE' THEN sid:=OLD.shipment_id; ELSE sid:=NEW.shipment_id; END IF;
       SELECT order_id,status INTO oid,state FROM public.shipments WHERE id=sid;
       IF state IN ('preparing','packed','dispatched','delivered') AND (NOT public.sr_fulfillment_eligible(oid)
        OR EXISTS(SELECT 1 FROM public.order_pair_units u WHERE u.order_id=oid AND u.status='allocated'
         AND NOT EXISTS(SELECT 1 FROM public.shipment_pairs sp WHERE sp.shipment_id=sid AND sp.pair_id=u.pair_id))) THEN
         RAISE EXCEPTION 'Shipment requires complete settled allocation and current physical QA' USING ERRCODE='23514';
       END IF;
       RETURN NULL;
      END $$;
      REVOKE ALL ON FUNCTION public.sr_fulfillment_complete() FROM PUBLIC,anon,authenticated;
      CREATE CONSTRAINT TRIGGER sr_fulfillment_complete AFTER INSERT OR UPDATE ON public.shipments DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_fulfillment_complete();
      CREATE CONSTRAINT TRIGGER sr_fulfillment_pairs_complete AFTER INSERT OR UPDATE OR DELETE ON public.shipment_pairs DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_fulfillment_complete();
    """)


def downgrade():
    raise RuntimeError(
        "Forward-only fulfillment guard; restore application without destructive downgrade"
    )
