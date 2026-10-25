"""Versioned standalone catalog and legacy customer checkout isolation."""

from pathlib import Path

from alembic import op

revision = "0039_single_qr_catalog"
down_revision = "0038_typed_inventory"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError("Preserve product and order history; roll forward")
