"""Expose encrypted finder details only to the worker holding the notification lease."""

from pathlib import Path

from alembic import op

revision = "0058_finder_email_details"
down_revision = "0057_downloaded_print_shipping"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    op.execute("DROP FUNCTION public.sr_notification_finder_details(uuid,integer)")
