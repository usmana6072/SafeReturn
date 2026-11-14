"""Approved application lifecycle/security fencing; offline only after pending0029."""

from pathlib import Path

from alembic import op

revision = "0030_account_lifecycle"
down_revision = "0029_staff_directory"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    # Security state may already have invalidated sessions and durable grants.
    # Forward-disable commands, retain enforcement; no downgrade revives sessions.
    raise RuntimeError(
        "Security history downgrade disabled; use reviewed forward correction"
    )
