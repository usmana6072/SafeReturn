"""Use genuine manual physical reviews in typed variant bindings and snapshots."""
from pathlib import Path

from alembic import op

revision = '0048_manual_template_binding'
down_revision = '0047_qa_auto_publication'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix('.sql').read_text(encoding='utf-8'))


def downgrade():
    raise RuntimeError('Publication and binding provenance must be retained')
