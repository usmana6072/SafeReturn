"""Add consent evidence, reversible contact removal and preference versions."""

from sqlalchemy import Column, DateTime, Integer, String, text

from alembic import op

revision = "0010_profile_consent"
down_revision = "0009_activation_rechecks"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='5s'")
    op.add_column(
        "ice_contacts",
        Column("publication_consent_version", String(30)),
        schema="public",
    )
    op.add_column(
        "ice_contacts", Column("removed_at", DateTime(timezone=True)), schema="public"
    )
    op.create_check_constraint(
        "ck_ice_contacts_removed_unpublished",
        "ice_contacts",
        "removed_at IS NULL OR NOT published",
        schema="public",
    )
    op.add_column(
        "tag_contact_preferences",
        Column("profile_version", Integer, nullable=False, server_default=text("1")),
        schema="public",
    )
    op.create_check_constraint(
        "ck_tag_contact_preferences_version",
        "tag_contact_preferences",
        "profile_version>0",
        schema="public",
    )


def downgrade():
    raise RuntimeError("Profile consent migration is forward-only")
