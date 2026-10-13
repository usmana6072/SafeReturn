"""Real PostgreSQL commerce invariants with rollback-only synthetic records."""

import importlib.util
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from test_identity_schema import migrated as _identity_migrated
from test_identity_schema import pair

from app.db.commerce import Order, OrderItem, ProductVariant

migrated = _identity_migrated


@pytest.fixture(scope="module")
def sample(migrated):
    suffix = uuid.uuid4().hex
    # A single PL/pgSQL round trip still executes real INSERTs and all triggers.
    migrated.execute(
        text(
            """
DO $$
DECLARE customer uuid:=gen_random_uuid(); product uuid; lost_variant uuid; ice_variant uuid;
        address uuid; batch uuid; pair uuid; lost uuid; ice uuid; purchase uuid;
        unit uuid; item uuid;
BEGIN
 INSERT INTO auth.users(id) VALUES(customer);
 INSERT INTO products(slug,name,lifecycle_status) VALUES('test-SUFFIX','Original Stickers','published') RETURNING id INTO product;
 INSERT INTO product_variants(product_id,sku,name,size_mm,unit_price,fulfillment_method,template_key)
 VALUES(product,'lost-SUFFIX','Small',30,0.10,'pdf_label','sticker-v1') RETURNING id INTO lost_variant;
 INSERT INTO product_variants(product_id,sku,name,size_mm,unit_price,fulfillment_method,template_key)
 VALUES(product,'ice-SUFFIX','Medium',35,0.20,'pdf_label','sticker-v1') RETURNING id INTO ice_variant;
 INSERT INTO shipping_addresses(customer_user_id,recipient_name_ciphertext,phone_ciphertext,address_ciphertext,city,key_version)
 VALUES(customer,decode('ab','hex'),decode('cd','hex'),decode('ef','hex'),'Lahore',1) RETURNING id INTO address;
 INSERT INTO qr_batches(batch_code,ecc_level) VALUES('test-SUFFIX','Q') RETURNING id INTO batch;
 INSERT INTO tag_pairs(pair_reference,batch_id) VALUES('test-SUFFIX',batch) RETURNING id INTO pair;
 INSERT INTO qr_codes(pair_id,tag_type,serial_number,public_token,ecc_level)
 VALUES(pair,'lost','lost-SUFFIX','lost-SUFFIX','Q') RETURNING id INTO lost;
 INSERT INTO qr_codes(pair_id,tag_type,serial_number,public_token,ecc_level)
 VALUES(pair,'ice','ice-SUFFIX','ice-SUFFIX','Q') RETURNING id INTO ice;
 INSERT INTO orders(order_number,customer_user_id,subtotal_pkr,shipping_pkr,tax_pkr,discount_pkr,total_pkr)
 VALUES('test-SUFFIX',customer,0.70,0.05,0.02,0.01,0.76) RETURNING id INTO purchase;
 INSERT INTO order_shipping_snapshots(order_id,source_address_id,recipient_name_ciphertext,phone_ciphertext,address_ciphertext,city,key_version)
 SELECT purchase,id,recipient_name_ciphertext,phone_ciphertext,address_ciphertext,city,key_version FROM shipping_addresses WHERE id=address;
 INSERT INTO order_pair_units(order_id,pair_id,reserved_until) VALUES(purchase,pair,now()+interval '1 hour') RETURNING id INTO unit;
 INSERT INTO order_items(order_id,product_id,variant_id,product_name_snapshot,variant_name_snapshot,sku_snapshot,size_mm_snapshot,fulfillment_method_snapshot,template_key_snapshot,template_version_snapshot,quantity,unit_price_snapshot,line_total)
 VALUES(purchase,product,lost_variant,'Original Stickers','Small','lost-SUFFIX',30,'pdf_label','sticker-v1',1,3,0.10,0.30) RETURNING id INTO item;
 INSERT INTO order_item_qr_uses(order_item_id,qr_code_id,pair_unit_id,use_kind,tag_type_snapshot,copies)
 VALUES(item,lost,unit,'new_pair','lost',3);
 INSERT INTO order_items(order_id,product_id,variant_id,product_name_snapshot,variant_name_snapshot,sku_snapshot,size_mm_snapshot,fulfillment_method_snapshot,template_key_snapshot,template_version_snapshot,quantity,unit_price_snapshot,line_total)
 VALUES(purchase,product,ice_variant,'Original Stickers','Medium','ice-SUFFIX',35,'pdf_label','sticker-v1',1,2,0.20,0.40) RETURNING id INTO item;
 INSERT INTO order_item_qr_uses(order_item_id,qr_code_id,pair_unit_id,use_kind,tag_type_snapshot,copies)
 VALUES(item,ice,unit,'new_pair','ice',2);
 INSERT INTO payment_attempts(order_id,provider_key,idempotency_key,amount)
 VALUES(purchase,'manual_bank','payment-SUFFIX',0.76);
END $$;
""".replace("SUFFIX", suffix)
        )
    )
    ids = dict(
        migrated.execute(
            text("""
SELECT o.id AS purchase,o.customer_user_id AS customer,p.id AS product,
 s.source_address_id AS address,u.id AS unit,u.pair_id AS pair,a.id AS attempt
FROM orders o JOIN order_shipping_snapshots s ON s.order_id=o.id
JOIN order_pair_units u ON u.order_id=o.id JOIN payment_attempts a ON a.order_id=o.id
JOIN products p ON p.slug=:slug WHERE o.order_number=:slug
"""),
            {"slug": "test-" + suffix},
        )
        .mappings()
        .one()
    )
    migrated.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    migrated.execute(text("SET CONSTRAINTS ALL DEFERRED"))
    return ids


