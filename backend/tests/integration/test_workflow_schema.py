"""Real PostgreSQL role, ownership, durable queue and privacy bypass checks."""

import hashlib
import uuid
from contextlib import contextmanager

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from test_identity_schema import migrated as _identity_migrated

migrated = _identity_migrated


@pytest.fixture(scope="module")
def workflow_sample(migrated):
    marker = uuid.uuid4().hex
    migrated.execute(
        text(
            """
DO $$
DECLARE a uuid:=gen_random_uuid(); b uuid:=gen_random_uuid(); f uuid:=gen_random_uuid();
 op uuid:=gen_random_uuid(); sup uuid:=gen_random_uuid(); sec uuid:=gen_random_uuid();
 batch uuid; pa uuid; pb uuid; pc uuid; la uuid; lb uuid; lc uuid; ic uuid;
 ma uuid; mb uuid;
BEGIN
 INSERT INTO auth.users(id) VALUES(a),(b),(f),(op),(sup),(sec);
 INSERT INTO user_profiles(user_id,display_name) VALUES(a,'owner-A-MARKER'),(b,'owner-B-MARKER');
 INSERT INTO staff_roles(user_id,role,reason) VALUES(f,'finance','test-MARKER'),(op,'operations','test-MARKER'),(sup,'support','test-MARKER'),(sec,'security_admin','test-MARKER');
 INSERT INTO qr_batches(batch_code,ecc_level) VALUES('test-MARKER','Q') RETURNING id INTO batch;
 INSERT INTO tag_pairs(pair_reference,batch_id,owner_user_id,ownership_status,activated_at)
 VALUES('A-MARKER',batch,a,'active',now()) RETURNING id INTO pa;
 INSERT INTO tag_pairs(pair_reference,batch_id,owner_user_id,ownership_status,activated_at)
 VALUES('B-MARKER',batch,b,'active',now()) RETURNING id INTO pb;
 INSERT INTO tag_pairs(pair_reference,batch_id) VALUES('C-MARKER',batch) RETURNING id INTO pc;
 INSERT INTO qr_codes(pair_id,tag_type,serial_number,public_token,ecc_level,public_status)
 VALUES(pa,'lost','LA-MARKER','LA-MARKER','Q','active') RETURNING id INTO la;
 INSERT INTO qr_codes(pair_id,tag_type,serial_number,public_token,ecc_level,public_status)
 VALUES(pa,'ice','IA-MARKER','IA-MARKER','Q','active');
 INSERT INTO qr_codes(pair_id,tag_type,serial_number,public_token,ecc_level,public_status)
 VALUES(pb,'lost','LB-MARKER','LB-MARKER','Q','active') RETURNING id INTO lb;
 INSERT INTO qr_codes(pair_id,tag_type,serial_number,public_token,ecc_level,public_status)
 VALUES(pb,'ice','IB-MARKER','IB-MARKER','Q','active');
 INSERT INTO qr_codes(pair_id,tag_type,serial_number,public_token,ecc_level)
 VALUES(pc,'lost','LC-MARKER','LC-MARKER','Q') RETURNING id INTO lc;
 INSERT INTO qr_codes(pair_id,tag_type,serial_number,public_token,ecc_level)
 VALUES(pc,'ice','IC-MARKER','IC-MARKER','Q') RETURNING id INTO ic;
 INSERT INTO pair_activation_credentials(pair_id,secret_verifier,verifier_key_version) VALUES(pc,decode('ab','hex'),1);
 INSERT INTO lost_item_profiles(qr_id,item_label) VALUES(la,'private A'),(lb,'private B');
 INSERT INTO ice_profiles(qr_id,display_name,medical_notes_ciphertext,medical_notes_key_version)
 SELECT id,'private medical',decode('ab','hex'),1 FROM qr_codes WHERE pair_id IN(pa,pb) AND tag_type='ice';
 INSERT INTO finder_messages(qr_id,recipient_owner_user_id,finder_email_ciphertext,finder_contact_key_version,message_text_ciphertext,message_key_version,consent_version,consent_at)
 VALUES(la,a,decode('ab','hex'),1,decode('cd','hex'),1,'v1',now()) RETURNING id INTO ma;
 INSERT INTO finder_messages(qr_id,recipient_owner_user_id,finder_email_ciphertext,finder_contact_key_version,message_text_ciphertext,message_key_version,consent_version,consent_at)
 VALUES(lb,b,decode('ab','hex'),1,decode('cd','hex'),1,'v1',now()) RETURNING id INTO mb;
 INSERT INTO finder_message_locations(finder_message_id,latitude_ciphertext,longitude_ciphertext,consent_at,consent_version,key_version)
 VALUES(ma,decode('ab','hex'),decode('cd','hex'),now(),'v1',1);
 INSERT INTO notification_outbox(event_type,aggregate_type,aggregate_id,recipient_user_id,idempotency_key)
 VALUES('finder_message.created','finder_message',ma,a,'A-MARKER'),('finder_message.created','finder_message',mb,b,'B-MARKER');
 INSERT INTO audit_events(actor_user_id,actor_kind,action,target_type,target_id,safe_details)
 VALUES(a,'customer','profile.updated','qr',la,jsonb_build_object('version',1));
END $$;
""".replace("MARKER", marker)
        )
    )
    users = migrated.execute(
        text(
            "SELECT user_id,display_name FROM user_profiles WHERE display_name LIKE :s"
        ),
        {"s": "%" + marker},
    ).all()
    ids = {"a": users[0][0] if users[0][1].startswith("owner-A") else users[1][0]}
    ids["b"] = next(row[0] for row in users if row[1].startswith("owner-B"))
    for role, uid in migrated.execute(
        text("SELECT role,user_id FROM staff_roles WHERE reason=:s"),
        {"s": "test-" + marker},
    ):
        ids[role] = uid
    for reference, pid in migrated.execute(
        text("SELECT pair_reference,id FROM tag_pairs WHERE pair_reference LIKE :s"),
        {"s": "%" + marker},
    ):
        ids["p" + reference[0].lower()] = pid
    for serial, qid in migrated.execute(
        text("SELECT serial_number,id FROM qr_codes WHERE serial_number LIKE :s"),
        {"s": "%" + marker},
    ):
        ids[serial[:2].lower()] = qid
    for mid, recipient in migrated.execute(
        text(
            "SELECT id,recipient_owner_user_id FROM finder_messages WHERE qr_id IN (:la,:lb)"
        ),
        ids,
    ):
        ids["ma" if recipient == ids["a"] else "mb"] = mid
    for oid, mid in migrated.execute(
        text(
            "SELECT id,aggregate_id FROM notification_outbox WHERE aggregate_id IN (:ma,:mb)"
        ),
        ids,
    ):
        ids["oa" if mid == ids["ma"] else "ob"] = oid
    ids["digest"] = hashlib.sha256(("LC-" + marker).encode()).hexdigest()
    migrated.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    migrated.execute(text("SET CONSTRAINTS ALL DEFERRED"))
    return ids


