"""Typed frozen printing and complete item shipment membership; source only."""

from pathlib import Path

from alembic import op

revision = "0042_typed_print_fulfillment"
down_revision = "0041_verified_qr_allocation"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError("Frozen print and shipment history must be preserved")
