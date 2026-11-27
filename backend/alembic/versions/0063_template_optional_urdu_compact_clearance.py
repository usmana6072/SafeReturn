"""Allow optional Urdu copy and the compact 8 mm fixed-footer layout."""

from pathlib import Path

from alembic import op

revision = "0063_optional_urdu_compact"
down_revision = "0062_template_geometry_minimums"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError(
        "Preserve template validation history; use a reviewed forward migration"
    )