@pytest.fixture
def workflow_conn(workflow_sample, migrated):
    nested = migrated.begin_nested()
    migrated.execute(text("SET CONSTRAINTS ALL DEFERRED"))
    try:
        yield migrated, workflow_sample
    finally:
        nested.rollback()


@contextmanager
def as_role(c, role, actor=None, *, mfa=False, worker="", submission=None, binding=""):
    assert role in ("safereturn_api", "safereturn_worker", "anon", "authenticated")
    nested = c.begin_nested()
    try:
        c.execute(text("SET LOCAL ROLE " + role))
        c.execute(
            text(
                "SELECT set_config('safereturn.actor_id',:a,true),set_config('safereturn.mfa_verified',:m,true),set_config('safereturn.worker_id',:w,true),set_config('safereturn.submission_id',:s,true),set_config('safereturn.scan_binding',:b,true)"
            ),
            {
                "a": str(actor) if actor else "",
                "m": "true" if mfa else "false",
                "w": worker,
                "s": str(submission) if submission else "",
                "b": binding,
            },
        )
        yield c
    except BaseException:
        nested.rollback()
        raise
    else:
        nested.commit()
    finally:
        c.execute(text("RESET ROLE"))
        c.execute(
            text(
                "SELECT set_config('safereturn.actor_id','',true),set_config('safereturn.worker_id','',true),set_config('safereturn.mfa_verified','false',true),set_config('safereturn.submission_id','',true),set_config('safereturn.scan_binding','',true)"
            )
        )


