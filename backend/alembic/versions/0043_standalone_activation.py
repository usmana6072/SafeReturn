"""Purchaser-only, delivered standalone activation; rollout remains closed."""

from pathlib import Path

from alembic import op

revision = "0043_standalone_activation"
down_revision = "0042_typed_print_fulfillment"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError("Independent ownership and activation history must be preserved")
