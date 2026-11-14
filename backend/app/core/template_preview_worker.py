"""Trusted standalone Linux worker; stdin is closed validated synthetic JSON only."""

import json
import resource
import socket
import sys
from pathlib import Path


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
    main()
