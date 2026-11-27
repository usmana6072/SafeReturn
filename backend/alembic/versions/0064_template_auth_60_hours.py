"""Extend the existing Print Template authentication freshness window."""

from pathlib import Path

from alembic import op

revision = "0064_template_auth_60_hours"
down_revision = "0063_template_optional_urdu_compact_clearance"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError(
        "Preserve the template authentication policy history; use a reviewed forward migration"
    )
