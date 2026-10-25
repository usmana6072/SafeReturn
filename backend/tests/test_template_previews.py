"""Synthetic PDF/asset tests; mocked process/admission are not OS or PG evidence."""

import hashlib
import io
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import fitz
import pytest
import zxingcpp
from PIL import Image
from print_fixture import bundle
from pypdf import PdfReader
from test_print_templates import BASE, RID, TID, content, revision
from test_print_templates import env as _env
from test_print_templates import verifier as _verifier

from app.core import template_preview as preview_core
from app.core.config import Settings
from app.core.print_render import PrintUnavailable, load_bundle

env = _env
verifier = _verifier


@pytest.fixture
def synthetic_assets(tmp_path):
    source = load_bundle(Settings(_env_file=None, **bundle(tmp_path / "bundle.json")))
    assets = {}
    for name in ("font", "logo"):
        target = tmp_path / ("font.ttf" if name == "font" else "logo.svg")
        shutil.copyfile(source[name]["path"], target)
        assets[name] = {"path": str(target), "sha256": source[name]["sha256"]}
    return {
        "key": "synthetic-key",
        "version": 1,
        "purpose": "lost",
        "content": content(),
        "assets": assets,
    }, str(tmp_path)


def test_real_synthetic_renderer_private_bounded_and_fixed_token(synthetic_assets):
    spec, root = synthetic_assets
    data = preview_core.render_synthetic(spec, root)
    pdf = PdfReader(io.BytesIO(data))
    assert len(pdf.pages) == 1 and len(data) < preview_core.MAX_OUTPUT
    text = pdf.pages[0].extract_text()
    assert "SYNTHETIC TEST - NOT APPROVED FOR PRODUCTION" in text
    assert "Synthetic Lost" in text and "PRIVATE_CANARY" not in text
    assert "activation" not in text.lower()
    with fitz.open(stream=data, filetype="pdf") as document:
        pix = document[0].get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        assert [value.text for value in zxingcpp.read_barcodes(image)] == [
            "https://preview.invalid/q/" + "S" * 43
        ]


@pytest.mark.parametrize("case", ["outside", "remote", "hash", "oversize", "markup"])
def test_preview_rejects_unsafe_registry_assets(synthetic_assets, case):
    spec, root = synthetic_assets
    if case == "outside":
        spec["assets"]["font"]["path"] = str(Path(root).parent / "outside.ttf")
    elif case == "remote":
        spec["assets"]["font"]["path"] = "https://evil.test/font.ttf"
    elif case == "hash":
        spec["assets"]["font"]["sha256"] = "0" * 64
    elif case == "oversize":
        Path(spec["assets"]["font"]["path"]).write_bytes(b"x" * 5_000_001)
    else:
        data = b'<svg xmlns="http://www.w3.org/2000/svg"><script>PRIVATE_CANARY</script></svg>'
        Path(spec["assets"]["logo"]["path"]).write_bytes(data)
        spec["assets"]["logo"]["sha256"] = hashlib.sha256(data).hexdigest()
    with pytest.raises((PrintUnavailable, OSError, ValueError)):
        preview_core.render_synthetic(spec, root)


