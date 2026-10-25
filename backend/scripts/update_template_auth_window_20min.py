"""Owner-authorized, source-checked template-only development auth policy update."""
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

import psycopg
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[2]
PROJECT='fhuxryfkfrvycsojkzvq'
def main():
    env = dotenv_values(ROOT / "backend/.env", interpolate=False)
    assert env["SAFERETURN_SUPABASE_URL"].rstrip("/") == f"https://{PROJECT}.supabase.co"
    target = urlsplit(env["SAFERETURN_MIGRATION_DATABASE_URL"].replace("postgresql+psycopg:", "postgresql:"))
    assert target.hostname == "aws-0-ap-northeast-2.pooler.supabase.com" and target.port == 5432 and target.path == "/postgres"
    assert unquote(target.username).endswith("." + PROJECT)
    ca = ROOT / "tmp/phase9-cloud-audit/supabase-verified-root.pem"
    assert hashlib.sha256(ca.read_bytes()).hexdigest() == "700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7"
    with psycopg.connect(host=target.hostname, port=target.port, dbname="postgres", user=unquote(target.username), password=unquote(target.password), sslmode="verify-full", sslrootcert=str(ca), connect_timeout=10, autocommit=True) as connection:
        assert connection.execute("SELECT version_num FROM public.alembic_version").fetchall() == [("0043_standalone_activation",)]
        definitions = connection.execute("SELECT proname,prosrc,prosecdef,proconfig,pg_get_userbyid(proowner),proacl::text FROM pg_proc WHERE oid IN ('public.sr_template_draft_service_v33(uuid,bigint,text,jsonb)'::regprocedure,'public.sr_template_preview_admit(uuid,bigint,text,text)'::regprocedure,'public.sr_template_lifecycle(uuid,bigint,text,jsonb)'::regprocedure) ORDER BY proname").fetchall()
        prior=(ROOT/'ops/template-draft-auth-window.sql').read_text()
        lifecycle=(ROOT/'backend/alembic/versions/0034_print_template_publication.sql').read_text()
        for name,body,definer,config,_owner,_acl in definitions:
            source=lifecycle if name=='sr_template_lifecycle' else prior
            marker=('CREATE FUNCTION public.' if name=='sr_template_lifecycle' else 'CREATE OR REPLACE FUNCTION public.')+name+'('
            expected=source[source.index(marker):].split('AS $$',1)[1].split('$$;',1)[0]
            assert body.strip()==expected.strip(), 'Installed source changed; review required'
            assert definer and config==['search_path=pg_catalog']
        raw=(ROOT/'ops/template-auth-window-20min.sql').read_text().encode()
        assert hashlib.sha256(raw).hexdigest()=='6a926295f55089dcd318b3230fac8a0ed76c1648f6e74c460a7cdbeead47566d'
        connection.execute(raw.decode(),prepare=False)
        after=connection.execute("SELECT proname,prosrc,prosecdef,proconfig,pg_get_userbyid(proowner),proacl::text FROM pg_proc WHERE oid IN ('public.sr_template_draft_service_v33(uuid,bigint,text,jsonb)'::regprocedure,'public.sr_template_preview_admit(uuid,bigint,text,text)'::regprocedure,'public.sr_template_lifecycle(uuid,bigint,text,jsonb)'::regprocedure) ORDER BY proname").fetchall()
        assert [r[2:] for r in after]==[r[2:] for r in definitions]
        assert all('clock_timestamp())-amr>1200' in r[1] for r in after)
    result={'project':PROJECT,'updated_helpers':[r[0] for r in after],'owner_acl_search_path_preserved':True,'migration_0044_applied':False}
    (ROOT/'tmp/template-activation/auth-window-20min-update.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
if __name__=='__main__':
    try:main()
    except psycopg.Error as error:
        print(json.dumps({'error_type':type(error).__name__,'sqlstate':error.sqlstate}))
        raise SystemExit(1)

