-- Additive, offline/unapplied. No authority/key/policy/evidence/asset/person seeds.
CREATE TABLE public.template_people (
 user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE RESTRICT,
 human_id uuid NOT NULL, enrollment_reference text NOT NULL,
 revoked_at timestamptz
);
CREATE TABLE public.template_authorities (
 authority_id uuid PRIMARY KEY, human_id uuid NOT NULL,
 scopes text[] NOT NULL CHECK(cardinality(scopes)>0 AND scopes<@ARRAY['custody','publish','physical_scan','copy_safety','licenses']::text[]),
 valid_from timestamptz NOT NULL, expires_at timestamptz NOT NULL CHECK(expires_at>valid_from),
 enrollment_reference text NOT NULL, revoked_at timestamptz
);
CREATE TABLE public.template_issuer_keys (
 key_id uuid PRIMARY KEY, authority_id uuid NOT NULL REFERENCES public.template_authorities(authority_id) ON DELETE RESTRICT,
 public_key bytea NOT NULL CHECK(octet_length(public_key)=32),
 valid_from timestamptz NOT NULL, expires_at timestamptz NOT NULL CHECK(expires_at>valid_from),
 witnessed_by uuid NOT NULL, enrollment_reference text NOT NULL, revoked_at timestamptz
);
CREATE TABLE public.template_production_policies (
 policy_id uuid NOT NULL, version integer NOT NULL CHECK(version>0),
 sha256 char(64) NOT NULL CHECK(sha256~'^[0-9a-f]{64}$'), body jsonb NOT NULL CHECK(jsonb_typeof(body)='object'),
 reviewed_by uuid NOT NULL, archive_reference text NOT NULL, revoked_at timestamptz,
 PRIMARY KEY(policy_id,version)
);
CREATE TABLE public.template_archive_entries (
 reference text PRIMARY KEY CHECK(reference~'^[A-Za-z0-9._-]{1,160}$'),
 kind text NOT NULL CHECK(kind IN('report','license')),
 sha256 char(64) NOT NULL CHECK(sha256~'^[0-9a-f]{64}$'), verified_by uuid NOT NULL,
 custody_reference text NOT NULL, revoked_at timestamptz
);
CREATE TABLE public.template_revision_contributors (
 event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 revision_id uuid NOT NULL REFERENCES public.print_template_revisions(revision_id) ON DELETE RESTRICT,
 actor_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 event_type text NOT NULL CHECK(event_type IN('created','edited','submitted','derived')),
 occurred_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE public.template_qa_approvals (
 approval_id uuid PRIMARY KEY, evidence_id uuid NOT NULL UNIQUE,
 revision_id uuid NOT NULL REFERENCES public.print_template_revisions(revision_id) ON DELETE RESTRICT,
 revision_row_version bigint NOT NULL, revision_fingerprint_sha256 char(64) NOT NULL,
 evidence_sha256 char(64) NOT NULL CHECK(evidence_sha256~'^[0-9a-f]{64}$'),
 policy_id uuid NOT NULL, policy_version integer NOT NULL,
 summary jsonb NOT NULL CHECK(jsonb_typeof(summary)='object'),
 ciphertext bytea NOT NULL CHECK(octet_length(ciphertext) BETWEEN 32 AND 140000), key_version smallint NOT NULL CHECK(key_version>0),
 importer_human uuid NOT NULL, expires_at timestamptz NOT NULL, imported_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 consumed_at timestamptz, consumed_by uuid, publisher_authority_id uuid REFERENCES public.template_authorities(authority_id) ON DELETE RESTRICT,
 revoked_at timestamptz, authority_version bigint NOT NULL DEFAULT 1,
 FOREIGN KEY(policy_id,policy_version) REFERENCES public.template_production_policies(policy_id,version) ON DELETE RESTRICT
);
CREATE TABLE public.print_template_variant_bindings (
 binding_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 variant_id uuid NOT NULL REFERENCES public.product_variants(id) ON DELETE RESTRICT,
 tag_type text NOT NULL CHECK(tag_type IN('lost','ice')),
 revision_id uuid NOT NULL REFERENCES public.print_template_revisions(revision_id) ON DELETE RESTRICT,
 is_active boolean NOT NULL DEFAULT true, row_version bigint NOT NULL DEFAULT 1,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE UNIQUE INDEX uq_template_active_binding ON public.print_template_variant_bindings(variant_id,tag_type) WHERE is_active;
CREATE INDEX ix_template_bound_revision ON public.print_template_variant_bindings(revision_id) WHERE is_active;
CREATE TABLE public.template_registry_sources (
 variant_id uuid PRIMARY KEY REFERENCES public.product_variants(id) ON DELETE RESTRICT,
 generation bigint NOT NULL DEFAULT 1 CHECK(generation>0)
);
CREATE TABLE public.order_use_print_specs (
 use_id uuid PRIMARY KEY REFERENCES public.order_item_qr_uses(id) ON DELETE RESTRICT,
 spec jsonb NOT NULL CHECK(jsonb_typeof(spec)='object' AND octet_length(spec::text)<=32768),
 revision_id uuid NOT NULL REFERENCES public.print_template_revisions(revision_id) ON DELETE RESTRICT,
 approval_id uuid NOT NULL REFERENCES public.template_qa_approvals(approval_id) ON DELETE RESTRICT
);
CREATE TABLE public.template_registry_orders (
 order_id uuid PRIMARY KEY REFERENCES public.orders(id) ON DELETE RESTRICT,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX ix_template_use_revision ON public.order_use_print_specs(revision_id);
CREATE INDEX ix_template_contributor_revision ON public.template_revision_contributors(revision_id);
CREATE TABLE public.template_order_holds (
 order_id uuid NOT NULL REFERENCES public.orders(id) ON DELETE RESTRICT,
 source_kind text NOT NULL, source_reference text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(order_id,source_kind,source_reference)
);
CREATE TABLE public.template_authority_withdrawals (
 revocation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),target_kind text NOT NULL CHECK(target_kind IN('evidence','key')),
 target_id uuid NOT NULL, authority_version bigint NOT NULL,
 reason_code text NOT NULL CHECK(reason_code IN('evidence_withdrawn','key_compromise')),
 actor_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
 occurred_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
ALTER TABLE public.template_issuer_keys ADD COLUMN authority_version bigint NOT NULL DEFAULT 1;
ALTER TABLE public.print_template_revisions ADD COLUMN provenance_complete boolean NOT NULL DEFAULT false;
ALTER TABLE public.print_template_revisions ADD COLUMN approval_id uuid REFERENCES public.template_qa_approvals(approval_id) ON DELETE RESTRICT;
ALTER TABLE public.print_templates DROP CONSTRAINT print_templates_lifecycle_status_check;
ALTER TABLE public.print_templates ADD CONSTRAINT ck_template_lifecycle CHECK(lifecycle_status IN('draft','active','retired'));
ALTER TABLE public.print_template_revisions DROP CONSTRAINT print_template_revisions_status_check;
ALTER TABLE public.print_template_revisions DROP CONSTRAINT print_template_revisions_published_at_check;
ALTER TABLE public.print_template_revisions DROP CONSTRAINT print_template_revisions_check;
ALTER TABLE public.print_template_revisions ADD CONSTRAINT ck_template_revision_lifecycle CHECK(
 (status='draft' AND fingerprint_sha256 IS NULL AND published_at IS NULL AND approval_id IS NULL)
 OR(status='pending_qa' AND fingerprint_sha256 IS NOT NULL AND published_at IS NULL AND approval_id IS NULL)
 OR(status IN('published','retired') AND fingerprint_sha256 IS NOT NULL AND published_at IS NOT NULL AND approval_id IS NOT NULL));

CREATE FUNCTION public.sr_template_registry_gate(exclusive boolean) RETURNS void
LANGUAGE plpgsql VOLATILE SET search_path=pg_catalog AS $$ BEGIN
 IF exclusive THEN PERFORM pg_advisory_xact_lock(51340001); ELSE PERFORM pg_advisory_xact_lock_shared(51340001); END IF;
END $$;

CREATE FUNCTION public.sr_template_resolve(vid uuid,uses jsonb) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE source public.template_registry_sources; v public.product_variants; r public.print_template_revisions;
 b public.print_template_variant_bindings; t public.print_templates; e public.template_qa_approvals; a public.print_template_asset_sets; p public.template_production_policies;
 kind text; specs jsonb:='[]'::jsonb;
BEGIN
 PERFORM public.sr_template_registry_gate(false);
 SELECT * INTO source FROM public.template_registry_sources WHERE variant_id=vid;
 IF NOT FOUND THEN RETURN NULL; END IF;
 IF jsonb_typeof(uses)<>'array' OR jsonb_array_length(uses) NOT BETWEEN 1 AND 30 THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
 SELECT * INTO v FROM public.product_variants WHERE id=vid;
 FOR kind IN SELECT DISTINCT value->>'tag_type' FROM jsonb_array_elements(uses) LOOP
  SELECT * INTO b FROM public.print_template_variant_bindings WHERE variant_id=vid AND tag_type=kind AND is_active;
  IF NOT FOUND OR NOT public.sr_template_revision_clear(b.revision_id,false) THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  SELECT * INTO r FROM public.print_template_revisions WHERE revision_id=b.revision_id;
  SELECT * INTO t FROM public.print_templates WHERE template_id=r.template_id;
  SELECT * INTO e FROM public.template_qa_approvals WHERE approval_id=r.approval_id;
  SELECT * INTO p FROM public.template_production_policies WHERE policy_id=e.policy_id AND version=e.policy_version;
  SELECT * INTO a FROM public.print_template_asset_sets WHERE asset_set_id=(r.content->>'asset_set_id')::uuid;
  IF v.template_key IS DISTINCT FROM t.key OR v.template_version IS DISTINCT FROM r.version OR v.size_mm IS DISTINCT FROM (r.content->>'symbol_mm')::numeric OR t.purpose IS DISTINCT FROM kind
  OR v.fulfillment_method IS DISTINCT FROM 'pdf_label' OR NOT COALESCE((r.content->'material_codes') ? v.material,false) THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  specs:=specs||jsonb_build_array(jsonb_build_object('binding_id',b.binding_id,'variant_id',vid,'source_generation',source.generation,'revision_id',r.revision_id,
   'material',v.material,'size_mm',v.size_mm,'fulfillment_method',v.fulfillment_method,
   'approval_id',e.approval_id,'fingerprint_sha256',r.fingerprint_sha256,'policy_id',p.policy_id,'policy_version',p.version,'policy_sha256',p.sha256,
   'asset_set_id',a.asset_set_id,'key',t.key,'version',r.version,'tag_type',kind,'content',r.content,'origin',p.body->>'canonical_origin',
   'assets',jsonb_build_object('font',jsonb_build_object('path',a.font_path,'sha256',a.font_sha256),'logo',jsonb_build_object('path',a.logo_path,'sha256',a.logo_sha256))));
 END LOOP;
 RETURN specs;
END $$;

CREATE FUNCTION public.sr_template_freeze_use(uid uuid,wanted jsonb) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE oid uuid; vid uuid; kind text; current_spec jsonb;
BEGIN
 PERFORM public.sr_template_registry_gate(false);
 SELECT i.order_id,i.variant_id,u.tag_type_snapshot INTO oid,vid,kind FROM public.order_item_qr_uses u JOIN public.order_items i ON i.id=u.order_item_id
 JOIN public.orders o ON o.id=i.order_id WHERE u.id=uid AND o.customer_user_id=public.sr_actor_id() AND o.order_status='draft';
 IF oid IS NULL THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
 current_spec:=public.sr_template_resolve(vid,jsonb_build_array(jsonb_build_object('tag_type',kind)));
 IF current_spec IS NULL OR current_spec ? 'error' OR current_spec->0 IS DISTINCT FROM wanted THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
 INSERT INTO public.template_registry_orders(order_id) VALUES(oid) ON CONFLICT DO NOTHING;
 INSERT INTO public.order_use_print_specs(use_id,spec,revision_id,approval_id) VALUES(uid,wanted,(wanted->>'revision_id')::uuid,(wanted->>'approval_id')::uuid);
 RETURN jsonb_build_object('state','frozen');
END $$;

CREATE FUNCTION public.sr_template_order_specs(oid uuid) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE value jsonb; total integer; saved integer; shipped boolean;
BEGIN
 IF NOT EXISTS(SELECT 1 FROM public.template_registry_orders WHERE order_id=oid) THEN RETURN NULL; END IF;
 IF NOT(public.sr_is_staff(ARRAY['operations']) OR EXISTS(SELECT 1 FROM public.orders WHERE id=oid AND customer_user_id=public.sr_actor_id())
 OR (current_setting('role',true)='safereturn_worker' AND COALESCE(current_setting('safereturn.worker_id',true),'')<>'')) THEN RETURN jsonb_build_object('error','FORBIDDEN'); END IF;
 SELECT EXISTS(SELECT 1 FROM public.shipments WHERE order_id=oid AND dispatched_at IS NOT NULL) INTO shipped;
 SELECT count(*) INTO total FROM public.order_item_qr_uses u JOIN public.order_items i ON i.id=u.order_item_id WHERE i.order_id=oid;
 SELECT count(*) INTO saved FROM public.order_use_print_specs s JOIN public.order_item_qr_uses u ON u.id=s.use_id JOIN public.order_items i ON i.id=u.order_item_id WHERE i.order_id=oid;
 IF total=0 OR total<>saved OR (NOT shipped AND (EXISTS(SELECT 1 FROM public.template_order_holds WHERE order_id=oid) OR EXISTS(SELECT 1 FROM public.order_use_print_specs s JOIN public.order_item_qr_uses u ON u.id=s.use_id JOIN public.order_items i ON i.id=u.order_item_id WHERE i.order_id=oid AND NOT public.sr_template_revision_clear(s.revision_id,true)))) THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
 SELECT jsonb_agg(s.spec||jsonb_build_object('use_id',s.use_id) ORDER BY s.use_id) INTO value FROM public.order_use_print_specs s JOIN public.order_item_qr_uses u ON u.id=s.use_id JOIN public.order_items i ON i.id=u.order_item_id WHERE i.order_id=oid;
 RETURN value;
END $$;

-- An old or disabled writer cannot place a newly registry-marked order without specs.
CREATE FUNCTION public.sr_template_catalog_eligible(vid uuid) RETURNS boolean LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM public.template_registry_sources WHERE variant_id=vid) THEN RETURN NULL; END IF;
 RETURN EXISTS(SELECT 1 FROM public.print_template_variant_bindings WHERE variant_id=vid AND is_active)
 AND NOT EXISTS(SELECT 1 FROM public.print_template_variant_bindings WHERE variant_id=vid AND is_active AND NOT public.sr_template_revision_clear(revision_id,false));
END $$;
CREATE FUNCTION public.sr_template_order_placement_guard() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE v jsonb;
BEGIN
 IF NEW.order_status='placed' AND OLD.order_status<>'placed' AND EXISTS(SELECT 1 FROM public.order_items i JOIN public.template_registry_sources s ON s.variant_id=i.variant_id WHERE i.order_id=NEW.id) THEN
  IF NOT EXISTS(SELECT 1 FROM public.template_registry_orders WHERE order_id=NEW.id) THEN RAISE EXCEPTION 'Registry snapshots required' USING ERRCODE='23514'; END IF;
  v:=public.sr_template_order_specs(NEW.id);
  IF v IS NULL OR v ? 'error' THEN RAISE EXCEPTION 'Registry snapshots invalid' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_template_placement BEFORE UPDATE ON public.orders FOR EACH ROW EXECUTE FUNCTION public.sr_template_order_placement_guard();

CREATE FUNCTION public.sr_template_catalog_guard() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM public.template_registry_sources WHERE variant_id=NEW.id) THEN
  PERFORM public.sr_template_registry_gate(false);
  IF EXISTS(SELECT 1 FROM public.print_template_variant_bindings b JOIN public.print_template_revisions r ON r.revision_id=b.revision_id JOIN public.print_templates t ON t.template_id=r.template_id
   WHERE b.variant_id=NEW.id AND b.is_active AND (NEW.template_key IS DISTINCT FROM t.key OR NEW.template_version IS DISTINCT FROM r.version
   OR NEW.size_mm IS DISTINCT FROM (r.content->>'symbol_mm')::numeric OR NEW.fulfillment_method IS DISTINCT FROM 'pdf_label' OR NOT COALESCE(r.content->'material_codes' ? NEW.material,false))) THEN
    RAISE EXCEPTION 'Registry binding mismatch' USING ERRCODE='23514';
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_template_catalog BEFORE UPDATE ON public.product_variants FOR EACH ROW EXECUTE FUNCTION public.sr_template_catalog_guard();

CREATE FUNCTION public.sr_template_no_rewrite() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN RAISE EXCEPTION 'Immutable template history' USING ERRCODE='23514'; END $$;
CREATE TRIGGER sr_template_specs_append BEFORE UPDATE OR DELETE ON public.order_use_print_specs FOR EACH ROW EXECUTE FUNCTION public.sr_template_no_rewrite();
CREATE TRIGGER sr_template_contributors_append BEFORE UPDATE OR DELETE ON public.template_revision_contributors FOR EACH ROW EXECUTE FUNCTION public.sr_template_no_rewrite();
CREATE TRIGGER sr_template_withdrawals_append BEFORE UPDATE OR DELETE ON public.template_authority_withdrawals FOR EACH ROW EXECUTE FUNCTION public.sr_template_no_rewrite();
CREATE TRIGGER sr_template_sources_keep BEFORE DELETE ON public.template_registry_sources FOR EACH ROW EXECUTE FUNCTION public.sr_template_no_rewrite();
CREATE TRIGGER sr_template_order_sources_keep BEFORE UPDATE OR DELETE ON public.template_registry_orders FOR EACH ROW EXECUTE FUNCTION public.sr_template_no_rewrite();
CREATE TRIGGER sr_template_order_holds_keep BEFORE UPDATE OR DELETE ON public.template_order_holds FOR EACH ROW EXECUTE FUNCTION public.sr_template_no_rewrite();

-- Ledger is complete only for post0034 revisions; no invented prior editor history.
CREATE FUNCTION public.sr_template_contributor_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP='INSERT' THEN NEW.provenance_complete:=true;
 ELSIF OLD.status<>'draft' AND (NEW.content IS DISTINCT FROM OLD.content OR NEW.version<>OLD.version OR NEW.template_id<>OLD.template_id
 OR NEW.created_by<>OLD.created_by OR NEW.created_at<>OLD.created_at OR NEW.fingerprint_sha256 IS DISTINCT FROM OLD.fingerprint_sha256) THEN
  RAISE EXCEPTION 'Submitted content is immutable' USING ERRCODE='23514';
 END IF;
 IF TG_OP='UPDATE' AND (OLD.status='retired' OR (OLD.status='published' AND NEW.status<>'retired') OR (OLD.status='pending_qa' AND NEW.status NOT IN('pending_qa','published'))) THEN
  RAISE EXCEPTION 'Invalid revision transition' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_template_immutable BEFORE INSERT OR UPDATE ON public.print_template_revisions FOR EACH ROW EXECUTE FUNCTION public.sr_template_contributor_guard();
CREATE FUNCTION public.sr_template_contributor_event() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP='INSERT' OR (TG_OP='UPDATE' AND OLD.status='draft') THEN
  INSERT INTO public.template_revision_contributors(revision_id,actor_id,event_type) VALUES(NEW.revision_id,public.sr_actor_id(),
  CASE WHEN TG_OP='INSERT' THEN 'created' WHEN NEW.status='pending_qa' THEN 'submitted' ELSE 'edited' END);
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_template_provenance AFTER INSERT OR UPDATE ON public.print_template_revisions FOR EACH ROW EXECUTE FUNCTION public.sr_template_contributor_event();

CREATE FUNCTION public.sr_template_revision_view(r public.print_template_revisions) RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT to_jsonb(r)-'created_by'-'updated_by'-'version_note'-'provenance_complete'-'approval_id'
$$;
-- Keep0033 untouched; widen its projection without leaking new protected columns.
ALTER FUNCTION public.sr_template_service(uuid,bigint,text,jsonb) RENAME TO sr_template_draft_service_v33;
CREATE FUNCTION public.sr_template_service(sid uuid,amr bigint,action text,payload jsonb) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE v jsonb; base uuid:=(payload->>'base_revision_id')::uuid;
BEGIN
 IF action NOT IN('list','detail','preview_input') THEN
  PERFORM public.sr_template_registry_gate(false);
  IF EXISTS(SELECT 1 FROM public.print_templates WHERE template_id=(payload->>'template_id')::uuid AND lifecycle_status='retired') THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  IF base IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.print_template_revisions WHERE revision_id=base AND template_id=(payload->>'template_id')::uuid AND provenance_complete) THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
 END IF;
 v:=public.sr_template_draft_service_v33(sid,amr,action,payload);
 IF action='revision' AND base IS NOT NULL AND v ? 'revision' THEN
  INSERT INTO public.template_revision_contributors(revision_id,actor_id,event_type) SELECT (v->'revision'->>'revision_id')::uuid,actor_id,'derived' FROM public.template_revision_contributors WHERE revision_id=base;
 END IF;
 IF v ? 'revision_id' THEN v:=v-'provenance_complete'-'approval_id'; END IF;
 IF v ? 'revision' THEN v:=jsonb_set(v,'{revision}',(v->'revision')-'provenance_complete'-'approval_id'); END IF;
 IF v ? 'revisions' THEN v:=jsonb_set(v,'{revisions}',COALESCE((SELECT jsonb_agg(value-'provenance_complete'-'approval_id') FROM jsonb_array_elements(v->'revisions')),'[]'::jsonb)); END IF;
 RETURN v;
