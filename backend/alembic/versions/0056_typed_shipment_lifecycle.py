"""Use typed packing checks for standalone orders at shipment commit."""

from alembic import op

revision = "0056_typed_shipment_lifecycle"
down_revision = "0055_print_ready_activation"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='3s'")
    op.execute("""
    DO $migration$
    DECLARE
        definition text;
        pair_check text := ' IF NOT EXISTS (SELECT 1 FROM public.shipment_pairs WHERE shipment_id=sid) OR EXISTS (';
    BEGIN
        SELECT pg_get_functiondef('public.sr_check_shipment()'::regprocedure) INTO definition;
        IF strpos(definition, pair_check) = 0 THEN
            RAISE EXCEPTION 'Unexpected legacy shipment guard definition';
        END IF;
        -- The deferred typed shipment trigger checks current PDF QA and packed item membership.
        EXECUTE replace(definition, pair_check, $typed$
 IF EXISTS (SELECT 1 FROM public.orders WHERE id=s.order_id AND commerce_model='single_qr') THEN
  RETURN NULL;
 END IF;
 $typed$ || pair_check);
    END $migration$
    """)


def downgrade():
    raise RuntimeError("Typed shipment lifecycle requires a reviewed forward change")
