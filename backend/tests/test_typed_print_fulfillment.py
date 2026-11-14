"""Offline Phase 6 checks; do not substitute these for PostgreSQL acceptance."""

import copy
import json
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import fitz
import pytest
import zxingcpp
from PIL import Image
from print_fixture import bundle
from pydantic import ValidationError

from app.api.v1.fulfillment import ShipmentRequest
from app.api.v1.printing import JobQARequest, binding_matches
from app.core.config import Settings
from app.core.print_render import (
    PrintUnavailable,
    build_manifest,
    load_bundle,
    render_pdf,
)


def frozen(tmp_path):
    b = load_bundle(Settings(**bundle(tmp_path / "typed-bundle.json")))
    bigger = copy.deepcopy(b["templates"][0])
    bigger["symbol_mm"] = 40
    b["templates"].append(bigger)
    first, second = uuid4(), uuid4()
    rows = [
        {
            "use_id": uuid4(),
            "qr_id": qr,
            "tag_type": "lost",
            "copies": copies,
            "size_mm": Decimal(mm),
            "template_key": "synthetic",
            "template_version": 1,
            "public_token": token * 43,
        }
        for qr, mm, copies, token in [
            (first, "35", 2, "A"),
            (first, "40", 3, "A"),
            (second, "35", 1, "B"),
        ]
    ]
    return rows, build_manifest(b, rows)


def test_one_identity_repeats_across_sizes_and_distinct_items_stay_distinct(tmp_path):
    rows, manifest = frozen(tmp_path)
    data, info = render_pdf(manifest)
    assert data == render_pdf(copy.deepcopy(manifest))[0]
    assert info["counts"]["lost"] == 6
    assert [p["symbol_mm"] for p in info["placements"]] == [35, 35, 40, 40, 40, 35]
    pdf = fitz.open(stream=data, filetype="pdf")
    urls = []
    for page in pdf:
        pix = page.get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False)
        urls.extend(
            r.text
            for r in zxingcpp.read_barcodes(
                Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            )
        )
    assert urls.count("https://print.example.test/q/" + "A" * 43) == 5
    assert urls.count("https://print.example.test/q/" + "B" * 43) == 1
    assert binding_matches(rows, manifest)


@pytest.mark.parametrize(
    "field,value",
    [
        ("use_id", uuid4()),
        ("qr_id", uuid4()),
        ("tag_type", "ice"),
        ("size_mm", Decimal(40)),
        ("copies", 3),
        ("public_token", "C" * 43),
    ],
)
def test_worker_and_reprint_reject_each_changed_binding(tmp_path, field, value):
    rows, manifest = frozen(tmp_path)
    rows[0][field] = value
    assert not binding_matches(rows, manifest)


def test_complete_checkout_copy_bound_is_renderable_but_bounded(tmp_path):
    rows, _ = frozen(tmp_path)
    b = load_bundle(Settings(**bundle(tmp_path / "limit-bundle.json")))
    row = dict(rows[0], copies=5000)
    assert build_manifest(b, [row])["occurrences"][0]["copies"] == 5000
    with pytest.raises(PrintUnavailable):
        build_manifest(b, [dict(row, copies=5001)])


@pytest.mark.parametrize(
    "members", [{}, {"pair_ids": [uuid4()], "logical_item_ids": [uuid4()]}]
)
def test_shipment_requires_exactly_one_membership_model(members):
    with pytest.raises(ValidationError):
        ShipmentRequest(
            order_id=uuid4(),
            shipping_address_id=uuid4(),
            carrier="Synthetic",
            reason="Inspection complete",
            **members,
        )


def test_new_model_membership_never_requires_a_pair():
    iid = uuid4()
    body = ShipmentRequest(
        order_id=uuid4(),
        shipping_address_id=uuid4(),
        logical_item_ids=[iid],
        carrier="Synthetic",
        reason="Inspection complete",
    )
    assert body.logical_item_ids == [iid] and not body.pair_ids


def test_inspection_contract_is_closed_and_has_no_ownership_credentials():
    assert JobQARequest.model_fields["inspected_item_ids"].default_factory is list
    assert "public_token" not in JobQARequest.model_fields
    assert "ownership_proof" not in JobQARequest.model_fields


def test_migration_preserves_legacy_bodies_and_private_handoff():
    sql = (
        Path(__file__).parents[1] / "alembic/versions/0042_typed_print_fulfillment.sql"
    ).read_text()
    assert "pg_get_functiondef" in sql and "IF updated=definition THEN RAISE" in sql
    assert (
        "GRANT EXECUTE ON FUNCTION public.sr_typed_print_handoff() TO safereturn_worker"
        in sql
    )
    assert "FOR UPDATE OF v SKIP LOCKED LIMIT 1" in sql
    assert "UNIQUE REFERENCES public.order_item_qr_allocations" in sql
    assert "SET enabled=true" not in sql


def test_worker_rechecks_every_binding_after_provider_upload(tmp_path, monkeypatch):
    from app.core.print_render import digest
    from app.workers import printing as worker

    rows, manifest = frozen(tmp_path)
    lease = {
        "id": uuid4(),
        "order_id": uuid4(),
        "print_job_id": uuid4(),
        "job_kind": "print.render",
        "lease_owner": "synthetic",
        "attempt_count": 1,
        "payload_ciphertext": b"synthetic",
        "payload_key_version": 1,
    }
    db, storage, completed = MagicMock(), MagicMock(), MagicMock()
    db.execute.return_value.scalar_one.return_value = digest(manifest)

    @contextmanager
    def transaction(*args):
        yield db

    monkeypatch.setattr(worker, "claim", lambda *a: lease)
    monkeypatch.setattr(worker, "worker_transaction", transaction)
    monkeypatch.setattr(worker, "fence", lambda *a, **kw: None)
    monkeypatch.setattr(worker, "gate", lambda *a: None)
    monkeypatch.setattr(worker, "occurrences", lambda *a: rows)
    monkeypatch.setattr(worker, "decrypt", lambda *a: json.dumps(manifest))
    monkeypatch.setattr(
        worker, "render_pdf", lambda *a: (b"synthetic", {"sha256": "a" * 64})
    )
    monkeypatch.setattr(worker, "complete", completed)
    storage.upload.side_effect = lambda *a: rows[0].update(size_mm=Decimal(40))
    assert (
        worker.run_one(
            None, SimpleNamespace(print_enabled=True, print_max_attempts=3), storage
        )
        is False
    )
    completed.assert_not_called()
    queries = [str(c.args[0]) for c in db.execute.call_args_list]
    assert not any("INSERT INTO public.print_artifacts" in sql for sql in queries)
    assert any("failure_code=:code" in sql for sql in queries)
