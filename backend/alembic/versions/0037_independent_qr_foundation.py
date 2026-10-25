"""Additive standalone identity foundation; runtime admission remains closed."""

from pathlib import Path

from alembic import op

revision = "0037_independent_qr_foundation"
down_revision = "0036_product_copy_pricing"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError(
        "Preserve standalone identities and legacy history; roll forward"
    )
