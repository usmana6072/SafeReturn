-- No runtime table grants. Existing pair generation/checkout/activation is unchanged.
-- Refuse admission if privileged Phase 1 fixtures left incomplete typed inventory.
DO $$ BEGIN
 IF EXISTS (
  SELECT 1 FROM public.qr_batches b WHERE b.generation_mode='standalone'
  AND ((SELECT count(*) FROM public.qr_codes q WHERE q.batch_id=b.id)>b.requested_quantity
   OR (b.status<>'draft' AND (SELECT count(*) FROM public.qr_codes q WHERE q.batch_id=b.id)<>b.requested_quantity))
 ) THEN RAISE EXCEPTION 'Existing typed inventory requires quantity reconciliation' USING ERRCODE='23514'; END IF;
END $$;
CREATE TABLE public.typed_inventory_receipts (
 actor_user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 idempotency_key varchar(160) NOT NULL,
 request_hash varchar(64) NOT NULL CHECK(request_hash ~ '^[0-9a-f]{64}$'),
 batch_id uuid NOT NULL UNIQUE REFERENCES public.qr_batches(id) ON DELETE RESTRICT,
 response jsonb NOT NULL CHECK(jsonb_typeof(response)='object'),
 created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(actor_user_id,idempotency_key)
);
ALTER TABLE public.typed_inventory_receipts ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.typed_inventory_receipts FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
CREATE INDEX ix_standalone_qr_type_created ON public.qr_codes(tag_type,created_at DESC,id DESC) WHERE pair_id IS NULL;

CREATE FUNCTION public.sr_typed_receipt_immutable() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN RAISE EXCEPTION 'Typed inventory receipts are immutable' USING ERRCODE='23514'; END $$;
CREATE TRIGGER sr_typed_receipt_immutable BEFORE UPDATE OR DELETE ON public.typed_inventory_receipts
 FOR EACH ROW EXECUTE FUNCTION public.sr_typed_receipt_immutable();

CREATE FUNCTION public.sr_typed_inventory_authorized(sid uuid) RETURNS boolean
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NOT public.sr_mfa() OR NOT EXISTS (
  SELECT 1 FROM public.sr_account_session_state(sid) WHERE email_verified AND mfa_active
 ) THEN RETURN false; END IF;
 -- Serialize staff revocation with the admitted transaction. No role inheritance.
 PERFORM 1 FROM public.staff_roles WHERE user_id=public.sr_actor_id()
  AND role='operations' AND revoked_at IS NULL FOR SHARE;
 RETURN FOUND;
END $$;

CREATE FUNCTION public.sr_typed_inventory_generate(
 sid uuid,label text,kind text,quantity integer,ecc text,request_key text,tokens jsonb
) RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE actor uuid:=public.sr_actor_id(); digest text; old public.typed_inventory_receipts;
 bid uuid; created timestamptz; result jsonb;
