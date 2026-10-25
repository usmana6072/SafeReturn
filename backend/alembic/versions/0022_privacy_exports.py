"""Reviewed basic_v1 exports; additive, no live storage or erasure permission."""

from pathlib import Path

from alembic import op

revision = "0022_privacy_exports"
down_revision = "0021_support_case_console"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='5s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError(
        "Preserve privacy decisions/artifacts; transactional DDL rollback only"
    )
