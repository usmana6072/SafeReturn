"""Focused local unit tests for Google Sheets finance mirror, worker leasing, and retention cleanup."""

import json
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings
from app.integrations.payment_storage import PaymentStorage
from app.integrations.print_storage import PrintStore
from app.workers.finance_retention import (
    SHEET_COLUMNS,
    GoogleSheetsProvider,
    SheetProviderError,
    StorageStore,
    build_masked_sheet_projection,
)


def test_build_masked_sheet_projection_data_minimization():
    order_id = uuid4()
    row = {
        "order_id": order_id,
        "order_number": "ORD-12345",
        "payment_status": "verified",
        "fulfillment_status": "allocated",
        "currency_code": "PKR",
        "total_pkr": Decimal("1500.00"),
        "payment_method": "manual_bank",
        "last_export_version": 2,
    }

    projection = build_masked_sheet_projection(row)

    assert projection.row_key == str(order_id)
    assert projection.values["order_id"] == str(order_id)
    assert projection.values["order_number"] == "ORD-12345"
    assert projection.values["payment_status"] == "verified"
    assert projection.values["fulfillment_status"] == "allocated"
    assert projection.values["currency"] == "PKR"
    assert projection.values["amount"] == "1500.00"
    assert projection.values["payment_method"] == "manual_bank"
    assert projection.values["sender_account"] == "masked"
    assert projection.values["evidence"] == "private"
    assert projection.values["export_version"] == "3"

    # Confirm sensitive identifiers never exist in projection values
    serialized = json.dumps(projection.values)
    for forbidden in [
        "iban",
        "account_number",
        "http://",
        "https://",
        "ice",
        "medical",
        "secret",
        "token",
    ]:
        assert forbidden not in serialized.lower()


def test_google_sheets_provider_unconfigured_fails_closed():
    settings = Settings(
        google_sheets_spreadsheet_id=None,
        google_sheets_service_account_json=None,
        google_sheets_approved=False,
    )
    provider = GoogleSheetsProvider(settings)

    with pytest.raises(SheetProviderError) as exc_info:
        provider.upsert(row_key="key-1", values={"order_id": "1"})
    assert exc_info.value.code == "google_sheets_not_configured"
    assert exc_info.value.transient is False


def test_google_sheets_provider_invalid_json_credentials():
    settings = Settings(
        google_sheets_spreadsheet_id="sheet-123",
        google_sheets_service_account_json=SecretStr("not-valid-json"),
    )
    provider = GoogleSheetsProvider(settings)

    with pytest.raises(SheetProviderError) as exc_info:
        provider.upsert(row_key="key-1", values={"order_id": "1"})
    assert exc_info.value.code == "google_sheets_invalid_credentials"
    assert exc_info.value.transient is False


def test_payment_storage_delete_idempotent():
    deleted_keys = []

    def mock_handler(request: httpx.Request):
        if "/bucket/" in request.url.path:
            return httpx.Response(200, json={"public": False})
        if request.method == "DELETE":
            deleted_keys.append(request.url.path)
            return httpx.Response(204)
        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)
    settings = Settings(
        supabase_url="https://test.supabase.co",
        supabase_storage_service_key=SecretStr("secret-key"),
    )
    storage = PaymentStorage(settings, transport=transport)

    assert storage.delete("payment-evidence/ord-1/attempt-1/proof.png") is True
    assert len(deleted_keys) == 1
    assert "payment-evidence/ord-1/attempt-1/proof.png" in deleted_keys[0]

    # Re-run: 404 response is treated as idempotent success
    def mock_404_handler(request: httpx.Request):
        if "/bucket/" in request.url.path:
            return httpx.Response(200, json={"public": False})
        return httpx.Response(404)

    storage_404 = PaymentStorage(
        settings, transport=httpx.MockTransport(mock_404_handler)
    )
    assert storage_404.delete("payment-evidence/ord-1/attempt-1/proof.png") is True


def test_print_storage_delete_idempotent():
    deleted_keys = []

    def mock_handler(request: httpx.Request):
        if "/bucket/" in request.url.path:
            return httpx.Response(200, json={"public": False})
        if request.method == "DELETE":
            deleted_keys.append(request.url.path)
            return httpx.Response(200)
        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)
    settings = Settings(
        supabase_url="https://test.supabase.co",
        supabase_storage_service_key=SecretStr("secret-key"),
    )
    store = PrintStore(settings, transport=transport)

    assert store.delete("order-print/ord-1/job-1/digest.pdf") is True
    assert len(deleted_keys) == 1
    assert "order-print/ord-1/job-1/digest.pdf" in deleted_keys[0]

    # Re-run: 404 is also idempotent success
    store_404 = PrintStore(
        settings,
        transport=httpx.MockTransport(
            lambda r: (
                httpx.Response(200, json={"public": False})
                if "/bucket/" in r.url.path
                else httpx.Response(404)
            )
        ),
    )
    assert store_404.delete("order-print/ord-1/job-1/digest.pdf") is True