@pytest.fixture
def commerce_conn(sample, migrated):
    nested = migrated.begin_nested()
    migrated.execute(text("SET CONSTRAINTS ALL DEFERRED"))
    try:
        yield migrated, sample
    finally:
        nested.rollback()


def sql(c, statement, ids):
    return c.execute(text(statement), ids)


def validate(c):
    c.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


def place(c, ids):
    sql(
        c,
        "UPDATE orders SET order_status='placed',placed_at=now() WHERE id=:purchase",
        ids,
    )
    validate(c)
    c.execute(text("SET CONSTRAINTS ALL DEFERRED"))


def pay(c, ids):
    sql(
        c,
        "INSERT INTO payment_reviews(attempt_id,reviewed_by,decision,bank_verified,bank_reference_fingerprint,bank_reference_key_version) VALUES (:attempt,:customer,'verify',true,decode('abcdef','hex'),1)",
        ids,
    )
    sql(
        c,
        "UPDATE payment_attempts SET state='verified',verified_at=now(),reviewed_by=:customer WHERE id=:attempt",
        ids,
    )
    sql(c, "UPDATE orders SET payment_status='verified' WHERE id=:purchase", ids)
    sql(
        c,
        "UPDATE order_pair_units SET status='allocated',allocated_at=now(),allocated_by=:customer WHERE id=:unit",
        ids,
    )
    validate(c)
    c.execute(text("SET CONSTRAINTS ALL DEFERRED"))


def qa(c, ids, approved=True):
    sql(
        c,
        """INSERT INTO pair_print_qa(pair_id,qa_round,lost_scan_passed,ice_scan_passed,pair_match_passed,
 credential_concealed,bilingual_label_passed,quiet_zone_passed,indoor_size_passed,outdoor_size_passed,
 packaging_method,tamper_evidence_passed,approved,inspected_by)
 VALUES(:pair,1,true,true,true,true,true,true,true,true,'sealed_sleeve',true,:approved,:customer)""",
        {**ids, "approved": approved},
    )


def shipment(c, ids):
    return sql(
        c,
        "INSERT INTO shipments(order_id,shipping_address_id) VALUES(:purchase,:address) RETURNING id",
        ids,
    ).scalar_one()


