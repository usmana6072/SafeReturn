"""Permit narrowly scoped owner locks without granting inventory UPDATE rights."""

from alembic import op

revision = "0011_profile_owner_locks"
down_revision = "0010_profile_consent"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout='5s'")
    op.execute("""
CREATE FUNCTION public.sr_lock_profile_qr(qid uuid, purpose text) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE pid uuid;
BEGIN
 IF public.sr_actor_id() IS NULL OR purpose NOT IN ('lost','ice') THEN RETURN false; END IF;
 SELECT p.id INTO pid FROM public.tag_pairs p JOIN public.qr_codes q ON q.pair_id=p.id
 WHERE q.id=qid AND p.owner_user_id=public.sr_actor_id() AND p.ownership_status='active'
 FOR SHARE OF p;
 IF pid IS NULL THEN RETURN false; END IF;
 PERFORM 1 FROM public.qr_codes WHERE id=qid AND pair_id=pid AND tag_type=purpose
  AND is_current AND public_status<>'revoked' FOR UPDATE;
 RETURN FOUND;
END $$;
REVOKE ALL ON FUNCTION public.sr_lock_profile_qr(uuid,text) FROM PUBLIC,anon,authenticated,safereturn_worker;
GRANT EXECUTE ON FUNCTION public.sr_lock_profile_qr(uuid,text) TO safereturn_api;
""")


def downgrade():
    raise RuntimeError("Owner lock permission correction is forward-only")
