"""Draft template registry only; publication/binding authority remains unavailable."""

from pathlib import Path

from alembic import op

revision = "0033_print_template_drafts"
down_revision = "0032_owner_qr_lifecycle"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    # Preserve keys, draft content and audit/receipt history. No destructive rollback.
    op.execute(
        "REVOKE EXECUTE ON FUNCTION public.sr_template_service(uuid,bigint,text,jsonb) FROM safereturn_api"
    )
    op.execute(
        "REVOKE EXECUTE ON FUNCTION public.sr_template_preview_admit(uuid,bigint,text,text) FROM safereturn_api"
    )
