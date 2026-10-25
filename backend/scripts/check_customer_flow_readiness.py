"""Pinned read-only customer lifecycle readiness; no provider/user/order changes."""
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

import psycopg
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]


def main():
    env = dotenv_values(ROOT / 'backend/.env', interpolate=False)
    assert env.get('SAFERETURN_SUPABASE_URL', '').rstrip('/') == 'https://fhuxryfkfrvycsojkzvq.supabase.co'
    target = urlsplit(env['SAFERETURN_MIGRATION_DATABASE_URL'].replace('postgresql+psycopg:', 'postgresql:'))
    assert target.hostname == 'aws-0-ap-northeast-2.pooler.supabase.com' and target.port == 5432
    assert unquote(target.username).endswith('.fhuxryfkfrvycsojkzvq') and target.path == '/postgres'
    ca = ROOT / 'tmp/phase9-cloud-audit/supabase-verified-root.pem'
    assert hashlib.sha256(ca.read_bytes()).hexdigest() == '700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7'
    queries = {
        'revision': 'SELECT version_num FROM public.alembic_version',
        'checkout_release': 'SELECT enabled FROM public.single_checkout_release WHERE singleton',
        'owner_activation_release': 'SELECT enabled FROM public.standalone_owner_release WHERE singleton',
        'official_payment_instruction_count': 'SELECT count(*) FROM public.checkout_payment_instructions WHERE active',
        'products': "SELECT p.id,p.name,p.lifecycle_status,p.commerce_model,p.qr_type,p.is_featured,count(v.id) FILTER(WHERE v.is_active) AS active_variants,count(v.id) FILTER(WHERE v.is_active AND public.sr_template_catalog_type_eligible(v.id,p.qr_type) IS TRUE) AS eligible_variants FROM public.products p LEFT JOIN public.product_variants v ON v.product_id=p.id GROUP BY p.id ORDER BY p.id",
        'manual_render_policies': "SELECT policy_id,body->>'canonical_origin',revoked_at IS NULL FROM public.template_production_policies WHERE body->>'approval_mode'='manual_print'",
        'public_catalog_count': 'SELECT jsonb_array_length(public.sr_public_catalog(NULL))',
        'binding_counts': 'SELECT count(*),count(*) FILTER(WHERE is_active) FROM public.print_template_variant_bindings',
        'release_tables': "SELECT tablename FROM pg_tables WHERE schemaname='public' AND (tablename LIKE '%release%' OR tablename LIKE '%allocation%') ORDER BY tablename",
    }
    result = {'project': 'fhuxryfkfrvycsojkzvq', 'read_only': True}
    with psycopg.connect(host=target.hostname, hostaddr='13.124.111.232', port=5432, dbname='postgres', user=unquote(target.username), password=unquote(target.password), sslmode='verify-full', sslrootcert=str(ca), connect_timeout=10, autocommit=True) as connection:
        connection.execute('BEGIN READ ONLY')
        connection.execute("SET LOCAL statement_timeout='8000ms'")
        for name, query in queries.items():
            connection.execute('SAVEPOINT readiness')
            try:
                cursor = connection.execute(query)
                result[name] = {'columns': [c.name for c in cursor.description], 'rows': cursor.fetchall()}
            except psycopg.Error as error:
                connection.execute('ROLLBACK TO SAVEPOINT readiness')
                result[name] = {'sqlstate': error.sqlstate}
            connection.execute('RELEASE SAVEPOINT readiness')
        connection.execute('ROLLBACK')
    output = ROOT / 'tmp/customer-flow-readiness.json'
    output.write_text(json.dumps(result, default=str, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, default=str, indent=2))


if __name__ == '__main__':
    main()
