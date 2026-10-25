"""Approved BTR03 fixture-only rehearsal; never imported by app/worker code.

All authority, stock, time and transaction state is synthetic. Python serialization
is not PostgreSQL locking/MVCC, nor a real approval/custody/physical-release proof.
"""

import base64
import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass, replace
from threading import Barrier, RLock
from uuid import UUID

import pytest
from pydantic import SecretStr
from test_health import ASGIClient

from app.core.config import Settings
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt, encrypt
from app.main import create_app


class Denied(Exception):
    pass


@dataclass(frozen=True)
class Command:
    case_id: str = "synthetic-case"
    expected_revision: int = 7
    expected_current_qr_id: str = "synthetic-lost"
    tag_type: str = "lost"
    replacement_batch_id: str = "synthetic-replacement-batch"
    replacement_serial: str = "synthetic-spare-serial"
    qa_reference: str = "synthetic-qa"
    reason_code: str = "damaged"
    confirmed: bool = True


class Rehearsal:
    """Fixture specification only: no DB, network, provider, files or real tokens."""

    def __init__(self):
        self.lock = RLock()
        self.actor, self.roles = "synthetic-operations", {"operations"}
        self.session = self.verified = self.signed_mfa = self.live_mfa = True
        self.origin, self.amr_age = True, 10
        self.authority_live = self.security_role = True
        self.approver, self.executor = "synthetic-security", self.actor
        self.expires, self.now = 200, 100
        self.case_revision = self.approved_case_revision = 2
        self.case_pair = "synthetic-pair"
        self.case_owner = "synthetic-owner"
        self.evidence = self.entitlement = self.custody = self.stock = True
        self.approved = Command()
        self.state = {
            "pair": "synthetic-pair",
            "owner": "synthetic-owner",
            "revision": 7,
            "ownership": "active",
            "credential": "consumed",
            "credential_exposed": False,
            "approval_used": False,
            "tags": {
                "synthetic-lost": {
                    "type": "lost",
                    "current": True,
                    "status": "active",
                    "token": "synthetic-old-token",
                },
                "synthetic-ice": {
                    "type": "ice",
                    "current": True,
                    "status": "active",
                    "token": "synthetic-sibling-token",
                },
            },
            "orders": [
                {
                    "id": "synthetic-order",
                    "held": False,
                    "disputed": False,
                    "cancellation_review": False,
                    "production_ambiguous": False,
                    "shipment_ambiguous": False,
                    "cancelled": False,
                    "occurrences": ["synthetic-lost"],
                }
            ],
            "fences": {
                "print": True,
                "artifact": True,
                "grant": True,
                "worker": True,
                "fulfillment": True,
            },
            "profiles": {
                "synthetic-lost": {
                    "ciphertext": "PRIVATE_CANARY",
                    "consent": "synthetic-old-consent",
                }
            },
            "messages": [("synthetic-lost", "synthetic-original-recipient")],
            "audit": [],
            "receipts": {},
        }

    def guard(self):
        if not (
            self.actor == self.executor
            and "operations" in self.roles
            and self.session
            and self.verified
            and self.signed_mfa
            and self.live_mfa
            and self.origin
            and 0 <= self.amr_age <= 300
        ):
            raise Denied("AUTHORIZATION")
        if not (
            self.authority_live
            and self.security_role
            and self.approver != self.actor
            and self.now < self.expires
        ):
            raise Denied("INDEPENDENT_AUTHORITY")
        if (
            self.case_pair != self.state["pair"]
            or self.case_owner != self.state["owner"]
            or self.case_revision != self.approved_case_revision
        ):
            raise Denied("APPROVAL_BINDING")

    def apply(self, body=None, key="synthetic-attempt", failure=None):
        body = body or Command()
        with self.lock:
            self.guard()
            if not isinstance(body, Command) or not key.startswith("synthetic-"):
                raise Denied("CLOSED_FIXTURE_COMMAND")
            if (
                type(body.confirmed) is not bool
                or not body.confirmed
                or type(body.expected_revision) is not int
                or not 1 <= body.expected_revision <= 2147483646
                or body.reason_code not in {"damaged", "compromised_public_token"}
            ):
                raise Denied("INVALID_COMMAND")
            # Fixture receipts are plain memory, not a production encrypted store.
            receipt_key = (self.actor, self.state["pair"], key)
            previous = self.state["receipts"].get(receipt_key)
            if previous:
                if previous[0] != body:
                    raise Denied("IDEMPOTENCY_KEY_REUSED")
                return deepcopy(previous[1])
            before = deepcopy(self.state)
            try:
                s = self.state
                if s["revision"] != body.expected_revision:
                    raise Denied("STALE_REVISION")
                if (
                    body != self.approved
                    or self.case_pair != s["pair"]
                    or self.case_owner != s["owner"]
                    or self.case_revision != self.approved_case_revision
                    or s["approval_used"]
                ):
                    raise Denied("APPROVAL_BINDING")
                if not (
                    self.evidence and self.entitlement and self.custody and self.stock
                ):
                    raise Denied("PROVENANCE")
                if (
                    s["ownership"] != "active"
                    or s["credential"] != "consumed"
                    or s["credential_exposed"]
                ):
                    raise Denied("SECURITY_RESPONSE_UNAVAILABLE")
                old = s["tags"].get(body.expected_current_qr_id)
                if not old or not old["current"] or old["type"] != body.tag_type:
                    raise Denied("CURRENT_CHILD")
                if old["status"] not in {"active", "owner_disabled"}:
                    raise Denied("SECURITY_STATE")
                if any(
                    q["status"] not in {"active", "owner_disabled"}
                    for q in s["tags"].values()
                    if q["current"]
                ):
                    raise Denied("SECURITY_STATE")
                if any(
                    any(
                        o[f]
                        for f in (
                            "held",
                            "disputed",
                            "cancellation_review",
                            "production_ambiguous",
                            "shipment_ambiguous",
                        )
                    )
                    for o in s["orders"]
                ):
                    raise Denied("ORDER_REVIEW")
                # Cancelled history grants no entitlement; all occurrences stay frozen.
                new_id = "synthetic-replacement-" + body.tag_type
                old.update(current=False, status="revoked", revoked_at=self.now)
                s["tags"][new_id] = {
                    "type": body.tag_type,
                    "current": True,
                    "status": "owner_disabled",
                    "token": "synthetic-new-token",
                    "replaces": body.expected_current_qr_id,
                }
                s["profiles"][new_id] = {"published": False, "consent": None}
                s["approval_used"] = True
                s["revision"] += 1
                s["fences"] = dict.fromkeys(s["fences"], False)
                current = [q["type"] for q in s["tags"].values() if q["current"]]
                if sorted(current) != ["ice", "lost"]:
                    raise Denied("EXACT_TWO")
                if failure == "audit":
                    raise Denied("AUDIT_FAILURE")
                s["audit"].append((s["pair"], body.expected_current_qr_id, new_id))
                result = {
                    "pair_id": s["pair"],
                    "pair_revision": s["revision"],
                    "old_qr_id": body.expected_current_qr_id,
                    "new_qr_id": new_id,
                    "tag_type": body.tag_type,
                    "old_public_status": "revoked",
                    "new_public_status": "owner_disabled",
                    "profile_state": "private_unpublished",
                }
                if failure == "receipt":
                    raise Denied("RECEIPT_FAILURE")
                s["receipts"][receipt_key] = (body, deepcopy(result))
                if failure == "authorization":
                    self.session = False
                self.guard()
                if failure == "commit":
                    raise Denied("COMMIT_FAILURE")
                return result
            except Exception:
                self.state = before
                raise