def test_five_copies_use_two_identities_one_pair_and_decimal_snapshots(commerce_conn):
    c, ids = commerce_conn
    place(c, ids)
    with Session(bind=c, join_transaction_mode="create_savepoint") as session:
        order = session.get(Order, ids["purchase"])
        assert order.total_pkr == Decimal("0.76")
        assert order.tax_pkr == Decimal("0.02")
        items = session.query(OrderItem).filter_by(order_id=order.id).all()
        assert sorted(i.quantity for i in items) == [2, 3]
        assert {i.size_mm_snapshot for i in items} == {
            Decimal("30.00"),
            Decimal("35.00"),
        }
        assert all(isinstance(i.unit_price_snapshot, Decimal) for i in items)
        assert (
            session.query(ProductVariant).filter_by(product_id=ids["product"]).count()
            == 2
        )
    assert (
        sql(c, "SELECT count(*) FROM qr_codes WHERE pair_id=:pair", ids).scalar_one()
        == 2
    )
    assert (
        sql(
            c, "SELECT count(*) FROM order_pair_units WHERE order_id=:purchase", ids
        ).scalar_one()
        == 1
    )


def test_catalog_and_account_edits_preserve_purchase_history(commerce_conn):
    c, ids = commerce_conn
    place(c, ids)
    sql(
        c,
        "UPDATE products SET name='Renamed',lifecycle_status='archived' WHERE id=:product",
        ids,
    )
    sql(
        c,
        "UPDATE product_variants SET unit_price=99,name='Changed',size_mm=45,is_active=false WHERE product_id=:product",
        ids,
    )
    sql(
        c,
        "UPDATE shipping_addresses SET address_ciphertext=decode('aa','hex'),city='Karachi' WHERE id=:address",
        ids,
    )
    assert (
        sql(
            c,
            "SELECT DISTINCT product_name_snapshot FROM order_items WHERE order_id=:purchase",
            ids,
        ).scalar_one()
        == "Original Stickers"
    )
    assert sql(
        c,
        "SELECT city,address_ciphertext FROM order_shipping_snapshots WHERE order_id=:purchase",
        ids,
    ).one() == ("Lahore", bytes.fromhex("ef"))
    validate(c)


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE orders SET total_pkr=1,subtotal_pkr=0.94 WHERE id=:purchase",
        "UPDATE orders SET placed_at=NULL,order_status='draft' WHERE id=:purchase",
        "UPDATE order_items SET product_name_snapshot='Changed' WHERE order_id=:purchase",
        "UPDATE order_shipping_snapshots SET city='Karachi' WHERE order_id=:purchase",
        "UPDATE order_item_qr_uses SET copies=9 WHERE pair_unit_id=:unit",
        "DELETE FROM orders WHERE id=:purchase",
    ],
)
def test_placed_order_records_are_immutable(commerce_conn, statement):
    c, ids = commerce_conn
    place(c, ids)
    with pytest.raises(IntegrityError):
        sql(c, statement, ids)


