-- Manual physical approval is now an explicit publication authority for that
-- exact immutable revision. Never manufacture a signed-evidence approval.
ALTER TABLE public.print_template_revisions ADD COLUMN manual_review_id uuid
 REFERENCES public.template_qa_reviews(review_id) ON DELETE RESTRICT;
ALTER TABLE public.print_template_revisions DROP CONSTRAINT ck_template_revision_lifecycle;
ALTER TABLE public.print_template_revisions ADD CONSTRAINT ck_template_revision_lifecycle CHECK(
 (status='draft' AND fingerprint_sha256 IS NULL AND published_at IS NULL AND approval_id IS NULL AND manual_review_id IS NULL)
 OR(status='pending_qa' AND fingerprint_sha256 IS NOT NULL AND published_at IS NULL AND approval_id IS NULL AND manual_review_id IS NULL)
 OR(status IN('published','retired') AND fingerprint_sha256 IS NOT NULL AND published_at IS NOT NULL AND ((approval_id IS NOT NULL AND manual_review_id IS NULL) OR (approval_id IS NULL AND manual_review_id IS NOT NULL)))
);
CREATE FUNCTION public.sr_template_manual_publication_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE q public.template_qa_reviews;
BEGIN
 IF TG_OP='UPDATE' AND OLD.manual_review_id IS NOT NULL AND NEW.manual_review_id IS DISTINCT FROM OLD.manual_review_id THEN
  RAISE EXCEPTION 'Physical publication reference is immutable' USING ERRCODE='23514';
 END IF;
 IF NEW.manual_review_id IS NOT NULL THEN
  SELECT * INTO q FROM public.template_qa_reviews WHERE review_id=NEW.manual_review_id;
  IF NOT FOUND OR q.revision_id<>NEW.revision_id OR q.decision<>'approved' OR q.evidence_kind<>'manual_print'
   OR q.preview_fingerprint IS DISTINCT FROM NEW.fingerprint_sha256 OR NEW.row_version<q.revision_row_version+1
   OR EXISTS(SELECT 1 FROM public.template_qa_reviews x WHERE x.revision_id=NEW.revision_id AND x.review_version>q.review_version)
  THEN RAISE EXCEPTION 'Matching physical QA approval required' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION public.sr_template_manual_publication_guard() FROM PUBLIC,anon,authenticated,safereturn_api,safereturn_worker;
CREATE TRIGGER sr_template_manual_publication BEFORE INSERT OR UPDATE ON public.print_template_revisions
 FOR EACH ROW EXECUTE FUNCTION public.sr_template_manual_publication_guard();

-- Keep the closed revision DTO unchanged; publication provenance is protected.
CREATE OR REPLACE FUNCTION public.sr_template_revision_view(r public.print_template_revisions) RETURNS jsonb
LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT to_jsonb(r)-'created_by'-'updated_by'-'version_note'-'provenance_complete'-'approval_id'-'manual_review_id'
$$;
DO $migration$
DECLARE source text; anchor text; replacement text;
BEGIN
 source:=pg_get_functiondef('public.sr_template_service(uuid,bigint,text,jsonb)'::regprocedure);
 IF position('-''approval_id''' IN source)=0 THEN RAISE EXCEPTION 'Unexpected revision projection'; END IF;
 source:=replace(source,'-''approval_id''','-''approval_id''-''manual_review_id''');
 EXECUTE source;
 source:=pg_get_functiondef('public.sr_template_lifecycle(uuid,bigint,text,jsonb)'::regprocedure);
 anchor:='    VALUES(r.revision_id,r.row_version,(payload->>''expected_review_version'')::bigint+1,payload->>''decision'',payload->>''reason'',public.sr_actor_id(),NULL,NULL,''manual_print'',r.fingerprint_sha256);';
 IF position(anchor IN source)=0 OR position('manual_review_id' IN source)>0 THEN RAISE EXCEPTION 'Unexpected manual review source'; END IF;
 replacement:=replace(anchor,'r.fingerprint_sha256);','r.fingerprint_sha256) RETURNING review_id INTO aid;')||$body$
   IF payload->>'decision'='approved' THEN
    SELECT * INTO t FROM public.print_templates WHERE template_id=r.template_id FOR UPDATE;
    IF t.lifecycle_status='retired' THEN RAISE EXCEPTION 'Retired template cannot publish' USING ERRCODE='23514'; END IF;
    IF NOT EXISTS(SELECT 1 FROM public.print_template_asset_sets a WHERE a.asset_set_id=(r.content->>'asset_set_id')::uuid AND a.withdrawn_at IS NULL) THEN RAISE EXCEPTION 'Template assets unavailable' USING ERRCODE='23514'; END IF;
    UPDATE public.print_template_revisions SET status='published',published_at=clock_timestamp(),manual_review_id=aid,row_version=row_version+1 WHERE revision_id=r.revision_id RETURNING * INTO r;
    UPDATE public.print_templates SET lifecycle_status='active',row_version=row_version+1 WHERE template_id=r.template_id;
   END IF;