END $$;

CREATE FUNCTION public.sr_template_human() RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT human_id FROM public.template_people WHERE user_id=public.sr_actor_id() AND revoked_at IS NULL
$$;
CREATE FUNCTION public.sr_template_assignment(h uuid,wanted text) RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT authority_id FROM public.template_authorities WHERE human_id=h AND wanted=ANY(scopes) AND revoked_at IS NULL AND valid_from<=clock_timestamp() AND expires_at>clock_timestamp() ORDER BY authority_id LIMIT 1
$$;
CREATE FUNCTION public.sr_template_revision_clear(rid uuid,historical boolean) RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE r public.print_template_revisions; e public.template_qa_approvals;
BEGIN
 SELECT * INTO r FROM public.print_template_revisions WHERE revision_id=rid;
 IF NOT FOUND OR r.status NOT IN('published','retired') OR (NOT historical AND r.status<>'published') THEN RETURN false; END IF;
 SELECT * INTO e FROM public.template_qa_approvals WHERE approval_id=r.approval_id;
 IF NOT FOUND OR e.revoked_at IS NOT NULL OR e.consumed_at IS NULL THEN RETURN false; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.print_template_asset_sets a WHERE a.asset_set_id=(r.content->>'asset_set_id')::uuid AND a.withdrawn_at IS NULL)
 OR NOT EXISTS(SELECT 1 FROM public.template_production_policies p WHERE p.policy_id=e.policy_id AND p.version=e.policy_version AND p.revoked_at IS NULL)
 OR EXISTS(SELECT 1 FROM jsonb_array_elements(e.summary->'attestations') s LEFT JOIN public.template_issuer_keys k ON k.key_id=(s->>'key_id')::uuid
 LEFT JOIN public.template_authorities a ON a.authority_id=(s->>'authority_id')::uuid
 WHERE k.key_id IS NULL OR k.revoked_at IS NOT NULL OR a.authority_id IS NULL OR a.revoked_at IS NOT NULL
 OR (NOT historical AND (k.expires_at<=clock_timestamp() OR a.expires_at<=clock_timestamp()))) THEN RETURN false; END IF;
 IF EXISTS(SELECT 1 FROM public.template_authorities a WHERE a.authority_id=e.publisher_authority_id AND a.revoked_at IS NOT NULL) THEN RETURN false; END IF;
 IF EXISTS(SELECT 1 FROM jsonb_array_elements_text(e.summary->'archive_references') ref
 LEFT JOIN public.template_archive_entries a ON a.reference=ref WHERE a.reference IS NULL OR a.revoked_at IS NOT NULL) THEN RETURN false; END IF;
 RETURN true;