@pytest.mark.parametrize("reason", ["damaged", "compromised_public_token"])
@pytest.mark.parametrize("status", ["active", "owner_disabled"])
@pytest.mark.parametrize("kind", ["lost", "ice"])
def test_fixture_replacement_preserves_sibling_owner_history_and_private_profile(
    reason, status, kind
):
    r = Rehearsal()
    r.approved = replace(
        Command(),
        reason_code=reason,
        tag_type=kind,
        expected_current_qr_id="synthetic-" + kind,
    )
    r.state["tags"]["synthetic-" + kind]["status"] = status
    before = deepcopy(r.state)
    result = r.apply(r.approved)
    sibling = "synthetic-" + ("ice" if kind == "lost" else "lost")
    assert r.state["tags"][sibling] == before["tags"][sibling]
    for field in ["owner", "credential", "orders", "messages"]:
        assert r.state[field] == before[field]
    assert r.state["tags"][result["old_qr_id"]]["status"] == "revoked"
    assert not any(r.state["fences"].values())
    assert r.state["profiles"][result["new_qr_id"]] == {
        "published": False,
        "consent": None,
    }
    assert "PRIVATE_CANARY" not in json.dumps(result)
    assert set(result) == {
        "pair_id",
        "pair_revision",
        "old_qr_id",
        "new_qr_id",
        "tag_type",
        "old_public_status",
        "new_public_status",
        "profile_state",
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("roles", {"superadmin"}),
        ("roles", {"security_admin"}),
        ("roles", {"operations_wrong"}),
        ("roles", {"finance", "support"}),
        ("actor", "synthetic-other-operator"),
        ("session", False),
        ("verified", False),
        ("signed_mfa", False),
        ("live_mfa", False),
        ("origin", False),
        ("amr_age", 301),
        ("amr_age", -1),
        ("authority_live", False),
        ("security_role", False),
        ("approver", "synthetic-operations"),
        ("expires", 100),
        ("case_pair", "synthetic-other-pair"),
        ("case_owner", "synthetic-other-owner"),
        ("case_revision", 3),
        ("evidence", False),
        ("custody", False),
        ("stock", False),
        ("entitlement", False),
    ],
)
def test_fixture_authority_and_provenance_denials_are_atomic(field, value):
    r = Rehearsal()
    setattr(r, field, value)
    before = deepcopy(r.state)
    with pytest.raises(Denied):
        r.apply()
    assert r.state == before


