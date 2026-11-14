"""Synthetic decision evidence only; no worker or real process is started."""

import importlib.util
import json
from pathlib import Path

import pytest

from app.workers.operations import (
    Compatibility,
    Job,
    Lease,
    Ownership,
    Refused,
    State,
    Supervisor,
    oldest_due_age,
)

RELEASE = "a" * 64


def model():
    return Supervisor(Job.NOTIFICATIONS, RELEASE, enabled=True)


@pytest.mark.parametrize("job", list(Job))
def test_disabled_has_no_admission_or_queue_health(job):
    worker = Supervisor(job, RELEASE)
    with pytest.raises(Refused):
        worker.begin_poll(0)
    report = worker.report(0)
    assert report["execution_state"] == "disabled"
    assert report["pending_count"] is None
    assert report["last_poll_at"] is None
    assert report["observation_source"] == "synthetic_model"


def test_poll_success_empty_is_idle_failure_is_not_idle():
    worker = model()
    assert worker.report(0)["execution_state"] == "not_observed"
    worker.begin_poll(0)
    worker.poll_result(1, None, ok=False)
    assert worker.report(1)["last_poll_at"] is None
    worker.begin_poll(5)
    worker.poll_result(6, None, ok=True)
    assert worker.report(6)["execution_state"] == "idle"
    assert worker.report(6)["last_completion_at"] is None


def test_no_overlapping_poll_or_execution_and_poll_interval():
    worker = model()
    worker.begin_poll(0)
    with pytest.raises(Refused):
        worker.begin_poll(0)
    worker.poll_result(1, Lease("fixture", 1, 60), ok=True)
    with pytest.raises(Refused):
        worker.begin_poll(2)
    assert worker.report(2)["active_count"] == 1
    assert worker.finish(Lease("fixture", 1, 60), 3, success=True)
    with pytest.raises(Refused):
        worker.begin_poll(4)
    worker.begin_poll(5)


@pytest.mark.parametrize("point", ["unknown", "idle", "polling", "working"])
def test_signal_closes_admission_and_drains_admitted_iteration(point):
    worker = model()
    lease = Lease("fixture", 1, 60)
    if point != "unknown":
        worker.begin_poll(0)
    if point in ("idle", "working"):
        worker.poll_result(1, lease if point == "working" else None, ok=True)
    worker.stop_admission()
    worker.stop_admission()
    with pytest.raises(Refused):
        worker.begin_poll(5)
    if point == "polling":
        worker.poll_result(6, lease, ok=True)
    if point in ("polling", "working"):
        assert worker.state == State.DRAINING
        assert worker.finish(lease, 7, success=True)
    assert worker.state == State.STOPPED
    with pytest.raises(Refused):
        worker.begin_poll(8)


@pytest.mark.parametrize("ok", [True, False])
def test_draining_empty_or_failed_poll_stops(ok):
    worker = model()
    worker.begin_poll(0)
    worker.stop_admission()
    worker.poll_result(1, None, ok=ok)
    assert worker.state == State.STOPPED


@pytest.mark.parametrize(
    "current,now",
    [
        (Lease("other", 1, 60), 2),
        (Lease("fixture", 2, 60), 2),
        (Lease("fixture", 1, 60), 60),
        (Lease("fixture", 1, 60), 61),
    ],
)
def test_reclaimed_or_expired_lease_never_completes(current, now):
    worker = model()
    worker.begin_poll(0)
    worker.poll_result(1, Lease("fixture", 1, 60), ok=True)
    assert not worker.finish(current, now, success=True)
    assert worker.last_completion_at is None
    assert worker.error_code == "iteration_unconfirmed"


def test_force_stop_preserves_immutable_lease_and_rejects_late_finish():
    worker = model()
    lease = Lease("fixture", 1, 60)
    worker.begin_poll(0)
    worker.poll_result(1, lease, ok=True)
    worker.force_stop()
    assert lease == Lease("fixture", 1, 60)
    with pytest.raises(Refused):
        worker.finish(lease, 2, success=True)
    assert worker.report(2)["last_completion_at"] is None


def test_duplicate_scheduler_owner_rejected_independent_kinds_allowed():
    owners = Ownership()
    owners.acquire(Job.PRINTING, "first")
    with pytest.raises(Refused):
        owners.acquire(Job.PRINTING, "first")
    with pytest.raises(Refused):
        owners.acquire(Job.PRINTING, "second")
    owners.acquire(Job.FINANCE, "second")
    with pytest.raises(Refused):
        owners.release(Job.PRINTING, "second")
    owners.release(Job.PRINTING, "first")
    owners.acquire(Job.PRINTING, "second")