END $$;

CREATE FUNCTION public.sr_template_evidence_context(rid uuid,pid uuid,pver integer,mode text,importer uuid) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE r public.print_template_revisions; a public.print_template_asset_sets; p public.template_production_policies; authors jsonb; authorities jsonb; archive jsonb;
BEGIN
 SELECT * INTO r FROM public.print_template_revisions WHERE revision_id=rid;
 SELECT * INTO a FROM public.print_template_asset_sets WHERE asset_set_id=(r.content->>'asset_set_id')::uuid AND withdrawn_at IS NULL;
 SELECT * INTO p FROM public.template_production_policies WHERE policy_id=pid AND version=pver AND revoked_at IS NULL;
 IF r.revision_id IS NULL THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
 IF a.asset_set_id IS NULL OR p.policy_id IS NULL THEN RETURN jsonb_build_object('error','PROVIDER_UNAVAILABLE'); END IF;
 SELECT jsonb_agg(human_id) INTO authors FROM (SELECT DISTINCT m.human_id FROM public.template_revision_contributors c LEFT JOIN public.template_people m ON m.user_id=c.actor_id AND m.revoked_at IS NULL WHERE c.revision_id=rid) x;
 SELECT COALESCE(jsonb_object_agg(x.authority_id,jsonb_build_object('human_id',x.human_id,'scopes',x.scopes,'revoked',false,'valid_from',to_char(x.valid_from AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS"Z"'),'expires_at',to_char(x.expires_at AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS"Z"'),'keys',
  (SELECT COALESCE(jsonb_object_agg(k.key_id,jsonb_build_object('public_key',replace(encode(k.public_key,'base64'),E'\n',''),
  'valid_from',to_char(k.valid_from AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS"Z"'),'expires_at',to_char(k.expires_at AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS"Z"'),'revoked',false)),'{}'::jsonb)
  FROM public.template_issuer_keys k WHERE k.authority_id=x.authority_id AND k.revoked_at IS NULL AND k.valid_from<=clock_timestamp() AND k.expires_at>clock_timestamp()))),'{}'::jsonb)
 INTO authorities FROM public.template_authorities x WHERE x.revoked_at IS NULL AND x.valid_from<=clock_timestamp() AND x.expires_at>clock_timestamp();
 SELECT COALESCE(jsonb_object_agg(reference,jsonb_build_object('kind',kind,'sha256',sha256)),'{}'::jsonb) INTO archive FROM public.template_archive_entries WHERE revoked_at IS NULL;
 RETURN jsonb_build_object('mode',mode,'actor_human',public.sr_template_human(),'importer_human',importer,'provenance_complete',r.provenance_complete,'contributors',COALESCE(authors,'[]'::jsonb),
 'revision',public.sr_template_revision_view(r)||(SELECT jsonb_build_object('key',key,'purpose',purpose) FROM public.print_templates WHERE template_id=r.template_id),'assets',jsonb_build_object('font',jsonb_build_object('path',a.font_path,'sha256',a.font_sha256),'logo',jsonb_build_object('path',a.logo_path,'sha256',a.logo_sha256)),
 'policy',jsonb_build_object('policy_id',p.policy_id,'version',p.version,'sha256',p.sha256,'body',p.body),'authorities',authorities,'archive',archive);
