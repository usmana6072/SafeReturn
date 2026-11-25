"""Auto-delete print artifacts and tombstone print jobs upon verified shipment delivery."""

from pathlib import Path

from alembic import op

revision = "0061_delivery_print_cleanup"
down_revision = "0060_owner_role"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError("Preserve delivery retention cleanup history; forward migration only")
