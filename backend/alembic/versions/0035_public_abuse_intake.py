"""Unseeded policy-gated blind public abuse intake and restricted triage linkage."""

from pathlib import Path

from alembic import op

revision = "0035_public_abuse_intake"
down_revision = "0034_print_template_publication"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    # Retain linked-case restrictions/readers, policy, consent, audit and data.
    # Roll forward by reviewed grant restoration, not blind CREATE replay.
    op.execute("REVOKE EXECUTE ON FUNCTION public.sr_abuse_intake(text,jsonb) FROM safereturn_api")