def test_preview_http_and_qa_submission_real_orchestration(
    env, synthetic_assets, monkeypatch
):
    client, db, headers, settings = env
    # Scripted HTTP orchestration only; this is not real OS isolation acceptance.
    monkeypatch.setattr("app.api.v1.print_templates.PREVIEW_PLATFORM_SUPPORTED", True)
    spec, root = synthetic_assets
    db.preview_spec = spec
    settings.print_template_asset_root = root
    calls = []

    def isolated(spec, root):
        calls.append(True)
        return preview_core.render_synthetic(spec, root)

    monkeypatch.setattr("app.api.v1.print_templates.isolated_preview", isolated)
    path = BASE + f"/{TID}/revisions/{RID}"
    response = client.post(
        path + "/preview", json={"expected_revision": 1}, headers=headers()
    )
    assert response.status_code == 200, response.text[:300]
    assert response.headers["content-type"] == "application/pdf"
    assert len(response.headers["x-template-fingerprint"]) == 64
    assert "location" not in response.headers and "set-cookie" not in response.headers
    assert "private, no-store" == response.headers["cache-control"]
    assert len(PdfReader(io.BytesIO(response.content)).pages) == 1
    assert not db.receipts
    pending = revision() | {
        "status": "pending_qa",
        "row_version": 2,
        "fingerprint_sha256": response.headers["x-template-fingerprint"],
    }
    db.helper_result = {
        "revision": pending,
        "validation_status": "needs_independent_physical_qa",
    }
    first = client.post(
        path + "/submit-qa",
        json={"reason": "Submit synthetic proof"},
        headers=headers(),
    )
    assert first.status_code == 200, first.text
    assert db.helper_calls[-1][0] == "submit"
    assert db.helper_calls[-1][1]["proof_content"] == content()
    assert (
        db.helper_calls[-1][1]["proof_fingerprint"]
        == response.headers["x-template-fingerprint"]
    )
    replay = client.post(
        path + "/submit-qa",
        json={"reason": "Submit synthetic proof"},
        headers=headers(),
    )
    assert replay.json() == first.json() and len(calls) == 2
    assert db.admissions == 2


@pytest.mark.parametrize(
    "admission,status",
    [("RATE_LIMITED", 429), ("FORBIDDEN", 403), ("IDEMPOTENCY_KEY_REUSED", 409)],
)
def test_admission_blocks_before_renderer(
    env, synthetic_assets, monkeypatch, admission, status
):
    client, db, headers, settings = env
    monkeypatch.setattr("app.api.v1.print_templates.PREVIEW_PLATFORM_SUPPORTED", True)
    db.preview_spec, settings.print_template_asset_root = synthetic_assets
    db.admission = admission
    monkeypatch.setattr(
        "app.api.v1.print_templates.isolated_preview",
        lambda *a: pytest.fail("renderer must not run"),
    )
    response = client.post(
        BASE + f"/{TID}/revisions/{RID}/preview",
        json={"expected_revision": 1},
        headers=headers(),
    )
    assert response.status_code == status


def test_isolation_no_silent_windows_fallback(synthetic_assets, monkeypatch):
    spec, root = synthetic_assets
    monkeypatch.setattr(
        preview_core,
        "sys",
        SimpleNamespace(platform="win32", executable=sys.executable),
    )
    with pytest.raises(PrintUnavailable, match="preview_isolation_unavailable"):
        preview_core.isolated_preview(spec, root)


def test_timeout_kills_worker_releases_capacity_and_scrubs_env(
    synthetic_assets, monkeypatch
):
    spec, root = synthetic_assets
    monkeypatch.setattr(
        preview_core,
        "sys",
        SimpleNamespace(platform="linux", executable=sys.executable),
    )
    process = SimpleNamespace(killed=False, count=0)

    def communicate(data=None, timeout=None):
        process.count += 1
        if timeout:
            assert timeout == 60
            raise subprocess.TimeoutExpired("synthetic", timeout)
        return b"", None

    process.communicate = communicate
    process.kill = lambda: setattr(process, "killed", True)

    def popen(args, **kwargs):
        assert args[1] == "-I"
        assert set(kwargs["env"]) == {"PATH", "LANG"}
        return process

    monkeypatch.setattr(preview_core.subprocess, "Popen", popen)
    with pytest.raises(PrintUnavailable, match="preview_timeout"):
        preview_core.isolated_preview(spec, root)
    assert process.killed and process.count == 2
    assert preview_core.CAPACITY.acquire(blocking=False)
    preview_core.CAPACITY.release()

def test_unsupported_preview_isolation_rejected_before_admission(env, monkeypatch):
    client, db, headers, settings = env
    settings.print_template_asset_root = 'configured-test-root'
    monkeypatch.setattr('app.api.v1.print_templates.PREVIEW_PLATFORM_SUPPORTED', False)
    response = client.post(BASE + f'/{TID}/revisions/{RID}/preview', json={'expected_revision':1}, headers=headers())
    assert response.status_code == 503
    assert response.json()['error']['code'] == 'PREVIEW_ISOLATION_UNAVAILABLE'
    assert db.admissions == 0