@pytest.mark.parametrize(
    "case", ["copies", "missing_ice", "subtotal", "currency", "address"]
)
def test_incomplete_checkout_cannot_pass_deferred_checks(commerce_conn, case):
    c, ids = commerce_conn
    if case == "copies":
        sql(
            c,
            "UPDATE order_item_qr_uses SET copies=2 WHERE pair_unit_id=:unit AND tag_type_snapshot='lost'",
            ids,
        )
    elif case == "missing_ice":
        sql(
            c,
            "DELETE FROM order_item_qr_uses WHERE pair_unit_id=:unit AND tag_type_snapshot='ice'",
            ids,
        )
        sql(
            c,
            "DELETE FROM order_items WHERE order_id=:purchase AND variant_name_snapshot='Medium'",
            ids,
        )
        sql(
            c,
            "UPDATE orders SET subtotal_pkr=0.30,total_pkr=0.36 WHERE id=:purchase",
            ids,
        )
    elif case == "subtotal":
        sql(
            c, "UPDATE orders SET subtotal_pkr=1,total_pkr=1.06 WHERE id=:purchase", ids
        )
    elif case == "currency":
        sql(
            c,
            "UPDATE order_items SET currency_code='USD' WHERE order_id=:purchase",
            ids,
        )
    else:
        sql(c, "DELETE FROM order_shipping_snapshots WHERE order_id=:purchase", ids)
    sql(
        c,
        "UPDATE orders SET order_status='placed',placed_at=now() WHERE id=:purchase",
        ids,
    )
    with pytest.raises(IntegrityError):
        validate(c)


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE order_item_qr_uses SET tag_type_snapshot='ice' WHERE pair_unit_id=:unit AND tag_type_snapshot='lost'",
        "UPDATE order_item_qr_uses SET use_kind='existing_owned',pair_unit_id=NULL WHERE pair_unit_id=:unit",
        "UPDATE order_item_qr_uses SET copies=0 WHERE pair_unit_id=:unit",
        "UPDATE order_items SET quantity=0 WHERE order_id=:purchase",
        "UPDATE order_items SET line_total=99 WHERE order_id=:purchase",
        "UPDATE product_variants SET size_mm=0 WHERE product_id=:product",
        "UPDATE product_variants SET unit_price=-1 WHERE product_id=:product",
    ],
)
def test_relations_quantities_and_prices_reject_direct_sql(commerce_conn, statement):
    c, ids = commerce_conn
    with pytest.raises(IntegrityError):
        sql(c, statement, ids)


def test_exclusive_reservation_and_no_silent_allocation(commerce_conn):
    c, ids = commerce_conn
    with pytest.raises(IntegrityError):
        sql(
            c,
            "INSERT INTO order_pair_units(order_id,pair_id,reserved_until) VALUES(:purchase,:pair,now()+interval '1 hour')",
            ids,
        )


@pytest.mark.parametrize("state", ["submitted", "under_review", "verified", "disputed"])
def test_payment_review_protects_reservation_from_expiry(commerce_conn, state):
    c, ids = commerce_conn
    if state == "verified":
        place(c, ids)
        # Verify payment without allocating, so the reservation release guard is exercised.
        sql(
            c,
            "INSERT INTO payment_reviews(attempt_id,reviewed_by,decision,bank_verified,bank_reference_fingerprint,bank_reference_key_version) VALUES(:attempt,:customer,'verify',true,decode('ab','hex'),1)",
            ids,
        )
        sql(
            c,
            "UPDATE payment_attempts SET state='verified',verified_at=now(),reviewed_by=:customer WHERE id=:attempt",
            ids,
        )
    else:
        sql(
            c,
            "UPDATE payment_attempts SET state=:state WHERE id=:attempt",
            {**ids, "state": state},
        )
    with pytest.raises(IntegrityError):
        sql(
            c,
            "UPDATE order_pair_units SET status='released',released_at=now() WHERE id=:unit",
            ids,
        )


def test_unpaid_reservation_can_be_closed_but_not_resurrected(commerce_conn):
    c, ids = commerce_conn
    sql(
        c,
        "UPDATE order_pair_units SET status='released',released_at=now() WHERE id=:unit",
        ids,
    )
    with pytest.raises(IntegrityError):
        sql(c, "UPDATE order_pair_units SET status='reserved' WHERE id=:unit", ids)


def test_unverified_payment_cannot_allocate_pair(commerce_conn):
    c, ids = commerce_conn
    place(c, ids)
    with pytest.raises(IntegrityError):
        sql(
            c,
            "UPDATE order_pair_units SET status='allocated',allocated_at=now() WHERE id=:unit",
            ids,
        )


def test_manual_verification_requires_review_even_with_timestamp(commerce_conn):
    c, ids = commerce_conn
    place(c, ids)
    sql(
        c,
        "UPDATE payment_attempts SET state='verified',verified_at=now(),reviewed_by=:customer WHERE id=:attempt",
        ids,
    )
    with pytest.raises(IntegrityError):
        validate(c)