END $$;

CREATE FUNCTION public.sr_template_lifecycle(sid uuid,amr bigint,action text,payload jsonb) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE h uuid; assignment uuid; r public.print_template_revisions; t public.print_templates; e public.template_qa_approvals;
 b public.print_template_variant_bindings; v public.product_variants; ctx jsonb; aid uuid; k public.template_issuer_keys; rows jsonb;
BEGIN
 IF NOT EXISTS(SELECT 1 FROM public.sr_account_session_state(sid) s WHERE s.email_verified AND s.mfa_active) THEN RETURN NULL; END IF;
 IF action IN('context_import','import','revoke','custody_check') THEN
  IF public.sr_is_staff(ARRAY['security_admin']) IS NOT TRUE THEN RETURN NULL; END IF;
 ELSIF action='bindings' THEN
  IF public.sr_is_staff(ARRAY['operations','security_admin','superadmin']) IS NOT TRUE THEN RETURN NULL; END IF;
 ELSE IF public.sr_is_staff(ARRAY['operations']) IS NOT TRUE THEN RETURN NULL; END IF; END IF;
 IF action<>'bindings' AND (amr IS NULL OR amr<0 OR amr>extract(epoch FROM clock_timestamp()) OR extract(epoch FROM clock_timestamp())-amr>300) THEN RETURN NULL; END IF;
 IF action<>'bindings' AND NOT EXISTS(SELECT 1 FROM public.template_people) THEN RETURN jsonb_build_object('error','PROVIDER_UNAVAILABLE'); END IF;
 h:=public.sr_template_human();
 IF h IS NULL AND action NOT IN('bindings','bind') THEN RETURN NULL; END IF;
 IF action IN('context_import','import','revoke','custody_check') THEN assignment:=public.sr_template_assignment(h,'custody');
 ELSIF action IN('context_publish','publish','retire','publisher_check','approval_input') THEN assignment:=public.sr_template_assignment(h,'publish'); END IF;
 IF action NOT IN('bind','bindings') AND assignment IS NULL THEN RETURN NULL; END IF;
 IF action IN('publisher_check','custody_check') THEN RETURN jsonb_build_object('human_id',h); END IF;
 IF action IN('context_import','context_publish') THEN
  RETURN public.sr_template_evidence_context((payload->>'revision_id')::uuid,(payload->>'policy_id')::uuid,(payload->>'policy_version')::integer,
  CASE WHEN action='context_import' THEN 'import' ELSE 'publish' END,(payload->>'importer_human')::uuid);
 END IF;
 IF action='approval_input' THEN
  SELECT * INTO e FROM public.template_qa_approvals WHERE approval_id=(payload->>'approval_id')::uuid;
  IF NOT FOUND THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
  RETURN jsonb_build_object('approval_id',e.approval_id,'ciphertext',encode(e.ciphertext,'hex'),'key_version',e.key_version,'importer_human',e.importer_human,'evidence_sha256',e.evidence_sha256);
 END IF;
 IF action='bindings' THEN
  SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY binding_id),'[]'::jsonb) INTO rows FROM (
   SELECT * FROM public.print_template_variant_bindings WHERE ((payload->>'after') IS NULL OR binding_id>(payload->>'after')::uuid)
   AND ((payload->>'variant_id') IS NULL OR variant_id=(payload->>'variant_id')::uuid)
   AND ((payload->>'tag_type') IS NULL OR tag_type=payload->>'tag_type') AND ((payload->>'active') IS NULL OR is_active=(payload->>'active')::boolean)
   ORDER BY binding_id LIMIT LEAST(COALESCE((payload->>'limit')::integer,20),50)+1) x;
  RETURN jsonb_build_object('items',rows,'next_cursor',NULL,'as_of',clock_timestamp());
 END IF;
 PERFORM public.sr_template_registry_gate(true);
 IF action='import' THEN
  SELECT * INTO r FROM public.print_template_revisions WHERE revision_id=(payload->'summary'->>'revision_id')::uuid FOR UPDATE;
  IF r.status<>'pending_qa' OR NOT r.provenance_complete OR r.row_version<>(payload->'summary'->>'revision_row_version')::bigint OR r.fingerprint_sha256<>payload->'summary'->>'revision_fingerprint_sha256' THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  IF (payload->'summary'->>'expires_at')::timestamptz<=clock_timestamp() THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  SELECT * INTO e FROM public.template_qa_approvals WHERE evidence_id=(payload->'summary'->>'evidence_id')::uuid;
  IF FOUND THEN
   IF e.evidence_sha256<>payload->'summary'->>'evidence_sha256' THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  ELSE
   INSERT INTO public.template_qa_approvals(approval_id,evidence_id,revision_id,revision_row_version,revision_fingerprint_sha256,evidence_sha256,policy_id,policy_version,summary,ciphertext,key_version,importer_human,expires_at)
   VALUES((payload->>'approval_id')::uuid,(payload->'summary'->>'evidence_id')::uuid,r.revision_id,r.row_version,r.fingerprint_sha256,payload->'summary'->>'evidence_sha256',
   (payload->'summary'->>'policy_id')::uuid,(payload->'summary'->>'policy_version')::integer,payload->'summary',decode(payload->>'ciphertext','hex'),(payload->>'key_version')::smallint,h,(payload->'summary'->>'expires_at')::timestamptz) RETURNING * INTO e;
  END IF;
  RETURN jsonb_build_object('approval_id',e.approval_id,'revision_id',r.revision_id,'revision_row_version',e.revision_row_version,'revision_fingerprint_sha256',e.revision_fingerprint_sha256,'evidence_sha256',e.evidence_sha256,'state','eligible','expires_at',e.expires_at);
 END IF;
 IF action='revoke' THEN
  IF (payload->>'key_id' IS NULL)=(payload->>'evidence_id' IS NULL) THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  IF payload->>'key_id' IS NOT NULL THEN
   SELECT * INTO k FROM public.template_issuer_keys WHERE key_id=(payload->>'key_id')::uuid FOR UPDATE;
   IF NOT FOUND THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
   IF k.authority_version<>(payload->>'expected_authority_version')::bigint THEN RETURN jsonb_build_object('error','VERSION_MISMATCH'); END IF;
   UPDATE public.template_issuer_keys SET revoked_at=COALESCE(revoked_at,clock_timestamp()),authority_version=authority_version+1 WHERE key_id=k.key_id;
   aid:=k.key_id;
  ELSE
   SELECT * INTO e FROM public.template_qa_approvals WHERE evidence_id=(payload->>'evidence_id')::uuid FOR UPDATE;
   IF NOT FOUND THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
   IF e.authority_version<>(payload->>'expected_authority_version')::bigint THEN RETURN jsonb_build_object('error','VERSION_MISMATCH'); END IF;
   UPDATE public.template_qa_approvals SET revoked_at=COALESCE(revoked_at,clock_timestamp()),authority_version=authority_version+1 WHERE approval_id=e.approval_id;
   aid:=e.evidence_id;
  END IF;
  INSERT INTO public.template_authority_withdrawals(target_kind,target_id,authority_version,reason_code,actor_id) VALUES(CASE WHEN payload->>'key_id' IS NOT NULL THEN 'key' ELSE 'evidence' END,aid,(payload->>'expected_authority_version')::bigint+1,payload->>'reason_code',public.sr_actor_id()) RETURNING revocation_id INTO assignment;
  RETURN jsonb_build_object('revocation_id',assignment,'target_kind',CASE WHEN payload->>'key_id' IS NOT NULL THEN 'key' ELSE 'evidence' END,'target_id',aid,'authority_version',(payload->>'expected_authority_version')::bigint+1,'state','withdrawn');
 END IF;
 IF action='bind' THEN
  IF payload->>'revision_id' IS NULL THEN
   SELECT r0.template_id INTO aid FROM public.print_template_variant_bindings b0 JOIN public.print_template_revisions r0 ON r0.revision_id=b0.revision_id
   WHERE b0.variant_id=(payload->>'variant_id')::uuid AND b0.tag_type=payload->>'tag_type' AND b0.is_active AND b0.binding_id=(payload->>'expected_binding_id')::uuid;
   SELECT * INTO b FROM public.print_template_variant_bindings WHERE binding_id=(payload->>'expected_binding_id')::uuid;
  ELSE SELECT template_id INTO aid FROM public.print_template_revisions WHERE revision_id=(payload->>'revision_id')::uuid; END IF;
 ELSE aid:=(payload->>'template_id')::uuid; END IF;
 SELECT * INTO t FROM public.print_templates WHERE template_id=aid FOR UPDATE;
 SELECT * INTO r FROM public.print_template_revisions WHERE revision_id=COALESCE((payload->>'revision_id')::uuid,b.revision_id) AND template_id=t.template_id FOR UPDATE;
 IF t.template_id IS NULL OR r.revision_id IS NULL THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
 IF action='publish' THEN
  IF (payload->>'expected')::bigint<>r.row_version THEN RETURN jsonb_build_object('error','VERSION_MISMATCH'); END IF;
  SELECT * INTO e FROM public.template_qa_approvals WHERE approval_id=(payload->>'approval_id')::uuid AND revision_id=r.revision_id FOR UPDATE;
  IF NOT FOUND OR e.revoked_at IS NOT NULL OR e.consumed_at IS NOT NULL OR e.expires_at<=clock_timestamp() OR e.revision_row_version<>r.row_version OR e.evidence_sha256<>payload->>'verified_evidence_sha256'
  OR r.status<>'pending_qa' OR NOT r.provenance_complete OR t.lifecycle_status='retired' THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  IF EXISTS(SELECT 1 FROM public.template_revision_contributors c LEFT JOIN public.template_people m ON m.user_id=c.actor_id AND m.revoked_at IS NULL WHERE c.revision_id=r.revision_id AND (m.human_id IS NULL OR m.human_id=h))
  OR EXISTS(SELECT 1 FROM jsonb_array_elements(e.summary->'attestations') x JOIN public.template_issuer_keys k ON k.key_id=(x->>'key_id')::uuid JOIN public.template_authorities a ON a.authority_id=k.authority_id
   WHERE k.revoked_at IS NOT NULL OR k.expires_at<=clock_timestamp() OR a.revoked_at IS NOT NULL OR a.expires_at<=clock_timestamp() OR a.human_id=h)
  OR ((e.summary->>'allow_importer_publisher')::boolean IS NOT TRUE AND e.importer_human=h) THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  UPDATE public.template_qa_approvals SET consumed_at=clock_timestamp(),consumed_by=h,publisher_authority_id=assignment,authority_version=authority_version+1 WHERE approval_id=e.approval_id;
  UPDATE public.print_template_revisions SET status='published',published_at=clock_timestamp(),approval_id=e.approval_id,row_version=row_version+1 WHERE revision_id=r.revision_id RETURNING * INTO r;
  UPDATE public.print_templates SET lifecycle_status='active',row_version=row_version+1 WHERE template_id=t.template_id;
  RETURN jsonb_build_object('revision',public.sr_template_revision_view(r),'approval_id',e.approval_id);
 ELSIF action='bind' THEN
  SELECT * INTO v FROM public.product_variants WHERE id=(payload->>'variant_id')::uuid FOR UPDATE;
  IF NOT FOUND THEN RETURN jsonb_build_object('error','NOT_FOUND'); END IF;
  IF v.catalog_version<>(payload->>'expected')::bigint OR v.catalog_version<>(payload->>'expected_variant_version')::bigint THEN RETURN jsonb_build_object('error','VERSION_MISMATCH'); END IF;
  IF payload->>'revision_id' IS NULL THEN
   IF v.is_active OR b.binding_id IS NULL OR NOT b.is_active OR b.variant_id<>v.id OR b.tag_type<>payload->>'tag_type' THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
   UPDATE public.print_template_variant_bindings SET is_active=false,row_version=row_version+1 WHERE binding_id=b.binding_id RETURNING * INTO b;
   UPDATE public.template_registry_sources SET generation=generation+1 WHERE variant_id=v.id;
   UPDATE public.product_variants SET catalog_version=catalog_version+1 WHERE id=v.id RETURNING * INTO v;
   RETURN jsonb_build_object('binding',to_jsonb(b),'variant_row_version',v.catalog_version);
  END IF;
  IF NOT public.sr_template_revision_clear(r.revision_id,false) THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  IF v.template_key IS DISTINCT FROM t.key OR v.template_version IS DISTINCT FROM r.version OR v.fulfillment_method IS DISTINCT FROM 'pdf_label' OR v.size_mm IS DISTINCT FROM (r.content->>'symbol_mm')::numeric OR t.purpose IS DISTINCT FROM payload->>'tag_type'
  OR NOT COALESCE((r.content->'material_codes') ? v.material,false) THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  SELECT * INTO b FROM public.print_template_variant_bindings WHERE variant_id=v.id AND tag_type=payload->>'tag_type' AND is_active FOR UPDATE;
  IF b.binding_id IS DISTINCT FROM (payload->>'expected_binding_id')::uuid THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  UPDATE public.print_template_variant_bindings SET is_active=false,row_version=row_version+1 WHERE binding_id=b.binding_id;
  INSERT INTO public.print_template_variant_bindings(variant_id,tag_type,revision_id) VALUES(v.id,t.purpose,r.revision_id) RETURNING * INTO b;
  INSERT INTO public.template_registry_sources(variant_id) VALUES(v.id) ON CONFLICT(variant_id) DO UPDATE SET generation=public.template_registry_sources.generation+1;
  UPDATE public.product_variants SET catalog_version=catalog_version+1 WHERE id=v.id RETURNING * INTO v;
  RETURN jsonb_build_object('binding',to_jsonb(b),'variant_row_version',v.catalog_version);
 ELSIF action='retire' THEN
  IF (payload->>'expected')::bigint<>r.row_version THEN RETURN jsonb_build_object('error','VERSION_MISMATCH'); END IF;
  IF r.status<>'published' OR EXISTS(SELECT 1 FROM public.print_template_variant_bindings WHERE revision_id=r.revision_id AND is_active) THEN RETURN jsonb_build_object('error','CONFLICT'); END IF;
  UPDATE public.print_template_revisions SET status='retired',row_version=row_version+1 WHERE revision_id=r.revision_id RETURNING * INTO r;
  UPDATE public.print_templates SET lifecycle_status=CASE WHEN NOT EXISTS(SELECT 1 FROM public.print_template_revisions WHERE template_id=t.template_id AND status<>'retired') THEN 'retired' ELSE lifecycle_status END,row_version=row_version+1 WHERE template_id=t.template_id RETURNING * INTO t;
  RETURN jsonb_build_object('revision',public.sr_template_revision_view(r),'template',to_jsonb(t)-'created_by');
 END IF;
 RETURN jsonb_build_object('error','CONFLICT');
