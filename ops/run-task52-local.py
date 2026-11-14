"""Start fresh loopback API/web processes without stopping existing applications."""

import os
import shutil
import socket
import subprocess
import time
import uuid
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def free_port(start):
    for port in range(start, start + 20):
        try:
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", port))
            return port
        except OSError:
            continue
    raise RuntimeError("No free local port")


def main():
    api, web = free_port(8030), free_port(3031)
    suffix = "task52-" + uuid.uuid4().hex
    env = {
        **os.environ,
        "SAFERETURN_API_ORIGIN": f"http://127.0.0.1:{api}",
        "SAFERETURN_WEB_ORIGIN": f"http://localhost:{web}",
        "NEXT_TELEMETRY_DISABLED": "1",
    }
    # Share required Auth settings and the server-only ticket key with Next.
    # The API loads its own ignored file; storage/provider/database keys stay out.
    backend_values = dotenv_values(ROOT / "backend/.env")
    frontend_values = dotenv_values(ROOT / "frontend/.env.local")
    for setting in (
        "SAFERETURN_SUPABASE_URL",
        "SAFERETURN_SUPABASE_PUBLISHABLE_KEY",
        "SAFERETURN_SESSION_SIGNING_KEY",
    ):
        value = (
            env.get(setting)
            or frontend_values.get(setting)
            or backend_values.get(setting)
        )
        if value:
            env[setting] = value
    services = [
        (
            "backend",
            [
                str(ROOT / "backend/.venv/Scripts/python.exe"),
                "-m",
                "uvicorn",
                "app.main:app",
                "--env-file",
                ".env",
                "--host",
                "127.0.0.1",
                "--port",
                str(api),
            ],
        ),
        (
            "frontend",
            [
                shutil.which("node"),
                "node_modules/next/dist/bin/next",
                "start",
                "--hostname",
                "127.0.0.1",
                "--port",
                str(web),
            ],
        ),
    ]
    pids = []
    for directory, args in services:
        with (
            (ROOT / directory / (suffix + ".stdout.log")).open("w") as out,
            (ROOT / directory / (suffix + ".stderr.log")).open("w") as err,
        ):
            child = subprocess.Popen(
                args,
                cwd=ROOT / directory,
                env=env,
                stdout=out,
                stderr=err,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            pids.append(child.pid)
    for _ in range(40):
        try:
            statuses = [
                httpx.get(
                    f"http://127.0.0.1:{api}/api/v1/health/live", timeout=5
                ).status_code,
                httpx.get(
                    f"http://127.0.0.1:{api}/api/v1/public/products", timeout=10
                ).status_code,
                httpx.get(f"http://127.0.0.1:{web}/", timeout=15).status_code,
                httpx.get(f"http://127.0.0.1:{web}/shop", timeout=15).status_code,
                httpx.get(f"http://127.0.0.1:{web}/cart", timeout=15).status_code,
            ]
            if statuses == [200] * 5:
                print(
                    f"App http://localhost:{web}; API http://127.0.0.1:{api}; health/catalog/home/shop/cart all 200; process IDs {pids}; logs {suffix}.*.log"
                )
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    raise RuntimeError("Local startup incomplete; inspect only the new task51 logs")


if __name__ == "__main__":
    main()
