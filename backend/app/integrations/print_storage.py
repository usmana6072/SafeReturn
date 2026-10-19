"""Private PDF Storage adapter; immutable object keys and checksum recovery."""

import hashlib
from urllib.parse import quote

import httpx

from app.core.print_render import PrintUnavailable
from app.integrations.storage_deletion import delete_private_object

BUCKET = "private-order-print"
MAX_BYTES = 20_000_000


class PrintStore:
    def __init__(self, settings, transport=None):
        if not settings.supabase_url or not settings.supabase_storage_service_key:
            raise PrintUnavailable("storage_not_configured")
        self.origin = settings.supabase_url
        self.key = settings.supabase_storage_service_key.get_secret_value()
        self.transport = transport

    def client(self):
        return httpx.Client(
            base_url=self.origin + "/storage/v1/",
            headers={"Authorization": "Bearer " + self.key, "apikey": self.key},
            timeout=15,
            follow_redirects=False,
            transport=self.transport,
        )

    def check_bucket(self, c):
        r = c.get("bucket/" + BUCKET)
        if r.status_code != 200:
            raise PrintUnavailable("private_bucket_unavailable")
        b = r.json()
        if (
            b.get("public") is not False
            or b.get("file_size_limit") != MAX_BYTES
            or b.get("allowed_mime_types") != ["application/pdf"]
        ):
            raise PrintUnavailable("unsafe_bucket_policy")

    def download(self, key, sha, size):
        if not key.startswith("order-print/") or size > MAX_BYTES:
            raise PrintUnavailable("invalid_artifact")
        try:
            with (
                self.client() as c,
                c.stream(
                    "GET", "object/authenticated/" + BUCKET + "/" + quote(key, safe="/")
                ) as r,
            ):
                if (
                    r.status_code != 200
                    or r.headers.get("content-type", "").split(";")[0]
                    != "application/pdf"
                ):
                    raise PrintUnavailable("object_unavailable")
                data = bytearray()
                for chunk in r.iter_bytes():
                    data.extend(chunk)
                    if len(data) > MAX_BYTES:
                        raise PrintUnavailable("object_too_large")
                data = bytes(data)
                if (
                    len(data) != size
                    or hashlib.sha256(data).hexdigest() != sha
                    or not data.startswith(b"%PDF-")
                ):
                    raise PrintUnavailable("object_integrity_failure")
                return data
        except httpx.HTTPError:
            raise PrintUnavailable("storage_unavailable") from None

    def upload(self, key, data):
        try:
            with self.client() as c:
                self.check_bucket(c)
                r = c.post(
                    "object/" + BUCKET + "/" + quote(key, safe="/"),
                    content=data,
                    headers={
                        "Content-Type": "application/pdf",
                        "x-upsert": "false",
                        "cache-control": "private, max-age=0, no-store",
                    },
                )
                if r.status_code not in (200, 201, 400, 409):
                    raise PrintUnavailable("upload_unavailable")
            # Recover a timeout/lost acknowledgement or duplicate only by exact hash match.
            return self.download(key, hashlib.sha256(data).hexdigest(), len(data))
        except httpx.HTTPError:
            raise PrintUnavailable("storage_unavailable") from None

    def delete(self, key: str) -> bool:
        try:
            with self.client() as c:
                return delete_private_object(c, BUCKET, key)
        except httpx.HTTPError:
            raise PrintUnavailable("storage_unavailable") from None


def store(request):
    return PrintStore(
        request.app.state.settings,
        getattr(request.app.state, "print_storage_transport", None),
    )
