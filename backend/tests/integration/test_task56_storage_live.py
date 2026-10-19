"""Live private-storage acceptance confined to fresh Task 5.6 disposable objects."""

import hashlib
import os
from uuid import uuid4

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.integrations.payment_storage import PaymentStorage
from app.integrations.print_storage import PrintStore
from app.integrations.storage_deletion import object_missing


@pytest.mark.parametrize("kind", ["print", "evidence"])
def test_disposable_private_object_delete_and_absence(kind):
    if os.environ.get("SAFERETURN_TASK56_LIVE_STORAGE") != "1":
        pytest.skip("Explicit disposable live-storage opt-in is required")
    origin = os.environ.get("SAFERETURN_SUPABASE_URL")
    secret = os.environ.get("SAFERETURN_SUPABASE_STORAGE_SERVICE_KEY")
    if not origin or not secret:
        pytest.skip("Private storage is unconfigured; keep cleanup disabled")
    settings = Settings(
        supabase_url=origin, supabase_storage_service_key=SecretStr(secret)
    )
    store = PrintStore(settings) if kind == "print" else PaymentStorage(settings)
    bucket = "private-order-print" if kind == "print" else "private-payment-evidence"
    prefix = "order-print" if kind == "print" else "payment-evidence"
    namespace = uuid4().hex
    key = f"{prefix}/task56-{namespace}/synthetic.pdf"
    data = (
        b"%PDF-1.4\n% Disposable Task 5.6 synthetic object; no customer data.\n%%EOF\n"
    )
    assert namespace in key and "task56-" in key
    with store.client() as client:
        policy = client.get("bucket/" + bucket)
        assert policy.status_code == 200 and policy.json().get("public") is False
        absent = client.get(
            "object/info/authenticated/" + bucket + "/" + key,
            params={"verification": uuid4().hex},
        )
        assert object_missing(absent), (
            "Disposable UUID object key must be absent before upload"
        )
        try:
            uploaded = client.post(
                "object/" + bucket + "/" + key,
                content=data,
                headers={"Content-Type": "application/pdf", "x-upsert": "false"},
            )
            assert uploaded.status_code in (200, 201)
            response = client.get("object/authenticated/" + bucket + "/" + key)
            assert response.status_code == 200
            assert (
                hashlib.sha256(response.content).digest()
                == hashlib.sha256(data).digest()
            )
            # Anonymous readers must not receive either a private body or URL.
            import httpx

            denied = httpx.get(
                origin + "/storage/v1/object/authenticated/" + bucket + "/" + key,
                timeout=10,
            )
            assert denied.status_code != 200
            assert store.delete(key) is True
            assert store.delete(key) is True
        finally:
            # Only this execution's random, test-owned object is addressed.
            removed = client.request(
                "DELETE", "object/" + bucket, json={"prefixes": [key]}
            )
            assert removed.status_code in (200, 204) or object_missing(removed)
            assert object_missing(
                client.get(
                    "object/info/authenticated/" + bucket + "/" + key,
                    params={"verification": uuid4().hex},
                )
            )