BEGIN
 IF NOT public.sr_typed_inventory_authorized(sid) THEN RETURN jsonb_build_object('error','FORBIDDEN'); END IF;
 IF label IS NULL OR char_length(label) NOT BETWEEN 3 AND 40 OR label !~ '^[A-Za-z0-9][A-Za-z0-9._-]+$'
  OR kind IS NULL OR kind NOT IN ('lost','ice') OR quantity IS NULL OR quantity NOT BETWEEN 1 AND 1000
  OR ecc IS NULL OR ecc NOT IN ('M','Q') OR request_key IS NULL OR request_key !~ '^[A-Za-z0-9._:-]{8,160}$'
 THEN RAISE EXCEPTION 'Invalid typed generation request' USING ERRCODE='22023'; END IF;
 digest:=encode(sha256(convert_to(jsonb_build_object('label',label,'type',kind,'quantity',quantity,'ecc',ecc)::text,'UTF8')),'hex');
 PERFORM pg_advisory_xact_lock(hashtextextended('typed-inventory:'||actor::text||':'||request_key,0));
 -- A replay can wait behind another transaction; recheck session expiry after waiting.
 IF NOT public.sr_typed_inventory_authorized(sid) THEN RETURN jsonb_build_object('error','FORBIDDEN'); END IF;
 SELECT * INTO old FROM public.typed_inventory_receipts WHERE actor_user_id=actor AND idempotency_key=request_key;
 IF FOUND THEN
  IF old.request_hash<>digest THEN RETURN jsonb_build_object('error','IDEMPOTENCY_KEY_REUSED'); END IF;
  RETURN old.response;
 END IF;
 -- Same label lock protocol as the legacy pair generator; uniqueness is the final guard.
 PERFORM pg_advisory_xact_lock(hashtextextended(label,0));
 IF EXISTS(SELECT 1 FROM public.qr_batches WHERE batch_code=label) THEN
  RETURN jsonb_build_object('error','BATCH_LABEL_CONFLICT');
 END IF;
 IF tokens IS NULL OR jsonb_typeof(tokens)<>'array' THEN
  RAISE EXCEPTION 'Invalid generated tokens' USING ERRCODE='22023';
 END IF;
 IF jsonb_array_length(tokens)<>quantity OR EXISTS (
  SELECT 1 FROM jsonb_array_elements(tokens) t WHERE jsonb_typeof(t)<>'string' OR (t#>>'{}') !~ '^[A-Za-z0-9_-]{43}$'
 ) OR (SELECT count(DISTINCT t#>>'{}') FROM jsonb_array_elements(tokens) t)<>quantity THEN
  RAISE EXCEPTION 'Invalid generated tokens' USING ERRCODE='22023';
 END IF;
 bid:=gen_random_uuid();
 INSERT INTO public.qr_batches(id,batch_code,ecc_level,status,generation_mode,qr_type,requested_quantity)
 VALUES(bid,label,ecc,'generated','standalone',kind,quantity) RETURNING created_at INTO created;
 INSERT INTO public.qr_codes(id,batch_id,tag_type,serial_number,public_token,ecc_level)
 SELECT gen_random_uuid(),bid,kind,'SR-'||replace(bid::text,'-','')||'-'||lpad(ordinality::text,6,'0'),value#>>'{}',ecc
 FROM jsonb_array_elements(tokens) WITH ORDINALITY;
 INSERT INTO public.standalone_qr_states(qr_id)
 SELECT id FROM public.qr_codes WHERE batch_id=bid AND pair_id IS NULL;
 result:=jsonb_build_object('batch_id',bid,'batch_label',label,'qr_type',kind,
  'generated_quantity',quantity,'status','generated','created_at',created);
 INSERT INTO public.typed_inventory_receipts(actor_user_id,idempotency_key,request_hash,batch_id,response)
 VALUES(actor,request_key,digest,bid,result);
 INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,request_id,safe_details)
 VALUES(actor,'staff','inventory.typed_batch.generated','qr_batch',bid,
  encode(sha256(convert_to(actor::text||':'||request_key,'UTF8')),'hex'),
  jsonb_build_object('qr_type',kind,'quantity',quantity,'outcome','success'));
 IF NOT public.sr_typed_inventory_authorized(sid) THEN
  RAISE EXCEPTION 'Inventory authority changed' USING ERRCODE='42501';
 END IF;
 RETURN result;
END $$;

-- Total generation is a commit-time invariant, not just a response count.
CREATE FUNCTION public.sr_typed_batch_quantity() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE bid uuid; b public.qr_batches; n integer;
BEGIN
 IF TG_TABLE_NAME='qr_batches' THEN bid:=NEW.id;
 ELSIF TG_OP='DELETE' THEN bid:=OLD.batch_id;
 ELSE bid:=NEW.batch_id; END IF;
 IF bid IS NULL THEN RETURN NULL; END IF;
 SELECT * INTO b FROM public.qr_batches WHERE id=bid FOR UPDATE;
 IF NOT FOUND OR b.generation_mode<>'standalone' THEN RETURN NULL; END IF;
 SELECT count(*) INTO n FROM public.qr_codes WHERE batch_id=bid AND pair_id IS NULL;
 IF n>b.requested_quantity OR (b.status<>'draft' AND n<>b.requested_quantity) THEN
  RAISE EXCEPTION 'Typed batch quantity does not match generated identities' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER sr_typed_batch_quantity AFTER INSERT OR UPDATE ON public.qr_batches
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_typed_batch_quantity();
-- Identity provenance is immutable: status-only updates cannot change quantity.
-- Avoid batch-lock upgrades on unrelated owner/public-status transitions.
CREATE CONSTRAINT TRIGGER sr_typed_qr_quantity AFTER INSERT OR DELETE ON public.qr_codes
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.sr_typed_batch_quantity();

-- One explicit projection; no public token, credential, owner ID, or private profile.
CREATE FUNCTION public.sr_typed_inventory_read(sid uuid,view_name text,filters jsonb)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE kind text; bid uuid; qid uuid; inv text; own text; label text; wanted_status text;
 take integer; stamp timestamptz; after_id uuid; result jsonb;
BEGIN
 IF NOT public.sr_typed_inventory_authorized(sid) THEN RETURN jsonb_build_object('error','FORBIDDEN'); END IF;
 IF view_name IS NULL OR view_name NOT IN ('codes','code','batches','batch','summary')
  OR filters IS NULL OR jsonb_typeof(filters)<>'object' THEN
  RAISE EXCEPTION 'Invalid inventory query' USING ERRCODE='22023';
 END IF;
 IF EXISTS(SELECT 1 FROM jsonb_object_keys(filters) k WHERE k NOT IN
  ('qr_type','batch_id','qr_id','inventory_status','ownership_status','batch_label','status','limit','at','after_id')) THEN
  RAISE EXCEPTION 'Unknown inventory filter' USING ERRCODE='22023';
 END IF;
 kind:=filters->>'qr_type'; bid:=(filters->>'batch_id')::uuid; qid:=(filters->>'qr_id')::uuid;
 inv:=filters->>'inventory_status'; own:=filters->>'ownership_status'; label:=filters->>'batch_label'; wanted_status:=filters->>'status';
 take:=coalesce((filters->>'limit')::integer,20); stamp:=(filters->>'at')::timestamptz; after_id:=(filters->>'after_id')::uuid;
 IF (kind IS NOT NULL AND kind NOT IN ('lost','ice')) OR take NOT BETWEEN 1 AND 100
  OR (inv IS NOT NULL AND inv NOT IN ('available','allocated','retired'))
  OR (own IS NOT NULL AND own NOT IN ('unclaimed','active','revoked'))
  OR (label IS NOT NULL AND char_length(label) NOT BETWEEN 1 AND 40)
  OR (wanted_status IS NOT NULL AND wanted_status NOT IN ('draft','generated','printed','qa_passed','rejected','closed'))
  OR (stamp IS NULL)<>(after_id IS NULL) OR (view_name='code' AND qid IS NULL) OR (view_name='batch' AND bid IS NULL) THEN
  RAISE EXCEPTION 'Invalid inventory filter' USING ERRCODE='22023';
 END IF;
 IF view_name IN ('codes','code') THEN
  SELECT jsonb_build_object('as_of',statement_timestamp(),'items',coalesce(jsonb_agg(to_jsonb(r) ORDER BY r.created_at DESC,r.qr_id DESC),'[]'::jsonb)) INTO result FROM (
   SELECT q.id AS qr_id,q.batch_id,b.batch_code AS batch_label,q.tag_type AS qr_type,q.serial_number,q.public_status,
    s.inventory_status,s.ownership_status,s.row_version,q.created_at,
    (s.inventory_status='available' AND s.ownership_status='unclaimed' AND s.owner_user_id IS NULL
     AND q.public_status='unactivated' AND q.is_current AND b.status='generated') AS allocatable
   FROM public.qr_codes q JOIN public.standalone_qr_states s ON s.qr_id=q.id JOIN public.qr_batches b ON b.id=q.batch_id
   WHERE q.pair_id IS NULL AND b.generation_mode='standalone'
    AND (kind IS NULL OR q.tag_type=kind) AND (bid IS NULL OR q.batch_id=bid) AND (qid IS NULL OR q.id=qid)
    AND (inv IS NULL OR s.inventory_status=inv) AND (own IS NULL OR s.ownership_status=own)
    AND (stamp IS NULL OR (q.created_at,q.id)<(stamp,after_id))
   ORDER BY q.created_at DESC,q.id DESC LIMIT take+1
  ) r;
  IF view_name='code' THEN result:=result->'items'->0; END IF;
 ELSIF view_name IN ('batches','batch') THEN
  SELECT jsonb_build_object('as_of',statement_timestamp(),'items',coalesce(jsonb_agg(to_jsonb(r) ORDER BY r.created_at DESC,r.batch_id DESC),'[]'::jsonb)) INTO result FROM (
   SELECT b.id AS batch_id,b.batch_code AS batch_label,b.qr_type,b.requested_quantity,b.status,b.ecc_level,b.created_at,
    (SELECT count(*) FROM public.qr_codes q WHERE q.batch_id=b.id AND q.pair_id IS NULL) AS generated_quantity
   FROM public.qr_batches b WHERE b.generation_mode='standalone'
    AND (kind IS NULL OR b.qr_type=kind) AND (bid IS NULL OR b.id=bid)
    AND (label IS NULL OR b.batch_code=label) AND (wanted_status IS NULL OR b.status=wanted_status)
    AND (stamp IS NULL OR (b.created_at,b.id)<(stamp,after_id))
   ORDER BY b.created_at DESC,b.id DESC LIMIT take+1
  ) r;
  IF view_name='batch' THEN result:=result->'items'->0; END IF;
 ELSE
  SELECT jsonb_build_object('as_of',statement_timestamp(),'items',jsonb_agg(to_jsonb(r) ORDER BY r.qr_type)) INTO result FROM (
   SELECT t.qr_type,count(q.id) AS total,
    count(q.id) FILTER(WHERE s.inventory_status='available') AS available,
    count(q.id) FILTER(WHERE s.inventory_status='allocated') AS allocated,
    count(q.id) FILTER(WHERE s.inventory_status='retired') AS retired,
    count(q.id) FILTER(WHERE s.inventory_status='available' AND s.ownership_status='unclaimed' AND s.owner_user_id IS NULL
     AND q.public_status='unactivated' AND q.is_current AND b.status='generated') AS allocatable
   FROM (VALUES('lost'),('ice')) t(qr_type)
   LEFT JOIN public.qr_codes q ON q.tag_type=t.qr_type AND q.pair_id IS NULL
   LEFT JOIN public.qr_batches b ON b.id=q.batch_id AND b.generation_mode='standalone'
   LEFT JOIN public.standalone_qr_states s ON s.qr_id=q.id
   WHERE kind IS NULL OR t.qr_type=kind GROUP BY t.qr_type
  ) r;
 END IF;
 IF NOT public.sr_typed_inventory_authorized(sid) THEN RETURN jsonb_build_object('error','FORBIDDEN'); END IF;
 RETURN result;
END $$;

REVOKE ALL ON FUNCTION public.sr_typed_receipt_immutable(),public.sr_typed_inventory_authorized(uuid),
 public.sr_typed_inventory_generate(uuid,text,text,integer,text,text,jsonb),public.sr_typed_batch_quantity(),
 public.sr_typed_inventory_read(uuid,text,jsonb) FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_typed_inventory_generate(uuid,text,text,integer,text,text,jsonb),
 public.sr_typed_inventory_read(uuid,text,jsonb) TO safereturn_api;
