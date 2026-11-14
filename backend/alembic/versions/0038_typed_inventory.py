"""Narrow operations helpers for standalone generation and safe metadata reads."""

from pathlib import Path

from alembic import op

revision = "0038_typed_inventory"
down_revision = "0037_independent_qr_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError(
        "Preserve generated identity history and replay receipts; roll forward"
    )
