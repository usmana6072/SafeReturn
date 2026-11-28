from pathlib import Path

from app.core.template_content import Content


def test_reported_compact_design_passes_api_content_contract():
    content = {
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
        "english_lines": ["SCAN TO CONTACT OWNER"],
        "urdu_lines": ["مالک سے رابطے کے لیے اسکین کریں"],
        "asset_set_id": "70af0cb0-0cef-4d3a-a24a-f3cb0c81d5e4",
        "material_codes": ["vinyl"],
    }

    validated = Content.model_validate(content)

    assert validated.width_mm == "25.00"
    assert validated.height_mm == "20.00"
    assert validated.symbol_mm == "15.00"
    assert validated.preset == "qr-only-v3"


def test_sticker_minimum_forward_migration_preserves_legacy_renderer_limits():
    root = Path(__file__).parents[1]
    migration = root / "alembic/versions/0065_sticker_minimums"
    assert 'down_revision = "0064_template_auth_60h"' in migration.with_suffix(".py").read_text()
    sql = migration.with_suffix(".sql").read_text()
    assert "'fixed-footer-v1','fixed-footer-v2','qr-only-v3'" in sql
    assert "CASE WHEN compact THEN 25 ELSE 30 END" in sql
    assert "CASE WHEN compact THEN 20 ELSE 50 END" in sql
    assert "CASE WHEN compact THEN 15 ELSE 20 END" in sql
    assert "BETWEEN 15 AND 100" in sql
    assert "size_mm_snapshot BETWEEN 15 AND 100" in sql
    assert "pg_get_functiondef(target)" in sql
