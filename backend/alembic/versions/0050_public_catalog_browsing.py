"""Publish catalog browsing independently of purchase/activation release."""
from pathlib import Path

from alembic import op

revision = '0050_public_catalog_browsing'
down_revision = '0049_manual_approval_attach'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix('.sql').read_text(encoding='utf-8'))


def downgrade():
    raise RuntimeError('Catalog release semantics require a reviewed forward change')
