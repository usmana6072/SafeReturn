"""Untrusted cursors cannot turn malformed JSON types into server exceptions."""

import base64
import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.api.v1.owner_qr import decode_cursor, encode_cursor


@pytest.mark.parametrize(
    "data",
    [
        None,
        [],
        4,
        {"id": [], "at": "2026-10-15T00:00:00Z"},
        {"id": "invalid", "at": None},
        {"id": "invalid", "at": "invalid"},
    ],
)
def test_hostile_cursor_shapes_are_rejected(data):
    encoded = base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")
    assert decode_cursor(encoded) is False


def test_cursor_preserves_microseconds_and_uuid_tie_breaker():
    identity, timestamp = uuid4(), datetime(2026, 10, 15, 10, 0, 0, 123456, UTC)
    assert decode_cursor(encode_cursor(identity, timestamp)) == (identity, timestamp)
