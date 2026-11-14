"""Product-level PKR copy pricing; legacy snapshots and identities preserved."""

from pathlib import Path

from alembic import op

revision = "0036_product_copy_pricing"
down_revision = "0035_public_abuse_intake"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError("Copy pricing is forward-only; preserve purchase history")
