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
from independent_finance_fixtures import claims as allocated_claims
from independent_finance_fixtures import make_order, seed, stock
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
    with local_cluster("0054_payment_qr_recovery") as (url, _, _):
        database = Database(create_engine(url, hide_parameters=True))
        settings = Settings(
            supabase_url=ORIGIN,
            supabase_storage_service_key="synthetic-storage-key",
            payment_reference_key="synthetic-bank-reference-key",
            profile_data_keys=json.dumps({"1": base64.b64encode(b"x" * 32).decode()}),
            print_enabled=True,
            print_template_asset_root=str(assets),
            print_template_public_origin="https://safe-return-frontend.vercel.app",
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
                c.execute(
                    text(
                        "INSERT INTO auth.sessions(id,user_id,aal,not_after) VALUES(:id,:uid,'aal1',now()+interval '1 hour')"
                    ),
                    {"id": customer_sid, "uid": customer},
                )
            oid, _, amount = make_order(
                case, kinds=("lost", "ice"), copies=3, submit_payment=False
            )
            stock(case, "lost")
            app = create_app(settings, verifier=verifier)
            app.state.database, app.state.jwt_verifier = database, verifier
            client = ASGIClient(app)

            def call(method, path, body=None, *, finance=False, key=None):
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

            objects = {}
            storage = SimpleNamespace(
                upload=lambda key, data: objects.setdefault(key, data)
            )
            assert run_one(database, settings, storage), (
                "Expected the payment handoff to queue printing"
            )
            job = call("GET", jobs, finance=True).json()["items"][0]
            assert job["status"] == "queued"
            assert run_one(database, settings, storage), (
                "Expected the print job to render"
            )
            assert not run_one(database, settings, storage), (
                "No duplicate job should be queued"
            )
            detail = call("GET", f"/admin/print-jobs/{job['id']}", finance=True).json()
            assert detail["status"] == "ready"
            assert len(detail["artifacts"]) == 1
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
            assert {urlsplit(url).hostname for url in decoded} == {"safe-return-frontend.vercel.app"}
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
        finally:
            verifier.close()
            database.close()
