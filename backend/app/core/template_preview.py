"""Private synthetic proof pipeline, with no order/token/provider input."""

import json
import os
import subprocess
import sys
import threading
from pathlib import Path

from app.core.print_render import (
    PrintUnavailable,
    asset_bytes,
    checked_logo,
    render_pdf,
)
from app.core.template_content import Content

CAPACITY = threading.BoundedSemaphore(1)
MAX_OUTPUT = 2 * 1024 * 1024
PREVIEW_WALL_TIMEOUT_SECONDS = 60


def checked_assets(assets, root):
    """Only pre-enrolled immutable local assets; caller paths never reach this API."""
    if not root:
        raise PrintUnavailable("asset_registry_unavailable")
    base = Path(root)
    if (
        not base.is_absolute()
        or not base.is_dir()
        or any(
            part.is_symlink() or part.is_junction() for part in (base, *base.parents)
        )
    ):
        raise PrintUnavailable("asset_registry_unavailable")
    base = base.resolve(strict=True)
    result = {}
    for name in ("font", "logo"):
        entry = assets[name]
        p = Path(entry["path"])
        if not p.is_absolute() or len(str(p)) > 2048:
            raise PrintUnavailable("unsafe_asset")
        # Refuse symlinks/reparse points in every component, including outside-root aliases.
        if any(part.is_symlink() or part.is_junction() for part in (p, *p.parents)):
            raise PrintUnavailable("unsafe_asset")
        resolved = p.resolve(strict=True)
        if not resolved.is_relative_to(base) or not resolved.is_file():
            raise PrintUnavailable("unsafe_asset")
        if resolved.stat().st_size > 5_000_000:
            raise PrintUnavailable("unsafe_asset")
        result[name] = {"path": str(resolved), "sha256": entry["sha256"]}
    return result


def render_synthetic(spec, root):
    """Runs in the restricted worker, also usable for offline synthetic verification."""
    content = Content.model_validate(spec["content"])
    assets = checked_assets(spec["assets"], root)
    # Validate the strict SVG subset before ReportLab receives it.
    checked_logo(asset_bytes(assets["logo"]))
    t = content.renderer_template(spec["key"], spec["version"], spec["purpose"])
    manifest = {
        "renderer": "safereturn-vector-v1",
        "approval_ref": "SYNTHETIC-NOT-FOR-PRODUCTION",
        **assets,
        "occurrences": [
            {
                "use_id": "synthetic",
                "qr_id": "synthetic",
                "copies": 1,
                "template": t.model_dump(),
                "url": "https://preview.invalid/q/" + "S" * 43,
            }
        ],
    }
    data, _ = render_pdf(manifest)
    if len(data) > MAX_OUTPUT:
        raise PrintUnavailable("preview_too_large")
    return data


def isolated_preview(spec, root):
    # Linux resource limits are required, never silently replaced by a thread timeout.
    # Windows currently fails closed until an equivalent OS sandbox is provided.
    if sys.platform != "linux" or not root:
        raise PrintUnavailable("preview_isolation_unavailable")
    checked_assets(spec["assets"], root)
    if not CAPACITY.acquire(blocking=False):
        raise PrintUnavailable("preview_busy")
    try:
        wire = json.dumps({"spec": spec, "root": root}, separators=(",", ":")).encode()
        if len(wire) > 32768:
            raise PrintUnavailable("preview_input_too_large")
        worker = Path(__file__).with_name("template_preview_worker.py")
        # -I ignores PYTHON* variables/user site; no Auth/provider credentials inherited.
        process = subprocess.Popen(
            [sys.executable, "-I", str(worker)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env={"PATH": os.defpath, "LANG": "C.UTF-8"},
        )
        try:
            # Throttled hosts need wall time beyond the unchanged five CPU seconds.
            data, _ = process.communicate(wire, timeout=PREVIEW_WALL_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise PrintUnavailable("preview_timeout") from None
        if (
            process.returncode != 0
            or not data.startswith(b"%PDF-")
            or len(data) > MAX_OUTPUT
        ):
            raise PrintUnavailable("preview_failed")
        return data
    except OSError:
        raise PrintUnavailable("preview_failed") from None
    finally:
        CAPACITY.release()
