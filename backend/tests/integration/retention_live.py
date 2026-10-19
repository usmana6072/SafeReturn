"""Optional live worker drill; only absent, fixture-owned UUID objects are uploaded."""

import hashlib
import os
from contextlib import ExitStack, contextmanager
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import text

from app.db.session import database_url
from app.integrations.payment_storage import PaymentStorage
from app.integrations.print_storage import PrintStore
from app.integrations.storage_deletion import object_missing
from app.workers.finance_retention import StorageStore

EVIDENCE_BYTES = b"%PDF-1.4 synthetic payment evidence fixture %%EOF"


@contextmanager
def retention_store(sample, artifact_ids, fallback):
    if os.environ.get("SAFERETURN_TASK56_LIVE_STORAGE") != "1":
        yield fallback
        return
    origin = os.environ.get("SAFERETURN_SUPABASE_URL")
    secret = os.environ.get("SAFERETURN_SUPABASE_STORAGE_SERVICE_KEY")
    if not origin or not secret:
        pytest.skip("Explicit live storage configuration is required")
    project = urlsplit(origin).hostname.split(".")[0]
    target = database_url(os.environ["SAFERETURN_TEST_DATABASE_URL"])
    assert target.host == f"db.{project}.supabase.co" or target.username.endswith(
        "." + project
    )
    settings = sample[3].state.settings.model_copy(
        update={
            "supabase_url": origin,
            "supabase_storage_service_key": SecretStr(secret),
        }
    )
    store = StorageStore(settings)
    with sample[0].connect() as db:
        rows = (
            db.execute(
                text("""SELECT id,bucket,object_key,sha256_hex,size_bytes FROM public.print_artifacts WHERE id=ANY(:ids)
            UNION ALL SELECT id,bucket,object_key,sha256_hex,bytes_size FROM public.payment_evidence WHERE id=ANY(:ids)"""),
                {"ids": list(artifact_ids)},
            )
            .mappings()
            .all()
        )
    assert {r["id"] for r in rows} == set(artifact_ids)
    with ExitStack() as cleanup:
        for row in rows:
            adapter = (
                PrintStore(settings)
                if row["bucket"] == "private-order-print"
                else PaymentStorage(settings)
            )
            data = (
                sample[5][3].objects[row["object_key"]]
                if row["bucket"] == "private-order-print"
                else EVIDENCE_BYTES
            )
            assert (
                len(data) == row["size_bytes"]
                and hashlib.sha256(data).hexdigest() == row["sha256_hex"]
            )
            with adapter.client() as client:
                policy = client.get("bucket/" + row["bucket"])
                assert (
                    policy.status_code == 200 and policy.json().get("public") is False
                )
                path = row["bucket"] + "/" + row["object_key"]
                assert object_missing(
                    client.get(
                        "object/info/authenticated/" + path,
                        params={"verification": uuid4().hex},
                    )
                )
                # Register exact-key cleanup before an upload with an ambiguous ack.
                cleanup.callback(
                    store.delete, bucket=row["bucket"], object_key=row["object_key"]
                )
                response = client.post(
                    "object/" + path,
                    content=data,
                    headers={
                        "Content-Type": "application/pdf",
                        "x-upsert": "false",
                        "Cache-Control": "no-store",
                    },
                )
                assert response.status_code in (200, 201)
                uploaded = client.get(
                    "object/authenticated/" + path, params={"verification": uuid4().hex}
                )
                assert (
                    uploaded.status_code == 200
                    and hashlib.sha256(uploaded.content).hexdigest()
                    == row["sha256_hex"]
                )
        yield store
