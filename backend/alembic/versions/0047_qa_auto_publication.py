"""Publish the exact revision atomically with a staff physical-QA approval."""
from pathlib import Path

from alembic import op

revision = '0047_qa_auto_publication'
down_revision = '0046_manual_template_qa'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix('.sql').read_text(encoding='utf-8'))


def downgrade():
    raise RuntimeError('Published revision and physical review history must be retained')