END $$;

CREATE FUNCTION public.sr_template_authority_record_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 PERFORM public.sr_template_registry_gate(true);
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Authority history is permanent' USING ERRCODE='23514'; END IF;
 IF TG_OP='UPDATE' THEN
  IF (to_jsonb(NEW)-'revoked_at'-'authority_version') IS DISTINCT FROM (to_jsonb(OLD)-'revoked_at'-'authority_version')
  OR (to_jsonb(OLD)->>'revoked_at' IS NOT NULL AND to_jsonb(NEW)->>'revoked_at' IS NULL) THEN
   RAISE EXCEPTION 'Authority identity and evidence are immutable' USING ERRCODE='23514';
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_template_people_fixed BEFORE INSERT OR UPDATE OR DELETE ON public.template_people FOR EACH ROW EXECUTE FUNCTION public.sr_template_authority_record_guard();
CREATE TRIGGER sr_template_authority_fixed BEFORE INSERT OR UPDATE OR DELETE ON public.template_authorities FOR EACH ROW EXECUTE FUNCTION public.sr_template_authority_record_guard();
CREATE TRIGGER sr_template_key_fixed BEFORE INSERT OR UPDATE OR DELETE ON public.template_issuer_keys FOR EACH ROW EXECUTE FUNCTION public.sr_template_authority_record_guard();
CREATE TRIGGER sr_template_policy_fixed BEFORE INSERT OR UPDATE OR DELETE ON public.template_production_policies FOR EACH ROW EXECUTE FUNCTION public.sr_template_authority_record_guard();
CREATE TRIGGER sr_template_archive_fixed BEFORE INSERT OR UPDATE OR DELETE ON public.template_archive_entries FOR EACH ROW EXECUTE FUNCTION public.sr_template_authority_record_guard();
CREATE FUNCTION public.sr_template_evidence_fixed() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Evidence is immutable' USING ERRCODE='23514'; END IF;
 IF ((to_jsonb(NEW)-'consumed_at'-'consumed_by'-'publisher_authority_id'-'revoked_at'-'authority_version') IS DISTINCT FROM
 (to_jsonb(OLD)-'consumed_at'-'consumed_by'-'publisher_authority_id'-'revoked_at'-'authority_version'))
 OR (OLD.consumed_at IS NOT NULL AND (NEW.consumed_at IS DISTINCT FROM OLD.consumed_at OR NEW.consumed_by IS DISTINCT FROM OLD.consumed_by OR NEW.publisher_authority_id IS DISTINCT FROM OLD.publisher_authority_id))
 OR (OLD.revoked_at IS NOT NULL AND NEW.revoked_at IS DISTINCT FROM OLD.revoked_at) THEN
  RAISE EXCEPTION 'Evidence is immutable' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_template_evidence_fixed BEFORE UPDATE OR DELETE ON public.template_qa_approvals FOR EACH ROW EXECUTE FUNCTION public.sr_template_evidence_fixed();
