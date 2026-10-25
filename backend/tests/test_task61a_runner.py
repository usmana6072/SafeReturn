"""Negative preparation checks only; fake processes and synthetic migration files."""

import importlib.util
import json
import socket
import sqlite3
import subprocess
from pathlib import Path

import pytest
import task61a_offline as guard

SPEC = importlib.util.spec_from_file_location(
    "task61a_runner", Path(__file__).resolve().parents[2] / "ops/run-task61a-backend.py"
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


@pytest.fixture(autouse=True)
def require_early_offline_guards():
    # Direct/full-suite invocation must never exercise denial probes unguarded.
    if not guard.INSTALLED:
        raise RuntimeError("Use the approved offline runner before collecting probes")


def test_early_guards_are_installed():
    assert guard.INSTALLED


@pytest.mark.parametrize(
    "method,args",
    [
        (socket.create_connection, (("127.0.0.1", 8030),)),
        (socket.getaddrinfo, ("example.invalid", 443)),
        (socket.gethostbyname, ("example.invalid",)),
    ],
)
def test_network_denied(method, args):
    with pytest.raises(PermissionError, match="offline boundary"):
        method(*args)


@pytest.mark.parametrize("method", ["connect", "connect_ex", "bind", "listen"])
def test_socket_denied(method):
    with (
        socket.socket() as connection,
        pytest.raises(PermissionError, match="offline boundary"),
    ):
        getattr(connection, method)(1 if method == "listen" else ("127.0.0.1", 8030))


def test_subprocess_denied():
    with pytest.raises(PermissionError, match="offline boundary"):
        subprocess.Popen(["never-executed-synthetic-command"])


def test_database_denied():
    import sqlalchemy
    from sqlalchemy.engine import create_engine

    for method in (sqlalchemy.create_engine, create_engine):
        with pytest.raises(PermissionError):
            method("postgresql://synthetic.invalid/no-credentials")


def test_memory_only_sqlite(tmp_path):
    with sqlite3.connect(":memory:") as connection:
        assert connection.execute("select 1").fetchone() == (1,)
    path = tmp_path / "not-created.db"
    with pytest.raises(PermissionError):
        sqlite3.connect(str(path))
    assert not path.exists()


def test_environment_canaries_removed(tmp_path):
    canary = "SYNTHETIC-SECRET-61A"
    source = {
        name: canary
        for name in (
            "SAFERETURN_DATABASE_URL",
            "SAFERETURN_TEST_DATABASE_URL",
            "SUPABASE_KEY",
            "AWS_ACCESS_KEY_ID",
            "GOOGLE_APPLICATION_CREDENTIALS",
            "HOME",
            "PYTEST_ADDOPTS",
            "PYTEST_PLUGINS",
            "PYTHONPATH",
            "GITHUB_TOKEN",
        )
    }
    source["PATH"] = "synthetic-runtime-path"
    clean = runner.child_environment(source, runner.ROOT, tmp_path)
    assert canary not in json.dumps(clean)
    assert clean["PATH"] == source["PATH"]
    assert clean["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
    assert clean["PYTHONDONTWRITEBYTECODE"] == "1"
    assert clean["TMP"] == str(tmp_path)
    assert source["GITHUB_TOKEN"] == canary

    class NoCredentialReads:
        def __iter__(self):
            return iter(("PATH", "SAFERETURN_DATABASE_URL", "GITHUB_TOKEN"))

        def __getitem__(self, key):
            assert key == "PATH", "Credential variable value accessed"
            return "synthetic-runtime-path"

    assert (
        runner.child_environment(NoCredentialReads(), runner.ROOT, tmp_path)["PATH"]
        == source["PATH"]
    )


def migration(tmp_path, name, parent):
    path = tmp_path / (name + ".py")
    path.write_text(
        f"revision = {name!r}\ndown_revision = {parent!r}\n", encoding="utf-8"
    )
    return path


def test_real_static_chain():
    chain = runner.current_chain(runner.ROOT)
    assert len(chain) == 36
    assert chain[-1] == "0035_public_abuse_intake"
    assert "0021_support_case_console" in chain


def test_graph_linear(tmp_path):
    migration(tmp_path, "one", None)
    migration(tmp_path, "two", "one")
    assert runner.migration_chain(tmp_path) == ["one", "two"]


@pytest.mark.parametrize(
    "kind",
    [
        "empty",
        "missing",
        "duplicate",
        "branch",
        "cycle",
        "disconnected",
        "dynamic",
        "sql",
    ],
)
def test_bad_graphs(tmp_path, kind):
    if kind == "missing":
        migration(tmp_path, "one", "absent")
    elif kind == "duplicate":
        path = migration(tmp_path, "one", None)
        (tmp_path / "duplicate.py").write_bytes(path.read_bytes())
    elif kind == "branch":
        migration(tmp_path, "one", None)
        migration(tmp_path, "two", "one")
        migration(tmp_path, "three", "one")
    elif kind in ("cycle", "disconnected"):
        migration(tmp_path, "one", "two")
        migration(tmp_path, "two", "one")
        if kind == "disconnected":
            migration(tmp_path, "three", None)
    elif kind == "dynamic":
        (tmp_path / "dynamic.py").write_text(
            "revision = forbidden()\ndown_revision = None"
        )
    elif kind == "sql":
        migration(tmp_path, "0022_synthetic", None)
    with pytest.raises((ValueError, TypeError)):
        runner.migration_chain(tmp_path)


def report(tmp_path, body):
    path = tmp_path / "synthetic.xml"
    path.write_text(body, encoding="utf-8")
    return path


def test_junit_counts(tmp_path):
    path = report(
        tmp_path,
        '<testsuites><testsuite tests="4" failures="1" errors="1" skipped="1">'
        "<testcase/><testcase><failure/></testcase><testcase><error/></testcase>"
        "<testcase><skipped/></testcase></testsuite></testsuites>",
    )
    assert runner.counts_from_junit(path) == {
        "collected": 4,
        "passed": 1,
        "failed": 1,
        "errors": 1,
        "skipped": 1,
    }


@pytest.mark.parametrize(
    "body",
    [
        "",
        "<testsuites>",
        "<other/>",
        "<testsuites/>",
        '<testsuite tests="0" failures="0" errors="0" skipped="0"/>',
        '<testsuite tests="2" failures="0" errors="0" skipped="0"><testcase/></testsuite>',
        '<testsuite tests="1" failures="1" errors="0" skipped="0"><testcase/></testsuite>',
        '<testsuite tests="1" failures="1" errors="1" skipped="0"><testcase><failure/><error/></testcase></testsuite>',
    ],
)
def test_invalid_junit(tmp_path, body):
    import xml.etree.ElementTree as ET

    with pytest.raises((ValueError, ET.ParseError)):
        runner.counts_from_junit(report(tmp_path, body))


def good_counts():
    return {"collected": 7, "passed": 7, "failed": 0, "errors": 0, "skipped": 0}


def good_collection():
    return {
        "files": list(runner.TESTS),
        "collected": 7,
        "completed": 7,
        "exit_code": 0,
        "unexpected_outcomes": 0,
        "guards_installed": True,
    }


def test_evaluate_success():
    assert runner.evaluate(0, good_counts(), good_collection())


@pytest.mark.parametrize(
    "change",
    [
        "skip",
        "failure",
        "error",
        "empty",
        "xpass",
        "guards",
        "selection",
        "partial",
        "exit",
    ],
)
def test_no_false_success(change):
    counts, collection = good_counts(), good_collection()
    code = 0
    if change in ("skip", "failure", "error"):
        counts[{"skip": "skipped", "failure": "failed", "error": "errors"}[change]] = 1
    elif change == "empty":
        counts["collected"] = 0
    elif change == "xpass":
        collection["unexpected_outcomes"] = 1
    elif change == "guards":
        collection["guards_installed"] = False
    elif change == "selection":
        collection["files"] = ["backend/tests/integration/unapproved.py"]
    elif change == "partial":
        collection["completed"] = 6
    else:
        code = 2
    assert not runner.evaluate(code, counts, collection)


@pytest.mark.parametrize(
    "failure,expected",
    [(None, "completed"), ("timeout", "timed_out"), ("interrupt", "interrupted")],
)
def test_timeout_interruption_no_process_spawn(failure, expected):
    class FakeProcess:
        killed = False

        def wait(self, timeout):
            if not self.killed:
                if failure == "timeout":
                    raise subprocess.TimeoutExpired("synthetic", timeout)
                if failure == "interrupt":
                    raise KeyboardInterrupt
            return 0

        def kill(self):
            self.killed = True

    process = FakeProcess()
    result = runner.wait_process(process, 600)
    assert result == (expected, 0 if failure is None else None)
    assert process.killed == (failure is not None)


def test_bounded_log(tmp_path):
    import io

    path = tmp_path / "bounded.log"
    runner.copy_log(
        io.BufferedReader(io.BytesIO(b"x" * (runner.LOG_LIMIT + 100))), path
    )
    assert path.stat().st_size == runner.LOG_LIMIT


def test_manifest_detects_source_and_excludes_env(tmp_path):
    for folder in ("backend", "frontend"):
        (tmp_path / folder).mkdir()
    (tmp_path / ".env").write_text("SYNTHETIC-NOT-READ")
    (tmp_path / "backend/.env.local").write_text("SYNTHETIC-NOT-READ")
    file = tmp_path / "backend/synthetic.py"
    file.write_text("one")
    before = runner.source_manifest(tmp_path)
    assert list(before) == ["backend/synthetic.py"]
    file.write_text("two")
    assert before != runner.source_manifest(tmp_path)


def test_guard_outcome_reporting(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(guard, "COMPLETED", 0)
    monkeypatch.setattr(guard, "UNEXPECTED", 0)
    guard.pytest_runtest_logreport(SimpleNamespace(when="teardown", skipped=False))
    guard.pytest_runtest_logreport(
        SimpleNamespace(when="call", skipped=False, wasxfail="synthetic")
    )
    assert guard.COMPLETED == 1
    assert guard.UNEXPECTED == 1


def test_memory_loop_timers_and_thread_wakeups():
    import asyncio

    async def exercise():
        await asyncio.sleep(0.001)
        return await asyncio.to_thread(lambda: 61)

    assert asyncio.run(exercise()) == 61
    with pytest.raises(PermissionError):
        guard.MemorySelector().register(1, 1)


@pytest.mark.parametrize(
    "scenario",
    [
        "passed",
        "test_failure",
        "skip",
        "missing_report",
        "truncated_report",
        "timeout",
        "interrupted",
        "source_change",
        "git_change",
    ],
)
def test_runner_reports_failures_and_preserves_on_every_exit(
    tmp_path, monkeypatch, scenario
):
    """Exercise orchestration with a fake child, never a nested pytest/process."""
    import io

    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(
        runner, "current_chain", lambda root: ["0035_public_abuse_intake"]
    )
    snapshots = {"source": 0, "git": 0}

    def manifest(root):
        snapshots["source"] += 1
        changed = scenario == "source_change" and snapshots["source"] > 1
        return {"backend/app/synthetic.py": "changed" if changed else "same"}

    def git(root):
        snapshots["git"] += 1
        changed = scenario == "git_change" and snapshots["git"] > 1
        return {
            "revision": "synthetic-revision",
            "branch": "changed" if changed else "synthetic-branch",
            "porcelain": " M synthetic.py",
        }

    monkeypatch.setattr(runner, "source_manifest", manifest)
    monkeypatch.setattr(runner, "git_state", git)

    class FakeProcess:
        killed = False

        def __init__(self, args, **kwargs):
            assert kwargs["env"]["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
            assert not any(name.startswith("SAFERETURN_") for name in kwargs["env"])
            self.stdout = io.BufferedReader(io.BytesIO(b"synthetic test log\n"))
            output = Path(
                next(a.split("=", 1)[1] for a in args if a.startswith("--junitxml="))
            )
            collection_path = Path(
                next(
                    a.split("=", 1)[1]
                    for a in args
                    if a.startswith("--task61a-report=")
                )
            )
            if scenario == "missing_report":
                return
            if scenario == "truncated_report":
                output.write_text("<testsuites>")
                return
            cases = "<testcase/>" * 7
            failure = int(scenario == "test_failure")
            skipped = int(scenario == "skip")
            if failure:
                cases = cases.replace(
                    "<testcase/>", "<testcase><failure/></testcase>", 1
                )
            if skipped:
                cases = cases.replace(
                    "<testcase/>", "<testcase><skipped/></testcase>", 1
                )
            output.write_text(
                f'<testsuite tests="7" failures="{failure}" errors="0" skipped="{skipped}">{cases}</testsuite>'
            )
            collection = good_collection()
            collection["exit_code"] = 1 if failure else 0
            collection_path.write_text(json.dumps(collection))

        def wait(self, timeout):
            if not self.killed:
                if scenario == "timeout":
                    raise subprocess.TimeoutExpired("synthetic", timeout)
                if scenario == "interrupted":
                    raise KeyboardInterrupt
            return 1 if scenario == "test_failure" else 0

        def kill(self):
            self.killed = True

    monkeypatch.setattr(runner.subprocess, "Popen", FakeProcess)
    assert runner.main() == (0 if scenario == "passed" else 1)
    latest = json.loads((tmp_path / "output/task61a/latest.json").read_text())
    summary = latest["summary"]
    expected = {
        "missing_report": "invalid_report",
        "truncated_report": "invalid_report",
        "timeout": "timed_out",
        "interrupted": "interrupted",
        "passed": "passed",
    }.get(scenario, "failed")
    assert summary["outcome"] == expected
    assert summary["preservation"] == (
        "failed" if scenario in ("source_change", "git_change") else "passed"
    )
    assert snapshots == {"source": 2, "git": 2}
    assert summary["not_run"] == list(runner.NOT_RUN)
    assert set(summary) == {
        "schema_version",
        "scope",
        "outcome",
        "exit_code",
        "collected",
        "passed",
        "failed",
        "errors",
        "skipped",
        "duration_seconds",
        "preservation",
        "not_run",
        "revision",
        "dirty",
        "migration_head",
    }
    evidence = tmp_path / "output/task61a" / latest["run_id"]
    assert (evidence / "summary.json").is_file()
    assert (evidence / "preservation.json").is_file()
