"""Run the real patched publication trigger in temporary tables only."""
from sqlalchemy import text


def verify_attachment_guard(connection):
    # Clone only table structure; use one already-published revision/review as a
    # temporary test input. No persistent table receives an insert/update.
    for name in ('print_template_revisions', 'template_qa_approvals', 'template_qa_reviews', 'template_production_policies'):
        connection.execute(text(f'CREATE TEMP TABLE qa_test_{name} ON COMMIT DROP AS SELECT * FROM public.{name} WITH NO DATA'))
    connection.execute(text("INSERT INTO qa_test_print_template_revisions SELECT * FROM public.print_template_revisions WHERE status='published' AND manual_review_id IS NOT NULL AND approval_id IS NULL ORDER BY revision_id LIMIT 1"))
    count = connection.execute(text('SELECT count(*) FROM qa_test_print_template_revisions')).scalar_one()
    if count != 1:
        raise RuntimeError('One unbound manual publication needed for temporary guard verification')
    connection.execute(text('INSERT INTO qa_test_template_qa_reviews SELECT q.* FROM public.template_qa_reviews q JOIN qa_test_print_template_revisions r ON r.manual_review_id=q.review_id'))
    connection.execute(text("INSERT INTO qa_test_template_production_policies(policy_id,version,sha256,body,reviewed_by,archive_reference) SELECT '00000000-0000-4000-8000-000000004901',1,repeat('a',64),'{\"approval_mode\":\"manual_print\"}'::jsonb,reviewer_user_id,'temporary-guard-test' FROM qa_test_template_qa_reviews"))
    connection.execute(text("""INSERT INTO qa_test_template_qa_approvals(approval_id,evidence_id,revision_id,revision_row_version,revision_fingerprint_sha256,evidence_sha256,policy_id,policy_version,summary,consumed_at,approval_kind,manual_review_id)
     SELECT '00000000-0000-4000-8000-000000004902',manual_review_id,revision_id,row_version,fingerprint_sha256,repeat('b',64),'00000000-0000-4000-8000-000000004901',1,jsonb_build_object('policy_sha256',repeat('a',64)),clock_timestamp(),'manual_print',manual_review_id FROM qa_test_print_template_revisions"""))
    definition = connection.execute(text("SELECT pg_get_functiondef('public.sr_template_contributor_guard()'::regprocedure)")).scalar_one()
    definition = definition.replace('FUNCTION public.sr_template_contributor_guard()', 'FUNCTION pg_temp.qa_attachment_guard()')
    for name in ('template_qa_approvals', 'template_qa_reviews', 'template_production_policies'):
        definition = definition.replace('public.' + name, 'pg_temp.qa_test_' + name)
    connection.execute(text(definition))
    connection.execute(text('CREATE TRIGGER qa_guard BEFORE UPDATE ON qa_test_print_template_revisions FOR EACH ROW EXECUTE FUNCTION pg_temp.qa_attachment_guard()'))
    # Permitted exact one-time provenance attachment.
    with connection.begin_nested() as temporary:
        connection.execute(text("UPDATE qa_test_print_template_revisions SET approval_id='00000000-0000-4000-8000-000000004902',row_version=row_version+1"))
        temporary.rollback()
    from sqlalchemy.exc import IntegrityError
    rejected = 0
    for setters in (
        "approval_id='00000000-0000-4000-8000-000000004902',row_version=row_version+1,version=version+1",
        "approval_id='00000000-0000-4000-8000-000000004902',row_version=row_version+2",
        "approval_id='00000000-0000-4000-8000-000000004903',row_version=row_version+1",
        'row_version=row_version+1',
        "content=jsonb_set(content,'{header}','\"Changed published content\"'::jsonb)",
    ):
        try:
            with connection.begin_nested():
                connection.execute(text('UPDATE qa_test_print_template_revisions SET ' + setters))
        except IntegrityError as error:
            if getattr(error.orig, 'sqlstate', None) != '23514':
                raise
            rejected += 1
        else:
            raise RuntimeError('Immutable publication update unexpectedly permitted')
    return {'exact_attachment_allowed': True, 'immutable_or_invalid_updates_rejected': rejected, 'persistent_writes': False}