$body$;
 source:=replace(source,anchor,replacement);
 -- The HTTP response reports publication independently from the review status.
 anchor:='''status'',COALESCE(rows->0->>''decision'',''pending''),''history'',rows,';
 IF position(anchor IN source)=0 THEN RAISE EXCEPTION 'Unexpected review response'; END IF;
 source:=replace(source,anchor,anchor||'''publication_status'',r.status,''published_at'',r.published_at,');
 -- A retired template may not accept new physical reviews that could publish it.
 source:=replace(source,'''can_review'',public.sr_is_staff(ARRAY[''operations'']) IS TRUE AND r.status=''pending_qa''', '''can_review'',public.sr_is_staff(ARRAY[''operations'']) IS TRUE AND NOT EXISTS(SELECT 1 FROM public.print_templates t0 WHERE t0.template_id=r.template_id AND t0.lifecycle_status=''retired'') AND r.status=''pending_qa''');
 EXECUTE source;
END $migration$;

-- Reconcile existing genuine manual approvals, never drafts, rejections, stale
-- reviews or changed fingerprints. Preserve the original reviewer/time record.
DO $$
DECLARE candidate record;
BEGIN
 FOR candidate IN SELECT r.revision_id,q.review_id FROM public.print_template_revisions r
 JOIN public.print_templates t ON t.template_id=r.template_id
 JOIN public.template_qa_reviews q ON q.revision_id=r.revision_id
 JOIN public.print_template_asset_sets a ON a.asset_set_id=(r.content->>'asset_set_id')::uuid AND a.withdrawn_at IS NULL
 WHERE r.status='pending_qa' AND t.lifecycle_status<>'retired' AND q.decision='approved' AND q.evidence_kind='manual_print'
 AND q.revision_row_version=r.row_version AND q.preview_fingerprint=r.fingerprint_sha256
 AND q.review_version=(SELECT max(q2.review_version) FROM public.template_qa_reviews q2 WHERE q2.revision_id=r.revision_id)
 ORDER BY r.revision_id FOR UPDATE OF r,t LOOP
  UPDATE public.print_template_revisions SET status='published',published_at=clock_timestamp(),manual_review_id=candidate.review_id,row_version=row_version+1 WHERE revision_id=candidate.revision_id;
  UPDATE public.print_templates SET lifecycle_status='active',row_version=row_version+1 WHERE template_id=(SELECT template_id FROM public.print_template_revisions WHERE revision_id=candidate.revision_id);
  INSERT INTO public.audit_events(actor_kind,action,target_type,target_id,reason,safe_details)
   VALUES('system','template.qa.publication_reconciled','print_template_revision',candidate.revision_id,'Owner-authorized publication of existing matching physical QA approval',jsonb_build_object('event_id',candidate.review_id::text,'outcome','success'));
 END LOOP;
END $$;
