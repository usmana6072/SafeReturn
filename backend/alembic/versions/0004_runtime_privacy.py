"""Keep historical shipping addresses in owner/fulfillment scope.

Forward-only correction to the API policy matrix. Finance retains billing and
settlement access. No rows or grants outside SafeReturn are changed.
"""

from sqlalchemy import text

from alembic import op

revision = "0004_runtime_privacy"
down_revision = "0003_workflows_security"
branch_labels = None
depends_on = None

PREDICATE = "public.sr_owns_order(order_id) OR public.sr_is_staff(ARRAY['operations','security_admin','superadmin'])"


def upgrade():
    policies = [
        "sr_safereturn_api_select",
        "sr_safereturn_api_insert",
        "sr_safereturn_api_update",
    ]
    count = (
        op.get_bind()
        .execute(
            text(
                "SELECT count(*) FROM pg_policies WHERE schemaname='public' AND tablename='order_shipping_snapshots' AND policyname=ANY(:policies)"
            ),
            {"policies": policies},
        )
        .scalar_one()
    )
    if count != 3:
        raise RuntimeError("Expected shipping policies require explicit reconciliation")
    op.execute("SET LOCAL lock_timeout='5s'")
    op.execute(
        "ALTER POLICY sr_safereturn_api_select ON public.order_shipping_snapshots USING ("
        + PREDICATE
        + ")"
    )
    op.execute(
        "ALTER POLICY sr_safereturn_api_insert ON public.order_shipping_snapshots WITH CHECK ("
        + PREDICATE
        + ")"
    )
    op.execute(
        "ALTER POLICY sr_safereturn_api_update ON public.order_shipping_snapshots USING ("
        + PREDICATE
        + ") WITH CHECK ("
        + PREDICATE
        + ")"
    )


def downgrade():
    raise RuntimeError("Privacy downgrade disabled; use reviewed forward revision")
