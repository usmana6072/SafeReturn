"""Temporary single-origin HTTPS testing. No services installed or env files edited."""
import argparse
import hashlib
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx
from dotenv import dotenv_values
from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import PlainTextResponse, StreamingResponse
from starlette.routing import Route

ROOT = Path(__file__).resolve().parents[1]
HOP = {b"connection", b"keep-alive", b"proxy-authenticate", b"proxy-authorization",
       b"te", b"trailer", b"transfer-encoding", b"upgrade"}


def gateway(origin, api, web):
    """Fixed upstreams only; validate Host and replace untrusted forwarding headers."""
    hostname = origin.removeprefix("https://")

    async def relay(request: Request):
        if request.headers.get("host") != hostname:
            return PlainTextResponse("Invalid host", status_code=400)
        path = request.url.path
        if any(part.startswith(".") for part in path.split("/") if part) or path.endswith(".map"):
            return PlainTextResponse("Not found", status_code=404)
        upstream = api if path.startswith("/api/") or path == "/api" else web
        # No arbitrary destination/header-controlled proxying, logs or caching.
        headers = [(k, v) for k, v in request.headers.raw
                   if k.lower() not in HOP and not k.lower().startswith(b"x-forwarded-")
                   and k.lower() not in {b"host", b"forwarded", b"cf-connecting-ip", b"cf-access-jwt-assertion"}]
        headers += [(b"host", hostname.encode()), (b"x-forwarded-host", hostname.encode()),
                    (b"x-forwarded-proto", b"https")]
        client = httpx.AsyncClient(timeout=httpx.Timeout(60, connect=5), follow_redirects=False)
        try:
            target = f"http://127.0.0.1:{upstream}" + path
            if request.url.query:
                target += "?" + request.url.query
            response = await client.send(client.build_request(request.method, target,
                                        headers=headers, content=request.stream()), stream=True)
        except httpx.HTTPError:
            await client.aclose()
            return PlainTextResponse("Local service unavailable", status_code=502)

        async def close():
            await response.aclose()
            await client.aclose()

        result = StreamingResponse(response.aiter_raw(), status_code=response.status_code,
                                   background=BackgroundTask(close))
        result.raw_headers = [(k, v) for k, v in response.headers.raw
                              if k.lower() not in HOP and k.lower() != b"cache-control"]
        result.raw_headers += [(b"cache-control", b"private, no-store"),
                               (b"x-content-type-options", b"nosniff")]
        return result

    return Starlette(routes=[Route("/{path:path}", relay,
                      methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])])


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, help="Reuse an already tested isolated Next production build")
    parser.add_argument("--stop", action="store_true", help="Ask the most recent owned mobile run to stop")
    args = parser.parse_args()
    if args.stop:
        state_file = ROOT / "tmp/mobile-test-current.json"
        if not state_file.exists():
            raise SystemExit("No mobile testing run recorded")
        run = Path(json.loads(state_file.read_text())["run"]).resolve()
        if not run.is_relative_to(ROOT / "tmp") or not run.name.startswith("mobile-test-"):
            raise SystemExit("Invalid run directory")
        (run / "stop.request").touch()
        print("Stop requested for the most recent mobile run; existing localhost services are unaffected.")
        return
    cloudflared = shutil.which("cloudflared") or str(ROOT / "tmp/local-tools/cloudflared.exe")
    if not Path(cloudflared).is_file():
        raise SystemExit("cloudflared missing. Install official binary with permission first.")
    if Path(cloudflared) == ROOT / "tmp/local-tools/cloudflared.exe":
        manifest = ROOT / "tmp/local-tools/cloudflared-release.json"
        if not manifest.exists() or hashlib.sha256(Path(cloudflared).read_bytes()).hexdigest() != json.loads(manifest.read_text())["sha256"]:
            raise SystemExit("Project-local cloudflared is incomplete or its verified checksum differs")
    run = ROOT / "tmp" / ("mobile-test-" + uuid.uuid4().hex)
    run.mkdir(parents=True)
    print(f"Runtime artifacts: {run}", flush=True)
    base = {k: v for k, v in os.environ.items() if not k.startswith("SAFERETURN_")}
    backend = {k: v for k, v in dotenv_values(ROOT / "backend/.env").items() if v is not None}
    frontend = dotenv_values(ROOT / "frontend/.env.local")
    web_env = dict(base, NEXT_TELEMETRY_DISABLED="1", NODE_ENV="production")
    for key in ("SAFERETURN_SUPABASE_URL", "SAFERETURN_SUPABASE_PUBLISHABLE_KEY", "SAFERETURN_SESSION_SIGNING_KEY"):
        value = frontend.get(key) or backend.get(key)
        if not value:
            raise SystemExit("Required configured authentication value missing; no secrets printed")
        web_env[key] = value
    node = shutil.which("node")
    if args.build_dir:
        build = args.build_dir.resolve()
        if not build.is_relative_to(ROOT / "tmp") or not (build / ".next/BUILD_ID").is_file():
            raise SystemExit("Reuse requires an existing isolated production build beneath project tmp")
    else:
        build = run / "web"
        build.mkdir()
        for name in ("app", "components", "lib", "messages", "public"):
            source = ROOT / "frontend" / name
            if source.exists():
                shutil.copytree(source, build / name)
        for name in ("package.json", "package-lock.json", "tsconfig.json", "next-env.d.ts", "postcss.config.mjs", "proxy.ts"):
            source = ROOT / "frontend" / name
            if source.exists():
                shutil.copy2(source, build / name)
        subprocess.run(["cmd", "/c", "mklink", "/J", str(build / "node_modules"),
                        str(ROOT / "frontend/node_modules")], check=True, capture_output=True)
        (build / "next.config.mjs").write_text("export default " + json.dumps({"turbopack": {"root": str(ROOT)}}) + ";")
        with (run / "build.log").open("w", encoding="utf-8") as log:
            result = subprocess.run([node, str(ROOT / "frontend/node_modules/next/dist/bin/next"),
                                     "build", "--webpack"], cwd=build, env=web_env, stdout=log, stderr=log, check=False)
        if result.returncode:
            raise SystemExit(f"Isolated build failed; inspect {run / 'build.log'}")
    ports = set()
    while len(ports) < 3:
        ports.add(free_port())
    api, web, proxy = ports
    processes = []
    files = []

    def spawn(command, name, cwd=ROOT, env=base):
        log = (run / (name + ".log")).open("w", encoding="utf-8")
        files.append(log)
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=log,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        processes.append(process)
        return process

    try:
        spawn([cloudflared, "tunnel", "--no-autoupdate", "--protocol", "http2", "--url",
               f"http://127.0.0.1:{proxy}"], "tunnel")
        origin = None
        for _ in range(90):
            found = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", (run / "tunnel.log").read_text(errors="replace"))
            if found:
                origin = found.group()
                break
            if processes[0].poll() is not None:
                break
            time.sleep(1)
        if not origin:
            raise RuntimeError(f"Quick Tunnel URL not allocated; inspect {run / 'tunnel.log'}")
        web_env.update(SAFERETURN_API_ORIGIN=f"http://127.0.0.1:{api}", SAFERETURN_WEB_ORIGIN=origin)
        # Process-only transport origin; never persist or change existing configured settings.
        api_env = {**base, **backend, "SAFERETURN_PRIVACY_EXPORT_WEB_ORIGIN": origin}
        for key in ("SAFERETURN_MIGRATION_DATABASE_URL", "SAFERETURN_WORKER_DATABASE_URL"):
            api_env.pop(key, None)
        spawn([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
               "--port", str(api), "--no-access-log", "--no-proxy-headers"], "api", ROOT / "backend", api_env)
        spawn([node, str(ROOT / "frontend/node_modules/next/dist/bin/next"), "start", "--hostname",
               "127.0.0.1", "--port", str(web)], "frontend", build, web_env)
        (run / "gateway.json").write_text(json.dumps({"origin": origin, "api": api, "web": web}))
        spawn([sys.executable, str(Path(__file__).resolve()), "gateway", str(run / "gateway.json"), str(proxy)], "gateway")
        state = {"url": origin, "pid": os.getpid(), "child_pids": [p.pid for p in processes], "build": str(build), "run": str(run)}
        (run / "state.json").write_text(json.dumps(state, indent=2))
        (ROOT / "tmp/mobile-test-current.json").write_text(json.dumps(state, indent=2))
        # A few ISP resolvers negatively cache newly allocated tunnel names.
        # Resolve only this verification process through public DoH if needed;
        # do not change Windows, browser, application or Supabase DNS settings.
        hostname = origin.removeprefix("https://")
        resolver = socket.getaddrinfo
        dns_address = None
        try:
            resolver(hostname, 443)
        except socket.gaierror:
            answer = httpx.get("https://cloudflare-dns.com/dns-query",
                               params={"name": hostname, "type": "A"},
                               headers={"Accept": "application/dns-json"}, timeout=20)
            answer.raise_for_status()
            dns_address = next(str(ipaddress.IPv4Address(row["data"]))
                               for row in answer.json().get("Answer", []) if row.get("type") == 1)

            def verification_resolver(host, port, *args, **kwargs):
                return resolver(dns_address if host in (hostname, hostname.encode()) else host,
                                port, *args, **kwargs)

            socket.getaddrinfo = verification_resolver
            print("Local DNS cannot yet resolve this new hostname; HTTPS verification uses process-only public DNS. "
                  "TLS hostname checks remain enabled. No Windows settings changed.", flush=True)
        with httpx.Client(timeout=20, follow_redirects=False) as client:
            for attempt in range(45):
                try:
                    home = client.get(origin + "/")
                    health = client.get(origin + "/api/v1/health/live")
                    if home.status_code == 200 and health.status_code == 200 and health.json() == {"status": "ok"}:
                        break
                except (httpx.HTTPError, ValueError):
                    pass
                time.sleep(2)
            else:
                raise RuntimeError(f"Public frontend/API verification failed; inspect logs in {run}")
            denied = client.get(origin + "/api/v1/me/staff-security")
            private = client.get(origin + "/.env")
            assert denied.status_code == 401 and private.status_code == 404
            (run / "verification.json").write_text(json.dumps({"url": origin, "home": home.status_code,
                "health": health.json(), "anonymous_staff": denied.status_code, "private_file": private.status_code,
                "dns_mode": "process-only public DNS" if dns_address else "Windows default DNS",
                "dns_address": dns_address}, indent=2))
        socket.getaddrinfo = resolver
        print(f"VERIFIED MOBILE URL: {origin}\nKeep this process running. Ctrl+C stops only these owned services.\n"
              f"Email callback (development Supabase only): {origin}/auth/callback", flush=True)
        while all(p.poll() is None for p in processes):
            if (run / "stop.request").exists():
                print("Stopping temporary mobile services.", flush=True)
                return
            time.sleep(1)
        raise RuntimeError(f"A service exited; inspect logs in {run}")
    except KeyboardInterrupt:
        print("Stopping temporary mobile services.", flush=True)
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                if os.name == "nt":
                    # Windows venv launchers can own a second Python process.
                    # Stop the owned tree so its server does not remain listening.
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                   capture_output=True, check=False)
                else:
                    process.terminate()
        for process in processes:
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
        for log in files:
            log.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "gateway":
        import uvicorn
        configuration = json.loads(Path(sys.argv[2]).read_text())
        uvicorn.run(gateway(**configuration), host="127.0.0.1", port=int(sys.argv[3]),
                    access_log=False, proxy_headers=False)
    else:
        main()
