"""Fixed offline test selection; no worker entrypoint is invoked."""

import importlib.util
import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
TEST = "backend/tests/test_worker_operations.py"


def base_module():
    spec = importlib.util.spec_from_file_location(
        "task63a_base", ROOT / "ops/run-task61a-backend.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def child(destination):
    from task61a_offline import install_guards

    install_guards()
    import pytest

    class Evidence:
        completed = 0
        unexpected = 0

        def pytest_collection_finish(self, session):
            self.collected = len(session.items)
            self.files = sorted(
                {
                    Path(item.path).resolve().relative_to(ROOT).as_posix()
                    for item in session.items
                }
            )
            if self.files != [TEST]:
                raise RuntimeError("Unapproved selection")

        def pytest_runtest_logreport(self, report):
            if report.when == "teardown":
                self.completed += 1
            if report.skipped or hasattr(report, "wasxfail"):
                self.unexpected += 1

    evidence = Evidence()
    code = pytest.main(
        [
            "-q",
            "-p",
            "no:cacheprovider",
            "--confcutdir=backend/tests",
            TEST,
            f"--junitxml={destination / 'tests.xml'}",
        ],
        plugins=[evidence],
    )
    (destination / "collection.json").write_text(
        json.dumps(
            {
                "files": evidence.files,
                "collected": evidence.collected,
                "completed": evidence.completed,
                "unexpected": evidence.unexpected,
                "exit_code": int(code),
                "guards_installed": True,
            }
        ),
        encoding="utf-8",
    )
    return int(code)


def accepted(outcome, exit_code, counts, collection, preserved):
    return (
        outcome == "completed"
        and exit_code == 0
        and counts is not None
        and counts["passed"] == counts["collected"] > 0
        and counts["failed"] == counts["errors"] == counts["skipped"] == 0
        and collection
        == {
            "files": [TEST],
            "collected": counts["collected"],
            "completed": counts["collected"],
            "unexpected": 0,
            "exit_code": 0,
            "guards_installed": True,
        }
        and preserved
    )


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--checks":
        return child(Path(sys.argv[2]))
    if len(sys.argv) != 1:
        raise SystemExit("No runtime worker arguments supported")
    base = base_module()
    identity = uuid4().hex
    destination = ROOT / "output/task63a" / identity
    scratch = ROOT / "tmp/task63a-backend" / identity
    destination.mkdir(parents=True)
    scratch.mkdir(parents=True)
    before, git_before = base.source_manifest(ROOT), base.git_state(ROOT)
    base.write_json(destination / "before.json", before)
    outcome, exit_code, counts, collection = "failed", None, None, None
    try:
        with subprocess.Popen(
            [
                sys.executable,
                "-B",
                str(Path(__file__).resolve()),
                "--checks",
                str(destination),
            ],
            cwd=ROOT,
            env=base.child_environment(os.environ, ROOT, scratch),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        ) as process:
            drainer = threading.Thread(
                target=base.copy_log, args=(process.stdout, destination / "tests.log")
            )
            drainer.start()
            outcome, exit_code = base.wait_process(process, 180)
            drainer.join(timeout=10)
            if drainer.is_alive():
                outcome = "log_incomplete"
        counts = base.counts_from_junit(destination / "tests.xml")
        collection = json.loads((destination / "collection.json").read_text())
    except (OSError, ValueError, KeyError):
        outcome = "invalid_evidence"
    finally:
        after, git_after = base.source_manifest(ROOT), base.git_state(ROOT)
        preserved = before == after and git_before == git_after
        passed = accepted(outcome, exit_code, counts, collection, preserved)
        report = {
            "run": identity,
            "passed": passed,
            "execution": outcome,
            "counts": counts,
            "preserved": preserved,
            "sources": len(before),
            "operational_acceptance": "blocked_pending_authorized_runtime_evidence",
            "not_run": ["workers", "database", "providers", "frontend", "deployment"],
        }
        base.write_json(destination / "summary.json", report)
        base.write_json(ROOT / "output/task63a/latest.json", report)
        print(json.dumps(report))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
