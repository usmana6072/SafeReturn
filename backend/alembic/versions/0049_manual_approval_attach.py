"""Allow only matching manual approval attachment to an immutable publication."""
from pathlib import Path

from alembic import op

revision = '0049_manual_approval_attach'
down_revision = '0048_manual_template_binding'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix('.sql').read_text(encoding='utf-8'))


def downgrade():
    raise RuntimeError('Publication provenance must be retained')
