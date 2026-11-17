"""Allow a verified purchaser to activate after their print PDF is ready."""

from pathlib import Path

from alembic import op

revision = "0055_print_ready_activation"
down_revision = "0054_payment_qr_recovery"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError("Print-ready activation requires a reviewed forward change")