def run(c, statement, ids):
    return c.execute(text(statement), ids)


def validate(c):
    c.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


@pytest.mark.parametrize("role", ["anon", "authenticated"])
@pytest.mark.parametrize(
    "table",
    [
        "finder_messages",
        "finder_message_locations",
        "ice_contacts",
        "pair_activation_credentials",
        "audit_events",
        "notification_outbox",
    ],
)
def test_browser_roles_have_no_private_table_access(workflow_conn, role, table):
    c, _ = workflow_conn
    with pytest.raises(DBAPIError), as_role(c, role):
        c.execute(text("SELECT * FROM public." + table))


def test_customer_profiles_and_original_recipient_isolation(workflow_conn):
    c, ids = workflow_conn
    with as_role(c, "safereturn_api", ids["a"]):
        assert c.execute(text("SELECT count(*) FROM finder_messages")).scalar_one() == 1
        assert (
            c.execute(
                text("SELECT count(*) FROM finder_message_locations")
            ).scalar_one()
            == 1
        )
        assert c.execute(text("SELECT count(*) FROM ice_profiles")).scalar_one() == 1
        assert (
            run(
                c,
                "UPDATE lost_item_profiles SET item_label='A edited' WHERE qr_id=:la",
                ids,
            ).rowcount
            == 1
        )
        assert (
            run(
                c,
                "UPDATE lost_item_profiles SET item_label='stolen' WHERE qr_id=:lb",
                ids,
            ).rowcount
            == 0
        )
    run(c, "UPDATE tag_pairs SET owner_user_id=:b WHERE id=:pa", ids)
    with as_role(c, "safereturn_api", ids["b"]):
        assert (
            run(
                c, "SELECT count(*) FROM finder_messages WHERE id=:ma", ids
            ).scalar_one()
            == 0
        )
        assert (
            run(
                c,
                "SELECT count(*) FROM finder_message_locations WHERE finder_message_id=:ma",
                ids,
            ).scalar_one()
            == 0
        )
    with as_role(c, "safereturn_api", ids["a"]):
        assert (
            run(
                c, "SELECT count(*) FROM finder_messages WHERE id=:ma", ids
            ).scalar_one()
            == 1
        )


def test_owner_cannot_claim_pair_or_mint_replacement(workflow_conn):
    c, ids = workflow_conn
    with as_role(c, "safereturn_api", ids["a"]):
        assert (
            run(c, "UPDATE tag_pairs SET owner_user_id=:a WHERE id=:pb", ids).rowcount
            == 0
        )
    with pytest.raises(IntegrityError), as_role(c, "safereturn_api", ids["a"]):
        run(c, "UPDATE qr_codes SET is_current=false WHERE id=:la", ids)


def test_operations_cannot_verify_payments_and_finance_cannot_edit_inventory(
    workflow_conn,
):
    c, ids = workflow_conn
    with as_role(c, "safereturn_api", ids["finance"], mfa=True):
        assert (
            run(
                c, "UPDATE tag_pairs SET inventory_status='packed' WHERE id=:pa", ids
            ).rowcount
            == 0
        )
    with (
        pytest.raises(DBAPIError),
        as_role(c, "safereturn_api", ids["operations"], mfa=True),
    ):
        # RLS rejects even before the referenced attempt can authorize a review.
        run(
            c,
            "INSERT INTO payment_reviews(attempt_id,reviewed_by,decision) VALUES(:id,:actor,'reject')",
            {"id": uuid.uuid4(), "actor": ids["operations"]},
        )


