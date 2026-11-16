CREATE OR REPLACE FUNCTION public.sr_typed_payment_autogenerate(sid uuid,oid uuid,seed text)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE o public.orders; t public.typed_order_settlements; kind text; required integer;
 available integer; missing integer; bid uuid; label text;
BEGIN
 PERFORM public.sr_template_registry_gate(false);
 IF NOT public.sr_typed_allocation_authorized(sid,ARRAY['finance','operations']) THEN RETURN jsonb_build_object('error','FORBIDDEN'); END IF;
 SELECT * INTO o FROM public.orders WHERE id=oid FOR UPDATE;
 IF o.id IS NULL THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
 SELECT * INTO t FROM public.typed_order_settlements WHERE order_id=oid FOR UPDATE;
 IF o.commerce_model<>'single_qr' OR o.order_status<>'placed' OR o.payment_status<>'verified' OR t.order_id IS NULL THEN
  RETURN jsonb_build_object('error','VERIFIED_TYPED_ORDER_REQUIRED');
 END IF;
 -- Recheck holds and inventory under the allocator's order and type locks.
 PERFORM public.sr_typed_allocate(oid);
 SELECT * INTO t FROM public.typed_order_settlements WHERE order_id=oid;
 IF t.state='reconciliation_pending' AND t.reason_code='stock_shortage' THEN
  -- Each logical line needs one identity; size and copy counts affect printing only.
  FOR kind,required IN
   SELECT qr_type_snapshot,count(*)::integer FROM public.order_logical_items
   WHERE order_id=oid GROUP BY qr_type_snapshot ORDER BY qr_type_snapshot
  LOOP
   SELECT count(*)::integer INTO available FROM (
    SELECT q.id FROM public.qr_codes q
    JOIN public.qr_batches b ON b.id=q.batch_id
    JOIN public.standalone_qr_states s ON s.qr_id=q.id
    WHERE q.tag_type=kind AND q.pair_id IS NULL AND q.is_current AND q.revoked_at IS NULL
     AND q.public_status='unactivated' AND b.status='generated' AND b.generation_mode='standalone' AND b.qr_type=kind
     AND s.inventory_status='available' AND s.ownership_status='unclaimed' AND s.owner_user_id IS NULL
     AND s.activated_at IS NULL AND s.revoked_at IS NULL
     AND NOT EXISTS(SELECT 1 FROM public.order_item_qr_allocations x WHERE x.qr_id=q.id)
    ORDER BY q.id FOR UPDATE OF q,s SKIP LOCKED LIMIT required
   ) AS stock;
   missing:=required-available;
   IF missing>0 THEN
    bid:=gen_random_uuid();
    label:='auto-'||replace(bid::text,'-','');
    INSERT INTO public.qr_batches(id,batch_code,ecc_level,status,generation_mode,qr_type,requested_quantity)
    VALUES(bid,label,'Q','generated','standalone',kind,missing);
    INSERT INTO public.qr_codes(id,batch_id,tag_type,serial_number,public_token,ecc_level)
    SELECT gen_random_uuid(),bid,kind,'SR-'||replace(bid::text,'-','')||'-'||lpad(n::text,6,'0'),
           rtrim(translate(encode(uuid_send(gen_random_uuid())||uuid_send(gen_random_uuid()),'base64'),'+/','-_'),'='),
           'Q'
    FROM generate_series(1,missing) AS n;
    INSERT INTO public.standalone_qr_states(qr_id)
    SELECT id FROM public.qr_codes WHERE batch_id=bid AND pair_id IS NULL;
    INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,reason,safe_details)
    VALUES(public.sr_actor_id(),'staff','inventory.typed_batch.generated','qr_batch',bid,
           'automatic inventory for verified payment',
           jsonb_build_object('event_id',oid,'outcome','success'));
   END IF;
  END LOOP;
  PERFORM public.sr_typed_allocate(oid);
 END IF;
 PERFORM public.sr_typed_settlement_handoff(oid);
 IF NOT public.sr_typed_allocation_authorized(sid,ARRAY['finance','operations']) THEN
  RAISE EXCEPTION 'Allocation authority changed' USING ERRCODE='42501';
 END IF;
 PERFORM public.sr_typed_settlement_complete(oid);
 RETURN public.sr_typed_allocation_status(oid);
END $$;
