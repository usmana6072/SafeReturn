"""Verified typed settlement and permanent, all-or-nothing item QR claims."""

from pathlib import Path

from alembic import op

revision = "0041_verified_qr_allocation"
down_revision = "0040_item_checkout"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError("Permanent paid claims and settlement history must be preserved")
