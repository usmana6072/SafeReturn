CREATE FUNCTION public.sr_typed_payment_autogenerate(sid uuid,oid uuid,seed text)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE kind text; required integer; available integer; missing integer; bid uuid; label text; result jsonb;
BEGIN
 IF NOT public.sr_typed_allocation_authorized(sid,ARRAY['finance']) THEN RETURN jsonb_build_object('error','FORBIDDEN'); END IF;
 SELECT o.id INTO STRICT bid FROM public.orders o
 WHERE o.id=oid AND o.commerce_model='single_qr' AND o.order_status='placed' AND o.payment_status='verified';
 IF NOT EXISTS(SELECT 1 FROM public.typed_order_settlements WHERE order_id=oid AND state='reconciliation_pending' AND reason_code='stock_shortage') THEN
  RETURN jsonb_build_object('error','ORDER_RECONCILIATION_REQUIRED');
 END IF;
 FOR kind,required IN
  SELECT qr_type_snapshot,sum(quantity)::integer FROM public.order_logical_items
  WHERE order_id=oid GROUP BY qr_type_snapshot
 LOOP
  SELECT count(*)::integer INTO available
  FROM public.qr_codes q
  JOIN public.qr_batches b ON b.id=q.batch_id
  JOIN public.standalone_qr_states s ON s.qr_id=q.id
  WHERE q.tag_type=kind AND q.pair_id IS NULL AND q.is_current AND q.revoked_at IS NULL
    AND q.public_status='unactivated' AND b.status='generated' AND b.generation_mode='standalone'
    AND s.inventory_status='available' AND s.ownership_status='unclaimed' AND s.owner_user_id IS NULL;
  missing:=greatest(required-coalesce(available,0),0);
  IF missing>0 THEN
   label:='auto-'||substr(replace(oid::text,'-',''),1,12)||'-'||kind;
   IF length(label)>40 THEN label:=substr(label,1,40); END IF;
   bid:=gen_random_uuid();
   INSERT INTO public.qr_batches(id,batch_code,ecc_level,status,generation_mode,qr_type,requested_quantity)
   VALUES(bid,label,'Q','generated','standalone',kind,missing);
   INSERT INTO public.qr_codes(id,batch_id,tag_type,serial_number,public_token,ecc_level)
   SELECT gen_random_uuid(),bid,kind,'SR-'||replace(bid::text,'-','')||'-'||lpad(n::text,6,'0'),
          rtrim(replace(replace(encode(gen_random_bytes(32),'base64'),'+','-'),'/','_'),'='),
          'Q'
   FROM generate_series(1,missing) AS n;
   INSERT INTO public.standalone_qr_states(qr_id)
   SELECT id FROM public.qr_codes WHERE batch_id=bid AND pair_id IS NULL;
   INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,reason,safe_details)
   VALUES(public.sr_actor_id(),'staff','inventory.typed_batch.generated','qr_batch',bid,
          'automatic inventory for verified payment',
          jsonb_build_object('order_id',oid,'qr_type',kind,'quantity',missing,'seed',seed));
  END IF;
 END LOOP;
 PERFORM public.sr_typed_allocate(oid);
 PERFORM public.sr_typed_settlement_handoff(oid);
 result:=public.sr_typed_allocation_status(oid);
 PERFORM public.sr_typed_settlement_complete(oid);
 RETURN result;
END $$;

REVOKE ALL ON FUNCTION public.sr_typed_payment_autogenerate(uuid,uuid,text)
FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_typed_payment_autogenerate(uuid,uuid,text) TO safereturn_api;
