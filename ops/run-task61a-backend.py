"""Bounded synthetic backend preparation; never provisions or contacts a database."""

import ast
import hashlib
import json
import math
import os
import subprocess
import sys
import threading
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = (
    "backend/tests/test_auth.py",
    "backend/tests/test_staff_security.py",
    "backend/tests/test_critical_workflow_boundaries.py",
    "backend/tests/test_finder_validation.py",
    "backend/tests/test_abuse_intake.py",
    "backend/tests/test_public_configuration.py",
    "backend/tests/test_task61a_runner.py",
)
NOT_RUN = (
    "PostgreSQL",
    "migration_execution",
    "full_backend_suite",
    "frontend",
    "provider",
    "Linux_deployed_acceptance",
)
TIMEOUT = 600
LOG_LIMIT = 1024 * 1024


def child_environment(parent, root, scratch):
    allowed = {
        "PATH",
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "PATHEXT",
        "TEMP",
        "TMP",
        "TMPDIR",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
    }
    env = {k: parent[k] for k in parent if k.upper() in allowed}
    env.update(
        PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONPATH=os.pathsep.join(str(root / p) for p in ("backend", "backend/tests")),
        PYTHONIOENCODING="utf-8",
        TEMP=str(scratch),
        TMP=str(scratch),
        TMPDIR=str(scratch),
    )
    return env


def migration_chain(directory):
    revisions = {}
    for path in sorted(directory.glob("*.py")):
        values = {}
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in (
                        "revision",
                        "down_revision",
                    ):
                        if target.id in values:
                            raise ValueError("Duplicate declaration")
                        values[target.id] = ast.literal_eval(node.value)
        revision = values.get("revision")
        if (
            not isinstance(revision, str)
            or not revision
            or revision in revisions
            or "down_revision" not in values
            or (
                values["down_revision"] is not None
                and not isinstance(values["down_revision"], str)
            )
        ):
            raise ValueError("Invalid revision")
        revisions[revision] = values["down_revision"]
        if (
            revision[:4].isdigit()
            and int(revision[:4]) >= 22
            and not path.with_suffix(".sql").is_file()
        ):
            raise ValueError("Missing companion SQL")
    if not revisions or any(
        parent is not None and parent not in revisions for parent in revisions.values()
    ):
        raise ValueError("Missing parent")
    heads = set(revisions) - set(revisions.values())
    if len(heads) != 1:
        raise ValueError("Expected one head")
    chain = []
    node = heads.pop()
    while node is not None:
        if node in chain:
            raise ValueError("Cycle")
        chain.append(node)
        node = revisions[node]
    if len(chain) != len(revisions):
        raise ValueError("Disconnected graph")
    return list(reversed(chain))


def current_chain(root):
    chain = migration_chain(root / "backend/alembic/versions")
    if len(chain) != 36 or chain[-1] != "0035_public_abuse_intake":
        raise ValueError("Unreviewed chain")
    tail = chain[chain.index("0021_support_case_console") :]
    if [int(item[:4]) for item in tail] != list(range(21, 36)):
        raise ValueError("Unreviewed pending chain")
    return chain


def source_manifest(root):
    roots = (
        "backend/app",
        "backend/tests",
        "backend/alembic",
        "docs",
        "ops",
        ".github/workflows",
        "frontend/app",
        "frontend/components",
        "frontend/lib",
        "frontend/scripts",
        "frontend/tests",
    )
    extensions = {
        ".py",
        ".sql",
        ".md",
        ".yml",
        ".yaml",
        ".toml",
        ".ini",
        ".tsx",
        ".ts",
        ".css",
        ".cjs",
        ".json",
        ".ps1",
    }
    files = set()
    for directory in roots:
        for path in (root / directory).rglob("*"):
            if (
                path.is_file()
                and not path.is_symlink()
                and "__pycache__" not in path.parts
                and path.suffix in extensions
            ):
                files.add(path)
    for directory in (root, root / "backend", root / "frontend"):
        files.update(
            p
            for p in directory.iterdir()
            if p.is_file()
            and not p.is_symlink()
            and p.suffix in extensions
            and not p.name.startswith(".env")
        )
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(files)
    }


def git_state(root):
    # Read-only Git metadata; no environment dump, credentials or source bodies.
    def read(*args):
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        return result.stdout.strip()

    return {
        "revision": read("rev-parse", "HEAD"),
        "branch": read("branch", "--show-current"),
        "porcelain": read("status", "--porcelain=v1", "--untracked-files=normal"),
    }


def counts_from_junit(path):
    if path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("Oversized report")
    root = ET.parse(path).getroot()
    suites = (
        [root]
        if root.tag == "testsuite"
        else list(root)
        if root.tag == "testsuites"
        else []
    )
    if not suites or any(s.tag != "testsuite" for s in suites):
        raise ValueError("Invalid report")
    result = {"collected": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0}
    for suite in suites:
        cases = suite.findall("testcase")
        totals = {
            key: int(suite.attrib[key])
            for key in ("tests", "failures", "errors", "skipped")
        }
        actual = {"failures": 0, "errors": 0, "skipped": 0}
        for case in cases:
            states = [
                key
                for tag, key in (
                    ("failure", "failures"),
                    ("error", "errors"),
                    ("skipped", "skipped"),
                )
                if case.find(tag) is not None
            ]
            if len(states) > 1:
                raise ValueError("Ambiguous case")
            if states:
                actual[states[0]] += 1
        if totals != {"tests": len(cases), **actual} or any(
            v < 0 for v in totals.values()
        ):
            raise ValueError("Inconsistent counts")
        result["collected"] += len(cases)
        result["failed"] += actual["failures"]
        result["errors"] += actual["errors"]
        result["skipped"] += actual["skipped"]
        result["passed"] += len(cases) - sum(actual.values())
    if not result["collected"]:
        raise ValueError("Empty report")
    return result


