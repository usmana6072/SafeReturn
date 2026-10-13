-- Frozen guard source for revision 0002_commerce. Services still authorize actors.
CREATE FUNCTION public.sr_order_history() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE oid uuid; placed timestamptz;
BEGIN
 IF TG_TABLE_NAME = 'orders' THEN
  IF TG_OP = 'DELETE' THEN
   IF OLD.placed_at IS NOT NULL THEN RAISE EXCEPTION 'Placed order history is immutable' USING ERRCODE='23514'; END IF;
   RETURN OLD;
  END IF;
  IF TG_OP = 'UPDATE' AND OLD.placed_at IS NOT NULL AND
     (NEW.id,NEW.order_number,NEW.customer_user_id,NEW.currency_code,NEW.subtotal_pkr,
      NEW.shipping_pkr,NEW.tax_pkr,NEW.discount_pkr,NEW.total_pkr,NEW.placed_at,NEW.created_at)
     IS DISTINCT FROM
     (OLD.id,OLD.order_number,OLD.customer_user_id,OLD.currency_code,OLD.subtotal_pkr,
      OLD.shipping_pkr,OLD.tax_pkr,OLD.discount_pkr,OLD.total_pkr,OLD.placed_at,OLD.created_at) THEN
   RAISE EXCEPTION 'Placed order snapshots are immutable' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
 END IF;
 IF TG_TABLE_NAME = 'order_item_qr_uses' THEN
  IF TG_OP='DELETE' THEN
   SELECT order_id INTO oid FROM public.order_items WHERE id=OLD.order_item_id;
  ELSE
   SELECT order_id INTO oid FROM public.order_items WHERE id=NEW.order_item_id;
   IF TG_OP='UPDATE' AND NEW.order_item_id <> OLD.order_item_id THEN
    RAISE EXCEPTION 'Cannot move historical QR use' USING ERRCODE='23514';
   END IF;
  END IF;
 ELSE
  IF TG_OP='DELETE' THEN oid:=OLD.order_id; ELSE oid:=NEW.order_id; END IF;
  IF TG_OP='UPDATE' AND NEW.order_id <> OLD.order_id THEN
   RAISE EXCEPTION 'Cannot move purchase snapshot' USING ERRCODE='23514';
  END IF;
 END IF;
 SELECT placed_at INTO placed FROM public.orders WHERE id=oid FOR UPDATE;
 IF placed IS NOT NULL THEN
  RAISE EXCEPTION 'Placed purchase records are immutable' USING ERRCODE='23514';
 END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; END IF;
 IF TG_TABLE_NAME='order_items' THEN
  IF NOT EXISTS (SELECT 1 FROM public.product_variants WHERE id=NEW.variant_id AND product_id=NEW.product_id) THEN
   RAISE EXCEPTION 'Variant does not belong to product' USING ERRCODE='23514';
  END IF;
 ELSIF TG_TABLE_NAME='order_shipping_snapshots' THEN
  IF NOT EXISTS (
   SELECT 1 FROM public.shipping_addresses a JOIN public.orders o ON o.customer_user_id=a.customer_user_id
    WHERE a.id=NEW.source_address_id AND o.id=NEW.order_id
  ) THEN RAISE EXCEPTION 'Shipping address owner mismatch' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE TRIGGER sr_order_history BEFORE INSERT OR UPDATE OR DELETE ON public.orders
FOR EACH ROW EXECUTE FUNCTION public.sr_order_history();
CREATE TRIGGER sr_item_history BEFORE INSERT OR UPDATE OR DELETE ON public.order_items
FOR EACH ROW EXECUTE FUNCTION public.sr_order_history();
CREATE TRIGGER sr_use_history BEFORE INSERT OR UPDATE OR DELETE ON public.order_item_qr_uses
FOR EACH ROW EXECUTE FUNCTION public.sr_order_history();
CREATE TRIGGER sr_shipping_history BEFORE INSERT OR UPDATE OR DELETE ON public.order_shipping_snapshots
FOR EACH ROW EXECUTE FUNCTION public.sr_order_history();

