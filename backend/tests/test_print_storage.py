"""Private PDF integrity and provider recovery; no external network."""

import hashlib

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.core.print_render import PrintUnavailable
from app.integrations.print_storage import PrintStore

DATA = b"%PDF-1.7 synthetic %%EOF"


def settings():
    return Settings(
        supabase_url="https://print.example.test",
        supabase_storage_service_key=SecretStr("synthetic-only"),
    )


def test_no_overwrite_recovers_only_exact_bytes():
    def provider(r):
        if "/bucket/" in r.url.path:
            return httpx.Response(
                200,
                json={
                    "public": False,
                    "file_size_limit": 20000000,
                    "allowed_mime_types": ["application/pdf"],
                },
            )
        if r.method == "POST":
            return httpx.Response(409)
        return httpx.Response(
            200, content=DATA, headers={"content-type": "application/pdf"}
        )

    s = PrintStore(settings(), httpx.MockTransport(provider))
    assert s.upload("order-print/synthetic/file.pdf", DATA) == DATA
    with pytest.raises(PrintUnavailable):
        s.upload("order-print/synthetic/file.pdf", b"%PDF-mutated")


@pytest.mark.parametrize(
    "status,mime,content",
    [
        (302, "application/pdf", DATA),
        (200, "text/html", DATA),
        (200, "application/pdf", b"changed"),
    ],
)
def test_download_rejects_redirect_mime_or_hash(status, mime, content):
    s = PrintStore(
        settings(),
        httpx.MockTransport(
            lambda r: httpx.Response(
                status, content=content, headers={"content-type": mime}
            )
        ),
    )
    with pytest.raises(PrintUnavailable):
        s.download(
            "order-print/synthetic/file.pdf",
            hashlib.sha256(DATA).hexdigest(),
            len(DATA),
        )


def test_public_bucket_blocks_upload():
    s = PrintStore(
        settings(),
        httpx.MockTransport(
            lambda r: httpx.Response(
                200,
                json={
                    "public": True,
                    "file_size_limit": 20000000,
                    "allowed_mime_types": ["application/pdf"],
                },
            )
        ),
    )
    with pytest.raises(PrintUnavailable):
        s.upload("order-print/synthetic/file.pdf", DATA)
