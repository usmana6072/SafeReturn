"""Bounded private-storage adapter checks; no network access."""

import hashlib

import httpx
import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from app.api.auth import AccessError
from app.core.config import Settings
from app.integrations.payment_storage import PaymentStorage

PDF = b"%PDF-1.7\nsynthetic\n%%EOF"


def adapter(handler):
    return PaymentStorage(
        Settings(
            supabase_url="https://storage.example",
            supabase_storage_service_key=SecretStr("synthetic"),
        ),
        httpx.MockTransport(handler),
    )


@pytest.mark.parametrize(
    "change",
    [
        {"public": True},
        {"file_size_limit": None},
        {"file_size_limit": 5000001},
        {"allowed_mime_types": []},
        {"allowed_mime_types": ["text/html"]},
    ],
)
def test_bucket_fails_closed(change):
    b = {
        "public": False,
        "file_size_limit": 5000000,
        "allowed_mime_types": ["image/png"],
    } | change
    with pytest.raises(AccessError):
        adapter(lambda r: httpx.Response(200, json=b)).authorize(
            "payment-evidence/synthetic/object"
        )


@pytest.mark.parametrize(
    "data,type,status",
    [
        (b"<html>", "application/pdf", 200),
        (b"%PDF-1.7 /JavaScript evil %%EOF", "application/pdf", 200),
        (PDF, "text/html", 200),
        (PDF, "application/pdf", 503),
        (PDF, "application/pdf", 302),
        (b"x" * 5000001, "application/pdf", 200),
    ],
    ids=["html", "active-pdf", "wrong-mime", "unavailable", "redirect", "oversize"],
)
def test_untrusted_bytes_rejected(data, type, status):
    a = adapter(
        lambda r: httpx.Response(status, content=data, headers={"content-type": type})
    )
    with pytest.raises((AccessError, HTTPException)):
        a.verify(
            {
                "object_key": "payment-evidence/synthetic/object",
                "bytes_size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "content_type": "application/pdf",
            }
        )


def test_valid_pdf_and_no_redirects():
    a = adapter(
        lambda r: httpx.Response(
            200, content=PDF, headers={"content-type": "application/pdf"}
        )
    )
    assert (
        a.verify(
            {
                "object_key": "payment-evidence/synthetic/object",
                "bytes_size": len(PDF),
                "sha256": hashlib.sha256(PDF).hexdigest(),
                "content_type": "application/pdf",
            }
        )
        == PDF
    )


def test_missing_config():
    with pytest.raises(AccessError):
        PaymentStorage(Settings())
