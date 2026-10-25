"""Independent cancellation reconciliation; never automatic payment/refund."""

from pathlib import Path

from alembic import op

revision = "0024_order_cancellations"
down_revision = "0023_saved_shipping_addresses"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='5s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError(
        "Preserve cancellation evidence; transactional DDL rollback only"
    )
