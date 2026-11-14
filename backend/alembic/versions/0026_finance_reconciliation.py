"""Approved read-only reconciliation helpers; no payment or historical backfill."""

from pathlib import Path

from alembic import op

revision = "0026_finance_reconciliation"
down_revision = "0025_financial_disputes"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='5s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    op.execute("DROP FUNCTION public.sr_finance_reconciliation_counts(timestamptz)")
    op.execute(
        "DROP FUNCTION public.sr_finance_reconciliation(timestamptz,text,timestamptz,uuid,uuid,text,integer)"
    )
    op.execute("DROP FUNCTION public.sr_finance_reconciliation_rows(timestamptz)")
