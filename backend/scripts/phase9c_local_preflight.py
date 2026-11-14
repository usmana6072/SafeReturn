"""Read-only local provisioning plan. Never initializes, starts or connects to DBs."""

import json
import os
import subprocess
from pathlib import Path


def inspect(root: Path):
    manifest_path = root / "ops/phase9c/local-environment.example.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {
        "purpose": "phase9c-local-support-metadata-acceptance",
        "database_name": "safereturn_phase9c_acceptance",
        "host": "127.0.0.1",
        "port": 55439,
        "postgres_major": 17,
        "postgres_bin": ".local-tools/pg17-core/pgsql/bin",
        "state_directory": "tmp/phase9c-local",
        "data_directory": "tmp/phase9c-local/pgdata",
        "load_existing_environment": False,
        "restore_existing_backup": False,
        "start_workers": False,
        "automatic_migrations": False,
        "automatic_identities": False,
        "automatic_fixtures": False,
    }
    if manifest != expected:
        raise ValueError("Manifest differs from the reviewed preparation template")
    root = root.resolve(strict=True)
    paths = {
        key: (root / manifest[key]).resolve()
        for key in ("postgres_bin", "state_directory", "data_directory")
    }
    if any(not path.is_relative_to(root) for path in paths.values()):
        raise ValueError("Local path resolves outside workspace")
    for key in ("state_directory", "data_directory"):
        # A preparation tool must never silently adopt old/shared state or links.
        candidate = root / manifest[key]
        for part in (candidate, *candidate.parents):
            if part == root:
                break
            if part.is_symlink() or part.is_junction():
                raise ValueError("State path traverses a link or junction")
    versions = {}
    for tool in ("postgres", "initdb", "pg_ctl", "psql"):
        binary = paths["postgres_bin"] / (tool + ".exe" if os.name == "nt" else tool)
        if not binary.is_file() or not binary.resolve().is_relative_to(root):
            versions[tool] = "unavailable"
            continue
        result = subprocess.run(
            [str(binary), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        value = result.stdout.strip()
        # Output only the expected tool version, never arbitrary process output.
        import re

        match = re.fullmatch(r"[a-z_]+ \(PostgreSQL\) (\d+\.\d+(?:\.\d+)?)", value)
        versions[tool] = (
            match[1]
            if match and int(match[1].split(".")[0]) == manifest["postgres_major"]
            else "version_mismatch"
        )
    inherited = any(
        os.environ.get(name)
        for name in (
            "PGHOST",
            "PGHOSTADDR",
            "PGPORT",
            "PGDATABASE",
            "PGUSER",
            "PGPASSWORD",
            "PGSERVICE",
            "PGSERVICEFILE",
            "PGPASSFILE",
            "PGOPTIONS",
            "SAFERETURN_DATABASE_URL",
            "SAFERETURN_MIGRATION_DATABASE_URL",
            "SAFERETURN_TEST_DATABASE_URL",
        )
    )
    return {
        "mode": "read_only_preparation",
        "manifest": "ops/phase9c/local-environment.example.json",
        "target": {
            "host": manifest["host"],
            "port": manifest["port"],
            "database_name": manifest["database_name"],
        },
        "portable_tool_versions": versions,
        "state_directory_exists": paths["state_directory"].exists(),
        "data_directory_exists": paths["data_directory"].exists(),
        "inherited_database_settings_present": inherited,
        "port_availability": "not_verified",
        "database_isolation": "designed_not_provisioned",
        "approval_required_before_initialization_or_start": True,
        "migration_review": "blocked_pending_complete_execution_path_review",
        "real_auth_mfa": "not_provisioned",
        "fixtures": "blocked_pending_safe_approved_creation_path",
    }


if __name__ == "__main__":
    try:
        report = inspect(Path(__file__).resolve().parents[2])
    except (ValueError, OSError, subprocess.SubprocessError):
        print(
            json.dumps(
                {
                    "mode": "read_only_preparation",
                    "error": "LOCAL_PREFLIGHT_FAILED",
                    "provisioning_authorized": False,
                }
            )
        )
        raise SystemExit(1) from None
    print(json.dumps(report, indent=2))
