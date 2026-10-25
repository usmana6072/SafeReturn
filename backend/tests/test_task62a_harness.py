"""Synthetic harness checks; fixture timing numbers are not benchmark evidence."""

import asyncio
import importlib.util
import json
import math
import threading
import time
from pathlib import Path

import pytest
import task61a_offline as guard
import task62a_harness as harness

SPEC = importlib.util.spec_from_file_location(
    "task62a_runner", Path(__file__).resolve().parents[2] / "ops/run-task62a-backend.py"
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


@pytest.fixture(autouse=True)
def guarded():
    if not guard.INSTALLED:
        raise RuntimeError("Use the guarded Task62a runner")


@pytest.mark.parametrize(
    "p,expected", [(0.5, 100), (0.95, 190), (0.99, 198), (1, 200), (0.001, 1)]
)
def test_nearest_rank(p, expected):
    assert harness.nearest_rank(list(range(200, 0, -1)), p) == expected


@pytest.mark.parametrize(
    "values,p",
    [
        ([], 0.5),
        ([0], 0.5),
        ([-1], 0.5),
        ([math.inf], 0.5),
        ([math.nan], 0.5),
        ([True], 0.5),
        (["secret"], 0.5),
        ([1], 0),
        ([1], 1.1),
    ],
)
def test_invalid_quantiles(values, p):
    with pytest.raises(harness.InvalidMeasurement):
        harness.nearest_rank(values, p)


def synthetic_samples():
    return [
        {
            "index": i,
            "duration_ns": (i + 1) * 1_000_000,
            "outcome": "succeeded",
            "response_bytes": 0,
        }
        for i in range(harness.SAMPLES)
    ]


def synthetic_report():
    samples, cells = [], []
    for case in harness.CASES:
        for concurrency in harness.CONCURRENCY:
            for repetition in range(harness.REPETITIONS):
                entries = synthetic_samples()
                cells.append(
                    harness.cell_result(
                        case, concurrency, repetition, entries, 1e9, 5e8
                    )
                )
                samples.extend(
                    {
                        "case_id": case,
                        "concurrency": concurrency,
                        "repetition": repetition,
                        **s,
                    }
                    for s in entries
                )
    return {
        "cells": cells,
        "allocation_observations": [
            {"case_id": case, "operations": 20, "traced_peak_bytes": 100}
            for case in harness.CASES
        ],
        "clock_resolution_seconds": 1e-9,
        "started_at_utc": "2026-01-01T00:00:00+00:00",
        "guard_mode": "memory_selector_no_network_database_process",
    }, samples


def test_exact_report_and_no_percentile_averaging():
    report, samples = synthetic_report()
    harness.validate_report(report, samples)
    assert len(report["cells"]) == 30
    assert len(samples) == 6000
    assert all(c["p95_ms"] == 190 for c in report["cells"])
    assert all(c["throughput_success_per_second"] == 200 for c in report["cells"])


@pytest.mark.parametrize(
    "defect",
    [
        "missing_cell",
        "duplicate_cell",
        "missing_sample",
        "duplicate_index",
        "failed_sample",
        "negative",
        "nonfinite",
        "private_field",
        "extra_cell_field",
        "false_percentile",
        "false_throughput",
        "bad_guard",
        "missing_allocation",
        "allocation_stop",
        "clock",
    ],
)
def test_invalid_reports(defect):
    report, samples = synthetic_report()
    if defect == "missing_cell":
        report["cells"].pop()
    elif defect == "duplicate_cell":
        report["cells"][1] = report["cells"][0]
    elif defect == "missing_sample":
        samples.pop()
    elif defect == "duplicate_index":
        samples[1]["index"] = 0
    elif defect == "failed_sample":
        samples[0]["outcome"] = "failed"
    elif defect == "negative":
        samples[0]["duration_ns"] = -1
    elif defect == "nonfinite":
        report["cells"][0]["p95_ms"] = math.nan
    elif defect == "private_field":
        samples[0]["token"] = "SYNTHETIC-SECRET-CANARY"
    elif defect == "extra_cell_field":
        report["cells"][0]["private_origin"] = "SYNTHETIC-SECRET-CANARY"
    elif defect == "false_percentile":
        report["cells"][0]["p99_ms"] = 1
    elif defect == "false_throughput":
        report["cells"][0]["throughput_success_per_second"] = 1
    elif defect == "bad_guard":
        report["guard_mode"] = "unguarded"
    elif defect == "missing_allocation":
        report["allocation_observations"].pop()
    elif defect == "allocation_stop":
        report["allocation_observations"][0]["traced_peak_bytes"] = (
            harness.ALLOCATION_LIMIT + 1
        )
    else:
        report["clock_resolution_seconds"] = math.inf
    with pytest.raises((harness.InvalidMeasurement, ValueError)):
        harness.validate_report(report, samples)


@pytest.mark.parametrize("value", [-1, True, math.inf, harness.ALLOCATION_LIMIT + 1])
def test_allocation_stop(value):
    with pytest.raises(harness.InvalidMeasurement):
        harness.check_allocation(value)


def test_fixture_boundaries_and_actual_validators():
    workloads = harness.Workloads()
    try:
        assert len(workloads.db.records) == len(workloads.tokens) == 32
        assert len(workloads.finance) == 1000
        assert len(workloads.pages) == 10
        assert workloads.app.state.settings.abuse_reports_enabled is False
        assert workloads.app.state.settings.print_template_management_enabled is False
        assert workloads.jwk_calls == 1
        for case in harness.CASES[2:]:
            assert workloads.sync_operation(case, 1) == 0
        workloads.prepare()
        assert workloads.jwk_calls == 1
    finally:
        asyncio.run(workloads.close())


@pytest.mark.parametrize("defect", ["refresh", "expired", "cache_old"])
def test_cache_contamination(defect):
    workloads = harness.Workloads()
    try:
        if defect == "refresh":
            workloads.jwk_calls += 1
        elif defect == "expired":
            workloads.expiry = 0
        else:
            workloads.verifier.loaded_at = -10000
        with pytest.raises(harness.InvalidMeasurement, match="jwt_cache_contamination"):
            workloads.prepare()
    finally:
        asyncio.run(workloads.close())


def test_warmup_excluded_and_concurrency_bounded():
    class Fake:
        active = peak = calls = 0

        async def http_operation(self, case, index):
            self.active += 1
            self.peak = max(self.peak, self.active)
            self.calls += 1
            await asyncio.sleep(0)
            self.active -= 1
            return 10

    async def exercise():
        fake = Fake()
        await harness.batch(fake, harness.CASES[0], 4, 20, measured=False)
        entries, wall, cpu = await harness.batch(
            fake, harness.CASES[0], 4, 200, measured=True
        )
        assert len(entries) == 200
        assert fake.calls == 220
        assert fake.peak == 4
        assert (
            harness.cell_result(harness.CASES[0], 4, 0, entries, wall, cpu)["attempted"]
            == 200
        )

    asyncio.run(exercise())


def test_sync_worker_limit_and_sample_count():
    class Fake:
        def __init__(self):
            self.active = self.peak = 0
            self.lock = threading.Lock()

        def sync_operation(self, case, index):
            with self.lock:
                self.active += 1
                self.peak = max(self.peak, self.active)
            time.sleep(0.001)  # test-only scheduling probe, never measurement evidence
            with self.lock:
                self.active -= 1
            return 0

    async def exercise():
        fake = Fake()
        entries, _, _ = await harness.batch(
            fake, harness.CASES[2], 4, 200, measured=True
        )
        assert len(entries) == 200 and 1 <= fake.peak <= 4

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "case,concurrency,count",
    [
        ("unknown", 1, 200),
        (harness.CASES[0], 8, 200),
        (harness.CASES[0], 0, 200),
        (harness.CASES[0], 1, 201),
    ],
)
def test_unapproved_batch_refused(case, concurrency, count):
    with pytest.raises(harness.InvalidMeasurement):
        asyncio.run(harness.batch(None, case, concurrency, count, measured=True))


