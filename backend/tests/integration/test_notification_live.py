"""Explicitly opt-in single-email smoke using a disposable database namespace."""

import os

import pytest
from test_notification_delivery import notification_database as _notification_database
from test_notification_delivery import sample as _sample

from app.core.config import Settings
from app.workers.notifications import ResendProvider, process_one

notification_database = _notification_database
sample = _sample


@pytest.mark.skipif(
    not os.environ.get("SAFERETURN_NOTIFICATION_SMOKE_RECIPIENT")
    or not os.environ.get("SAFERETURN_NOTIFICATION_SMOKE_KEY"),
    reason="Live notification requires explicit authorization",
)
def test_authorized_single_notification(sample):
    recipient = os.environ.get("SAFERETURN_NOTIFICATION_SMOKE_RECIPIENT")
    key = os.environ.get("SAFERETURN_NOTIFICATION_SMOKE_KEY")
    if not recipient or not key:
        pytest.skip("A controlled recipient and explicit stable smoke key are required")
    actual = Settings(_env_file=".env")
    settings = actual.model_copy(
        update={"profile_data_keys": sample.settings.profile_data_keys}
    )
    sample.update(
        "UPDATE auth.users SET email=:recipient WHERE id=:id",
        {"recipient": recipient, "id": sample.owner},
    )
    oid = sample.enqueue(idempotency_key=key)
    actual_provider = ResendProvider(settings)

    class AuthorizedProvider:
        calls = 0

        def send(self, **message):
            assert message["to"] == recipient, (
                "Only the authorized test recipient is allowed"
            )
            assert message["idempotency_key"] == key
            assert self.calls == 0, "This smoke test permits only one provider call"
            self.calls += 1
            return actual_provider.send(
                **{
                    **message,
                    "subject": "[Development test] " + message["subject"],
                    "html": "<p>This is an authorized SafeReturn development delivery test. No real customer message or location is included.</p>"
                    + message["html"],
                }
            )

    provider = AuthorizedProvider()
    assert process_one(
        sample.database, settings, provider, worker_id="authorized-provider-smoke"
    )
    row = sample.row(oid)
    assert row["status"] == "sent", (
        f"Provider acceptance failed: {row['last_error_code']}"
    )
    assert row["provider_message_id"]
    assert not process_one(
        sample.database, settings, provider, worker_id="authorized-provider-smoke"
    )
    assert provider.calls == 1
    print(
        "Authorized notification accepted by Resend; no second send from the completed event."
    )
