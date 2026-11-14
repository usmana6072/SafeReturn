"""Disabled owner public-status/history helpers; offline after pending0031."""

from pathlib import Path

from alembic import op

revision = "0032_owner_qr_lifecycle"
down_revision = "0031_staff_account_state"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    # Helper-only rollback: retain all actual child states/audit/receipt history.
    op.execute(
        "DROP FUNCTION public.sr_qr_lifecycle_save(uuid,bigint,uuid,text,text,bytea,smallint)"
    )
    op.execute(
        "DROP FUNCTION public.sr_qr_lifecycle_command(uuid,bigint,uuid,integer,text,text,text,text)"
    )
    op.execute(
        "DROP FUNCTION public.sr_qr_lifecycle_history(uuid,uuid,integer,timestamptz,uuid)"
    )