def test_evidence_upload_does_not_verify_payment(commerce_conn):
    c, ids = commerce_conn
    sql(
        c,
        "INSERT INTO payment_evidence(attempt_id,object_key,sha256_hex,content_type,bytes_size) VALUES(:attempt,'synthetic-receipt',repeat('a',64),'image/png',100)",
        ids,
    )
    validate(c)
    assert (
        sql(c, "SELECT state FROM payment_attempts WHERE id=:attempt", ids).scalar_one()
        == "initiated"
    )
    assert (
        sql(c, "SELECT payment_status FROM orders WHERE id=:purchase", ids).scalar_one()
        == "awaiting_transfer"
    )


@pytest.mark.parametrize(
    "case",
    [
        "idempotency",
        "external",
        "bank_reference",
        "review_without_bank",
        "amount",
        "sender_key",
        "public_bucket",
    ],
)
def test_payment_security_and_deduplication(commerce_conn, case):
    c, ids = commerce_conn
    if case == "external":
        sql(
            c,
            "UPDATE payment_attempts SET provider_external_id='settlement-one' WHERE id=:attempt",
            ids,
        )
    elif case == "bank_reference":
        sql(
            c,
            "INSERT INTO payment_reviews(attempt_id,reviewed_by,decision,bank_verified,bank_reference_fingerprint,bank_reference_key_version) VALUES(:attempt,:customer,'verify',true,decode('ab','hex'),1)",
            ids,
        )
    with pytest.raises(IntegrityError):
        if case == "idempotency":
            sql(
                c,
                "INSERT INTO payment_attempts(order_id,provider_key,idempotency_key,amount) SELECT order_id,provider_key,idempotency_key,amount FROM payment_attempts WHERE id=:attempt",
                ids,
            )
        elif case == "external":
            sql(
                c,
                "INSERT INTO payment_attempts(order_id,provider_key,idempotency_key,provider_external_id,amount) VALUES(:purchase,'manual_bank','other','settlement-one',0.76)",
                ids,
            )
        elif case == "bank_reference":
            sql(
                c,
                "INSERT INTO payment_reviews(attempt_id,reviewed_by,decision,bank_verified,bank_reference_fingerprint,bank_reference_key_version) VALUES(:attempt,:customer,'verify',true,decode('ab','hex'),1)",
                ids,
            )
        elif case == "review_without_bank":
            sql(
                c,
                "INSERT INTO payment_reviews(attempt_id,reviewed_by,decision) VALUES(:attempt,:customer,'verify')",
                ids,
            )
        elif case == "amount":
            sql(c, "UPDATE payment_attempts SET amount=1 WHERE id=:attempt", ids)
        elif case == "sender_key":
            sql(
                c,
                "UPDATE payment_attempts SET sender_holder_ciphertext=decode('ab','hex') WHERE id=:attempt",
                ids,
            )
        else:
            sql(
                c,
                "INSERT INTO payment_evidence(attempt_id,bucket,object_key,sha256_hex,content_type,bytes_size) VALUES(:attempt,'public','bad',repeat('a',64),'image/png',100)",
                ids,
            )


def test_verified_settlement_allocates_once_and_keeps_entitlement(commerce_conn):
    c, ids = commerce_conn
    place(c, ids)
    pay(c, ids)
    sql(c, "UPDATE order_pair_units SET status='allocated' WHERE id=:unit", ids)
    validate(c)
    assert (
        sql(
            c,
            "SELECT count(*) FROM order_pair_units WHERE pair_id=:pair AND status='allocated'",
            ids,
        ).scalar_one()
        == 1
    )
    with pytest.raises(IntegrityError):
        sql(
            c,
            "UPDATE order_pair_units SET status='released',released_at=now() WHERE id=:unit",
            ids,
        )