def test_mfa_and_revoked_staff_role_fail_closed(workflow_conn):
    c, ids = workflow_conn
    with as_role(c, "safereturn_api", ids["operations"]):
        assert c.execute(text("SELECT count(*) FROM qr_batches")).scalar_one() == 0
    with as_role(c, "safereturn_api", ids["operations"], mfa=True):
        assert c.execute(text("SELECT count(*) FROM qr_batches")).scalar_one() >= 1
    run(c, "UPDATE staff_roles SET revoked_at=now() WHERE user_id=:operations", ids)
    with as_role(c, "safereturn_api", ids["operations"], mfa=True):
        assert c.execute(text("SELECT count(*) FROM qr_batches")).scalar_one() == 0


def test_support_has_no_ice_or_location_access(workflow_conn):
    c, ids = workflow_conn
    with as_role(c, "safereturn_api", ids["support"], mfa=True):
        assert c.execute(text("SELECT count(*) FROM ice_profiles")).scalar_one() == 0
        assert (
            c.execute(
                text("SELECT count(*) FROM finder_message_locations")
            ).scalar_one()
            == 0
        )
        assert c.execute(text("SELECT count(*) FROM finder_messages")).scalar_one() == 0


@pytest.mark.parametrize(
    "table",
    [
        "shipping_addresses",
        "order_shipping_snapshots",
        "ice_profiles",
        "ice_contacts",
        "pair_activation_credentials",
        "finder_message_locations",
        "payment_attempts",
        "staff_roles",
        "auth.users",
    ],
)
def test_worker_has_no_shipping_medical_finance_or_auth_payload(workflow_conn, table):
    c, _ = workflow_conn
    name = table if "." in table else "public." + table
    with (
        pytest.raises(DBAPIError),
        as_role(c, "safereturn_worker", worker="worker-one"),
    ):
        c.execute(text("SELECT * FROM " + name))


def test_finder_message_requires_outbox_at_commit_boundary(workflow_conn):
    c, ids = workflow_conn
    run(
        c,
        "INSERT INTO finder_messages(qr_id,recipient_owner_user_id,finder_email_ciphertext,finder_contact_key_version,message_text_ciphertext,message_key_version,consent_version,consent_at) VALUES(:la,:a,decode('ab','hex'),1,decode('cd','hex'),1,'v1',now())",
        ids,
    )
    with pytest.raises(IntegrityError):
        validate(c)


def test_anonymous_submission_is_atomic_and_context_scoped(workflow_conn):
    c, ids = workflow_conn
    mid = uuid.uuid4()
    with as_role(c, "safereturn_api", submission=mid):
        run(
            c,
            "INSERT INTO finder_messages(id,qr_id,recipient_owner_user_id,finder_email_ciphertext,finder_contact_key_version,message_text_ciphertext,message_key_version,consent_version,consent_at) VALUES(:mid,:la,:a,decode('ab','hex'),1,decode('cd','hex'),1,'v1',now())",
            {**ids, "mid": mid},
        )
        run(
            c,
            "INSERT INTO finder_message_locations(finder_message_id,latitude_ciphertext,longitude_ciphertext,consent_at,consent_version,key_version) VALUES(:mid,decode('ab','hex'),decode('cd','hex'),now(),'v1',1)",
            {"mid": mid},
        )
        run(
            c,
            "INSERT INTO notification_outbox(event_type,aggregate_type,aggregate_id,recipient_user_id,idempotency_key) VALUES('finder_message.created','finder_message',:mid,:a,:key)",
            {**ids, "mid": mid, "key": str(mid)},
        )
        validate(c)
    with as_role(c, "safereturn_api"):
        assert (
            run(
                c, "SELECT count(*) FROM finder_messages WHERE id=:mid", {"mid": mid}
            ).scalar_one()
            == 0
        )