CREATE FUNCTION public.sr_template_asset_fixed() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 PERFORM public.sr_template_registry_gate(true);
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Historical assets are immutable' USING ERRCODE='23514'; END IF;
 IF ((to_jsonb(NEW)-'withdrawn_at') IS DISTINCT FROM (to_jsonb(OLD)-'withdrawn_at'))
 OR (OLD.withdrawn_at IS NOT NULL AND NEW.withdrawn_at IS DISTINCT FROM OLD.withdrawn_at) THEN RAISE EXCEPTION 'Historical assets are immutable' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_template_asset_fixed BEFORE UPDATE OR DELETE ON public.print_template_asset_sets FOR EACH ROW EXECUTE FUNCTION public.sr_template_asset_fixed();

-- Permanent, separate security holds; no mutation of order/payment/QR/print history.
-- Called only after a protected authority/evidence/artwork withdrawal, under the
-- exclusive gate. Mere unused-evidence expiry or ordinary retirement is not a hold.
CREATE FUNCTION public.sr_template_record_holds() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE before_row jsonb:=to_jsonb(OLD); after_row jsonb:=to_jsonb(NEW); source text;
BEGIN
 IF (before_row->>'revoked_at' IS NULL AND after_row->>'revoked_at' IS NOT NULL)
 OR (before_row->>'withdrawn_at' IS NULL AND after_row->>'withdrawn_at' IS NOT NULL) THEN
  PERFORM public.sr_template_registry_gate(true);
  source:=COALESCE(after_row->>'key_id',after_row->>'authority_id',after_row->>'approval_id',after_row->>'asset_set_id',after_row->>'reference',after_row->>'user_id',(after_row->>'policy_id')||':'||(after_row->>'version'));
  INSERT INTO public.template_order_holds(order_id,source_kind,source_reference)
   SELECT o.order_id,TG_TABLE_NAME,source FROM public.template_registry_orders o
   WHERE NOT EXISTS(SELECT 1 FROM public.shipments sh WHERE sh.order_id=o.order_id AND sh.dispatched_at IS NOT NULL)
   AND EXISTS(SELECT 1 FROM public.order_use_print_specs s JOIN public.order_item_qr_uses u ON u.id=s.use_id JOIN public.order_items i ON i.id=u.order_item_id
    WHERE i.order_id=o.order_id AND NOT public.sr_template_revision_clear(s.revision_id,true))
   ON CONFLICT DO NOTHING;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sr_template_key_holds AFTER UPDATE ON public.template_issuer_keys FOR EACH ROW EXECUTE FUNCTION public.sr_template_record_holds();