CREATE FUNCTION public.sr_qr_use_relation() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE qr_row public.qr_codes%ROWTYPE; oid uuid; customer uuid; product public.products%ROWTYPE;
BEGIN
 SELECT i.order_id,o.customer_user_id INTO oid,customer
 FROM public.order_items i JOIN public.orders o ON o.id=i.order_id
 JOIN public.products p ON p.id=i.product_id WHERE i.id=NEW.order_item_id;
 PERFORM 1 FROM public.orders WHERE id=oid FOR UPDATE;
 SELECT p.* INTO product FROM public.products p JOIN public.order_items i ON i.product_id=p.id WHERE i.id=NEW.order_item_id;
 -- Read and lock the parent before QR, matching the identity mutation lock order.
 PERFORM 1 FROM public.tag_pairs p JOIN public.qr_codes q ON q.pair_id=p.id
 WHERE q.id=NEW.qr_code_id FOR UPDATE OF p;
 SELECT * INTO qr_row FROM public.qr_codes WHERE id=NEW.qr_code_id FOR SHARE;
 IF NOT FOUND OR qr_row.tag_type <> NEW.tag_type_snapshot OR NOT qr_row.is_current
    OR qr_row.public_status IN ('revoked','admin_suspended') THEN
  RAISE EXCEPTION 'QR use does not match eligible identity' USING ERRCODE='23514';
 END IF;
 IF NEW.use_kind='new_pair' THEN
  IF NOT product.allows_new_pair OR NOT EXISTS (
   SELECT 1 FROM public.order_pair_units u WHERE u.id=NEW.pair_unit_id
    AND u.order_id=oid AND u.pair_id=qr_row.pair_id AND u.status IN ('reserved','allocated')
  ) THEN RAISE EXCEPTION 'QR use pair/order mismatch' USING ERRCODE='23514'; END IF;
 ELSE
  IF NOT product.allows_existing_qr OR NOT EXISTS (
   SELECT 1 FROM public.tag_pairs WHERE id=qr_row.pair_id AND owner_user_id=customer AND ownership_status='active'
  ) THEN RAISE EXCEPTION 'Existing QR is not owned by customer or reuse is disabled' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_qr_use_relation BEFORE INSERT OR UPDATE ON public.order_item_qr_uses
FOR EACH ROW EXECUTE FUNCTION public.sr_qr_use_relation();

CREATE FUNCTION public.sr_pair_claim_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE ownership text; placed timestamptz;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Reservation history cannot be deleted' USING ERRCODE='23514'; END IF;
 SELECT placed_at INTO placed FROM public.orders WHERE id=NEW.order_id FOR UPDATE;
 SELECT ownership_status INTO ownership FROM public.tag_pairs WHERE id=NEW.pair_id FOR UPDATE;
 IF TG_OP='INSERT' THEN
  IF placed IS NOT NULL OR ownership <> 'unclaimed' THEN
   RAISE EXCEPTION 'Pair is not eligible for new reservation' USING ERRCODE='23514';
  END IF;
 ELSE
  IF (NEW.id,NEW.order_id,NEW.pair_id,NEW.kind,NEW.created_at) IS DISTINCT FROM
     (OLD.id,OLD.order_id,OLD.pair_id,OLD.kind,OLD.created_at) THEN
   RAISE EXCEPTION 'Reservation identity is immutable' USING ERRCODE='23514';
  END IF;
  IF OLD.status='allocated' AND (NEW.status <> 'allocated' OR NEW.allocated_at IS DISTINCT FROM OLD.allocated_at) THEN
   RAISE EXCEPTION 'Permanent allocation cannot be recycled' USING ERRCODE='23514';
  END IF;
  IF OLD.status IN ('released','cancelled') AND NEW.status <> OLD.status THEN
   RAISE EXCEPTION 'Closed reservation cannot be resurrected' USING ERRCODE='23514';
  END IF;
 END IF;
 IF NEW.status IN ('released','cancelled') AND EXISTS (
  SELECT 1 FROM public.payment_attempts WHERE order_id=NEW.order_id
   AND state IN ('submitted','under_review','verified','disputed')
 ) THEN RAISE EXCEPTION 'Payment reconciliation prevents reservation release' USING ERRCODE='23514'; END IF;
 IF NEW.status='allocated' AND NOT EXISTS (
  SELECT 1 FROM public.orders o JOIN public.payment_attempts p ON p.order_id=o.id
   WHERE o.id=NEW.order_id AND o.placed_at IS NOT NULL AND o.payment_status='verified'
    AND p.state='verified' AND p.amount=o.total_pkr AND p.currency_code=o.currency_code
 ) THEN RAISE EXCEPTION 'Allocation requires verified settlement' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_pair_claim_guard BEFORE INSERT OR UPDATE OR DELETE ON public.order_pair_units