@pytest.mark.parametrize(
    "case",
    [
        "recipient",
        "ice",
        "contact",
        "key",
        "location_consent",
        "location_key",
        "payload_key",
    ],
)
def test_message_location_and_payload_constraints(workflow_conn, case):
    c, ids = workflow_conn
    with pytest.raises(IntegrityError):
        if case in ("recipient", "ice", "contact", "key"):
            params = {
                **ids,
                "qr": ids["ia"] if case == "ice" else ids["la"],
                "recipient": ids["b"] if case == "recipient" else ids["a"],
                "contact": None if case == "contact" else bytes.fromhex("ab"),
                "key": 0 if case == "key" else 1,
            }
            run(
                c,
                "INSERT INTO finder_messages(qr_id,recipient_owner_user_id,finder_email_ciphertext,finder_contact_key_version,message_text_ciphertext,message_key_version,consent_version,consent_at) VALUES(:qr,:recipient,:contact,1,decode('cd','hex'),:key,'v1',now())",
                params,
            )
        elif case == "location_consent":
            run(
                c,
                "UPDATE finder_message_locations SET consent_version=NULL WHERE finder_message_id=:ma",
                ids,
            )
        elif case == "location_key":
            run(
                c,
                "UPDATE finder_message_locations SET key_version=0 WHERE finder_message_id=:ma",
                ids,
            )
        else:
            run(
                c,
                "UPDATE notification_outbox SET payload_ciphertext=decode('ab','hex') WHERE id=:oa",
                ids,
            )


def test_recipient_snapshot_and_audit_are_immutable(workflow_conn):
    c, ids = workflow_conn
    with pytest.raises(IntegrityError):
        run(
            c, "UPDATE finder_messages SET recipient_owner_user_id=:b WHERE id=:ma", ids
        )


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE audit_events SET action='erased'",
        "DELETE FROM audit_events",
        "INSERT INTO audit_events(actor_kind,action,target_type,safe_details) VALUES('system','test','test','{\"phone\":\"private\"}')",
    ],
)
def test_audit_append_only_and_metadata_allowlist(workflow_conn, statement):
    c, _ = workflow_conn
    with pytest.raises(IntegrityError):
        c.execute(text(statement))


def claim(c, oid, worker):
    return run(
        c,
        "UPDATE notification_outbox SET status='leased',lease_owner=:worker,lease_until=now()+interval '1 minute',attempt_count=attempt_count+1 WHERE id=:id",
        {"worker": worker, "id": oid},
    )


def test_worker_claim_ack_and_attempt_metadata(workflow_conn):
    c, ids = workflow_conn
    with as_role(c, "safereturn_worker", worker="worker-one"):
        assert claim(c, ids["oa"], "worker-one").rowcount == 1
        run(
            c,
            "INSERT INTO notification_attempts(outbox_id,attempt_number,outcome) VALUES(:oa,1,'unknown')",
            ids,
        )
        run(
            c,
            "UPDATE notification_attempts SET outcome='success',finished_at=now() WHERE outbox_id=:oa",
            ids,
        )
        assert (
            run(
                c,
                "UPDATE notification_outbox SET status='sent',sent_at=now(),lease_owner=NULL,lease_until=NULL WHERE id=:oa",
                ids,
            ).rowcount
            == 1
        )
    validate(c)
    assert run(
        c, "SELECT status,attempt_count FROM notification_outbox WHERE id=:oa", ids
    ).one() == ("sent", 1)


def test_foreign_worker_cannot_ack_lease(workflow_conn):
    c, ids = workflow_conn
    with as_role(c, "safereturn_worker", worker="worker-one"):
        claim(c, ids["oa"], "worker-one")
    with as_role(c, "safereturn_worker", worker="worker-two"):
        assert (
            run(
                c,
                "UPDATE notification_outbox SET status='sent',sent_at=now(),lease_owner=NULL,lease_until=NULL WHERE id=:oa",
                ids,
            ).rowcount
            == 0
        )