def test_storage_store_adapter_routing():
    settings = Settings(
        supabase_url="https://test.supabase.co",
        supabase_storage_service_key=SecretStr("secret-key"),
    )
    called = []

    def handler(request: httpx.Request):
        if "/bucket/" in request.url.path:
            return httpx.Response(200, json={"public": False})
        if request.method == "DELETE":
            called.append(request.url.path)
            return httpx.Response(204)
        return httpx.Response(404)

    unified = StorageStore(
        settings,
        payment_transport=httpx.MockTransport(handler),
        print_transport=httpx.MockTransport(handler),
    )

    assert (
        unified.delete(bucket="private-payment-evidence", object_key="proof.pdf")
        is True
    )
    assert unified.delete(bucket="private-order-print", object_key="label.pdf") is True
    assert len(called) == 2

    with pytest.raises(ValueError, match="Unsupported storage bucket"):
        unified.delete(bucket="unknown-bucket", object_key="file.bin")


def test_retention_hold_request_validation():
    from app.api.v1.retention import RetentionHoldRequest

    # Valid reason codes
    valid = RetentionHoldRequest(reason_code="legal_dispute_123")
    assert valid.reason_code == "legal_dispute_123"

    valid_chars = RetentionHoldRequest(reason_code="CHARGEBACK-2026.10")
    assert valid_chars.reason_code == "CHARGEBACK-2026.10"

    # Invalid reason codes (spaces, special chars, empty)
    with pytest.raises(ValidationError):
        RetentionHoldRequest(reason_code="invalid spaces")

    with pytest.raises(ValidationError):
        RetentionHoldRequest(reason_code="invalid;drop")

    with pytest.raises(ValidationError):
        RetentionHoldRequest(reason_code="")


def test_cursor_pagination_roundtrip():
    from datetime import UTC, datetime

    from app.api.v1.retention import _encode_cursor, _parse_cursor

    now = datetime.now(UTC)
    ident = uuid4()

    cursor_str = _encode_cursor(now, ident)
    parsed_ts, parsed_id = _parse_cursor(cursor_str)

    assert parsed_ts == now
    assert parsed_id == ident

    # Corrupt cursor handling
    corrupt_ts, corrupt_id = _parse_cursor("invalid-base64-string!!")
    assert corrupt_ts is None
    assert corrupt_id is None


def provider_settings():
    return Settings(
        google_sheets_spreadsheet_id="synthetic-sheet",
        google_sheets_tab="SyntheticMirror",
        google_sheets_approved=True,
        google_sheets_service_account_json=SecretStr(
            json.dumps(
                {
                    "client_email": "synthetic@example.invalid",
                    "private_key": "synthetic",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            )
        ),
    )


def test_sheet_approval_gate_never_calls_network():
    settings = provider_settings()
    settings.google_sheets_approved = False
    provider = GoogleSheetsProvider(
        settings,
        transport=httpx.MockTransport(lambda r: pytest.fail("unapproved network call")),
    )
    with pytest.raises(SheetProviderError, match="not_approved"):
        provider.upsert(row_key="synthetic", values={})


def test_google_upsert_recovers_ambiguous_append_and_uses_raw(monkeypatch):
    monkeypatch.setattr("jwt.encode", lambda *a, **k: "synthetic-assertion")
    rows = [SHEET_COLUMNS.copy()]
    writes = []

    def handler(r):
        if r.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "synthetic"})
        if r.method == "GET":
            return httpx.Response(200, json={"values": rows})
        assert r.url.params["valueInputOption"] == "RAW"
        data = json.loads(r.content)["values"][0]
        writes.append(r.method)
        if r.method == "POST":
            rows.append(data)
            raise httpx.ReadTimeout("synthetic lost acknowledgement")
        rows[1] = data
        return httpx.Response(200, json={})

    provider = GoogleSheetsProvider(
        provider_settings(), transport=httpx.MockTransport(handler)
    )
    values = build_masked_sheet_projection(
        {
            "order_id": uuid4(),
            "order_number": "=IMPORTXML(x)",
            "payment_status": "verified",
            "currency_code": "PKR",
            "total_pkr": "12.00",
        }
    ).values
    with pytest.raises(SheetProviderError):
        provider.upsert(row_key=values["order_id"], values=values)
    provider.upsert(row_key=values["order_id"], values=values)
    assert writes == ["POST", "PUT"] and len(rows) == 2