FOR EACH ROW EXECUTE FUNCTION public.sr_pair_claim_guard();

CREATE FUNCTION public.sr_payment_history() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE oid uuid;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Payment history cannot be deleted' USING ERRCODE='23514'; END IF;
 IF TG_TABLE_NAME='payment_reviews' THEN
  IF TG_OP='UPDATE' THEN RAISE EXCEPTION 'Payment reviews are append only' USING ERRCODE='23514'; END IF;
  SELECT order_id INTO oid FROM public.payment_attempts WHERE id=NEW.attempt_id;
 ELSE
  oid:=NEW.order_id;
  IF TG_OP='UPDATE' AND (NEW.id,NEW.order_id,NEW.provider_key,NEW.idempotency_key,NEW.amount,NEW.currency_code,NEW.created_at)
     IS DISTINCT FROM (OLD.id,OLD.order_id,OLD.provider_key,OLD.idempotency_key,OLD.amount,OLD.currency_code,OLD.created_at) THEN
   RAISE EXCEPTION 'Payment identity and amount are immutable' USING ERRCODE='23514';
  END IF;
  IF TG_OP='UPDATE' AND OLD.verified_at IS NOT NULL AND
     (NEW.verified_at IS DISTINCT FROM OLD.verified_at OR NEW.state NOT IN ('verified','refunded','disputed')) THEN
   RAISE EXCEPTION 'Verified payment history cannot be erased' USING ERRCODE='23514';
  END IF;
 END IF;
 PERFORM 1 FROM public.orders WHERE id=oid FOR UPDATE;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_payment_history BEFORE INSERT OR UPDATE OR DELETE ON public.payment_attempts
FOR EACH ROW EXECUTE FUNCTION public.sr_payment_history();
CREATE TRIGGER sr_review_history BEFORE INSERT OR UPDATE OR DELETE ON public.payment_reviews
FOR EACH ROW EXECUTE FUNCTION public.sr_payment_history();

CREATE FUNCTION public.sr_check_payment() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE pid uuid; p public.payment_attempts%ROWTYPE; o public.orders%ROWTYPE;
BEGIN
 IF TG_TABLE_NAME='payment_reviews' THEN pid:=NEW.attempt_id; ELSE pid:=NEW.id; END IF;
 SELECT * INTO p FROM public.payment_attempts WHERE id=pid;
 SELECT * INTO o FROM public.orders WHERE id=p.order_id FOR UPDATE;
 IF p.state='verified' THEN
  IF o.placed_at IS NULL OR p.amount <> o.total_pkr OR p.currency_code <> o.currency_code THEN
   RAISE EXCEPTION 'Verified payment amount/currency/order mismatch' USING ERRCODE='23514';
  END IF;
  IF p.provider_key='manual_bank' AND (p.reviewed_by IS NULL OR NOT EXISTS (
   SELECT 1 FROM public.payment_reviews r WHERE r.attempt_id=p.id AND r.decision='verify'
    AND r.bank_verified AND r.reviewed_by=p.reviewed_by
  )) THEN RAISE EXCEPTION 'Manual payment requires independent bank review' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER sr_payment_verified AFTER INSERT OR UPDATE ON public.payment_attempts
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_check_payment();
CREATE CONSTRAINT TRIGGER sr_review_verified AFTER INSERT ON public.payment_reviews
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_check_payment();

