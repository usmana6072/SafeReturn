"""Finder submission, recipient inbox and email on a fresh loopback PostgreSQL."""

import base64
import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from independent_finance_local import local_cluster
from sqlalchemy import create_engine, text
from test_health import ASGIClient
from test_identity_schema import pair

from app.api.v1.messages import get_finder_message, list_finder_messages
from app.core.config import Settings
from app.db.runtime import api_transaction, worker_transaction
from app.db.session import Database
from app.main import create_app
from app.workers.notifications import process_one

pytestmark = pytest.mark.skipif(
    os.environ.get("SAFERETURN_FINDER_REHEARSAL") != "1",
    reason="Requires disposable loopback PostgreSQL",
)


def test_submission_reaches_owner_inbox_and_structured_email():
    with local_cluster("0058_finder_email_details") as (url, _, _):
        db = Database(create_engine(url, hide_parameters=True))
        try:
            owner, other = uuid4(), uuid4()
            with db.engine.begin() as c:
                for uid in (owner, other):
                    c.execute(
                        text(
                            "INSERT INTO auth.users(id,email,email_confirmed_at) VALUES(:id,'owner@example.test',now())"
                        ),
                        {"id": uid},
                    )
                pid, ids = pair(c)
                c.execute(
                    text(
                        "UPDATE tag_pairs SET ownership_status='active',owner_user_id=:owner,activated_at=now() WHERE id=:id"
                    ),
                    {"owner": owner, "id": pid},
                )
                c.execute(
                    text(
                        "UPDATE qr_codes SET public_status='active' WHERE pair_id=:id"
                    ),
                    {"id": pid},
                )
                c.execute(
                    text(
                        "INSERT INTO lost_item_profiles(qr_id,item_label,published) VALUES(:id,'Test bag',true)"
                    ),
                    {"id": ids["lost"]},
                )
                token = c.execute(
                    text("SELECT public_token FROM qr_codes WHERE id=:id"),
                    {"id": ids["lost"]},
                ).scalar_one()
            settings = Settings(
                notification_worker_enabled=False,
                profile_data_keys=json.dumps(
                    {"1": base64.b64encode(b"x" * 32).decode()}
                ),
            )
            app = create_app(settings)
            app.state.database = db
            client = ASGIClient(app)
            body = {
                "finder_name": "Test finder",
                "finder_email": "finder@example.test",
                "finder_phone": "+923001234567",
                "preferred_contact": "email",
                "message": "I found your bag near the station.",
                "consent_version": "finder-public-v1",
                "contact_consent_accepted": True,
                "location_consent": True,
                "location": {"latitude": 31.5, "longitude": 74.3},
                "turnstile_token": uuid4().hex,
            }
            key = str(uuid4())
            with patch("app.api.v1.public_actions.verify"):
                response = client.post(
                    f"/api/v1/public/qr/{token}/finder-messages",
                    json=body,
                    headers={"Idempotency-Key": key},
                )
                assert response.status_code == 202, response.text
                body["turnstile_token"] = uuid4().hex
                assert (
                    client.post(
                        f"/api/v1/public/qr/{token}/finder-messages",
                        json=body,
                        headers={"Idempotency-Key": key},
                    ).status_code
                    == 202
                )
            with api_transaction(db, owner) as session:
                session.info["settings"] = settings
                context = SimpleNamespace(
                    session=session, principal=SimpleNamespace(user_id=owner)
                )
                inbox = list_finder_messages(
                    context, cursor=None, limit=25, status=None, qr_id=None
                )
                assert len(inbox["items"]) == 1
                mid = inbox["items"][0]["id"]
                detail = get_finder_message(mid, context)
                assert detail["message"] == body["message"]
                assert detail["finder_email"] == body["finder_email"]
                assert detail["preferred_contact"] == "email"
                assert detail["location"]["latitude"] == 31.5
            with api_transaction(db, other) as session:
                context = SimpleNamespace(
                    session=session, principal=SimpleNamespace(user_id=other)
                )
                assert (
                    list_finder_messages(
                        context, cursor=None, limit=25, status=None, qr_id=None
                    )["items"]
                    == []
                )
            with worker_transaction(db, "unleased-worker") as session:
                assert (
                    session.execute(
                        text("SELECT * FROM sr_notification_finder_details(:id,1)"),
                        {"id": uuid4()},
                    ).first()
                    is None
                )
            provider = MagicMock()
            provider.send.return_value = "accepted-test-email"

            def inspect_lease(**_kwargs):
                with db.engine.connect() as c:
                    oid = c.execute(
                        text(
                            "SELECT id FROM notification_outbox WHERE aggregate_id=:id"
                        ),
                        {"id": mid},
                    ).scalar_one()
                with worker_transaction(db, "intruder") as session:
                    assert (
                        session.execute(
                            text("SELECT * FROM sr_notification_finder_details(:id,1)"),
                            {"id": oid},
                        ).first()
                        is None
                    )
                with worker_transaction(db, "delivery-test") as session:
                    assert (
                        session.execute(
                            text("SELECT * FROM sr_notification_finder_details(:id,2)"),
                            {"id": oid},
                        ).first()
                        is None
                    )
                return "accepted-test-email"

            provider.send.side_effect = inspect_lease
            assert process_one(db, settings, provider, worker_id="delivery-test")
            args = provider.send.call_args.kwargs
            assert args["to"] == "owner@example.test"
            for value in (
                body["message"],
                body["finder_email"],
                body["finder_phone"],
                "google.com/maps?q=31.5,74.3",
                f"/inbox/{mid}",
            ):
                assert value in args["html"]
            assert not process_one(db, settings, provider)
            assert provider.send.call_count == 1
            with db.engine.connect() as c:
                assert (
                    c.execute(
                        text(
                            "SELECT status FROM notification_outbox WHERE aggregate_id=:id"
                        ),
                        {"id": mid},
                    ).scalar_one()
                    == "sent"
                )
                for role in ("anon", "authenticated", "safereturn_api"):
                    assert not c.execute(
                        text(
                            "SELECT has_function_privilege(:role,'public.sr_notification_finder_details(uuid,integer)','EXECUTE')"
                        ),
                        {"role": role},
                    ).scalar_one()
        finally:
            db.close()