CREATE TRIGGER sr_template_authority_holds AFTER UPDATE ON public.template_authorities FOR EACH ROW EXECUTE FUNCTION public.sr_template_record_holds();
CREATE TRIGGER sr_template_evidence_holds AFTER UPDATE ON public.template_qa_approvals FOR EACH ROW EXECUTE FUNCTION public.sr_template_record_holds();
CREATE TRIGGER sr_template_policy_holds AFTER UPDATE ON public.template_production_policies FOR EACH ROW EXECUTE FUNCTION public.sr_template_record_holds();
CREATE TRIGGER sr_template_archive_holds AFTER UPDATE ON public.template_archive_entries FOR EACH ROW EXECUTE FUNCTION public.sr_template_record_holds();
CREATE TRIGGER sr_template_asset_holds AFTER UPDATE ON public.print_template_asset_sets FOR EACH ROW EXECUTE FUNCTION public.sr_template_record_holds();

-- Preserve the complete pending-chain financial/QA predicate. Add registry holds
-- to ready-to-ship discovery and the existing deferred fulfillment guard.
ALTER FUNCTION public.sr_fulfillment_eligible(uuid) RENAME TO sr_fulfillment_eligible_v33;
CREATE FUNCTION public.sr_fulfillment_eligible(oid uuid) RETURNS boolean
LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT public.sr_fulfillment_eligible_v33(oid)
 AND COALESCE(NOT (public.sr_template_order_specs(oid) ? 'error'),true)
