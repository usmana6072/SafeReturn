"""Durable delivery confirmation email bound to the shipment's customer."""

from pathlib import Path

from alembic import op

revision = "0059_shipment_delivery_email"
down_revision = "0058_finder_email_details"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError("Preserve delivery event history; use a forward migration")
