"""Narrow runtime procedures for entitled, atomic paired activation."""

from pathlib import Path

from alembic import op

revision = "0008_atomic_activation"
down_revision = "0007_qr_batch_environment"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='5s'")
    op.execute(
        Path(__file__).parents[1].joinpath("activation_procedures.sql").read_text()
    )


def downgrade():
    raise RuntimeError("Atomic activation is forward-only")
