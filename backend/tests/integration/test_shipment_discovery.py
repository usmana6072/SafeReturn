"""Bounded synthetic fulfillment UI acceptance using existing isolated harness."""

from test_fulfillment import (  # noqa: F401
    checkout_sample,
    payment_sample,
    print_sample,
    sample,
    test_create_idempotency_concurrency_membership_and_address,
    test_exception_path_cannot_bypass_dispatch,
    test_operations_address_access_and_finance_minimization,
    test_ordered_pack_dispatch_delivery_and_retry,
    test_refund_pauses_outbound_and_allows_safe_exception,
)
from test_health import ASGIClient


def test_shipment_discovery_browser(sample):  # noqa: F811
    from checkout_browser import run

    body, _ = sample[2]()
    app = sample[3]
    app.state.checkout_fixture_token = lambda: sample[4]()
    app.state.checkout_fixture_user = app.state.printing_fixture_user
    base = sample[5][0]
    run(
        (base[0], ASGIClient(app), base[2], app, *base[4:]),
        test_files=["tests/shipment-discovery.spec.ts"],
        extra_env={"FULFILLMENT_ORDER": body["order_id"]},
    )
