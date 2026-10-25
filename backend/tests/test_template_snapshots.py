"""Production snapshot adapters with synthetic records, never real orders or I/O."""

from copy import deepcopy
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException
from test_critical_workflow_boundaries import Result
from test_print_templates import content

from app.api.auth import AccessError
from app.core.print_render import PrintUnavailable, digest
from app.db.template_registry import (
    attach_quote_specs,
    gate,
    order_specs,
    recheck_quote,
    registry_manifest,
    resolve,
)


def spec():
    return {
        "use_id": str(UUID(int=1)),
        "asset_set_id": content()["asset_set_id"],
        "policy_sha256": "a" * 64,
        "content": content(),
        "key": "synthetic-key",
        "version": 1,
        "tag_type": "lost",
        "origin": "https://synthetic.test",
        "assets": {
            "font": {"path": "synthetic/font.ttf", "sha256": "b" * 64},
            "logo": {"path": "synthetic/logo.svg", "sha256": "c" * 64},
        },
        "revision_id": str(UUID(int=2)),
        "approval_id": str(UUID(int=3)),
        "fingerprint_sha256": "d" * 64,
    }


def occurrence():
    return {
        "use_id": UUID(int=1),
        "qr_id": UUID(int=4),
        "copies": 2,
        "tag_type": "lost",
        "size_mm": "35.00",
        "public_token": "S" * 43,
        "template_key": "changed-current-key",
        "template_version": 99,
    }


class Session:
    def __init__(self, values, available=True):
        self.values = iter(values)
        self.info = {
            "template_registry_available": available,
            "settings": SimpleNamespace(print_template_management_enabled=True),
        }
        self.calls = []

    def execute(self, sql, params=None):
        self.calls.append((str(sql), params))
        if "sr_template_registry_gate" in str(sql):
            return Result(None)
        return Result(deepcopy(next(self.values)))


def test_manifest_uses_frozen_purchase_not_current_catalog_or_configuration():
    frozen, row = spec(), occurrence()
    original = deepcopy((frozen, row))
    result = registry_manifest([frozen], [row])
    saved_hash = digest(result)
    assert result["occurrences"][0]["template"]["key"] == frozen["key"]
    assert result["occurrences"][0]["qr_id"] == str(row["qr_id"])
    assert result["occurrences"][0]["copies"] == 2
    assert result["registry_snapshots"][0]["approval_id"] == frozen["approval_id"]
    row["template_key"] = "another-current-key"
    row["template_version"] = 100
    assert digest(registry_manifest([frozen], [row])) == saved_hash
    assert frozen == original[0]  # adapter cannot rewrite stored purchase content


@pytest.mark.parametrize(
    "mutation", ["missing", "duplicate", "tag", "token", "assets", "unsafe-content"]
)
def test_registry_manifest_refuses_partial_or_incompatible_frozen_data(mutation):
    values, rows = [spec()], [occurrence()]
    if mutation == "missing":
        values = []
    elif mutation == "duplicate":
        values.append(deepcopy(values[0]))
    elif mutation == "tag":
        rows[0]["tag_type"] = "ice"
    elif mutation == "token":
        rows[0]["public_token"] = "S" * 80
    elif mutation == "assets":
        values.append(spec() | {"use_id": str(UUID(int=5)), "policy_sha256": "e" * 64})
        rows.append(occurrence() | {"use_id": UUID(int=5)})
    else:
        values[0]["content"]["html"] = "<script>PRIVATE_CANARY</script>"
    with pytest.raises((PrintUnavailable, ValueError)):
        registry_manifest(values, rows)


def test_legacy_source_is_explicit_and_registry_never_downgrades():
    line = {"variant_id": str(UUID(int=9)), "qr_uses": [{"tag_type": "lost"}]}
    old = Session([], available=False)
    assert resolve(old, line) is None and not old.calls
    legacy = Session([None])
    assert resolve(legacy, line) is None
    blocked = Session([{"error": "CONFLICT"}])
    with pytest.raises(HTTPException):
        resolve(blocked, line)
    assert all("sr_template" in sql for sql, _ in blocked.calls)


def test_admission_disable_retains_historical_readers_and_withdrawal_denial():
    line = {"variant_id": str(UUID(int=9)), "qr_uses": [{"tag_type": "lost"}]}
    session = Session([[spec()], [spec()]])
    session.info["settings"].print_template_management_enabled = False
    with pytest.raises(AccessError) as exc:
        resolve(session, line)
    assert exc.value.status == 503
    assert order_specs(session, UUID(int=10)) == [spec()]
    with pytest.raises(HTTPException):
        order_specs(Session([{"error": "CONFLICT"}]), UUID(int=10))


def test_quote_rechecks_source_generation_and_binding_before_confirmation():
    frozen = spec() | {"source_generation": 1}
    line = {
        "variant_id": str(UUID(int=9)),
        "qr_uses": [{"tag_type": "lost"}],
        "registry_specs": [frozen],
    }
    recheck_quote(Session([[frozen]]), [line])
    for changed in (
        None,
        [frozen | {"source_generation": 2}],
        [frozen | {"revision_id": str(UUID(int=99))}],
    ):
        with pytest.raises(HTTPException):
            recheck_quote(Session([changed]), [line])


@pytest.mark.parametrize(
    "values",
    [
        [None, [spec()]],
        [[spec()], [spec() | {"asset_set_id": str(UUID(int=99))}]],
        [[spec()], [spec() | {"policy_sha256": "e" * 64}]],
    ],
)
def test_incompatible_mixed_orders_rejected_before_payment(values):
    lines = [
        {"variant_id": str(UUID(int=n)), "qr_uses": [{"tag_type": "lost"}]}
        for n in (1, 2)
    ]
    with pytest.raises(HTTPException):
        attach_quote_specs(Session(values), lines)


def test_gate_mode_chosen_before_row_locks_no_upgrade():
    session = Session([])
    assert gate(session)
    with pytest.raises(AccessError):
        gate(session, exclusive=True)
    assert len(session.calls) == 1


def test_worker_lease_and_withdrawal_fences_remain_distinct(monkeypatch):
    from app.workers import printing

    calls = []
    monkeypatch.setattr(printing, "gate", lambda db: calls.append("gate"))

    def withdrawn(*args):
        calls.append("admission")
        raise HTTPException(409)

    monkeypatch.setattr(printing, "order_specs", withdrawn)

    class DB:
        def execute(self, sql, params):
            calls.append("lease")
            return Result({"id": "synthetic-lease"})

    lease = {
        "order_id": "synthetic-order",
        "id": "synthetic-lease",
        "lease_owner": "synthetic-worker",
        "attempt_count": 1,
    }
    with pytest.raises(HTTPException):
        printing.fence(DB(), lease)
    assert calls == ["gate", "admission"]
    calls.clear()
    printing.fence(DB(), lease, admit=False)
    assert calls == ["gate", "lease"]  # failure bookkeeping grants no render/release