@pytest.mark.parametrize(
    "defect",
    ["boolean_index", "boolean_concurrency", "naive_timestamp", "boolean_resolution"],
)
def test_strict_report_types(defect):
    report, samples = synthetic_report()
    if defect == "boolean_index":
        samples[0]["index"] = False
    elif defect == "boolean_concurrency":
        report["cells"][0]["concurrency"] = True
    elif defect == "naive_timestamp":
        report["started_at_utc"] = "2026-01-01T00:00:00"
    else:
        report["clock_resolution_seconds"] = True
    with pytest.raises(harness.InvalidMeasurement):
        harness.validate_report(report, samples)


def test_child_deadline_no_spawn(tmp_path):
    assert runner.run_child(
        [], tmp_path, tmp_path / "absent.log", time.monotonic() - 1
    ) == ("timed_out", None)
    assert not (tmp_path / "absent.log").exists()


def test_failure_accounting_does_not_silently_drop_samples():
    class Fake:
        async def http_operation(self, case, index):
            raise ValueError("SYNTHETIC-SECRET-CANARY")

    async def exercise():
        entries, wall, cpu = await harness.batch(
            Fake(), harness.CASES[0], 1, 200, measured=True
        )
        assert len(entries) == 200 and all(s["outcome"] == "failed" for s in entries)
        assert "SYNTHETIC-SECRET-CANARY" not in json.dumps(entries)
        with pytest.raises(harness.InvalidMeasurement):
            harness.cell_result(harness.CASES[0], 1, 0, entries, wall, cpu)
        with pytest.raises(harness.InvalidMeasurement, match="warmup_failed"):
            await harness.batch(Fake(), harness.CASES[0], 1, 20, measured=False)

    asyncio.run(exercise())


