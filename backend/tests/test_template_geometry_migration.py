from pathlib import Path

from app.core.template_content import Content


def test_forward_migration_aligns_database_geometry_minimums():
    root = Path(__file__).parents[1]
    migration = root / "alembic/versions/0062_template_geometry_minimums"
    assert (
        'down_revision = "0061_delivery_print_cleanup"'
        in migration.with_suffix(".py").read_text()
    )
    sql = migration.with_suffix(".sql").read_text()
    assert "CREATE OR REPLACE FUNCTION public.sr_template_content_valid(c jsonb)" in sql
    assert "NOT BETWEEN 20 AND 100" in sql
    assert "NOT BETWEEN 30 AND 190" in sql
    assert "NOT BETWEEN 50 AND 270" in sql
    assert "(c->>'qr_y_mm')::numeric<13" in sql
    assert (
        "(c->>'qr_x_mm')::numeric+(c->>'symbol_mm')::numeric>"
        "(c->>'width_mm')::numeric-4"
    ) in sql
    assert (
        "(c->>'qr_y_mm')::numeric+(c->>'symbol_mm')::numeric>"
        "(c->>'height_mm')::numeric-12"
    ) in sql
    assert "NOT BETWEEN 30 AND 100" not in sql
    assert "NOT BETWEEN 40 AND 190" not in sql
    assert "NOT BETWEEN 60 AND 270" not in sql
    assert "(c->>'qr_y_mm')::numeric<18" not in sql


def test_reported_compact_design_passes_api_content_contract():
    content = {
        "schema_version": 1,
        "renderer": "safereturn-vector-v1",
        "preset": "fixed-footer-v1",
        "symbol_mm": "25.00",
        "width_mm": "35.00",
        "height_mm": "50.00",
        "qr_x_mm": "5.00",
        "qr_y_mm": "13.00",
        "logo_mm": "3.50",
        "min_pitch_mm": "0.30",
        "font_pt": "8.00",
        "header": "SafeReturn",
        "english_lines": ["SCAN TO CONTACT THE OWNER"],
        "urdu_lines": ["مالک سے رابطہ کرنے کے لیے اسکین کریں"],
        "asset_set_id": "0a7c508b-fc96-42d6-ba58-e367dbb8d08b",
        "material_codes": ["vinyl"],
    }

    validated = Content.model_validate(content)

    assert validated.width_mm == "35.00"
    assert validated.height_mm == "50.00"
    assert validated.qr_y_mm == "13.00"
