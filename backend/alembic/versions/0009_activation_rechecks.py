"""Preserve activation decisions and forbid credential bypass of live commerce."""

from pathlib import Path

from alembic import op

revision = "0009_activation_rechecks"
down_revision = "0008_atomic_activation"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='5s'")
    op.execute(
        Path(__file__).parents[1].joinpath("activation_rechecks.sql").read_text()
    )


def downgrade():
    raise RuntimeError("Activation entitlement correction is forward-only")
