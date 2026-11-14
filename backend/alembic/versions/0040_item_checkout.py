"""Logical item checkout snapshots alongside preserved legacy purchases."""

from pathlib import Path

from alembic import op

revision = "0040_item_checkout"
down_revision = "0039_single_qr_catalog"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError("Preserve immutable purchases; roll forward")
