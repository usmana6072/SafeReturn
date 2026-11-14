-- Browse valid published products without opening checkout, payments, allocation
-- or owner activation. No release flag or product/featured setting is changed.
DO $patch$
DECLARE source text; anchor text;
BEGIN
 source:=pg_get_functiondef('public.sr_public_catalog(text)'::regprocedure);
 anchor:='p.commerce_model=''single_qr'' AND public.sr_single_checkout_enabled() AND EXISTS';
 IF position(anchor IN source)=0 OR position('checkout_available' IN source)>0 THEN RAISE EXCEPTION 'Review public catalog source'; END IF;
 source:=replace(source,anchor,'p.commerce_model=''single_qr'' AND EXISTS');
 anchor:='''commerce_model'',p.commerce_model,''qr_type'',p.qr_type,';
 IF position(anchor IN source)=0 THEN RAISE EXCEPTION 'Review public catalog projection'; END IF;
 source:=replace(source,anchor,anchor||'''checkout_available'',CASE WHEN p.commerce_model=''single_qr'' THEN public.sr_single_checkout_enabled() AND EXISTS(SELECT 1 FROM public.checkout_payment_instructions i WHERE i.active) ELSE true END,');
 EXECUTE source;
END $patch$;
