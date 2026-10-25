"""Controlled encrypted batch transport; unapplied after pending 0026."""

from pathlib import Path

from alembic import op

revision = "0027_manufacturing_exports"
down_revision = "0026_finance_reconciliation"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='5s'")
    op.execute(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    # Preserve custody records and encrypted payloads. Roll forward after any use.
    op.execute("""DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM public.manufacturing_sources) OR
         EXISTS(SELECT 1 FROM public.durable_jobs WHERE job_kind='manufacturing.export')
      THEN RAISE EXCEPTION 'Manufacturing history requires forward recovery'; END IF;
    END $$""")
    op.execute("DROP TRIGGER sr_mfg_job ON public.durable_jobs")
    op.execute("DROP FUNCTION public.sr_mfg_job_guard()")
    for signature in (
        "sr_mfg_record_handoff(uuid,jsonb)",
        "sr_mfg_handoff_context(uuid)",
        "sr_mfg_finish(uuid,jsonb)",
        "sr_mfg_claim(uuid)",
        "sr_mfg_revoke(uuid)",
        "sr_mfg_provision(uuid,jsonb)",
        "sr_mfg_register(uuid,jsonb)",
        "sr_mfg_apply(text,uuid,jsonb)",
        "sr_mfg_context(uuid,uuid)",
        "sr_mfg_authorized(uuid)",
        "sr_mfg_eligible(uuid)",
        "sr_mfg_pairs(uuid)",
    ):
        op.execute("DROP FUNCTION public." + signature)
    for name in (
        "manufacturing_handoffs",
        "manufacturing_grants",
        "manufacturing_receipts",
        "manufacturing_events",
        "manufacturing_exports",
        "manufacturing_approvals",
        "manufacturing_sources",
    ):
        op.execute("DROP TABLE public." + name)
    op.execute("DROP FUNCTION public.sr_mfg_binding_guard()")
    op.execute("ALTER TABLE public.durable_jobs DROP CONSTRAINT ck_durable_jobs_kind")
    op.execute(
        "ALTER TABLE public.durable_jobs ADD CONSTRAINT ck_durable_jobs_kind CHECK(job_kind IN('allocation.finalize','print.render','finance.sync','retention.cleanup'))"
    )
    op.execute("ALTER TABLE public.durable_jobs DROP CONSTRAINT ck_durable_jobs_order")
    op.execute(
        "ALTER TABLE public.durable_jobs ADD CONSTRAINT ck_durable_jobs_order CHECK(job_kind='retention.cleanup' OR order_id IS NOT NULL)"
    )
