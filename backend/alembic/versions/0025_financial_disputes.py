"""Owner-approved case-scoped review; refunds and fence removal disabled."""

from pathlib import Path

from alembic import op

revision = "0025_financial_disputes"
down_revision = "0024_order_cancellations"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='5s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError(
        "Preserve financial decisions/fences; transactional DDL rollback only"
    )