def wait_process(process, timeout):
    try:
        return "completed", process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)
        return "timed_out", None
    except KeyboardInterrupt:
        process.kill()
        process.wait(timeout=10)
        return "interrupted", None


def copy_log(stream, path):
    remaining = LOG_LIMIT
    with path.open("wb") as target:
        while chunk := stream.read1(8192):
            if remaining:
                target.write(chunk[:remaining])
                remaining = max(0, remaining - len(chunk))
    stream.close()


def evaluate(exit_code, counts, collection):
    return (
        exit_code == 0
        and counts["collected"] > 0
        and counts["failed"] == counts["errors"] == counts["skipped"] == 0
        and set(collection["files"]) == set(TESTS)
        and collection["collected"] == counts["collected"]
        and collection["completed"] == counts["collected"]
        and collection["exit_code"] == 0
        and collection["unexpected_outcomes"] == 0
        and collection["guards_installed"] is True
    )


def write_json(path, value):
    path.write_text(
        json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def main():
    run_id = uuid.uuid4().hex
    output = ROOT / "output/task61a" / run_id
    scratch = ROOT / "tmp/task61a-backend" / run_id
    output.mkdir(parents=True, exist_ok=False)
    scratch.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    summary = {
        "schema_version": 1,
        "scope": "backend_offline_preparation",
        "outcome": "failed",
        "exit_code": None,
        "collected": 0,
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "duration_seconds": 0.0,
        "preservation": "not_completed",
        "not_run": list(NOT_RUN),
        "revision": None,
        "dirty": None,
        "migration_head": None,
    }
    before = state = None
    try:
        before, state = source_manifest(ROOT), git_state(ROOT)
        summary.update(revision=state["revision"], dirty=bool(state["porcelain"]))
        summary["migration_head"] = current_chain(ROOT)[-1]
        write_json(output / "source-before.json", before)
        bootstrap = (
            "import task61a_offline; task61a_offline.install_guards(); "
            "import pytest,sys; sys.exit(pytest.main(sys.argv[1:]))"
        )
        args = [
            sys.executable,
            "-c",
            bootstrap,
            *TESTS,
            "-p",
            "task61a_offline",
            "-p",
            "no:cacheprovider",
            "-q",
            "--basetemp=" + str(scratch / "pytest"),
            "--junitxml=" + str(output / "junit.xml"),
            "--task61a-report=" + str(output / "collection.json"),
        ]
        process = subprocess.Popen(
            args,
            cwd=ROOT,
            env=child_environment(os.environ, ROOT, scratch),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        reader = threading.Thread(
            target=copy_log, args=(process.stdout, output / "pytest.log"), daemon=True
        )
        reader.start()
        outcome, code = wait_process(process, TIMEOUT)
        reader.join(timeout=10)
        summary["exit_code"] = code
        if outcome != "completed":
            summary["outcome"] = outcome
        else:
            summary["outcome"] = "invalid_report"
        try:
            counts = counts_from_junit(output / "junit.xml")
            summary.update(counts)
            collection = json.loads(
                (output / "collection.json").read_text(encoding="utf-8")
            )
            if outcome == "completed":
                summary["outcome"] = (
                    "passed" if evaluate(code, counts, collection) else "failed"
                )
        except (OSError, ValueError, KeyError, TypeError, ET.ParseError):
            pass
    except KeyboardInterrupt:
        summary["outcome"] = "interrupted"
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        # Never serialize raw exceptions: they may carry paths/config/provider data.
        summary["outcome"] = "failed"
    finally:
        try:
            if before is not None and state is not None:
                after, final_state = source_manifest(ROOT), git_state(ROOT)
                preserved = before == after and state == final_state
                summary["preservation"] = "passed" if preserved else "failed"
                write_json(output / "source-after.json", after)
                write_json(
                    output / "preservation.json",
                    {
                        "status": summary["preservation"],
                        "before": state,
                        "after": final_state,
                        "changed_paths": sorted(
                            k
                            for k in set(before) | set(after)
                            if before.get(k) != after.get(k)
                        ),
                    },
                )
        except (OSError, subprocess.SubprocessError):
            summary["preservation"] = "not_completed"
        if summary["preservation"] != "passed" and summary["outcome"] == "passed":
            summary["outcome"] = "failed"
        summary["duration_seconds"] = round(time.monotonic() - started, 3)
        assert math.isfinite(summary["duration_seconds"])
        write_json(output / "summary.json", summary)
        write_json(
            ROOT / "output/task61a/latest.json", {"run_id": run_id, "summary": summary}
        )
    print(json.dumps(summary))
    return 0 if summary["outcome"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
