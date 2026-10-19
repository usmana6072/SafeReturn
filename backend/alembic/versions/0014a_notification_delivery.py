"""Lease-scoped verified recipient resolution and write-once encrypted snapshots."""

from sqlalchemy import inspect, text

from alembic import op

revision = "0014a_notification_delivery"
down_revision = "0014_public_finder_messages"
branch_labels = None
depends_on = None


def upgrade():
    columns = {
        column["name"]
        for column in inspect(op.get_bind()).get_columns("users", schema="auth")
    }
    if not {
        "email",
        "email_confirmed_at",
        "deleted_at",
        "banned_until",
        "is_anonymous",
    }.issubset(columns):
        raise RuntimeError("Auth recipient metadata requires reconciliation")
    op.execute("SET LOCAL lock_timeout='5s'")
    definition = (
        op.get_bind()
        .execute(
            text(
                "SELECT pg_get_functiondef('public.sr_public_submit_finder_message(text,text,bytea,bytea,smallint,text,bytea,smallint,text,timestamptz,bytea,bytea,numeric,text,timestamptz,text,smallint,text,text)'::regprocedure)"
            )
        )
        .scalar_one()
    )
    if definition.count("FOR SHARE OF q,p,l;") != 1:
        raise RuntimeError("Finder recipient locking requires reconciliation")
    # The finder insert guard needs a parent UPDATE lock; take it before idempotency
    # serialization so two submissions cannot deadlock while upgrading SHARE locks.
    op.execute(
        definition.replace("FOR SHARE OF q,p,l;", "FOR UPDATE OF p FOR SHARE OF q,l;")
    )
    op.execute("""
CREATE OR REPLACE FUNCTION public.sr_outbox_relation() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NEW.event_type='finder_message.created' AND NOT EXISTS (
  SELECT 1 FROM public.finder_messages WHERE id=NEW.aggregate_id AND NEW.aggregate_type='finder_message'
   AND recipient_owner_user_id=NEW.recipient_user_id
 ) THEN RAISE EXCEPTION 'Notification recipient/aggregate mismatch' USING ERRCODE='23514'; END IF;
 IF TG_OP='UPDATE' THEN
  IF (NEW.id,NEW.event_type,NEW.aggregate_type,NEW.aggregate_id,NEW.recipient_user_id,
      NEW.payload_ciphertext,NEW.payload_key_version,NEW.payload_version,NEW.idempotency_key,NEW.created_at)
     IS DISTINCT FROM
     (OLD.id,OLD.event_type,OLD.aggregate_type,OLD.aggregate_id,OLD.recipient_user_id,
      OLD.payload_ciphertext,OLD.payload_key_version,OLD.payload_version,OLD.idempotency_key,OLD.created_at) THEN
   RAISE EXCEPTION 'Notification event identity/payload is immutable' USING ERRCODE='23514';
  END IF;
  IF (NEW.recipient_email_snapshot_ciphertext,NEW.recipient_email_key_version) IS DISTINCT FROM
     (OLD.recipient_email_snapshot_ciphertext,OLD.recipient_email_key_version) AND (
     OLD.recipient_email_snapshot_ciphertext IS NULL AND OLD.recipient_email_key_version IS NULL
     AND NEW.recipient_email_snapshot_ciphertext IS NOT NULL AND NEW.recipient_email_key_version>0
     AND OLD.status='leased' AND NEW.status='leased'
     AND OLD.lease_owner=public.sr_worker_id() AND NEW.lease_owner=OLD.lease_owner
     AND OLD.lease_until>clock_timestamp() AND NEW.lease_until=OLD.lease_until
     AND NEW.attempt_count=OLD.attempt_count
  ) IS NOT TRUE THEN
   RAISE EXCEPTION 'Notification recipient snapshot is write-once under lease' USING ERRCODE='23514';
  END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION public.sr_notification_recipient(
 notification uuid, attempt integer, snapshot bytea DEFAULT NULL, key_version smallint DEFAULT NULL
) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE recipient text;
BEGIN
 SELECT u.email INTO recipient
 FROM public.notification_outbox o
 JOIN public.finder_messages m ON m.id=o.aggregate_id AND m.recipient_owner_user_id=o.recipient_user_id
 JOIN auth.users u ON u.id=o.recipient_user_id
 WHERE o.id=$1 AND o.attempt_count=$2
   AND o.event_type='finder_message.created' AND o.aggregate_type='finder_message' AND o.payload_version=1
   AND o.status='leased' AND o.lease_owner=public.sr_worker_id() AND o.lease_until>clock_timestamp()
   AND m.deleted_at IS NULL AND u.deleted_at IS NULL AND u.email_confirmed_at IS NOT NULL
   AND NOT COALESCE(u.is_anonymous,false)
   AND (u.banned_until IS NULL OR u.banned_until<=clock_timestamp())
 FOR UPDATE OF o;
 IF recipient IS NULL THEN RETURN NULL; END IF;
 IF $3 IS NOT NULL OR $4 IS NOT NULL THEN
  IF $3 IS NULL OR octet_length($3)<32 OR $4 IS NULL OR $4<=0 THEN
   RAISE EXCEPTION 'Invalid encrypted recipient' USING ERRCODE='23514';
  END IF;
  UPDATE public.notification_outbox SET recipient_email_snapshot_ciphertext=$3,recipient_email_key_version=$4
  WHERE id=$1 AND recipient_email_snapshot_ciphertext IS NULL AND recipient_email_key_version IS NULL;
 END IF;
 RETURN recipient;
END $$;
REVOKE ALL ON FUNCTION public.sr_notification_recipient(uuid,integer,bytea,smallint)
 FROM PUBLIC,anon,authenticated,safereturn_api;
GRANT EXECUTE ON FUNCTION public.sr_notification_recipient(uuid,integer,bytea,smallint) TO safereturn_worker;
""")


def downgrade():
    raise RuntimeError("Notification delivery is forward-only")