def test_expired_lease_can_be_reclaimed(workflow_conn):
    c, ids = workflow_conn
    run(
        c,
        "UPDATE notification_outbox SET status='leased',lease_owner='crashed',lease_until=now()-interval '1 minute',attempt_count=1 WHERE id=:oa",
        ids,
    )
    with as_role(c, "safereturn_worker", worker="recovery"):
        assert claim(c, ids["oa"], "recovery").rowcount == 1
    assert run(
        c, "SELECT lease_owner,attempt_count FROM notification_outbox WHERE id=:oa", ids
    ).one() == ("recovery", 2)


def test_worker_cannot_mark_pending_event_sent_without_claim(workflow_conn):
    c, ids = workflow_conn
    with (
        pytest.raises(IntegrityError),
        as_role(c, "safereturn_worker", worker="worker-one"),
    ):
        run(
            c,
            "UPDATE notification_outbox SET status='sent',sent_at=now() WHERE id=:oa",
            ids,
        )


def test_worker_cannot_rewrite_payload_or_verify_payment(workflow_conn):
    c, ids = workflow_conn
    with (
        pytest.raises(DBAPIError),
        as_role(c, "safereturn_worker", worker="worker-one"),
    ):
        run(
            c,
            "UPDATE notification_outbox SET payload_ciphertext=decode('ab','hex') WHERE id=:oa",
            ids,
        )


def test_idempotency_owner_binding_request_hash_and_completed_response(workflow_conn):
    c, ids = workflow_conn
    record = uuid.uuid4()
    with as_role(c, "safereturn_api", ids["a"]):
        run(
            c,
            "INSERT INTO idempotency_records(id,actor_scope,actor_user_id,operation,idempotency_key,request_hash,expires_at) VALUES(:id,:scope,:a,'checkout','one',repeat('a',64),now()+interval '1 hour')",
            {**ids, "id": record, "scope": str(ids["a"])},
        )
        run(
            c,
            "UPDATE idempotency_records SET state='completed',response_status=201 WHERE id=:id",
            {"id": record},
        )
    with as_role(c, "safereturn_api", ids["b"]):
        assert (
            run(
                c,
                "SELECT count(*) FROM idempotency_records WHERE id=:id",
                {"id": record},
            ).scalar_one()
            == 0
        )
    with pytest.raises(IntegrityError), as_role(c, "safereturn_api", ids["a"]):
        run(
            c,
            "UPDATE idempotency_records SET request_hash=repeat('b',64) WHERE id=:id",
            {"id": record},
        )


def create_scan(c, ids, actor, binding="a" * 64):
    return run(
        c,
        "INSERT INTO scan_contexts(qr_code_id,public_token_digest,session_binding_digest,bound_actor_user_id,expires_at) VALUES(:lc,:digest,:binding,:actor,now()+interval '15 minutes') RETURNING id",
        {**ids, "binding": binding, "actor": actor},
    ).scalar_one()


def test_scan_binding_and_actor_bound_intent_no_replay(workflow_conn):
    c, ids = workflow_conn
    with as_role(c, "safereturn_api", ids["a"], binding="a" * 64):
        sid = create_scan(c, ids, ids["a"])
        iid = run(
            c,
            "INSERT INTO activation_intents(actor_user_id,pair_id,lost_qr_id,ice_qr_id,scan_context_id,method,verifier_key_version,expires_at) VALUES(:a,:pc,:lc,:ic,:sid,'concealed_credential',1,now()+interval '10 minutes') RETURNING id",
            {**ids, "sid": sid},
        ).scalar_one()
        assert (
            run(
                c,
                "UPDATE activation_intents SET state='consumed',consumed_at=now() WHERE id=:id",
                {"id": iid},
            ).rowcount
            == 1
        )
    with as_role(c, "safereturn_api", ids["b"], binding="b" * 64):
        assert (
            run(
                c, "SELECT count(*) FROM scan_contexts WHERE id=:id", {"id": sid}
            ).scalar_one()
            == 0
        )
        assert (
            run(
                c,
                "UPDATE activation_intents SET state='consumed',consumed_at=now() WHERE id=:id",
                {"id": iid},
            ).rowcount
            == 0
        )
    with pytest.raises(IntegrityError), as_role(c, "safereturn_api", ids["a"]):
        run(
            c,
            "UPDATE activation_intents SET state='pending',consumed_at=NULL WHERE id=:id",
            {"id": iid},
        )


