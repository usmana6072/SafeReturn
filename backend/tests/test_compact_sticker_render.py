import json
from pathlib import Path

import fitz
import pytest

from app.core.print_render import PrintUnavailable
from app.core.template_preview import render_synthetic

ROOT = Path(__file__).parents[1] / "print-assets"
MANIFEST = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))


def compact(english, urdu):
    return {
        "schema_version": 1,
        "renderer": "safereturn-vector-v1",
        "preset": "qr-only-v3",
        "symbol_mm": "15.00",
        "width_mm": "25.00",
        "height_mm": "20.00",
        "qr_x_mm": "5.00",
        "qr_y_mm": "4.26",
        "logo_mm": "2.00",
        "min_pitch_mm": "0.30",
        "font_pt": "5.00",
        "header": "SafeReturn",
        "english_lines": english,
        "urdu_lines": urdu,
        "asset_set_id": MANIFEST["candidate_asset_set_id"],
        "material_codes": ["vinyl"],
    }


def spec(english, urdu):
    logo_name = MANIFEST["candidate_logo_file"]
    return {
        "content": compact(english, urdu),
        "key": "compact-minimum",
        "version": 1,
        "purpose": "lost",
        "assets": {
            "font": {
                "path": str(ROOT / "Amiri-Regular.ttf"),
                "sha256": MANIFEST["files"]["Amiri-Regular.ttf"],
            },
            "logo": {
                "path": str(ROOT / logo_name),
                "sha256": MANIFEST["files"][logo_name],
            },
        },
    }


@pytest.mark.parametrize(
    "english,urdu",
    [([], []), (["SCAN TO CONTACT OWNER"], []), ([], ["مالک سے رابطے کے لیے اسکین کریں"]),
     (["SCAN TO CONTACT OWNER"], ["مالک سے رابطے کے لیے اسکین کریں"])],
)
def test_minimum_sticker_pdf_keeps_physical_geometry_and_shapes_urdu(english, urdu):
    pdf = render_synthetic(spec(english, urdu), str(ROOT))
    document = fitz.open(stream=pdf, filetype="pdf")
    drawings = document[0].get_drawings()
    dimensions = [
        (round(d["rect"].width / 72 * 25.4, 2), round(d["rect"].height / 72 * 25.4, 2))
        for d in drawings
        if d["type"] in {"s", "f"} and d["rect"].width > 30
    ]
    assert (25.0, 20.0) in dimensions
    assert (15.0, 15.0) in dimensions
    assert document.page_count == 1
    assert pdf.startswith(b"%PDF-")


def test_minimum_sticker_rejects_caption_that_cannot_fit_physical_width():
    with pytest.raises(PrintUnavailable, match="caption_overflow"):
        render_synthetic(spec(["W" * 120], []), str(ROOT))


def test_minimum_sticker_rejects_urdu_caption_that_cannot_fit_physical_width():
    with pytest.raises(PrintUnavailable, match="caption_overflow"):
        render_synthetic(spec([], ["مالک " * 12]), str(ROOT))
