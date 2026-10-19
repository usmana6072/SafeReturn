"""Synthetic vector/geometry/Urdu/QR checks, never physical print approval."""

import io
from uuid import uuid4

import fitz
import pytest
import zxingcpp
from PIL import Image
from print_fixture import ROOT, bundle
from pypdf import PdfReader

from app.core.config import Settings
from app.core.print_render import (
    PrintUnavailable,
    build_manifest,
    load_bundle,
    render_pdf,
)


def manifest(tmp_path):
    b = load_bundle(Settings(**bundle(tmp_path / "bundle.json")))
    return build_manifest(
        b,
        [
            {
                "use_id": uuid4(),
                "qr_id": uuid4(),
                "tag_type": kind,
                "copies": copies,
                "size_mm": 35,
                "template_key": "synthetic",
                "template_version": 1,
                "public_token": token,
            }
            for kind, copies, token in [("lost", 3, "L" * 32), ("ice", 2, "I" * 32)]
        ],
    )


def test_vector_pdf_counts_quiet_zone_sizes_and_decoding(tmp_path):
    m = manifest(tmp_path)
    data, info = render_pdf(m)
    assert data == render_pdf(m)[0]
    assert (
        info["counts"] == {"lost": 3, "ice": 2}
        and [p["tag_type"] for p in info["placements"]] == ["lost"] * 3 + ["ice"] * 2
    )
    assert all(p["symbol_mm"] == 35 for p in info["placements"])
    assert len(data) < 1_000_000
    reader = PdfReader(io.BytesIO(data))
    assert not reader.is_encrypted
    assert len(reader.pages) == 1
    page = reader.pages[0]
    assert abs(float(page.mediabox.width) * 25.4 / 72 - 210) < 0.01
    assert not page.images
    pdf = fitz.open(stream=data, filetype="pdf")
    pix = pdf[0].get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    decoded = zxingcpp.read_barcodes(im)
    urls = [r.text for r in decoded]
    assert urls.count("https://print.example.test/q/" + "L" * 32) == 3, urls
    assert urls.count("https://print.example.test/q/" + "I" * 32) == 2, urls
    assert b"activation_secret" not in data
    out = ROOT / "output/pdf"
    out.mkdir(parents=True, exist_ok=True)
    (out / "task54-synthetic-labels.pdf").write_bytes(data)
    im.save(out / "task54-synthetic-labels.png")


def test_invalid_or_changed_assets_fail_closed(tmp_path):
    m = manifest(tmp_path)
    m["font"]["sha256"] = "0" * 64
    with pytest.raises(PrintUnavailable):
        render_pdf(m)


def test_template_overflow_is_blocked(tmp_path):
    m = manifest(tmp_path)
    m["occurrences"][0]["template"]["english_lines"] = ["Oversized caption " * 30]
    with pytest.raises(PrintUnavailable):
        render_pdf(m)
