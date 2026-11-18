"""Allow shipment creation after downloading a template-approved print PDF."""

from pathlib import Path

from alembic import op

revision = "0057_downloaded_print_shipping"
down_revision = "0056_typed_shipment_lifecycle"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError("Downloaded print shipping requires a reviewed forward change")
