"""Fail before any connection when untrusted runtime context has invalid types."""

import pytest

from app.db.runtime import api_transaction, worker_transaction


@pytest.mark.parametrize(
    "kwargs",
    [
        {"actor_user_id": "arbitrary-user"},
        {"mfa_verified": "true"},
        {"submission_id": "caller-selected-id"},
        {"scan_binding_digest": "not-a-digest"},
    ],
)
def test_api_context_rejects_invalid_inputs_before_database_access(kwargs):
    with pytest.raises((TypeError, ValueError)), api_transaction(None, **kwargs):
        pytest.fail("Invalid context reached a transaction")


@pytest.mark.parametrize("worker", ["", "a" * 101, "worker; DROP TABLE x", None])
def test_worker_identity_rejects_invalid_inputs_before_database_access(worker):
    with pytest.raises((TypeError, ValueError)), worker_transaction(None, worker):
        pytest.fail("Invalid worker identity reached a transaction")
