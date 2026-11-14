"""Approved count-only dashboard reads; unapplied after pending 0027."""

from pathlib import Path

from alembic import op

revision = "0028_dashboard_reads"
down_revision = "0027_manufacturing_exports"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='5s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    op.execute("DROP FUNCTION public.sr_dashboard_trend(text,timestamptz)")
    op.execute("DROP FUNCTION public.sr_dashboard_summary(text)")
