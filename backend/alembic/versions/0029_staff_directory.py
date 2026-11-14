"""Task 2.3C read-only metadata helper; offline rehearsal only."""

from pathlib import Path

from alembic import op

revision = "0029_staff_directory"
down_revision = "0028_dashboard_reads"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='5s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    op.execute(
        "DROP FUNCTION public.sr_staff_directory(uuid,text,uuid,boolean,text,integer,timestamptz,uuid)"
    )
