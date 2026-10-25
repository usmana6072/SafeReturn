-- Keep published designs immutable. Permit the single provenance attachment
-- required by manual binding, without allowing any content or lifecycle edit.
DO $patch$
DECLARE source text; anchor text; injected text;
BEGIN
 source:=pg_get_functiondef('public.sr_template_contributor_guard()'::regprocedure);
 anchor:=' IF TG_OP=''UPDATE'' AND (OLD.status=''retired''';
 IF position(anchor IN source)=0 OR position('manual approval attachment' IN source)>0 THEN RAISE EXCEPTION 'Review publication transition guard'; END IF;
 injected:=$body$
 -- Exact one-time manual approval attachment, not a general published update.
 IF TG_OP='UPDATE' AND OLD.status='published' AND NEW.status='published'
  AND OLD.approval_id IS NULL AND NEW.approval_id IS NOT NULL
  AND OLD.manual_review_id IS NOT NULL AND NEW.manual_review_id=OLD.manual_review_id
  AND NEW.row_version=OLD.row_version+1
  AND (to_jsonb(NEW)-'approval_id'-'row_version')=(to_jsonb(OLD)-'approval_id'-'row_version')
  AND EXISTS(SELECT 1 FROM public.template_qa_approvals a
   JOIN public.template_qa_reviews q ON q.review_id=a.manual_review_id
   JOIN public.template_production_policies p ON p.policy_id=a.policy_id AND p.version=a.policy_version
   WHERE a.approval_id=NEW.approval_id AND a.approval_kind='manual_print' AND a.manual_review_id=OLD.manual_review_id
   AND a.revision_id=OLD.revision_id AND a.revision_row_version=OLD.row_version AND a.revision_fingerprint_sha256=OLD.fingerprint_sha256
   AND a.revoked_at IS NULL AND a.consumed_at IS NOT NULL
   AND q.revision_id=OLD.revision_id AND q.decision='approved' AND q.evidence_kind='manual_print' AND q.preview_fingerprint=OLD.fingerprint_sha256
   AND NOT EXISTS(SELECT 1 FROM public.template_qa_reviews newer WHERE newer.revision_id=OLD.revision_id AND newer.review_version>q.review_version)
   AND p.revoked_at IS NULL AND p.sha256=a.summary->>'policy_sha256' AND p.body->>'approval_mode'='manual_print') THEN
  RETURN NEW;
 END IF;
$body$;
 EXECUTE replace(source,anchor,injected||anchor);
END $patch$;
