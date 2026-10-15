"""Persist the approved QR template selected for a generated batch."""

from sqlalchemy import Column, String, inspect

from alembic import op

revision = "0006_qr_batch_template"
down_revision = "0005_account_session_guard"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("qr_batches", schema="public"):
        raise RuntimeError("QR batch table is missing; nothing changed")
    if "logo_template_key" in {
        column["name"] for column in inspector.get_columns("qr_batches", schema="public")
    }:
        raise RuntimeError("QR batch template metadata requires reconciliation")
    op.execute("SET LOCAL lock_timeout='5s'")
    op.add_column("qr_batches", Column("logo_template_key", String(80)), schema="public")
    op.create_check_constraint(
        "ck_qr_batches_logo_template_key",
        "qr_batches",
        "logo_template_key IS NULL OR logo_template_key ~ '^[a-z0-9][a-z0-9-]{0,79}$'",
        schema="public",
    )


def downgrade():
    raise RuntimeError("Inventory generation migration is forward-only")
