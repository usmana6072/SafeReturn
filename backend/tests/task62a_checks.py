"""Focused Task62a collection and outcome report; no other test files allowed."""

import json
from pathlib import Path

import task61a_offline as guard

COMPLETED = 0
UNEXPECTED = 0


def pytest_addoption(parser):
    parser.addoption("--task62a-report", required=True)


def files(session):
    root = Path(__file__).resolve().parents[2]
    return sorted(
        {
            Path(item.path).resolve().relative_to(root).as_posix()
            for item in session.items
        }
    )


def pytest_collection_finish(session):
    if (
        files(session) != ["backend/tests/test_task62a_harness.py"]
        or not guard.INSTALLED
    ):
        raise RuntimeError("Unapproved offline selection")


def pytest_runtest_logreport(report):
    global COMPLETED, UNEXPECTED
    if report.when == "teardown":
        COMPLETED += 1
    if hasattr(report, "wasxfail") or report.skipped:
        UNEXPECTED += 1


def pytest_sessionfinish(session, exitstatus):
    Path(session.config.getoption("--task62a-report")).write_text(
        json.dumps(
            {
                "files": files(session),
                "collected": len(session.items),
                "completed": COMPLETED,
                "exit_code": int(exitstatus),
                "unexpected_outcomes": UNEXPECTED,
                "guards_installed": guard.INSTALLED,
            }
        ),
        encoding="utf-8",
    )