@pytest.mark.parametrize(
    "changes",
    [
        {"confirmed": False},
        {"confirmed": 1},
        {"expected_revision": True},
        {"expected_revision": 6},
        {"expected_revision": 2147483647},
        {"expected_current_qr_id": "synthetic-historical"},
        {"tag_type": "ice"},
        {"case_id": "synthetic-other-case"},
        {"replacement_serial": "synthetic-other"},
        {"replacement_batch_id": "synthetic-other"},
        {"qa_reference": "synthetic-other"},
        {"reason_code": "compromised_secret"},
    ],
)
def test_fixture_closed_command_and_binding(changes):
    r = Rehearsal()
    before = deepcopy(r.state)
    with pytest.raises(Denied):
        r.apply(replace(Command(), **changes))
    assert r.state == before
    with pytest.raises(TypeError):
        Command(owner="synthetic-other")


@pytest.mark.parametrize(
    "field,value",
    [
        ("ownership", "disputed"),
        ("ownership", "revoked"),
        ("credential", "unused"),
        ("credential", "locked"),
        ("credential", "revoked"),
        ("credential_exposed", True),
        ("approval_used", True),
    ],
)
def test_fixture_unavailable_security_response(field, value):
    r = Rehearsal()
    r.state[field] = value
    with pytest.raises(Denied):
        r.apply()


@pytest.mark.parametrize(
    "field",
    [
        "held",
        "disputed",
        "cancellation_review",
        "production_ambiguous",
        "shipment_ambiguous",
    ],
)
def test_fixture_order_fences_include_reused_identity_orders(field):
    r = Rehearsal()
    other = deepcopy(r.state["orders"][0])
    other.update(id="synthetic-second-order", **{field: True})
    r.state["orders"].append(other)
    before = deepcopy(r.state)
    with pytest.raises(Denied, match="ORDER_REVIEW"):
        r.apply()
    assert r.state == before


@pytest.mark.parametrize("status", ["admin_suspended", "revoked", "unactivated"])
def test_fixture_does_not_restore_staff_or_unactivated_state(status):
    r = Rehearsal()
    r.state["tags"]["synthetic-lost"]["status"] = status
    with pytest.raises(Denied, match="SECURITY_STATE"):
        r.apply()