def test_scripted_repository_is_closed_and_copies_projection():
    repo = harness.ScriptedQR()
    first = repo.execute(
        "sr_public_qr_projection", {"token": repo.tokens[0]}
    ).scalar_one()
    first["lost_item"]["label"] = "changed"
    assert repo.records[repo.tokens[0]]["lost_item"]["label"] != "changed"
    with pytest.raises(harness.InvalidMeasurement):
        repo.execute("unapproved synthetic writer")


def test_child_failure_sanitized(tmp_path, monkeypatch):
    async def fail(path):
        raise ValueError("SYNTHETIC-SECRET-CANARY")

    monkeypatch.setattr(harness, "measure", fail)
    assert harness.child(str(tmp_path)) == 1
    assert (
        "SYNTHETIC-SECRET-CANARY"
        not in (tmp_path / "measurement-failure.json").read_text()
    )


@pytest.mark.parametrize(
    "scenario",
    [
        "completed",
        "timeout",
        "interrupt",
        "invalid",
        "partial",
        "test_failure",
        "preservation",
    ],
)
def test_parent_failure_paths_no_real_process(tmp_path, monkeypatch, scenario):
    report, samples = synthetic_report()
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(
        runner.previous, "current_chain", lambda root: ["0035_public_abuse_intake"]
    )
    monkeypatch.setattr(
        runner.previous,
        "git_state",
        lambda root: {
            "revision": "synthetic",
            "porcelain": "dirty",
            "branch": "synthetic",
        },
    )
    calls = {"snapshot": 0, "child": 0}

    def snapshot(root):
        calls["snapshot"] += 1
        return {
            "synthetic.py": "changed"
            if scenario == "preservation" and calls["snapshot"] > 1
            else "same"
        }

    monkeypatch.setattr(runner.previous, "source_manifest", snapshot)

    def fake(arguments, scratch, logfile, deadline):
        calls["child"] += 1
        output = logfile.parent
        if calls["child"] == 1:
            if scenario == "timeout":
                return "timed_out", None
            if scenario == "interrupt":
                return "interrupted", None
            if scenario == "invalid":
                (output / "measurement.json").write_text("{")
                return "completed", 0
            if scenario == "partial":
                report["cells"].pop()
            harness.write_json(output / "measurement.json", report)
            harness.write_json(output / "samples.json", samples)
        else:
            failure = int(scenario == "test_failure")
            (output / "tests.xml").write_text(
                f'<testsuite tests="1" failures="{failure}" errors="0" skipped="0"><testcase>{"<failure/>" if failure else ""}</testcase></testsuite>'
            )
            harness.write_json(
                output / "collection.json",
                {
                    "files": list(runner.TESTS),
                    "collected": 1,
                    "completed": 1,
                    "unexpected_outcomes": 0,
                    "guards_installed": True,
                    "exit_code": failure,
                },
            )
            return "completed", failure
        return "completed", 0

    monkeypatch.setattr(runner, "run_child", fake)
    assert runner.main() == (0 if scenario == "completed" else 1)
    latest = json.loads((tmp_path / "output/task62a/latest.json").read_text())
    summary = json.loads(
        (tmp_path / "output/task62a" / latest["run_id"] / "summary.json").read_text()
    )
    expected = {
        "timeout": "timed_out",
        "interrupt": "interrupted",
        "invalid": "invalid_report",
        "partial": "invalid_report",
    }.get(scenario, "completed" if scenario == "completed" else "failed")
    assert summary["execution"] == expected
    assert summary["performance_acceptance"] == harness.ACCEPTANCE
    assert summary["targets"] is None
    assert calls["snapshot"] == 2
    assert summary["preservation"] == (
        "failed" if scenario == "preservation" else "passed"
    )


def test_environment_guard_and_memory_loop_still_installed():
    import socket

    with pytest.raises(PermissionError):
        socket.getaddrinfo("synthetic.invalid", 443)
    with pytest.raises(PermissionError):
        guard.MemorySelector().register(1, 1)


def test_closed_test_report():
    counts = {"collected": 1, "passed": 1, "failed": 0, "errors": 0, "skipped": 0}
    collection = {
        "files": list(runner.TESTS),
        "collected": 1,
        "completed": 1,
        "unexpected_outcomes": 0,
        "guards_installed": True,
        "exit_code": 0,
    }
    assert runner.test_report_ok(0, counts, collection)
    collection["unexpected_outcomes"] = 1
    assert not runner.test_report_ok(0, counts, collection)


def test_closed_report_has_no_fixture_data():
    report, samples = synthetic_report()
    serialized = json.dumps({"report": report, "samples": samples})
    for private in (
        "synthetic.invalid",
        "SYNTHETIC-SECRET-CANARY",
        "authorization",
        "+12025550100",
        "recipient_name",
        "medical_notes",
    ):
        assert private not in serialized
