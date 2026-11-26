"""Align template database validation with the current compact geometry contract."""

from pathlib import Path

from alembic import op

revision = "0062_template_geometry_minimums"
down_revision = "0061_delivery_print_cleanup"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError(
        "Preserve template validation history; use a reviewed forward migration"
    )
