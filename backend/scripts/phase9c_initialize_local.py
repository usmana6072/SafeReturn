"""Explicitly approved blank local cluster only; no application schema or fixtures."""

import csv
import io
import json
import os
import re
import secrets
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "tmp/phase9c-local"
DATA = STATE / "pgdata"
BIN = ROOT / ".local-tools/pg17-core/pgsql/bin"
HOST, PORT = "127.0.0.1", 55439
DATABASE, ROLE = "safereturn_phase9c_acceptance", "sr_phase9c_bootstrap"
FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def run(args, env, stage, timeout=30):
    result = subprocess.run(
        args,
        cwd=ROOT,
        env=env,
        creationflags=FLAGS,
        capture_output=True,
        check=False,
        text=True,
        timeout=timeout,
    )
    if result.returncode:
        # Raw diagnostics stay inside the private run directory, never console.
        if STATE.is_dir():
            (STATE / f"{stage}.diagnostic.log").write_text(
                result.stdout + result.stderr, encoding="utf-8"
            )
        raise RuntimeError(stage)
    return result.stdout.strip()


def port_free():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        probe.bind((HOST, PORT))


def psql(env, database, sql, stage):
    return run(
        [
            str(BIN / "psql.exe"),
            "--no-psqlrc",
            "--no-password",
            "--host=" + HOST,
            "--port=" + str(PORT),
            "--username=" + ROLE,
            "--dbname=" + database,
            "--set=ON_ERROR_STOP=1",
            "--no-align",
            "--tuples-only",
            "--command=" + sql,
        ],
        env,
        stage,
    )


def wait_for_local_start(process):
    import time

    for _ in range(60):
        if process.poll() is not None:
            raise RuntimeError("LOCAL_POSTGRES_EXITED")
        if (DATA / "postmaster.pid").exists():
            lines = (DATA / "postmaster.pid").read_text().splitlines()
            if len(lines) >= 8 and lines[7].strip() == "ready":
                return
        time.sleep(0.25)
    raise RuntimeError("LOCAL_POSTGRES_START_TIMEOUT")


