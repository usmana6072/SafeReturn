"""One fixed offline measurement plan, followed by focused guarded harness tests."""

import importlib.util
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

import task62a_harness as harness

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "task61a_primitives", ROOT / "ops/run-task61a-backend.py"
)
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
TESTS = ("backend/tests/test_task62a_harness.py",)
CHILD_LIMIT = 180
OVERALL_LIMIT = 600
REPORT_LIMIT = 8 * 1024 * 1024


def read_json(path):
    if path.stat().st_size > REPORT_LIMIT:
        raise ValueError("report_size")
    return json.loads(path.read_text(encoding="utf-8"))


def run_child(arguments, scratch, logfile, deadline):
    remaining = min(CHILD_LIMIT, deadline - time.monotonic())
    if remaining <= 0:
        return "timed_out", None
    env = previous.child_environment(os.environ, ROOT, scratch)
    env["PYTHONPATH"] += os.pathsep + str(ROOT / "ops")
    process = subprocess.Popen(
        [sys.executable, "-c", *arguments],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    reader = threading.Thread(
        target=previous.copy_log, args=(process.stdout, logfile), daemon=True
    )
    reader.start()
    result = previous.wait_process(process, remaining)
    reader.join(timeout=10)
    return result


def test_report_ok(code, counts, collection):
    return (
        code == 0
        and counts["collected"] > 0
        and counts["failed"] == counts["errors"] == counts["skipped"] == 0
        and set(collection["files"]) == set(TESTS)
        and counts["collected"] == collection["collected"] == collection["completed"]
        and collection["unexpected_outcomes"] == 0
        and collection["guards_installed"] is True
        and collection["exit_code"] == 0
    )


def main():
    run_id = uuid.uuid4().hex
    output, scratch = (
        ROOT / "output/task62a" / run_id,
        ROOT / "tmp/task62a-backend" / run_id,
    )
    output.mkdir(parents=True, exist_ok=False)
    scratch.mkdir(parents=True, exist_ok=False)
    deadline = time.monotonic() + OVERALL_LIMIT
    summary = {
        "schema_version": 1,
        "scope": "backend_offline_performance_preparation",
        "execution": "failed",
        "performance_acceptance": harness.ACCEPTANCE,
        "targets": None,
        "environment": None,
        "plan": {
            "workload_ids": list(harness.CASES),
            "concurrency": list(harness.CONCURRENCY),
            "repetitions": harness.REPETITIONS,
            "warmup_per_cell": harness.WARMUP,
            "samples_per_cell": harness.SAMPLES,
        },
        "cells": [],
        "allocation_observations": [],
        "preservation": "not_completed",
        "not_run": harness.NOT_RUN,
        "limitations": harness.LIMITATIONS,
        "measurement_metadata": None,
        "tests": None,
    }
    before = state = None
    try:
        before, state = previous.source_manifest(ROOT), previous.git_state(ROOT)
        head = previous.current_chain(ROOT)[-1]
        summary["environment"] = harness.environment(
            state["revision"], bool(state["porcelain"]), head
        )
        harness.write_json(output / "source-before.json", before)
        bootstrap = "import task61a_offline; task61a_offline.install_guards(); "
        outcome, code = run_child(
            [
                bootstrap
                + "import task62a_harness,sys; sys.exit(task62a_harness.child(sys.argv[1]))",
                str(output),
            ],
            scratch,
            output / "measurement.log",
            deadline,
        )
        if outcome != "completed":
            summary["execution"] = outcome
        elif code != 0:
            summary["execution"] = "failed"
        else:
            summary["execution"] = "invalid_report"
            report, samples = (
                read_json(output / "measurement.json"),
                read_json(output / "samples.json"),
            )
            harness.validate_report(report, samples)
            summary["cells"] = report["cells"]
            summary["allocation_observations"] = report["allocation_observations"]
            summary["measurement_metadata"] = {
                key: report[key]
                for key in ("clock_resolution_seconds", "started_at_utc", "guard_mode")
            }
            outcome, code = run_child(
                [
                    bootstrap
                    + "import pytest,sys; sys.exit(pytest.main(sys.argv[1:]))",
                    *TESTS,
                    "-p",
                    "task62a_checks",
                    "-p",
                    "no:cacheprovider",
                    "-q",
                    "--basetemp=" + str(scratch / "pytest"),
                    "--junitxml=" + str(output / "tests.xml"),
                    "--task62a-report=" + str(output / "collection.json"),
                ],
                scratch,
                output / "tests.log",
                deadline,
            )
            if outcome != "completed":
                summary["execution"] = outcome
            else:
                summary["tests"] = previous.counts_from_junit(output / "tests.xml")
                collection = read_json(output / "collection.json")
                summary["execution"] = (
                    "completed"
                    if test_report_ok(code, summary["tests"], collection)
                    else "failed"
                )
    except KeyboardInterrupt:
        summary["execution"] = "interrupted"
    except Exception:  # noqa: BLE001 -- sanitized report boundary; no exception/config serialization
        # No raw exceptions, URLs, fixture contents or environment values in reports.
        if summary["execution"] not in {
            "failed",
            "invalid_report",
            "timed_out",
            "interrupted",
        }:
            summary["execution"] = "failed"
    finally:
        try:
            if before is not None and state is not None:
                after, final_state = (
                    previous.source_manifest(ROOT),
                    previous.git_state(ROOT),
                )
                summary["preservation"] = (
                    "passed" if before == after and state == final_state else "failed"
                )
                harness.write_json(output / "source-after.json", after)
                harness.write_json(
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
        except Exception:  # noqa: BLE001 -- preservation failure must never turn into a pass
            summary["preservation"] = "not_completed"
        if summary["preservation"] != "passed" and summary["execution"] == "completed":
            summary["execution"] = "failed"
        harness.write_json(output / "summary.json", summary)
        harness.write_json(
            ROOT / "output/task62a/latest.json",
            {
                "run_id": run_id,
                "execution": summary["execution"],
                "performance_acceptance": harness.ACCEPTANCE,
            },
        )
    print(
        json.dumps(
            {
                "run_id": run_id,
                "execution": summary["execution"],
                "performance_acceptance": harness.ACCEPTANCE,
            }
        )
    )
    return 0 if summary["execution"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