CREATE FUNCTION public.sr_check_order() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
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
CREATE CONSTRAINT TRIGGER sr_order_complete AFTER INSERT OR UPDATE ON public.orders
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_check_order();
CREATE CONSTRAINT TRIGGER sr_item_complete AFTER INSERT OR UPDATE OR DELETE ON public.order_items
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_check_order();
CREATE CONSTRAINT TRIGGER sr_use_complete AFTER INSERT OR UPDATE OR DELETE ON public.order_item_qr_uses
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_check_order();
CREATE CONSTRAINT TRIGGER sr_unit_complete AFTER INSERT OR UPDATE ON public.order_pair_units
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_check_order();
CREATE CONSTRAINT TRIGGER sr_shipping_complete AFTER INSERT OR UPDATE OR DELETE ON public.order_shipping_snapshots
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_check_order();
CREATE CONSTRAINT TRIGGER sr_payment_order_complete AFTER INSERT OR UPDATE ON public.payment_attempts
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_check_order();

CREATE FUNCTION public.sr_shipment_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
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
 PERFORM 1 FROM public.orders o JOIN public.payment_attempts a ON a.order_id=o.id
 WHERE o.id=oid AND o.payment_status='verified' AND o.placed_at IS NOT NULL
  AND a.state='verified' AND a.amount=o.total_pkr AND a.currency_code=o.currency_code FOR UPDATE OF o;
 IF NOT FOUND THEN RAISE EXCEPTION 'Shipment requires verified paid order' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_shipment_guard BEFORE INSERT OR UPDATE ON public.shipments
FOR EACH ROW EXECUTE FUNCTION public.sr_shipment_guard();
CREATE TRIGGER sr_shipment_pair_guard BEFORE INSERT OR UPDATE ON public.shipment_pairs
FOR EACH ROW EXECUTE FUNCTION public.sr_shipment_guard();

CREATE FUNCTION public.sr_check_shipment() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE sid uuid; s public.shipments%ROWTYPE;
BEGIN
 IF TG_TABLE_NAME='shipments' THEN sid:=NEW.id;
 ELSIF TG_OP='DELETE' THEN sid:=OLD.shipment_id; ELSE sid:=NEW.shipment_id; END IF;
 SELECT * INTO s FROM public.shipments WHERE id=sid FOR UPDATE;
 IF NOT FOUND OR s.status NOT IN ('packed','dispatched','delivered') THEN RETURN NULL; END IF;
 IF NOT EXISTS (
  SELECT 1 FROM public.orders o JOIN public.payment_attempts a ON a.order_id=o.id
   WHERE o.id=s.order_id AND o.payment_status='verified' AND a.state='verified'
    AND a.amount=o.total_pkr AND a.currency_code=o.currency_code
 ) THEN RAISE EXCEPTION 'Shipment release requires matching verified settlement' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS (SELECT 1 FROM public.shipment_pairs WHERE shipment_id=sid) OR EXISTS (
  SELECT 1 FROM public.shipment_pairs p WHERE p.shipment_id=sid AND
   (NOT p.packed_qa_confirmed OR NOT COALESCE((
     SELECT approved FROM public.pair_print_qa WHERE pair_id=p.pair_id ORDER BY qa_round DESC LIMIT 1
    ),false))
 ) THEN RAISE EXCEPTION 'Shipment release requires packed QA-approved pairs' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER sr_shipment_complete AFTER INSERT OR UPDATE ON public.shipments
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_check_shipment();
CREATE CONSTRAINT TRIGGER sr_shipment_pairs_complete AFTER INSERT OR UPDATE OR DELETE ON public.shipment_pairs
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_check_shipment();
