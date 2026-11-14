"""Typed finance audit compatibility; no release or authority changes."""
from pathlib import Path
from alembic import op
revision = "0052_typed_finance_audit"
down_revision = "0051_independent_finance"
branch_labels = None
depends_on = None

def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))

def downgrade():
    raise RuntimeError("Audit compatibility requires a reviewed forward change")
