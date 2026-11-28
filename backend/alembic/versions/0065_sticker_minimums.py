"""Allow the minimum compact 25 x 20 mm sticker and 15 mm QR template."""

from pathlib import Path

from alembic import op

revision = "0065_sticker_minimums"
down_revision = "0064_template_auth_60h"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError("Use a reviewed forward migration to preserve template history")