@pytest.mark.parametrize(
    "rows,code",
    [
        ([["same"] * 11, ["same"] * 11], "duplicate_sheet_rows"),
        ([["same"] * 9 + ["99"]], "sheet_version_conflict"),
    ],
)
def test_google_reconciliation_conflicts_never_write(monkeypatch, rows, code):
    monkeypatch.setattr("jwt.encode", lambda *a, **k: "synthetic")

    def handler(r):
        if r.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "synthetic"})
        assert r.method == "GET"
        return httpx.Response(200, json={"values": [SHEET_COLUMNS, *rows]})

    with pytest.raises(SheetProviderError, match=code):
        GoogleSheetsProvider(
            provider_settings(), transport=httpx.MockTransport(handler)
        ).upsert(row_key="same", values={"order_id": "same", "export_version": "1"})


@pytest.mark.parametrize("status", [200, 401, 403, 500, 302])
def test_storage_delete_requires_authoritative_absence(status):
    def handler(r):
        if "/bucket/" in r.url.path:
            return httpx.Response(200, json={"public": False})
        return httpx.Response(204 if r.method == "DELETE" else status)

    store = PrintStore(
        Settings(
            supabase_url="https://test.supabase.co",
            supabase_storage_service_key=SecretStr("synthetic"),
        ),
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(OSError, match="unconfirmed"):
        store.delete("synthetic/test.pdf")


def test_retention_without_policy_never_touches_database_or_storage():
    from app.workers.finance_retention import cleanup_private_artifact

    assert (
        cleanup_private_artifact(
            None, None, worker_id="synthetic", artifact_id=uuid4(), settings=Settings()
        )["reason"]
        == "policy_not_approved"
    )


@pytest.mark.parametrize(
    "error,accepted",
    [
        ({"statusCode": "404", "code": "NoSuchKey"}, True),
        (
            {"statusCode": "404", "error": "not_found", "message": "Object not found"},
            True,
        ),
        (
            {
                "statusCode": "404",
                "error": "Bucket not found",
                "message": "Bucket not found",
            },
            False,
        ),
        (
            {"statusCode": "403", "error": "not_found", "message": "Object not found"},
            False,
        ),
        ({"statusCode": "400"}, False),
    ],
)
def test_typed_storage_absence_is_narrow(error, accepted):
    from app.integrations.storage_deletion import object_missing

    assert object_missing(httpx.Response(400, json=error)) is accepted


def test_sheet_credential_endpoint_cannot_exfiltrate_assertion():
    settings = provider_settings()
    settings.google_sheets_service_account_json = SecretStr(
        json.dumps(
            {
                "client_email": "synthetic@example.invalid",
                "private_key": "synthetic",
                "token_uri": "https://untrusted.invalid/token",
            }
        )
    )
    provider = GoogleSheetsProvider(
        settings,
        transport=httpx.MockTransport(
            lambda r: pytest.fail("untrusted credential request")
        ),
    )
    with pytest.raises(SheetProviderError, match="invalid_credentials"):
        provider.upsert(row_key="same", values={"order_id": "same"})


def test_provider_error_code_cannot_embed_secret_or_url():
    assert (
        SheetProviderError("https://private.invalid/full-bank-identifier").code
        == "provider_failure"
    )


def test_private_http_access_logs_omit_urls_keys_and_credentials(caplog):
    import logging

    caplog.set_level(logging.INFO, logger="httpx")

    def handler(r):
        if "/bucket/" in r.url.path:
            return httpx.Response(200, json={"public": False})
        return httpx.Response(204 if r.method == "DELETE" else 404)

    store = PrintStore(
        Settings(
            supabase_url="https://private-project.supabase.co",
            supabase_storage_service_key=SecretStr("server-only-secret"),
        ),
        transport=httpx.MockTransport(handler),
    )
    assert store.delete("order-print/synthetic-private-capability/fixture.pdf")
    assert caplog.records
    for record in caplog.records:
        value = str(record.__dict__)
        assert (
            "https://" not in value
            and "synthetic-private-capability" not in value
            and "server-only-secret" not in value
        )
