"""Trusted standalone Linux worker; stdin is closed validated synthetic JSON only."""

import json
import re
import resource
import socket
import sys
from pathlib import Path

ERROR_PREFIX = b"SAFERETURN_PREVIEW_ERROR:"

def main():
    sys.dont_write_bytecode = True
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    def denied(*args, **kwargs):
        raise RuntimeError("Network unavailable")

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.core.template_preview import render_synthetic

    socket.socket = denied
    socket.create_connection = denied
    raw = sys.stdin.buffer.read(32769)
    if len(raw) > 32768:
        raise ValueError("Input too large")
    value = json.loads(raw)
    data = render_synthetic(value["spec"], value["root"])
    sys.stdout.buffer.write(data)


if __name__ == "__main__":
    try:
        main()
    # Keep worker tracebacks (which may contain private paths or content) inside
    # the sandbox and report only a safe error category to the parent process.
    except Exception as exc:  # noqa: BLE001
        error = type(exc).__name__
        if (
            error == "PrintUnavailable"
            and exc.args
            and isinstance(exc.args[0], str)
            and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", exc.args[0])
        ):
            error = exc.args[0]
        sys.stdout.buffer.write(ERROR_PREFIX + error.encode("ascii"))
        sys.stdout.buffer.flush()
        raise SystemExit(1) from None
