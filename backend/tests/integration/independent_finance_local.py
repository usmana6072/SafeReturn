"""Disposable loopback PostgreSQL. Never reads .env or contacts Supabase.

Synthetic Auth tables test SQL invariants, NOT genuine provider authentication.
Runs only after explicit rehearsal authorization; cluster is stopped, not deleted.
"""
import os
import secrets
import socket
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import psycopg
from alembic import command
from alembic.config import Config
from sqlalchemy import URL, create_engine, text

ROOT = Path(__file__).resolve().parents[3]
BIN = ROOT / ".local-tools/pg17-core/pgsql/bin"


@contextmanager
def local_cluster(revision='0052_typed_finance_audit'):
    if os.environ.get("SAFERETURN_INDEPENDENT_FINANCE_REHEARSAL") != "1":
        raise RuntimeError("Explicit isolated rehearsal approval required")
    state = ROOT / "tmp" / ("finance-pg-" + uuid4().hex)
    state.mkdir()
    assert state.resolve().is_relative_to((ROOT / 'tmp').resolve())
    data = state / "data"
    user, password = "sr_finance_rehearsal", secrets.token_urlsafe(40)
    env = {k:v for k,v in os.environ.items() if not k.startswith(('PG', 'SAFERETURN_'))}
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    secret_file = state / "init-password"
    secret_file.write_text(password, encoding='utf-8')
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    try:
        result = subprocess.run([str(BIN/'initdb.exe'), '-D', str(data), '-U', user,
            '--auth=scram-sha-256', '--encoding=UTF8', '--locale=C', '--pwfile='+str(secret_file)],
            env=env,capture_output=True,timeout=60,creationflags=flags)
        (state/'init.log').write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(f'initdb failed; local log {state}/init.log')
    finally:
        secret_file.unlink(missing_ok=True)
    (data/'pg_hba.conf').write_text(f'host all {user} 127.0.0.1/32 scram-sha-256\nhost all all 0.0.0.0/0 reject\nhost all all ::0/0 reject\n')
    log = (state/'postgres.log').open('wb')
    process = subprocess.Popen([str(BIN/'postgres.exe'),'-D',str(data),'-h','127.0.0.1','-p',str(port),
        '-c','log_line_prefix=%a ', '-c','log_statement=none'],env=env,stdout=log,stderr=log,creationflags=flags)
    def connect(db='postgres'):
        return psycopg.connect(host='127.0.0.1',port=port,dbname=db,user=user,password=password,connect_timeout=3)
    try:
        for _ in range(40):
            if process.poll() is not None:raise RuntimeError(f'Local postgres exited; inspect {state}/postgres.log')
            try:
                with connect() as c:
                    directory=c.execute('SHOW data_directory').fetchone()[0]
                    assert Path(directory).resolve()==data.resolve()
                    assert c.execute('SELECT host(inet_server_addr())').fetchone()[0]=='127.0.0.1'
                break
            except psycopg.OperationalError:time.sleep(.25)
        else:raise RuntimeError('Local PostgreSQL did not become ready')
        with connect() as c:
            c.autocommit=True
            c.execute('CREATE DATABASE finance_template')
        url=URL.create('postgresql+psycopg',username=user,password=password,host='127.0.0.1',port=port,database='finance_template')
        engine=create_engine(url,hide_parameters=True)
        with engine.begin() as c:
            c.execute(text('CREATE ROLE anon NOLOGIN; CREATE ROLE authenticated NOLOGIN'))
            c.execute(text('CREATE SCHEMA auth'))
            c.execute(text('CREATE TABLE auth.users(id uuid PRIMARY KEY,created_at timestamptz NOT NULL DEFAULT now(),email text,email_confirmed_at timestamptz,deleted_at timestamptz,banned_until timestamptz,is_anonymous boolean DEFAULT false)'))
            c.execute(text('CREATE TABLE auth.sessions(id uuid PRIMARY KEY,created_at timestamptz NOT NULL DEFAULT now(),user_id uuid REFERENCES auth.users(id),aal text,not_after timestamptz)'))
            cfg=Config(str(ROOT/'backend/alembic.ini'))
            cfg.set_main_option('script_location',str(ROOT/'backend/alembic'))
            cfg.attributes['connection']=c
            command.upgrade(cfg, revision)
            assert c.execute(text('SELECT version_num FROM public.alembic_version')).scalar_one() == revision
        engine.dispose()
        print(f'LOCAL_REHEARSAL {state.name} port={port} migrations={revision} synthetic_auth=true',flush=True)
        yield url,connect,state
    finally:
        # Stop only this freshly created and path-verified cluster. Preserve logs.
        result=subprocess.run([str(BIN/'pg_ctl.exe'),'-D',str(data),'-m','fast','-w','stop'],
            env=env,capture_output=True,timeout=30,creationflags=flags)
        (state/'stop.log').write_bytes(result.stdout+result.stderr)
        if process.poll() is None:process.wait(timeout=10)
        log.close()
