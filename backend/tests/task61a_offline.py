"""Early guards for the approved offline selection. PYTEST_DONT_REWRITE"""

import json
import selectors
import sys
import threading
from pathlib import Path

INSTALLED = False
COMPLETED = 0
UNEXPECTED = 0


class MemorySelector(selectors.BaseSelector):
    """Timers/thread wakeups only; never registers or opens an OS descriptor."""

    def __init__(self):
        self.wakeup = threading.Event()

    def register(self, fileobj, events, data=None):
        return denied()

    def unregister(self, fileobj):
        return denied()

    def select(self, timeout=None):
        self.wakeup.wait(timeout)
        self.wakeup.clear()
        return []

    def get_map(self):
        return {}

    def close(self):
        self.wakeup.set()


def memory_event_loop():
    import asyncio

    class MemoryLoop(asyncio.SelectorEventLoop):
        def _make_self_pipe(self):
            pass

        def _close_self_pipe(self):
            pass

        def _write_to_self(self):
            if self._selector is not None:
                self._selector.wakeup.set()

    return MemoryLoop(selector=MemorySelector())


def audit_guard(event, args):
    if event in {
        "socket.connect",
        "socket.bind",
        "socket.getaddrinfo",
        "socket.gethostbyname",
        "socket.gethostbyaddr",
        "socket.getnameinfo",
        "subprocess.Popen",
        "os.system",
        "os.fork",
        "os.forkpty",
        "os.posix_spawn",
        "os.exec",
        "os.spawn",
    }:
        raise PermissionError("Task61a offline boundary")
    if event == "sqlite3.connect" and args[0] != ":memory:":
        raise PermissionError("Task61a memory-only SQLite")


def denied(*args, **kwargs):
    raise PermissionError("Task61a offline boundary")


def install_guards():
    global INSTALLED
    if INSTALLED:
        return
    import asyncio.events
    import socket

    import sqlalchemy
    import sqlalchemy.engine
    import sqlalchemy.engine.create

    for module, name in (
        (socket.socket, "connect"),
        (socket.socket, "connect_ex"),
        (socket.socket, "bind"),
        (socket.socket, "listen"),
        (socket, "create_connection"),
        (socket, "getaddrinfo"),
        (socket, "gethostbyname"),
        (socket, "gethostbyname_ex"),
        (socket, "gethostbyaddr"),
        (socket, "getnameinfo"),
        (sqlalchemy, "create_engine"),
        (sqlalchemy.engine, "create_engine"),
        (sqlalchemy.engine.create, "create_engine"),
        (sqlalchemy.engine.Engine, "__init__"),
    ):
        setattr(module, name, denied)
    sys.addaudithook(audit_guard)
    # Windows socketpair otherwise opens a loopback listener for asyncio's
    # self-pipe. Use only memory/thread wakeups for synthetic ASGI on every OS.
    asyncio.events.new_event_loop = memory_event_loop
    INSTALLED = True


def pytest_addoption(parser):
    parser.addoption("--task61a-report", required=True)


def pytest_collection_finish(session):
    from importlib.util import module_from_spec, spec_from_file_location

    root = Path(__file__).resolve().parents[2]
    spec = spec_from_file_location(
        "task61a_selection", root / "ops/run-task61a-backend.py"
    )
    selection = module_from_spec(spec)
    spec.loader.exec_module(selection)
    paths = {
        Path(item.path).resolve().relative_to(root).as_posix() for item in session.items
    }
    if paths != set(selection.TESTS):
        raise RuntimeError("Unapproved test selection")


def pytest_runtest_logreport(report):
    global COMPLETED, UNEXPECTED
    if report.when == "teardown":
        COMPLETED += 1
    if hasattr(report, "wasxfail") or report.skipped:
        UNEXPECTED += 1


def pytest_sessionfinish(session, exitstatus):
    root = Path(__file__).resolve().parents[2]
    value = {
        "files": sorted(
            {
                Path(item.path).resolve().relative_to(root).as_posix()
                for item in session.items
            }
        ),
        "collected": len(session.items),
        "completed": COMPLETED,
        "exit_code": int(exitstatus),
        "unexpected_outcomes": UNEXPECTED,
        "guards_installed": INSTALLED,
    }
    Path(session.config.getoption("--task61a-report")).write_text(
        json.dumps(value), encoding="utf-8"
    )