@pytest.mark.parametrize("job", ["retention", "privacy", "manufacturing", "all"])
def test_unapproved_job_has_no_model_admission(job):
    with pytest.raises(Refused):
        Supervisor(job, RELEASE, enabled=True)


@pytest.mark.parametrize(
    "release,schema,payload",
    [
        ("b" * 64, "0021", 1),
        (RELEASE, "0035", 1),
        (RELEASE, "0021", 2),
        (RELEASE, "0021", True),
    ],
)
def test_unknown_release_schema_or_payload_blocks_overlap_and_rollback(
    release, schema, payload
):
    policy = Compatibility(RELEASE, "0021", frozenset({1}))
    assert not policy.admits(release, schema, payload)
    assert policy.admits(RELEASE, "0021", 1)


@pytest.mark.parametrize("versions", [frozenset(), frozenset({True}), frozenset({0})])
def test_no_unreviewed_compatibility(versions):
    with pytest.raises(Refused):
        Compatibility(RELEASE, "0021", versions).admits(RELEASE, "0021", 1)


@pytest.mark.parametrize(
    "value", [-1, float("nan"), float("inf"), True, "secret-canary", 10**1000]
)
def test_invalid_clock_never_leaks_input(value):
    worker = model()
    with pytest.raises(Refused) as error:
        worker.report(value)
    assert str(error.value) == "invalid_number"


def test_clock_regression_fails_closed():
    worker = model()
    worker.report(10)
    with pytest.raises(Refused):
        worker.begin_poll(9)


def test_lag_unknown_empty_future_due_and_overdue():
    assert oldest_due_age(100, None) is None
    assert oldest_due_age(100, ()) == 0
    assert oldest_due_age(100, (101, 120)) == 0
    assert oldest_due_age(100, (50, 80, 120)) == 50


def test_closed_report_never_includes_private_lease_identity_or_false_queue_counts():
    worker = model()
    worker.begin_poll(0)
    worker.poll_result(1, Lease("private-canary", 1, 60), ok=True)
    report = worker.report(2)
    assert len(report) == 15
    assert "private-canary" not in json.dumps(report)
    assert report["pending_count"] is report["oldest_due_age_seconds"] is None
    assert report["last_completion_at"] is None


def test_network_database_and_process_guards_installed():
    import socket
    import subprocess

    import sqlalchemy

    with pytest.raises(PermissionError):
        socket.getaddrinfo("offline.invalid", 443)
    with pytest.raises(PermissionError):
        sqlalchemy.create_engine("postgresql://offline.invalid/db")
    with pytest.raises(PermissionError):
        subprocess.Popen(["must-never-execute"])


@pytest.mark.parametrize(
    "failure",
    [
        "timeout",
        "exit",
        "empty",
        "skip",
        "failure",
        "incomplete",
        "unexpected",
        "selection",
        "guards",
        "preservation",
    ],
)
def test_runner_never_accepts_partial_or_unapproved_evidence(failure):
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "task63a_runner", root / "ops/run-task63a-backend.py"
    )
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    counts = {"collected": 2, "passed": 2, "failed": 0, "errors": 0, "skipped": 0}
    collection = {
        "files": [runner.TEST],
        "collected": 2,
        "completed": 2,
        "unexpected": 0,
        "exit_code": 0,
        "guards_installed": True,
    }
    assert runner.accepted("completed", 0, counts, collection, True)
    outcome, exit_code, preserved = "completed", 0, True
    if failure == "timeout":
        outcome = "timed_out"
    elif failure == "exit":
        exit_code = 1
    elif failure == "empty":
        counts.update(collected=0, passed=0)
    elif failure == "skip":
        counts.update(passed=1, skipped=1)
    elif failure == "failure":
        counts.update(passed=1, failed=1)
    elif failure == "incomplete":
        collection["completed"] = 1
    elif failure == "unexpected":
        collection["unexpected"] = 1
    elif failure == "selection":
        collection["files"] = ["not-approved"]
    elif failure == "guards":
        collection["guards_installed"] = False
    elif failure == "preservation":
        preserved = False
    assert not runner.accepted(outcome, exit_code, counts, collection, preserved)


def test_proposed_manifest_is_disabled_and_has_no_executable_deployment():
    import tomllib

    root = Path(__file__).resolve().parents[2]
    proposed = tomllib.loads(
        (root / "backend/railway.workers.proposed.toml").read_text()
    )
    assert proposed["enabled"] is False
    assert proposed["status"] == "proposed_not_deployable"
    assert proposed["concurrency_per_job"] == proposed["replicas_per_job"] == 1
    assert proposed["jobs"] == [job.value for job in Job]
    assert (
        not {"deploy", "startCommand", "cronSchedule", "healthcheckPath"}
        & proposed.keys()
    )
