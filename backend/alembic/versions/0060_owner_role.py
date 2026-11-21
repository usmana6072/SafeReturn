"""Owner authorization without assigning any account or enabling demo data."""

from pathlib import Path

from alembic import op

revision = "0060_owner_role"
down_revision = "0059_shipment_delivery_email"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError("Preserve role grant history; use a reviewed forward migration")