@pytest.mark.parametrize("case", ["unpaid", "wrong_order", "no_qa", "empty_dispatch"])
def test_fulfillment_requires_payment_membership_and_physical_qa(commerce_conn, case):
    c, ids = commerce_conn
    place(c, ids)
    if case == "unpaid":
        with pytest.raises(IntegrityError):
            shipment(c, ids)
        return
    pay(c, ids)
    sid = shipment(c, ids)
    with pytest.raises(IntegrityError):
        if case == "wrong_order":
            other_pair, _ = pair(c)
            sql(
                c,
                "INSERT INTO shipment_pairs(shipment_id,pair_id) VALUES(:sid,:pair)",
                {"sid": sid, "pair": other_pair},
            )
        elif case == "no_qa":
            sql(
                c,
                "INSERT INTO shipment_pairs(shipment_id,pair_id,packed_qa_confirmed,packed_by,packed_at) VALUES(:sid,:pair,true,:customer,now())",
                {**ids, "sid": sid},
            )
        else:
            sql(
                c,
                "UPDATE shipments SET status='dispatched',dispatched_at=now() WHERE id=:sid",
                {"sid": sid},
            )
            validate(c)


def test_paid_allocated_qa_approved_pair_can_ship(commerce_conn):
    c, ids = commerce_conn
    place(c, ids)
    pay(c, ids)
    qa(c, ids)
    sid = shipment(c, ids)
    sql(
        c,
        "INSERT INTO shipment_pairs(shipment_id,pair_id,packed_qa_confirmed,packed_by,packed_at) VALUES(:sid,:pair,true,:customer,now())",
        {**ids, "sid": sid},
    )
    sql(
        c,
        "UPDATE shipments SET status='dispatched',dispatched_at=now() WHERE id=:sid",
        {"sid": sid},
    )
    validate(c)
    assert (
        sql(c, "SELECT status FROM shipments WHERE id=:sid", {"sid": sid}).scalar_one()
        == "dispatched"
    )


def test_commerce_browser_access_denied_and_unknown_schema_not_adopted(
    commerce_conn, monkeypatch
):
    c, _ = commerce_conn
    assert c.execute(
        text(
            "SELECT has_table_privilege('anon','orders','SELECT'),has_table_privilege('authenticated','payment_reviews','INSERT')"
        )
    ).one() == (False, False)
    path = Path(__file__).parents[2] / "alembic/versions/0002_commerce.py"
    spec = importlib.util.spec_from_file_location("commerce_revision", path)
    revision = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(revision)
    monkeypatch.setattr(revision.op, "get_bind", lambda: c)
    with pytest.raises(RuntimeError, match="explicit reconciliation"):
        revision.upgrade()
    with pytest.raises(RuntimeError, match="Destructive downgrade"):
        revision.downgrade()
    assert inspect(c).has_table("orders")


def test_qr_use_must_match_pair_unit_and_order(commerce_conn):
    c, ids = commerce_conn
    other_pair, _ = pair(c)
    other_order = sql(
        c,
        "INSERT INTO orders(order_number,customer_user_id,subtotal_pkr,total_pkr) VALUES(:number,:customer,0,0) RETURNING id",
        {**ids, "number": uuid.uuid4().hex},
    ).scalar_one()
    other_unit = sql(
        c,
        "INSERT INTO order_pair_units(order_id,pair_id,reserved_until) VALUES(:order,:pair,now()+interval '1 hour') RETURNING id",
        {"order": other_order, "pair": other_pair},
    ).scalar_one()
    with pytest.raises(IntegrityError):
        sql(
            c,
            "UPDATE order_item_qr_uses SET pair_unit_id=:other WHERE pair_unit_id=:unit",
            {**ids, "other": other_unit},
        )


def test_verified_amount_mismatch_is_rejected(commerce_conn):
    c, ids = commerce_conn
    place(c, ids)
    attempt = sql(
        c,
        "INSERT INTO payment_attempts(order_id,provider_key,idempotency_key,amount) VALUES(:purchase,'manual_bank','wrong-amount',0.75) RETURNING id",
        ids,
    ).scalar_one()
    sql(
        c,
        "INSERT INTO payment_reviews(attempt_id,reviewed_by,decision,bank_verified,bank_reference_fingerprint,bank_reference_key_version) VALUES(:attempt,:customer,'verify',true,decode('dd','hex'),1)",
        {**ids, "attempt": attempt},
    )
    sql(
        c,
        "UPDATE payment_attempts SET state='verified',verified_at=now(),reviewed_by=:customer WHERE id=:attempt",
        {**ids, "attempt": attempt},
    )
    with pytest.raises(IntegrityError):
        validate(c)


