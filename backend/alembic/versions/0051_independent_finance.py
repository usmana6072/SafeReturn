"""Unreleased independent-only finance helpers; no API grants or rollout."""

from pathlib import Path

from alembic import op

revision = "0051_independent_finance"
down_revision = "0050_public_catalog_browsing"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError("Independent finance requires a reviewed forward change")
