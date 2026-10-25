"""Manual physical-QA binding integration migration (rollback rehearsal by default; --apply commits), fenced to the development project.

No upgrade head, Support migration, enrollment, synthetic fixture or new QA decision.
No product, policy, approval, binding or QA decision is created by this schema migration.
"""
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

import psycopg
from alembic.config import Config
from dotenv import dotenv_values
from sqlalchemy import create_engine, text

from alembic import command

ROOT = Path(__file__).resolve().parents[2]
PROJECT = 'fhuxryfkfrvycsojkzvq'
REVISION = '0050_public_catalog_browsing'
SQL_SHA256 = 'dedeb4d23d77ff74d4f0da113fca4fd4859858a829d84968695668c129a79b4a'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--hostaddr', help='Freshly DNS-verified pooler address; host/TLS/project fencing remains mandatory')
    args = parser.parse_args()
    apply = args.apply
    if args.hostaddr:
        assert ipaddress.ip_address(args.hostaddr).is_global, 'Public pooler address required'
    env = dotenv_values(ROOT / 'backend/.env', interpolate=False)
    assert env.get('SAFERETURN_SUPABASE_URL', '').rstrip('/') == f'https://{PROJECT}.supabase.co'
    target = urlsplit(env['SAFERETURN_MIGRATION_DATABASE_URL'].replace('postgresql+psycopg:', 'postgresql:'))
    assert target.hostname == 'aws-0-ap-northeast-2.pooler.supabase.com' and target.port == 5432
    assert unquote(target.username).endswith('.' + PROJECT) and target.path == '/postgres'
    ca = ROOT / 'tmp/phase9-cloud-audit/supabase-verified-root.pem'
    assert hashlib.sha256(ca.read_bytes()).hexdigest() == '700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7'
    sql = ROOT / 'backend/alembic/versions/0050_public_catalog_browsing.sql'
    assert hashlib.sha256(sql.read_bytes().replace(b'\r\n', b'\n')).hexdigest() == SQL_SHA256
    assert hashlib.sha256((ROOT / 'backend/alembic/versions/0044_support_dev_exception.sql').read_bytes()).hexdigest() == '17b3b5bd5964f6dfb7a1b610bce455d32fc805539282e3ecb7d79a9e39a19a2d'
    assert hashlib.sha256((ROOT / 'backend/alembic/versions/0044_support_dev_exception.py').read_bytes()).hexdigest() == '67318373a9fecdca0fa441697d37ae4a1c0719d7ce0dd1e125e85ea07ddc5c30'
    config = Config(str(ROOT / 'backend/alembic.ini'))
    config.set_main_option('script_location', str(ROOT / 'backend/alembic'))
    from alembic.script import ScriptDirectory
    scripts = ScriptDirectory.from_config(config)
    migration = scripts.get_revision(REVISION)
    assert migration.down_revision == '0049_manual_approval_attach'
    metadata = text("SELECT jsonb_agg(jsonb_build_array(oid::text,proowner::regrole::text,proacl::text,proconfig,prosecdef) ORDER BY oid) FROM pg_proc WHERE oid IN ('public.sr_template_lifecycle(uuid,bigint,text,jsonb)'::regprocedure,'public.sr_public_catalog(text)'::regprocedure)")
    report = {'project': PROJECT, 'requested_revision': REVISION, 'sql_sha256': SQL_SHA256}
    engine = create_engine('postgresql+psycopg://', creator=lambda: psycopg.connect(host=target.hostname, port=target.port, dbname='postgres', user=unquote(target.username), password=unquote(target.password), sslmode='verify-full', sslrootcert=str(ca), connect_timeout=10, **({'hostaddr': args.hostaddr} if args.hostaddr else {})))
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            connection.execute(text("SET LOCAL lock_timeout='3s'"))
            connection.execute(text("SET LOCAL statement_timeout='20000ms'"))
            connection.execute(text("SELECT pg_advisory_xact_lock(hashtextextended('safereturn.qa-migration-0050',0))"))
            installed = connection.execute(text('SELECT version_num FROM public.alembic_version')).scalars().all()
            assert installed == ['0049_manual_approval_attach'], 'Unexpected installed revision; no upgrade attempted'
            assert not connection.execute(text("SELECT position('checkout_available' IN pg_get_functiondef('public.sr_public_catalog(text)'::regprocedure))>0")).scalar_one()
            releases_before = connection.execute(text('SELECT (SELECT enabled FROM public.single_checkout_release),(SELECT enabled FROM public.standalone_owner_release)')).one()
            published_before = connection.execute(text("SELECT count(*) FROM public.print_template_revisions WHERE status='published'")).scalar_one()
            reviews_before = connection.execute(text('SELECT count(*) FROM public.template_qa_reviews')).scalar_one()
            assert connection.execute(text("SELECT to_regclass('public.support_dev_exception')")).scalar_one() is None
            support_role = connection.execute(text("SELECT count(*) FROM pg_roles WHERE rolname='safereturn_support_provisioner'")).scalar_one()
            before = connection.execute(metadata).one()
            connection.execute(text('SELECT public.sr_template_registry_gate(true)'))
            config.attributes['connection'] = connection
            command.upgrade(config, REVISION)
            assert connection.execute(text('SELECT version_num FROM public.alembic_version')).scalars().all() == [REVISION]
            assert connection.execute(metadata).one() == before, 'Lifecycle owner/ACL/config changed'
            assert connection.execute(text("SELECT to_regclass('public.support_dev_exception')")).scalar_one() is None
            assert connection.execute(text("SELECT count(*) FROM pg_roles WHERE rolname='safereturn_support_provisioner'")).scalar_one() == support_role
            assert connection.execute(text("SELECT relrowsecurity FROM pg_class WHERE oid='public.template_qa_reviews'::regclass")).scalar_one()
            assert connection.execute(text('SELECT count(*) FROM public.template_qa_reviews')).scalar_one() == reviews_before
            for role in ['anon', 'authenticated', 'safereturn_api', 'safereturn_worker']:
                for privilege in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER']:
                    assert not connection.execute(text('SELECT has_table_privilege(:role,:table,:privilege)'), {'role': role, 'table': 'public.template_qa_reviews', 'privilege': privilege}).scalar_one()
            report['existing_approved_revisions_published'] = connection.execute(text("SELECT count(*) FROM public.print_template_revisions WHERE status='published'")).scalar_one() - published_before
            assert connection.execute(text('SELECT (SELECT enabled FROM public.single_checkout_release),(SELECT enabled FROM public.standalone_owner_release)')).one() == releases_before
            report['release_switches_unchanged'] = True
            report['catalog'] = connection.execute(text('SELECT public.sr_public_catalog(NULL)')).scalar_one()
            report.update(function_metadata_preserved=True, review_table_rls=True, runtime_table_access=False, support_migration_applied=False, review_count=reviews_before)
            report['mode'] = 'apply' if apply else 'rollback-rehearsal'
            if apply:
                transaction.commit()
            else:
                transaction.rollback()
        # New transaction verifies committed state rather than reporting precommit success.
        with engine.connect() as connection:
            report['installed_revision'] = connection.execute(text('SELECT version_num FROM public.alembic_version')).scalars().all()
            assert report['installed_revision'] == ([REVISION] if apply else ['0049_manual_approval_attach'])
            present = connection.execute(text("SELECT position('checkout_available' IN pg_get_functiondef('public.sr_public_catalog(text)'::regprocedure))>0")).scalar_one()
            assert present == apply
            report['commit_verified' if apply else 'rollback_verified'] = True
    finally:
        engine.dispose()
    output = ROOT / ('tmp/template-activation/public-catalog-browsing-applied.json' if apply else 'tmp/template-activation/public-catalog-browsing-rehearsal.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
