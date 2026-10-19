"""Explicitly synthetic locked template; never approved retail artwork."""

import hashlib
import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]


def bundle(path):
    font = Path(
        os.environ.get("SAFERETURN_TEST_URDU_FONT", "C:/Windows/Fonts/arial.ttf")
    )
    if not font.is_file():
        pytest.skip("A licensed Urdu test font must be configured")
    logo = ROOT / "frontend/public/brand/safereturn_logo.svg"
    assets = lambda p: {
        "path": str(p),
        "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
    }
    data = {
        "renderer": "safereturn-vector-v1",
        "approval_ref": "SYNTHETIC-NOT-FOR-PRODUCTION",
        "origin": "https://print.example.test",
        "font": assets(font),
        "logo": assets(logo),
        "templates": [],
    }
    for kind in ("lost", "ice"):
        data["templates"].append(
            {
                "key": "synthetic",
                "version": 1,
                "tag_type": kind,
                "symbol_mm": 35,
                "width_mm": 55,
                "height_mm": 80,
                "qr_x_mm": 10,
                "qr_y_mm": 30,
                "logo_mm": 4,
                "min_pitch_mm": 0.4,
                "font_pt": 9,
                "header": "SafeReturn " + kind.upper(),
                "english_lines": ["Found this item?", "Scan to contact its owner."]
                if kind == "lost"
                else ["Emergency information", "Scan to view shared details."],
                "urdu_lines": ["مالک سے رابطے کے لیے", "اسکین کریں"]
                if kind == "lost"
                else ["ایمرجنسی معلومات کے لیے", "اسکین کریں"],
            }
        )
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return {
        "print_enabled": True,
        "print_template_bundle_path": str(path),
        "print_template_bundle_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
