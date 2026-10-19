"""Server-only Supabase evidence adapter. No public URLs or redirects."""

import hashlib
from urllib.parse import quote, urlsplit

import httpx

from app.api.auth import AccessError
from app.api.v1.catalog import fail
from app.integrations.storage_deletion import delete_private_object

BUCKET = "private-payment-evidence"
MAX_BYTES = 5_000_000
TYPES = {"image/png", "image/jpeg", "application/pdf"}


class PaymentStorage:
    def __init__(self, settings, transport=None):
        if not settings.supabase_url or not settings.supabase_storage_service_key:
            raise AccessError(503)
        self.origin = settings.supabase_url
        self.secret = settings.supabase_storage_service_key.get_secret_value()
        self.transport = transport

    def client(self):
        return httpx.Client(
            base_url=self.origin + "/storage/v1/",
            headers={"Authorization": "Bearer " + self.secret, "apikey": self.secret},
            timeout=10,
            follow_redirects=False,
            transport=self.transport,
        )

    def authorize(self, object_key):
        try:
            with self.client() as c:
                bucket = c.get("bucket/" + BUCKET)
                if bucket.status_code != 200:
                    raise AccessError(503)
                b = bucket.json()
                if (
                    b.get("public") is not False
                    or not b.get("file_size_limit")
                    or int(b["file_size_limit"]) > MAX_BYTES
                    or not b.get("allowed_mime_types")
                    or not set(b["allowed_mime_types"]).issubset(TYPES)
                ):
                    raise AccessError(503)
                r = c.post(
                    "object/upload/sign/" + BUCKET + "/" + quote(object_key, safe="/"),
                    json={},
                    headers={"x-upsert": "false"},
                )
                if r.status_code != 200:
                    raise AccessError(503)
                url = r.json()["url"]
                if url.startswith("/"):
                    url = self.origin + "/storage/v1" + url
                parsed = urlsplit(url)
                if (
                    parsed.scheme != "https"
                    or parsed.netloc != urlsplit(self.origin).netloc
                    or not parsed.path.startswith(
                        "/storage/v1/object/upload/sign/" + BUCKET + "/"
                    )
                ):
                    raise AccessError(503)
                return url
        except (httpx.HTTPError, ValueError, KeyError):
            raise AccessError(503) from None

    def verify(self, payload):
        try:
            with (
                self.client() as c,
                c.stream(
                    "GET",
                    "object/authenticated/"
                    + BUCKET
                    + "/"
                    + quote(payload["object_key"], safe="/"),
                ) as r,
            ):
                if r.status_code == 404:
                    fail(409, "EVIDENCE_NOT_UPLOADED")
                if r.status_code != 200:
                    raise AccessError(503)
                content = bytearray()
                for chunk in r.iter_bytes():
                    content.extend(chunk)
                    if len(content) > MAX_BYTES:
                        fail(413, "FILE_TOO_LARGE")
                data = bytes(content)
                kind = payload["content_type"]
                if (
                    r.headers.get("content-type", "").split(";")[0] != kind
                    or len(data) != payload["bytes_size"]
                    or hashlib.sha256(data).hexdigest() != payload["sha256"]
                ):
                    fail(422, "EVIDENCE_MISMATCH")
                signatures = {
                    "image/png": data.startswith(b"\x89PNG\r\n\x1a\n")
                    and data.endswith(b"IEND\xaeB`\x82"),
                    "image/jpeg": data.startswith(b"\xff\xd8\xff")
                    and data.endswith(b"\xff\xd9"),
                    "application/pdf": data.startswith(b"%PDF-")
                    and data.rstrip().endswith(b"%%EOF"),
                }
                if not signatures[kind]:
                    fail(422, "UNSUPPORTED_MEDIA_TYPE")
                # Reject active documents; dedicated malware-scanner acceptance remains a release gate.
                if kind == "application/pdf" and any(
                    x in data.lower()
                    for x in (
                        b"/javascript",
                        b"/js",
                        b"/launch",
                        b"/embeddedfile",
                        b"/openaction",
                        b"/aa",
                    )
                ):
                    fail(422, "UNSAFE_DOCUMENT")
                return data
        except httpx.HTTPError:
            raise AccessError(503) from None

    def delete(self, object_key: str) -> bool:
        try:
            with self.client() as c:
                return delete_private_object(c, BUCKET, object_key)
        except httpx.HTTPError:
            raise AccessError(503) from None


def storage(request):
    return PaymentStorage(
        request.app.state.settings,
        getattr(request.app.state, "payment_storage_transport", None),
    )
