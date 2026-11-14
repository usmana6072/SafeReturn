"""Private export adapter boundary; no live bucket or provider is activated.

An approved host injects the same adapter into the worker and API app state.
Uploads must be immutable: duplicate keys succeed only for identical bytes.
Reads must be bounded to MAX_CIPHERTEXT_BYTES, authenticated, and fail closed.
There is deliberately no URL/signing/email/delete operation in this interface.
"""

from typing import Protocol

MAX_CIPHERTEXT_BYTES = 10 * 1024 * 1024 + 32


class PrivacyExportStorage(Protocol):
    def upload(self, key: str, data: bytes) -> None: ...

    def read(self, key: str) -> bytes: ...