def test_order_cannot_claim_verified_without_settlement(commerce_conn):
    c, ids = commerce_conn
    place(c, ids)
    sql(c, "UPDATE orders SET payment_status='verified' WHERE id=:purchase", ids)
    with pytest.raises(IntegrityError):
        validate(c)


def test_latest_failed_qa_prevents_shipment_release(commerce_conn):
    c, ids = commerce_conn
    place(c, ids)
    pay(c, ids)
    qa(c, ids, approved=False)
    sid = shipment(c, ids)
    with pytest.raises(IntegrityError):
        sql(
            c,
            "INSERT INTO shipment_pairs(shipment_id,pair_id,packed_qa_confirmed,packed_by,packed_at) VALUES(:sid,:pair,true,:customer,now())",
            {**ids, "sid": sid},
        )


@pytest.mark.parametrize("case", ["review", "allocation_identity", "qa_false_approval"])
def test_historical_review_allocation_and_qa_guards(commerce_conn, case):
    c, ids = commerce_conn
    place(c, ids)
    pay(c, ids)
    with pytest.raises(IntegrityError):
        if case == "review":
            sql(
                c,
                "UPDATE payment_reviews SET decision='reject' WHERE attempt_id=:attempt",
                ids,
            )

        elif case == "allocation_identity":
            sql(
                c,
                "UPDATE order_pair_units SET allocated_at=now()+interval '1 second' WHERE id=:unit",
                ids,
            )
        else:
            sql(
                c,
                """INSERT INTO pair_print_qa(pair_id,qa_round,lost_scan_passed,ice_scan_passed,pair_match_passed,
 credential_concealed,bilingual_label_passed,quiet_zone_passed,indoor_size_passed,outdoor_size_passed,
 packaging_method,tamper_evidence_passed,approved,inspected_by)
 VALUES(:pair,1,false,true,true,true,true,true,true,true,'sealed_sleeve',true,true,:customer)""",
                ids,
            )


def test_refund_requires_order_payment_reconciliation(commerce_conn):
    c, ids = commerce_conn
    place(c, ids)
    pay(c, ids)
    sql(c, "UPDATE payment_attempts SET state='refunded' WHERE id=:attempt", ids)
    with pytest.raises(IntegrityError):
        validate(c)


def test_refunded_order_cannot_create_shipment(commerce_conn):
    c, ids = commerce_conn
    place(c, ids)
    pay(c, ids)
    sql(c, "UPDATE payment_attempts SET state='refunded' WHERE id=:attempt", ids)
    sql(c, "UPDATE orders SET payment_status='refunded' WHERE id=:purchase", ids)
    validate(c)
    with pytest.raises(IntegrityError):
        shipment(c, ids)


def test_refund_in_same_transaction_prevents_dispatch(commerce_conn):
    c, ids = commerce_conn
    place(c, ids)
    pay(c, ids)
    qa(c, ids)
    sid = shipment(c, ids)
    sql(
        c,
        "INSERT INTO shipment_pairs(shipment_id,pair_id,packed_qa_confirmed,packed_by,packed_at) VALUES(:sid,:pair,true,:customer,now())",
        {**ids, "sid": sid},
    )
    sql(
        c,
        "UPDATE shipments SET status='dispatched',dispatched_at=now() WHERE id=:sid",
        {"sid": sid},
    )
    sql(c, "UPDATE payment_attempts SET state='refunded' WHERE id=:attempt", ids)
    sql(c, "UPDATE orders SET payment_status='refunded' WHERE id=:purchase", ids)
    with pytest.raises(IntegrityError):
        validate(c)
