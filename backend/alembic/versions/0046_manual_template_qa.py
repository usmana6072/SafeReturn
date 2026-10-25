"""Owner-requested manual print review; no signed evidence needed for QA alone."""
from pathlib import Path

from alembic import op

revision = '0046_manual_template_qa'
down_revision = '0045_template_qa_reviews'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix('.sql').read_text(encoding='utf-8'))


def downgrade():
    raise RuntimeError('Staff review history must be retained')
