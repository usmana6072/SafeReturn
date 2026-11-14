"""Task 5.2A saved addresses; additive, never rewrite purchase snapshots."""

from pathlib import Path

from alembic import op

revision = "0023_saved_shipping_addresses"
down_revision = "0022_privacy_exports"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='5s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError("Preserve saved addresses; transactional DDL rollback only")
