"""Use typed packing checks for standalone orders at shipment commit."""

from pathlib import Path

from alembic import op

revision = "0056_typed_shipment_lifecycle"
down_revision = "0055_print_ready_activation"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix('.sql').read_text(encoding='utf-8'))


def downgrade():
    raise RuntimeError("Typed shipment lifecycle requires a reviewed forward change")
