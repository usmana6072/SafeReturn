"""Empty-authority registry, publication, bindings and purchase-time print specs."""

from pathlib import Path

from alembic import op

revision = "0034_print_template_publication"
down_revision = "0033_print_template_drafts"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    # Never drop snapshots, authorities, evidence, fences or compatible readers.
    # Existing registry orders must retain readers and security-withdrawal guards.
    op.execute(
        "REVOKE EXECUTE ON FUNCTION public.sr_template_lifecycle(uuid,bigint,text,jsonb) FROM safereturn_api"
    )
