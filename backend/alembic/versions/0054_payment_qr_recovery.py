"""Repair automatic typed QR inventory for verified payments."""

from pathlib import Path

from alembic import op

revision = "0054_payment_qr_recovery"
down_revision = "0053_payment_qr_autogeneration"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError("Payment QR recovery requires a reviewed forward change")
