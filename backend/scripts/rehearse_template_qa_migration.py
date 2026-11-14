"""Pinned rollback-only QA DDL rehearsal; no fixtures, grants or committed DDL."""
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

import psycopg
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
PROJECT = 'fhuxryfkfrvycsojkzvq'


def main():
    env = dotenv_values(ROOT / 'backend/.env', interpolate=False)
    assert env.get('SAFERETURN_SUPABASE_URL', '').rstrip('/') == f'https://{PROJECT}.supabase.co'
    target = urlsplit(env['SAFERETURN_MIGRATION_DATABASE_URL'].replace('postgresql+psycopg:', 'postgresql:'))
    assert target.hostname == 'aws-0-ap-northeast-2.pooler.supabase.com' and target.port == 5432
    assert unquote(target.username).endswith('.' + PROJECT) and target.path == '/postgres'
    ca = ROOT / 'tmp/phase9-cloud-audit/supabase-verified-root.pem'
    assert hashlib.sha256(ca.read_bytes()).hexdigest() == '700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7'
    sql = (ROOT / 'backend/alembic/versions/0045_template_qa_reviews.sql').read_text(encoding='utf-8')
    metadata = """SELECT proowner::regrole::text,proacl::text,proconfig,prosecdef
        FROM pg_proc WHERE oid='public.sr_template_lifecycle(uuid,bigint,text,jsonb)'::regprocedure"""
    report = {'project': PROJECT, 'mode': 'rollback-only', 'migration_sql_sha256': hashlib.sha256(sql.encode()).hexdigest()}
    with psycopg.connect(host=target.hostname, port=target.port, dbname='postgres', user=unquote(target.username), password=unquote(target.password), sslmode='verify-full', sslrootcert=str(ca), connect_timeout=10, autocommit=True) as connection:
        connection.execute('BEGIN')
        try:
            connection.execute("SET LOCAL lock_timeout='3s'")
            connection.execute("SET LOCAL statement_timeout='20000ms'")
            assert connection.execute('SELECT version_num FROM public.alembic_version').fetchall() == [('0043_standalone_activation',)]
            assert connection.execute("SELECT to_regclass('public.template_qa_reviews')").fetchone()[0] is None
            before = connection.execute(metadata).fetchone()
            connection.execute('SELECT public.sr_template_registry_gate(true)')
            connection.execute(sql)
            after = connection.execute(metadata).fetchone()
            assert before == after, 'Function owner/ACL/config/security mode changed'
            table = connection.execute("SELECT relrowsecurity,relowner::regrole::text FROM pg_class WHERE oid='public.template_qa_reviews'::regclass").fetchone()
            assert table[0] and table[1] == after[0], 'Review table RLS/function ownership mismatch'
            for role in ['anon', 'authenticated', 'safereturn_api', 'safereturn_worker']:
                for privilege in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER']:
                    assert not connection.execute('SELECT has_table_privilege(%s,%s,%s)', (role, 'public.template_qa_reviews', privilege)).fetchone()[0], 'Unexpected runtime table privilege'
            report.update(sql_compiled=True, function_metadata_preserved=True, new_table_rls=True, runtime_table_privileges=False)
        finally:
            connection.execute('ROLLBACK')
        report['rollback_verified'] = connection.execute("SELECT to_regclass('public.template_qa_reviews') IS NULL").fetchone()[0]
        report['installed_revision'] = connection.execute('SELECT version_num FROM public.alembic_version').fetchall()
    output = ROOT / 'tmp/template-activation/qa-migration-rehearsal.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
