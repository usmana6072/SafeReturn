"""Durable template QA review overlay; source only until separately authorized."""
from pathlib import Path

from alembic import op

revision = "0045_template_qa_reviews"
down_revision = "0044_support_dev_exception"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix('.sql').read_text(encoding='utf-8'))


def downgrade():
    raise RuntimeError('Template review and audit history must be retained')