def start_local_postgres(env):
    # pg_ctl's extra CreateRestrictedToken step can fail under an already restricted
    # Windows sandbox token. Direct startup retains that same OS identity/token.
    with (STATE / "postgresql.log").open("ab") as log:
        process = subprocess.Popen(
            [str(BIN / "postgres.exe"), "-D", str(DATA), "-h", HOST, "-p", str(PORT)],
            cwd=ROOT,
            env=env,
            creationflags=FLAGS,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    return process


def create_and_verify_empty_database(env):
    control = run(
        [str(BIN / "pg_controldata.exe"), "-D", str(DATA)], env, "local_control"
    )
    match = re.search(r"Database system identifier:\s+(\d+)", control)
    if not match:
        raise RuntimeError("LOCAL_CLUSTER_ID_UNAVAILABLE")
    system_id = match[1]
    identity_sql = """SELECT json_build_object(
      'data_directory',current_setting('data_directory'),
      'listen_addresses',current_setting('listen_addresses'),
      'port',current_setting('port'), 'server_address',host(inet_server_addr()),
      'server_port',inet_server_port(), 'database',current_database(),
      'role',current_user,'system_identifier',(SELECT system_identifier::text FROM pg_control_system()),
      'version_num',current_setting('server_version_num'))"""
    identity = json.loads(psql(env, "postgres", identity_sql, "verify_identity"))
    if (
        Path(identity["data_directory"]).resolve() != DATA.resolve()
        or identity["system_identifier"] != system_id
        or identity["listen_addresses"] != HOST
        or identity["server_address"] != HOST
        or identity["server_port"] != PORT
        or identity["port"] != str(PORT)
        or identity["database"] != "postgres"
        or identity["role"] != ROLE
        or identity["version_num"] != "170011"
    ):
        raise RuntimeError("LOCAL_SERVER_IDENTITY_MISMATCH_NO_DATABASE_CREATED")
    # Only the fresh cluster's built-in databases may exist before CREATE DATABASE.
    before = json.loads(
        psql(
            env,
            "postgres",
            "SELECT json_agg(datname ORDER BY datname) FROM pg_database",
            "verify_initial_databases",
        )
    )
    if before != ["postgres", "template0", "template1"]:
        raise RuntimeError("UNEXPECTED_DATABASES_NO_DATABASE_CREATED")
    psql(
        env,
        "postgres",
        "CREATE DATABASE safereturn_phase9c_acceptance",
        "create_empty_database",
    )
    verified = json.loads(
        psql(
            env,
            DATABASE,
            """SELECT json_build_object(
      'database',current_database(),
      'user_relations',(SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%'
        AND n.nspname NOT LIKE 'pg_temp%'),
      'user_functions',(SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
        WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_%'),
      'user_schemas',(SELECT json_agg(nspname ORDER BY nspname) FROM pg_namespace
        WHERE nspname NOT IN ('pg_catalog','information_schema') AND nspname NOT LIKE 'pg_%'),
      'bootstrap_scram',(SELECT rolpassword LIKE 'SCRAM-SHA-256$%' FROM pg_authid WHERE rolname=current_user),
      'hba_errors',(SELECT count(*) FROM pg_hba_file_rules WHERE error IS NOT NULL))""",
            "verify_empty",
        )
    )
    if (
        verified["database"] != DATABASE
        or verified["user_relations"] != 0
        or verified["user_functions"] != 0
        or verified["user_schemas"] != ["public"]
        or verified["bootstrap_scram"] is not True
        or verified["hba_errors"] != 0
    ):
        raise RuntimeError("EMPTY_DATABASE_VERIFICATION_FAILED")
    pid = int((DATA / "postmaster.pid").read_text().splitlines()[0])
    netstat = run(["netstat.exe", "-ano"], env, "verify_listener")
    listeners = []
    for line in netstat.splitlines():
        columns = line.split()
        if (
            len(columns) == 5
            and columns[0] == "TCP"
            and columns[3] == "LISTENING"
            and (columns[1].endswith(":" + str(PORT)) or columns[4] == str(pid))
        ):
            listeners.append({"address": columns[1], "pid": int(columns[4])})
    if listeners != [{"address": f"{HOST}:{PORT}", "pid": pid}]:
        raise RuntimeError("EXCLUSIVE_LISTENER_VERIFICATION_FAILED")
    databases = json.loads(
        psql(
            env,
            DATABASE,
            "SELECT json_agg(datname ORDER BY datname) FROM pg_database",
            "verify_final_databases",
        )
    )
    if databases != ["postgres", DATABASE, "template0", "template1"]:
        raise RuntimeError("UNEXPECTED_FINAL_DATABASE_LIST")
    report = {
        "status": "blank_local_database_running",
        "postgres_version": "17.11",
        "data_directory": str(DATA),
        "host": HOST,
        "port": PORT,
        "postmaster_pid": pid,
        "system_identifier": system_id,
        "database": DATABASE,
        "databases": databases,
        "listener": listeners,
        "verification": verified,
        "created_application_schemas": False,
        "applied_migrations": False,
        "created_auth_identities_or_fixtures": False,
        "acceptance_passed": False,
    }
    (STATE / "initialization-result.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


def main():
    if os.name != "nt" or sys.argv[1:] != ["--initialize-approved-phase9c"]:
        raise RuntimeError("EXPLICIT_APPROVED_WINDOWS_INITIALIZATION_REQUIRED")
    if str(ROOT.resolve()).lower() != r"e:\projects\safereturn":
        raise RuntimeError("WORKSPACE_MISMATCH")
    for candidate in (STATE, DATA, BIN):
        if not candidate.resolve().is_relative_to(ROOT.resolve()):
            raise RuntimeError("PATH_OUTSIDE_WORKSPACE")
        for node in (candidate, *candidate.parents):
            if node == ROOT:
                break
            if node.is_symlink() or node.is_junction():
                raise RuntimeError("LINKED_PATH_REJECTED")
    # Do not adopt old run state, even when the proposed data child is empty.
    if STATE.exists() or DATA.exists():
        raise RuntimeError("FRESH_STATE_DIRECTORY_REQUIRED")
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.upper().startswith(("PG", "SAFERETURN_"))
    }
    env.update(
        PGCONNECT_TIMEOUT="3",
        PGAPPNAME="phase9c_blank_cluster_verification",
        PGSSLMODE="prefer",
        LC_ALL="C",
    )
    for tool in ("postgres", "initdb", "pg_ctl", "psql", "pg_controldata"):
        version = run([str(BIN / (tool + ".exe")), "--version"], env, "version")
        if not re.fullmatch(r"[a-z_]+ \(PostgreSQL\) 17\.11", version):
            raise RuntimeError("POSTGRES_VERSION_MISMATCH")
    port_free()
    sid_output = run(["whoami.exe", "/user", "/fo", "csv", "/nh"], env, "identity")
    sid = next(iter(csv.reader(io.StringIO(sid_output))))[1]
    if not re.fullmatch(r"S-1-(?:\d+-)+\d+", sid):
        raise RuntimeError("LOCAL_IDENTITY_UNAVAILABLE")
    STATE.mkdir(parents=True, exist_ok=False)
    run(
        [
            "icacls.exe",
            str(STATE),
            "/inheritance:r",
            "/grant:r",
            "*" + sid + ":(OI)(CI)F",
            "*S-1-5-18:(OI)(CI)F",
        ],
        env,
        "private_acl",
    )
    private = STATE / "private"
    private.mkdir()
    secret = secrets.token_urlsafe(48)
    password_file = private / "initdb-password"
    passfile = private / "pgpass.conf"
    password_file.write_text(secret + "\n", encoding="utf-8")
    passfile.write_text(
        "".join(
            f"{HOST}:{PORT}:{db}:{ROLE}:{secret}\n" for db in ("postgres", DATABASE)
        ),
        encoding="utf-8",
    )
    del secret
    env["PGPASSFILE"] = str(passfile)
    run(
        [
            str(BIN / "initdb.exe"),
            "--pgdata=" + str(DATA),
            "--username=" + ROLE,
            "--auth=scram-sha-256",
            "--encoding=UTF8",
            "--locale=C",
            "--pwfile=" + str(password_file),
        ],
        env,
        "initdb",
        timeout=60,
    )
    # Only a single known, private temporary password file is removed.
    password_file.unlink()
    with (DATA / "postgresql.conf").open("a", encoding="utf-8") as config:
        config.write(
            "\n# Explicit user-approved Phase9C local cluster.\n"
            "listen_addresses = '127.0.0.1'\nport = 55439\n"
            "password_encryption = 'scram-sha-256'\n"
            "logging_collector = off\nlog_connections = off\nlog_disconnections = off\n"
        )
    (DATA / "pg_hba.conf").write_text(
        "# Phase9C: only this cluster bootstrap role on IPv4 loopback.\n"
        f"host all {ROLE} 127.0.0.1/32 scram-sha-256\n"
        "host all all 0.0.0.0/0 reject\nhost all all ::0/0 reject\n",
        encoding="utf-8",
    )
    # A competing bind causes pg_ctl failure; never redirect or stop another server.
    port_free()
    process = start_local_postgres(env)
    wait_for_local_start(process)
    create_and_verify_empty_database(env)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        # No raw subprocess/connection/secret diagnostics on stdout/stderr.
        print(
            json.dumps(
                {
                    "status": "STOPPED",
                    "stage": str(exc)
                    if isinstance(exc, RuntimeError)
                    else type(exc).__name__,
                    "acceptance_passed": False,
                }
            )
        )
        raise SystemExit(1) from None