def test_expired_context_cannot_be_consumed(workflow_conn):
    c, ids = workflow_conn
    sid = run(
        c,
        "INSERT INTO scan_contexts(qr_code_id,public_token_digest,session_binding_digest,bound_actor_user_id,created_at,expires_at) VALUES(:lc,:digest,repeat('a',64),:a,now()-interval '1 hour',now()-interval '1 minute') RETURNING id",
        ids,
    ).scalar_one()
    with pytest.raises(IntegrityError):
        run(
            c,
            "UPDATE scan_contexts SET state='consumed',consumed_at=now() WHERE id=:id",
            {"id": sid},
        )


def test_owner_cannot_change_retention_policy_and_hold_blocks_deletion(workflow_conn):
    c, ids = workflow_conn
    with pytest.raises(IntegrityError), as_role(c, "safereturn_api", ids["a"]):
        run(
            c,
            "UPDATE finder_messages SET retention_until=now()-interval '1 minute',deleted_at=now() WHERE id=:ma",
            ids,
        )


def test_privacy_hold_prevents_due_message_tombstone(workflow_conn):
    c, ids = workflow_conn
    run(
        c,
        "UPDATE finder_messages SET retention_until=now()-interval '1 minute' WHERE id=:ma",
        ids,
    )
    run(
        c,
        "INSERT INTO retention_holds(resource_type,resource_id,reason_code,placed_by) VALUES('finder_message',:ma,'dispute',:security_admin)",
        ids,
    )
    with pytest.raises(IntegrityError):
        run(c, "UPDATE finder_messages SET deleted_at=now() WHERE id=:ma", ids)


def test_security_admin_can_release_hold_without_rewriting_history(workflow_conn):
    c, ids = workflow_conn
    with as_role(c, "safereturn_api", ids["security_admin"], mfa=True):
        hid = run(
            c,
            "INSERT INTO retention_holds(resource_type,resource_id,reason_code,placed_by) VALUES('finder_message',:ma,'dispute',:security_admin) RETURNING id",
            ids,
        ).scalar_one()
        run(
            c,
            "UPDATE retention_holds SET released_at=now(),released_by=:security_admin WHERE id=:id",
            {**ids, "id": hid},
        )
    with pytest.raises(IntegrityError):
        run(
            c,
            "UPDATE retention_holds SET reason_code='erase' WHERE id=:id",
            {"id": hid},
        )


def test_definer_paths_and_runtime_role_attributes(workflow_conn):
    c, _ = workflow_conn
    rows = c.execute(
        text(
            "SELECT rolname,rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname IN ('safereturn_api','safereturn_worker','safereturn_api_login','safereturn_worker_login')"
        )
    ).all()
    assert len(rows) == 4 and all(not any(row[1:]) for row in rows)
    assert (
        c.execute(
            text(
                "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname LIKE 'sr_%' AND p.prosecdef AND NOT ('search_path=pg_catalog'=ANY(p.proconfig))"
            )
        ).scalar_one()
        == 0
    )
    assert c.execute(
        text(
            "SELECT pg_has_role('anon','safereturn_api','MEMBER'),pg_has_role('authenticated','safereturn_worker','MEMBER')"
        )
    ).one() == (False, False)