@pytest.mark.parametrize("failure", ["audit", "receipt", "authorization", "commit"])
def test_fixture_failure_rollback(failure):
    r = Rehearsal()
    before = deepcopy(r.state)
    with pytest.raises(Denied):
        r.apply(failure=failure)
    assert r.state == before
    r.session = True
    assert r.apply()["pair_revision"] == 8


def test_fixture_idempotency_revocation_and_cancelled_history():
    r = Rehearsal()
    r.state["orders"][0]["cancelled"] = True
    result = r.apply()
    before = deepcopy(r.state)
    assert r.apply() == result
    assert r.state == before
    with pytest.raises(Denied, match="IDEMPOTENCY_KEY_REUSED"):
        r.apply(replace(Command(), reason_code="compromised_public_token"))
    with pytest.raises(Denied, match="STALE_REVISION"):
        r.apply(key="synthetic-another-attempt")
    r.authority_live = False
    with pytest.raises(Denied, match="INDEPENDENT_AUTHORITY"):
        r.apply()
    assert r.state == before


def test_fixture_two_concurrent_replacements_have_one_winner():
    r, barrier = Rehearsal(), Barrier(2)

    def attempt(key):
        barrier.wait()
        try:
            return r.apply(key=key)
        except Denied as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ["synthetic-first", "synthetic-second"]))
    assert sum(isinstance(v, dict) for v in results) == 1
    assert "STALE_REVISION" in results
    assert r.state["revision"] == 8 and len(r.state["audit"]) == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("case_owner", "synthetic-new-owner"),
        ("case_pair", "synthetic-other-pair"),
        ("case_revision", 3),
        ("session", False),
        ("roles", {"finance"}),
        ("security_role", False),
        ("expires", 100),
    ],
)
def test_fixture_replay_rechecks_live_authority_and_subject(field, value):
    r = Rehearsal()
    r.apply()
    before = deepcopy(r.state)
    setattr(r, field, value)
    with pytest.raises(Denied):
        r.apply()
    assert r.state == before


@pytest.mark.parametrize(
    "fault", ["historical", "missing_sibling", "suspended_sibling"]
)
def test_fixture_current_identity_and_exact_two_fail_closed(fault):
    r = Rehearsal()
    if fault == "historical":
        r.state["tags"]["synthetic-lost"]["current"] = False
    elif fault == "missing_sibling":
        del r.state["tags"]["synthetic-ice"]
    else:
        r.state["tags"]["synthetic-ice"]["status"] = "admin_suspended"
    before = deepcopy(r.state)
    with pytest.raises(Denied):
        r.apply()
    assert r.state == before


def test_production_aead_rejects_ciphertext_copied_to_replacement_identity():
    settings = Settings(
        profile_data_keys=SecretStr(
            json.dumps(
                {
                    "1": base64.urlsafe_b64encode(b"s" * 32).decode(),
                }
            )
        ),
        profile_data_key_version=1,
    )
    old, new = UUID(int=1), UUID(int=2)
    value, version = encrypt(settings, old, "medical_notes", "SYNTHETIC_PRIVATE_CANARY")
    assert (
        decrypt(settings, old, "medical_notes", value, version)
        == "SYNTHETIC_PRIVATE_CANARY"
    )
    with pytest.raises(ProfileCryptoUnavailable):
        decrypt(settings, new, "medical_notes", value, version)


def test_runtime_replacement_and_staff_security_remain_unavailable_without_listener():
    app = create_app(Settings())
    operations = {
        op.get("operationId")
        for path in app.openapi()["paths"].values()
        for op in path.values()
        if isinstance(op, dict)
    }
    assert "API-089" not in operations and "API-088" not in operations
    response = ASGIClient(app).post(
        "/api/v1/admin/tag-pairs/00000000-0000-0000-0000-000000000001/replacements",
        json={"case_id": "PRIVATE_CANARY"},
        follow_redirects=False,
    )
    assert response.status_code == 404
    assert "PRIVATE_CANARY" not in response.text
