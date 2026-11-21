"""Orders, finance and private printing on a disposable loopback database."""

import base64
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
import pymupdf
import pytest
import zxingcpp
from cryptography.hazmat.primitives.asymmetric import ec
from independent_finance_fixtures import actor, make_order, seed, stock
from independent_finance_fixtures import claims as allocated_claims
from independent_finance_local import local_cluster
from PIL import Image
from sqlalchemy import create_engine, text
from test_auth import ORIGIN, claims, keyset, signed
from test_health import ASGIClient

from app.core.auth import JWTVerifier
from app.core.config import Settings
from app.db.session import Database
from app.main import create_app
from app.workers.printing import run_one

pytestmark = pytest.mark.skipif(
    os.environ.get("SAFERETURN_INDEPENDENT_FINANCE_REHEARSAL") != "1",
    reason="Requires disposable PostgreSQL on loopback",
)


def test_payment_queue_evidence_approval_allocation_and_pdf():
    root = Path(__file__).resolve().parents[3]
    assets = root / "backend/print-assets"
    font = next(assets.glob("*.ttf"))
    logo = next(assets.glob("*.svg"))
    with local_cluster("0059_shipment_delivery_email") as (url, _, _):
        database = Database(create_engine(url, hide_parameters=True))
        settings = Settings(
            supabase_url=ORIGIN,
            supabase_storage_service_key="synthetic-storage-key",
            payment_reference_key="synthetic-bank-reference-key",
            profile_data_keys=json.dumps({"1": base64.b64encode(b"x" * 32).decode()}),
            print_enabled=True,
            print_template_asset_root=str(assets),
            print_template_public_origin="https://www.safereturnqr.me",
        )
        signing_key = ec.generate_private_key(ec.SECP256R1())
        jwks = httpx.MockTransport(
            lambda _: httpx.Response(200, json={"keys": [keyset(signing_key)]})
        )
        verifier = JWTVerifier(settings, transport=jwks)
        try:
            case = seed(
                SimpleNamespace(connect=database.engine.connect),
                {
                    "font_path": f"/app/print-assets/{font.name}",
                    "font_sha": hashlib.sha256(font.read_bytes()).hexdigest(),
                    "logo_path": f"/app/print-assets/{logo.name}",
                    "logo_sha": hashlib.sha256(logo.read_bytes()).hexdigest(),
                },
                origin="http://127.0.0.1:3100",
            )
            _, staff, customer, staff_sid, _ = case
            customer_sid = uuid4()
            with database.engine.begin() as c:
                c.execute(text("UPDATE public.standalone_owner_release SET enabled=true"))
                c.execute(
                    text(
                        "INSERT INTO auth.sessions(id,user_id,aal,not_after) VALUES(:id,:uid,'aal1',now()+interval '1 hour')"
                    ),
                    {"id": customer_sid, "uid": customer},
                )
            oid, _, amount = make_order(
                case, kinds=("lost", "ice"), copies=6, submit_payment=False, shipping_settings=settings
            )
            stock(case, "lost")
            app = create_app(settings, verifier=verifier)
            app.state.database, app.state.jwt_verifier = database, verifier
            client = ASGIClient(app)

            def call(method, path, body=None, *, finance=False, key=None, version=None):
                token = signed(
                    signing_key,
                    claims(
                        sub=str(staff if finance else customer),
                        session_id=str(staff_sid if finance else customer_sid),
                        aal="aal2" if finance else "aal1",
                    ),
                )
                return client.request(
                    method,
                    "/api/v1" + path,
                    json=body,
                    headers={
                        "Authorization": "Bearer " + token,
                        "Idempotency-Key": key or str(uuid4()),
                        **({"If-Match": f'"{version}"'} if version is not None else {}),
                    },
                )

            queue = "/admin/order-metadata?order_status=placed&payment_status=pending"
            assert (
                call("GET", queue, finance=True).json()["items"][0]["payment_status"]
                == "awaiting_transfer"
            )
            attempts = f"/me/orders/{oid}/payment-attempts"
            submitted = call(
                "POST",
                attempts,
                {
                    "sender_holder_name": "Synthetic sender",
                    "sender_account": "TEST1234",
                },
            )
            assert submitted.status_code == 201, submitted.text
            assert submitted.json()["state"] == "initiated"
            aid = submitted.json()["attempt_id"]
            review = f"/admin/payment-attempts/{aid}/reviews"
            decision = {
                "decision": "verify",
                "bank_verified": True,
                "bank_match_reference": "synthetic verified reference",
                "settled_amount": f"{amount:.2f}",
                "settled_currency": "PKR",
                "reason": "Synthetic bank settlement verified",
            }
            premature = call("POST", review, decision, finance=True)
            assert premature.status_code == 409, premature.text
            assert premature.json()["error"]["code"] == "PAYMENT_EVIDENCE_REQUIRED"
            assert (
                call("GET", queue, finance=True).json()["items"][0]["payment_status"]
                == "awaiting_transfer"
            )
            assert (
                call("GET", attempts).json()["items"][0]["evidence_received"] is False
            )

            proof = b"\x89PNG\r\n\x1a\nsyntheticIEND\xaeB`\x82"
            proof_hash = hashlib.sha256(proof).hexdigest()

            def payment_storage(request):
                if "/bucket/" in request.url.path:
                    return httpx.Response(
                        200,
                        json={
                            "public": False,
                            "file_size_limit": 5000000,
                            "allowed_mime_types": ["image/png"],
                        },
                    )
                if request.method == "POST":
                    suffix = request.url.path.split("private-payment-evidence/")[1]
                    return httpx.Response(
                        200,
                        json={
                            "url": f"/object/upload/sign/private-payment-evidence/{suffix}?token=synthetic"
                        },
                    )
                return httpx.Response(
                    200, content=proof, headers={"Content-Type": "image/png"}
                )

            app.state.payment_storage_transport = httpx.MockTransport(payment_storage)
            upload = f"/me/payment-attempts/{aid}/evidence-uploads"
            upload_body = {
                "filename": "proof.png",
                "content_type": "image/png",
                "bytes_size": len(proof),
                "sha256": proof_hash,
            }
            first = call("POST", upload, upload_body)
            stale = call("POST", upload, upload_body)
            assert first.status_code == stale.status_code == 200, first.text
            finalize = f"/me/payment-attempts/{aid}/evidence-finalize"
            proof_body = {
                "upload_token": first.json()["upload_token"],
                "sha256": proof_hash,
            }
            key = str(uuid4())
            receipt = call("POST", finalize, proof_body, key=key)
            assert receipt.status_code == 200, receipt.text
            assert receipt.json()["payment_state"] == "under_review"
            assert (
                call("GET", queue, finance=True).json()["items"][0]["payment_status"]
                == "under_review"
            )
            assert call("POST", finalize, proof_body, key=key).json() == receipt.json()
            assert (
                call(
                    "POST",
                    finalize,
                    proof_body | {"upload_token": stale.json()["upload_token"]},
                ).status_code
                == 409
            )
            assert call("POST", upload, upload_body).status_code == 409
            assert call("GET", attempts).json()["items"][0]["evidence_received"] is True

            jobs = f"/admin/orders/{oid}/print-jobs"
            assert call("GET", jobs, finance=True).json()["items"] == []
            key = str(uuid4())
            approved = call("POST", review, decision, key=key, finance=True)
            assert approved.status_code == 200, approved.text
            assert approved.json()["state"] == "verified"
            assert approved.json()["allocation"] == {
                "state": "allocated",
                "reason_code": None,
                "requested_count": 2,
                "allocated_count": 2,
            }
            original = allocated_claims(case, oid)
            assert len(original) == 2
            assert (
                call("POST", review, decision, key=key, finance=True).json()
                == approved.json()
            )
            assert allocated_claims(case, oid) == original
            assert call("GET", queue, finance=True).json()["items"] == []
            with database.engine.connect() as c:
                assert c.execute(
                    text(
                        "SELECT qr_type,requested_quantity FROM public.qr_batches WHERE batch_code LIKE 'auto-%'"
                    )
                ).all() == [("ice", 1)]
                tags = c.execute(text("""SELECT a.logical_item_id, q.tag_type, q.public_token
                    FROM public.order_item_qr_allocations a JOIN public.qr_codes q ON q.id=a.qr_id
                    WHERE a.order_id=:id"""), {"id": oid}).mappings().all()

            lost = next(tag for tag in tags if tag["tag_type"] == "lost")
            purchase = {"logical_item_id": str(lost["logical_item_id"])}
            scan = f"/api/v1/public/qr/{lost['public_token']}"
            assert client.request("GET", scan).json() == {
                "tag_type": "lost", "status": "unactivated", "locale_options": ["en", "ur"]
            }
            intents = "/me/independent-qr/activation-intents"
            assert call("POST", intents, purchase).json()["error"]["code"] == "NOT_ELIGIBLE"

            objects = {}
            storage = SimpleNamespace(
                upload=lambda key, data: objects.setdefault(key, data)
            )
            assert run_one(database, settings, storage), (
                "Expected the payment handoff to queue printing"
            )
            job = call("GET", jobs, finance=True).json()["items"][0]
            assert job["status"] == "queued"
            assert all(not item["can_activate"] for item in call("GET", "/me/independent-qr").json()["items"])
            assert run_one(database, settings, storage), (
                "Expected the print job to render"
            )
            assert not run_one(database, settings, storage), (
                "No duplicate job should be queued"
            )
            detail = call("GET", f"/admin/print-jobs/{job['id']}", finance=True).json()
            assert detail["status"] == "ready"
            assert len(detail["artifacts"]) == 1
            shipment_path = f"/admin/orders/{oid}/shipment"
            shipping = {"carrier": "Independent courier"}
            assert call("GET", shipment_path, finance=True).json()["eligible"] is False
            assert call("POST", shipment_path, shipping, finance=True).status_code == 409
            assert all(item["can_activate"] for item in call("GET", "/me/independent-qr").json()["items"])
            assert call("POST", intents, purchase, finance=True).status_code == 404
            intent = call("POST", intents, purchase)
            assert intent.status_code == 201, intent.text
            confirm = call("POST", "/me/independent-qr/activations", {
                "intent_id": intent.json()["intent_id"], "confirmed": True,
            })
            assert confirm.status_code == 201, confirm.text
            projection = client.request("GET", scan).json()
            assert projection["status"] == "active" and projection["lost_item"]["label"] is None
            activated = confirm.json()
            hidden = call("PATCH", f"/me/independent-qr/{activated['qr_id']}/availability", {
                "public_status": "owner_disabled", "expected_revision": activated["revision"], "confirmed": True,
            })
            assert hidden.status_code == 200, hidden.text
            assert client.request("GET", scan).json()["status"] == "owner_disabled"
            resumed = call("PATCH", f"/me/independent-qr/{activated['qr_id']}/availability", {
                "public_status": "active", "expected_revision": hidden.json()["revision"], "confirmed": True,
            })
            assert resumed.status_code == 200, resumed.text
            identities = call("GET", "/me/independent-qr").json()["items"]
            assert len(identities) == 2
            assert len([qr for qr in identities if qr["ownership_status"] == "active"]) == 1
            assert len([qr for qr in identities if qr["tag_type"] == "lost"]) == 1
            profile_path = f"/me/qr/{activated['qr_id']}/lost-profile"
            profile = call("GET", profile_path)
            assert profile.status_code == 200, profile.text
            assert call("GET", f"/me/qr/{activated['qr_id']}").json()["tag_type"] == "lost"
            draft = {"item_label": "Fixture bag", "description": "Fixture owner details", "published": False}
            saved = call("PUT", profile_path, draft, version=profile.json()["version"])
            assert saved.status_code == 200, saved.text
            assert call("GET", profile_path, finance=True).status_code == 404
            assert call("PUT", profile_path, draft, version=saved.json()["version"], finance=True).status_code == 404
            assert client.request("GET", scan).json()["lost_item"]["label"] is None
            published = call("PUT", profile_path, {"published": True}, version=saved.json()["version"])
            assert published.status_code == 200, published.text
            assert client.request("GET", scan).json()["lost_item"]["label"] == "Fixture bag"
            assert call("PUT", profile_path, draft, version=saved.json()["version"]).status_code == 412
            with database.engine.connect() as c:
                assert c.execute(text("""SELECT sum(z.copies) FROM public.order_item_sizes z
                    JOIN public.order_item_qr_allocations a ON a.logical_item_id=z.logical_item_id
                    WHERE a.qr_id=:qr"""), {"qr": activated["qr_id"]}).scalar_one() == 6
            app.state.print_storage_transport = httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    content=objects[request.url.path.split("private-order-print/")[1]],
                    headers={"Content-Type": "application/pdf"},
                )
            )
            artifact = detail["artifacts"][0]
            download = (
                f"/admin/print-jobs/{job['id']}/artifacts/{artifact['id']}/download"
            )
            app.state.settings.print_enabled = False
            assert call("POST", download).status_code == 403
            response = call("POST", download, finance=True)
            assert response.status_code == 200, response.text
            assert response.content.startswith(b"%PDF-")
            decoded = set()
            with pymupdf.open(stream=response.content, filetype="pdf") as pdf:
                for page in pdf:
                    pixels = page.get_pixmap(matrix=pymupdf.Matrix(3, 3), alpha=False)
                    image = Image.frombytes("RGB", (pixels.width, pixels.height), pixels.samples)
                    decoded.update(barcode.text for barcode in zxingcpp.read_barcodes(image))
            assert len(decoded) == 2
            assert {urlsplit(url).scheme for url in decoded} == {"https"}
            assert {urlsplit(url).hostname for url in decoded} == {"www.safereturnqr.me"}
            with database.engine.connect() as c:
                tokens = set(c.execute(text("""SELECT q.public_token FROM public.order_item_qr_allocations a
                    JOIN public.qr_codes q ON q.id=a.qr_id WHERE a.order_id=:id"""), {"id": oid}).scalars())
            assert {urlsplit(url).path for url in decoded} == {f"/q/{token}" for token in tokens}
            assert (
                hashlib.sha256(response.content).hexdigest() == artifact["sha256_hex"]
            )
            assert (
                call("GET", jobs, finance=True).json()["items"][0]["status"]
                == "downloaded"
            )
            app.state.settings.print_enabled = True
            assert call("GET", shipment_path, finance=True).json()["eligible"] is True
            with database.engine.connect() as c:
                actor(c, staff)
                template_hold = c.begin_nested()
                c.execute(text("""INSERT INTO public.template_order_holds(order_id,source_kind,source_reference)
                    VALUES(:id,'synthetic-template-hold','shipment-regression')"""), {"id": oid})
                assert c.execute(text("SELECT public.sr_typed_fulfillment_eligible(:id)"), {"id": oid}).scalar_one() is False
                template_hold.rollback()
                assert c.execute(text("SELECT public.sr_typed_fulfillment_eligible(:id)"), {"id": oid}).scalar_one() is True
            assert call("POST", shipment_path, shipping).status_code == 403
            assert call("POST", shipment_path, {"carrier": ""}, finance=True).status_code == 422
            assert call("GET", "/me/shipments").json()["items"] == []
            order_summary = call("GET", f"/admin/orders/{oid}/summary", finance=True).json()
            assert order_summary["id"] == str(oid)
            assert len(order_summary["order_items"]) == 2
            if os.environ.get("SAFERETURN_FULFILLMENT_BROWSER") == "1":
                from fulfillment_browser import run

                tokens = {
                    email: (uid, signed(signing_key, claims(sub=str(uid), session_id=str(sid), aal=level)))
                    for email, uid, sid, level in (
                        ("operations@fixture.test", staff, staff_sid, "aal2"),
                        ("buyer@fixture.test", customer, customer_sid, "aal1"),
                    )
                }
                run(app, tokens, oid, job["id"])
                assert call("GET", "/me/shipments").json()["items"][0]["status"] == "delivered"
                assert client.request("GET", scan).json()["lost_item"]["label"] == "Browser bag"
                return
            with database.engine.connect() as c:
                assert c.execute(text("SELECT count(*) FROM public.print_job_qa WHERE print_job_id=:id"), {"id": job["id"]}).scalar_one() == 0
            shipment_key = str(uuid4())
            shipment = call("POST", shipment_path, shipping, key=shipment_key, finance=True)
            assert shipment.status_code == 201, shipment.text
            shipment_id = shipment.json()["shipment_id"]
            assert call("POST", shipment_path, shipping, key=shipment_key, finance=True).json() == shipment.json()
            assert call("POST", shipment_path, shipping, finance=True).json()["error"]["code"] == "SHIPMENT_EXISTS"
            assert call("GET", "/me/shipments", finance=True).json()["items"] == []
            assert client.request("GET", "/api/v1/me/shipments").status_code == 401

            def check_buyer(expected):
                buyer = call("GET", "/me/shipments").json()["items"]
                assert len(buyer) == 1 and buyer[0]["id"] == shipment_id
                assert buyer[0]["status"] == expected
                assert buyer[0]["order_id"] == str(oid)
                assert buyer[0]["order_items"] == order_summary["order_items"]
                assert {key: buyer[0][key] for key in shipping} == shipping

            check_buyer("dispatched")
            assert shipment.json()["status"] == "dispatched"
            assert call("GET", shipment_path, finance=True).json()["next_statuses"] == ["delivered"]
            assert call("PATCH", shipment_path, {"status": "delivered", "expected_status": "preparing"}, finance=True).status_code == 412
            shipping["tracking_reference"] = "SR-2026-42"
            tracked = call("PATCH", shipment_path, {"status": "dispatched", "expected_status": "dispatched", "tracking_reference": shipping["tracking_reference"]}, finance=True)
            assert tracked.status_code == 200, tracked.text
            check_buyer("dispatched")
            with database.engine.begin() as c:
                c.execute(text("UPDATE auth.users SET email='buyer@example.test' WHERE id=:id"), {"id": customer})
                assert c.execute(text("SELECT count(*) FROM notification_outbox WHERE event_type='shipment.delivered'")).scalar_one() == 0
            saved_keys = settings.profile_data_keys
            settings.profile_data_keys = None
            try:
                failed = call("PATCH", shipment_path, {"status": "delivered", "expected_status": "dispatched"}, finance=True)
                assert failed.status_code == 503, failed.text
            finally:
                settings.profile_data_keys = saved_keys
            check_buyer("dispatched")
            with database.engine.connect() as c:
                assert c.execute(text("SELECT count(*) FROM notification_outbox WHERE event_type='shipment.delivered'")).scalar_one() == 0
            delivered_key = str(uuid4())
            delivery_body = {"status": "delivered", "expected_status": "dispatched", "received_by": "Ahmed <Receiver>"}
            updated = call("PATCH", shipment_path, delivery_body, key=delivered_key, finance=True)
            assert updated.status_code == 200, updated.text
            assert call("PATCH", shipment_path, delivery_body, key=delivered_key, finance=True).json() == updated.json()
            assert call("PATCH", shipment_path, delivery_body, finance=True).status_code == 412
            check_buyer("delivered")
            from unittest.mock import MagicMock
            from app.workers.notifications import process_one
            provider = MagicMock()
            provider.send.return_value = "delivery-test-id"
            assert process_one(database, settings, provider)
            mail = provider.send.call_args.kwargs
            assert mail["from_email"] == "SafeReturn <services@safereturnqr.me>"
            assert mail["to"] == "buyer@example.test"
            assert "Ahmed &lt;Receiver&gt;" in mail["html"]
            assert shipping["tracking_reference"] in mail["html"]
            assert not process_one(database, settings, provider)
            with database.engine.connect() as c:
                assert c.execute(text("SELECT count(*) FROM notification_outbox WHERE event_type='shipment.delivered'")).scalar_one() == 1
                assert c.execute(text("SELECT status FROM notification_outbox WHERE event_type='shipment.delivered'")).scalar_one() == "sent"
            assert call("GET", shipment_path, finance=True).json()["next_statuses"] == []
            with database.engine.connect() as c:
                assert c.execute(text("""SELECT h.status,h.tracking_reference,h.carrier,o.fulfillment_status
                    FROM public.shipments h JOIN public.orders o ON o.id=h.order_id WHERE h.id=:id"""),
                    {"id": shipment_id}).one() == ("delivered", shipping["tracking_reference"], shipping["carrier"], "delivered")
        finally:
            verifier.close()
            database.close()
