"""Controlled local Next/API browser runtime; no provider calls or real users."""

import os
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import httpx
import uvicorn
from sqlalchemy import text
from test_identity_schema import pair


def run(sample, *, test_files=None, extra_env=None):
    pg, client, ids, tokens, _, _ = sample
    with pg.connect() as c:
        c.execute(
            text(
                "UPDATE public.ice_profiles SET display_name=NULL,blood_group=NULL WHERE qr_id=:id"
            ),
            {"id": ids["ice"]},
        )
        c.execute(
            text(
                "UPDATE public.lost_item_profiles SET description=:text WHERE qr_id=:id"
            ),
            {"id": ids["lost"], "text": "<script>window.scanInjected=true</script>"},
        )
        for status in ("unactivated", "owner_disabled", "admin_suspended", "revoked"):
            pid, tags = pair(c)
            c.execute(
                text(
                    "UPDATE public.qr_codes SET public_status=CAST(:s AS varchar),revoked_at=CASE WHEN CAST(:s AS varchar)='revoked' THEN now() END WHERE pair_id=:id"
                ),
                {"s": status, "id": pid},
            )
            tokens[status] = c.execute(
                text("SELECT public_token FROM public.qr_codes WHERE id=:id"),
                {"id": tags["lost"]},
            ).scalar_one()
        c.commit()
    for port in (8115, 3100):
        with socket.socket() as probe:
            assert probe.connect_ex(("127.0.0.1", port)) != 0, (
                "Isolated browser port is occupied"
            )
    root = Path(__file__).parents[3]
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("SAFERETURN_", "QR_TEST_", "PUBLIC_QR_"))
    }
    env.update(extra_env or {})
    env.update(
        {
            "SAFERETURN_API_ORIGIN": "http://127.0.0.1:8115",
            "SAFERETURN_WEB_ORIGIN": "http://127.0.0.1:3100",
            "NEXT_TELEMETRY_DISABLED": "1",
            "PLAYWRIGHT_EXTERNAL_SERVER": "1",
            "PLAYWRIGHT_CHANNEL": "msedge",
        }
    )
    server = uvicorn.Server(
        uvicorn.Config(
            client.application,
            host="127.0.0.1",
            port=8115,
            lifespan="off",
            access_log=False,
            log_level="error",
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    process = None
    thread.start()
    try:
        process = subprocess.Popen(
            [
                shutil.which("node"),
                "--require",
                "./tests/qr-fixture-fetch.cjs",
                "node_modules/next/dist/bin/next",
                "start",
                "--hostname",
                "127.0.0.1",
                "--port",
                "3100",
            ],
            cwd=root / "frontend",
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        for _ in range(20):
            try:
                if (
                    httpx.get(
                        "http://127.0.0.1:3100/q/" + "unknown" * 5, timeout=10
                    ).status_code
                    == 200
                ):
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.2)
        else:
            raise AssertionError("Isolated Next runtime did not start")
        result = subprocess.run(
            [
                shutil.which("npm.cmd" if os.name == "nt" else "npm"),
                "test",
                "--",
                *(test_files or ["tests/public-qr.spec.ts"]),
                "--workers=1",
            ],
            cwd=root / "frontend",
            env={**env, **{"PUBLIC_QR_" + k.upper(): v for k, v in tokens.items()}},
            timeout=300,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        print(result.stdout.encode("ascii", "backslashreplace").decode("ascii"))
        if result.returncode:
            print(result.stderr.encode("ascii", "backslashreplace").decode("ascii"))
        assert result.returncode == 0, "Public scan browser acceptance failed"
    finally:
        if process is not None:
            process.terminate()
            process.wait(timeout=15)
        server.should_exit = True
        thread.join(timeout=15)
