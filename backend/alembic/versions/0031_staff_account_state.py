"""Opt-in read only; no lifecycle/schema activation. Offline after pending0030."""

from pathlib import Path

from alembic import op

revision = "0031_staff_account_state"
down_revision = "0030_account_lifecycle"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    op.execute("DROP FUNCTION public.sr_staff_account_state(uuid,uuid)")