$$;
REVOKE ALL ON FUNCTION public.sr_fulfillment_eligible_v33(uuid),public.sr_fulfillment_eligible(uuid) FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_fulfillment_eligible(uuid) TO safereturn_api;

DO $$ DECLARE tbl text; fn record; BEGIN
 FOREACH tbl IN ARRAY ARRAY['template_people','template_authorities','template_issuer_keys','template_production_policies','template_archive_entries','template_revision_contributors','template_qa_approvals','print_template_variant_bindings','template_registry_sources','order_use_print_specs','template_authority_withdrawals','template_registry_orders','template_order_holds'] LOOP
  EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',tbl);
  EXECUTE format('REVOKE ALL ON public.%I FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker',tbl);
 END LOOP;
 -- All helpers (including trigger/internal functions) default to no public runtime entry.
 FOR fn IN SELECT p.oid::regprocedure AS signature FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public'
  AND (p.proname LIKE 'sr_template_%' OR p.proname='sr_template_service') LOOP
  EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker',fn.signature);
 END LOOP;
END $$;
GRANT EXECUTE ON FUNCTION public.sr_template_registry_gate(boolean) TO safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_template_service(uuid,bigint,text,jsonb),public.sr_template_preview_admit(uuid,bigint,text,text),public.sr_template_lifecycle(uuid,bigint,text,jsonb),public.sr_template_resolve(uuid,jsonb),public.sr_template_freeze_use(uuid,jsonb) TO safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_template_order_specs(uuid) TO safereturn_api,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_template_catalog_eligible(uuid) TO safereturn_api;

