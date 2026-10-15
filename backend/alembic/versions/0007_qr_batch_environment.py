"""Persist physical environment for the approved symbol-size minimum."""

from sqlalchemy import Column, String, inspect

from alembic import op

revision = "0007_qr_batch_environment"
down_revision = "0006_qr_batch_template"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("qr_batches", schema="public"):
        raise RuntimeError("QR batch table is missing; nothing changed")
    if "intended_environment" in {
        column["name"]
        for column in inspector.get_columns("qr_batches", schema="public")
    }:
        raise RuntimeError("QR batch environment metadata requires reconciliation")
    op.execute("SET LOCAL lock_timeout='5s'")
    op.add_column(
        "qr_batches", Column("intended_environment", String(8)), schema="public"
    )
    op.create_check_constraint(
        "ck_qr_batches_intended_environment",
        "qr_batches",
        "intended_environment IS NULL OR intended_environment IN ('indoor','outdoor')",
        schema="public",
    )


def downgrade():
    raise RuntimeError("Inventory environment migration is forward-only")
