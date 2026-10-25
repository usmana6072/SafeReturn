"""BTR-01 fixture-only examples, not a role writer or production authority contract.

Python lock/counters/booleans/plain memory receipts are synthetic scaffolding.
No DB, Auth administration, network, storage, credentials or runtime imports.
"""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass, replace
from threading import Barrier, RLock

import pytest

ROLES = {"support", "finance", "operations", "security_admin", "superadmin"}


@dataclass(frozen=True)
class Packet:
    subject: str = "synthetic-member"
    role: str = "operations"
    action: str = "grant"
    executor: str = "synthetic-executor"
    owner: str = "synthetic-owner"
    custodian: str = "synthetic-reviewer"
    reference: str = "synthetic-change"
    key: str = "synthetic-attempt"
    fixture_version: int = 0
    confirmed: bool = True


class Denied(Exception):
    pass


class Rehearsal:
    """Closed synthetic fixture. This class is never imported by application code."""

    def __init__(self):
        self.lock = RLock()
        self.grants = [
            {"person": "synthetic-owner", "role": role, "revoked": False}
            for role in ["operations", "finance"]
        ] + [
            {"person": person, "role": "security_admin", "revoked": False}
            for person in ["synthetic-security-a", "synthetic-security-b"]
        ]
        self.recoverable = {"synthetic-security-a", "synthetic-security-b"}
        self.suspended = set()
        self.versions = {}
        self.audit, self.receipts = [], {}
        self.owner_approved = self.custodian_reviewed = self.channel_reviewed = True
        self.identity_live = self.verified = self.signed_aal2 = self.provider_aal2 = (
            True
        )
        self.authority_current = True
        self.signed_amr_age = 10

    def roles(self, person):
        return {
            r["role"] for r in self.grants if r["person"] == person and not r["revoked"]
        }

    def protected(self, person, explicitly_allowed):
        return (
            self.identity_live
            and self.verified
            and self.signed_aal2
            and self.provider_aal2
            and bool(self.roles(person) & set(explicitly_allowed))
        )

    def state(self):
        return deepcopy((self.grants, self.versions, self.audit, self.receipts))

    def apply_fixture(self, packet, failure=None):
        with self.lock:
            if not all(
                type(v) is str and v.startswith("synthetic-")
                for v in [
                    packet.subject,
                    packet.executor,
                    packet.owner,
                    packet.custodian,
                    packet.reference,
                    packet.key,
                ]
            ):
                raise Denied("FIXTURE_ONLY")
            if packet.role not in ROLES or packet.action not in {"grant", "revoke"}:
                raise Denied("UNSUPPORTED")
            if packet.subject == "synthetic-owner":
                raise Denied("OWNER_EXCLUDED")
            if (
                packet.subject in {packet.executor, packet.owner, packet.custodian}
                or packet.owner == packet.custodian
            ):
                raise Denied("INDEPENDENCE")
            if not all(
                [
                    self.owner_approved,
                    self.custodian_reviewed,
                    self.channel_reviewed,
                    self.identity_live,
                    self.verified,
                    self.signed_aal2,
                    self.provider_aal2,
                    self.authority_current,
                ]
            ):
                raise Denied("NO_AUTHORITY")
            if (
                type(self.signed_amr_age) is not int
                or not 0 <= self.signed_amr_age <= 300
            ):
                raise Denied("RECENT_AMR")
            if packet.confirmed is not True or type(packet.fixture_version) is not int:
                raise Denied("REVIEW_REQUIRED")
            # Synthetic canonical body/scope only; not a receipt encryption design.
            body = json.dumps(packet.__dict__, sort_keys=True)
            scope = (
                packet.executor,
                packet.action,
                packet.subject,
                packet.role,
                packet.key,
            )
            digest = hashlib.sha256(body.encode()).hexdigest()
            if scope in self.receipts:
                previous, receipt = self.receipts[scope]
                if digest != previous:
                    raise Denied("KEY_REUSED")
                return receipt
            if packet.fixture_version != self.versions.get(packet.subject, 0):
                raise Denied("STALE_FIXTURE")
            active = [
                r
                for r in self.grants
                if r["person"] == packet.subject
                and r["role"] == packet.role
                and not r["revoked"]
            ]
            if bool(active) != (packet.action == "revoke"):
                raise Denied("ACTIVE_UNIQUENESS")
            if packet.action == "revoke" and packet.role == "security_admin":
                remaining = [
                    p
                    for p in self.recoverable
                    if p != packet.subject
                    and p not in self.suspended
                    and "security_admin" in self.roles(p)
                ]
                if not remaining:
                    raise Denied("LAST_RECOVERABLE_CUSTODIAN")
            before = self.state()
            try:
                if packet.action == "grant":
                    self.grants.append(
                        {
                            "person": packet.subject,
                            "role": packet.role,
                            "revoked": False,
                        }
                    )
                else:
                    active[0]["revoked"] = True
                self.versions[packet.subject] = packet.fixture_version + 1
                if failure == "state":
                    raise Denied("SIMULATED_STATE_FAILURE")
                # No new production audit JSON keys. All values are fixture metadata.
                self.audit.append(
                    {
                        "event_id": packet.reference,
                        "from_status": "active" if active else "absent",
                        "to_status": "revoked" if active else "active",
                        "version": self.versions[packet.subject],
                        "outcome": "simulation_only",
                    }
                )
                if failure == "audit":
                    raise Denied("SIMULATED_AUDIT_FAILURE")
                receipt = (
                    "SIMULATION_ONLY",
                    packet.reference,
                    self.versions[packet.subject],
                )
                self.receipts[scope] = (digest, receipt)
                if failure in {"receipt", "commit"}:
                    raise Denied("SIMULATED_TRANSACTION_FAILURE")
                return receipt
            except BaseException:
                self.grants, self.versions, self.audit, self.receipts = before
                raise


def test_grant_revoke_regrant_preserves_history_owner_and_next_command_denial():
    r, p = Rehearsal(), Packet()
    original = deepcopy(r.grants)
    r.apply_fixture(p)
    assert r.protected(p.subject, ["operations"])
    r.apply_fixture(
        replace(p, action="revoke", fixture_version=1, key="synthetic-revoke")
    )
    assert not r.protected(p.subject, ["operations"])
    assert len(r.grants) == len(original) + 1 and r.grants[-1]["revoked"]
    r.apply_fixture(replace(p, fixture_version=2, key="synthetic-regrant"))
    assert len(r.grants) == len(original) + 2 and r.grants[-2]["revoked"]
    assert r.grants[: len(original)] == original
    assert r.roles("synthetic-owner") == {"operations", "finance"}


@pytest.mark.parametrize(
    "field",
    [
        "owner_approved",
        "custodian_reviewed",
        "channel_reviewed",
        "identity_live",
        "verified",
        "signed_aal2",
        "provider_aal2",
        "authority_current",
    ],
)
def test_absent_evidence_never_inferred_from_roles(field):
    r = Rehearsal()
    setattr(r, field, False)
    before = r.state()
    with pytest.raises(Denied, match="NO_AUTHORITY"):
        r.apply_fixture(Packet())
    assert r.state() == before


@pytest.mark.parametrize(
    "change",
    [
        {"subject": "real-account"},
        {"role": "admin"},
        {"role": "*"},
        {"subject": "synthetic-owner"},
        {"subject": "synthetic-executor"},
        {"subject": "synthetic-reviewer"},
        {"custodian": "synthetic-owner"},
        {"confirmed": False},
        {"fixture_version": True},
        {"fixture_version": 1},
    ],
)
def test_closed_scope_self_independence_confirmation_and_staleness(change):
    r = Rehearsal()
    before = r.state()
    with pytest.raises(Denied):
        r.apply_fixture(replace(Packet(), **change))
    assert r.state() == before


@pytest.mark.parametrize("age", [None, True, "10", -1, 301])
def test_recent_amr_not_token_refresh_or_typed_timestamp(age):
    r = Rehearsal()
    r.signed_amr_age = age
    with pytest.raises(Denied, match="RECENT_AMR"):
        r.apply_fixture(Packet())


def test_role_union_does_not_inherit_or_supply_independent_people():
    r = Rehearsal()
    r.apply_fixture(Packet(role="superadmin"))
    assert not r.protected("synthetic-member", ["operations", "finance"])
    assert r.protected("synthetic-owner", ["finance"])
    with pytest.raises(Denied, match="INDEPENDENCE"):
        r.apply_fixture(Packet(subject="synthetic-executor", role="security_admin"))


@pytest.mark.parametrize("unusable", ["suspended", "unrecoverable", "no_active_role"])
def test_nominal_second_custodian_is_not_recoverable(unusable):
    r = Rehearsal()
    if unusable == "suspended":
        r.suspended.add("synthetic-security-b")
    elif unusable == "unrecoverable":
        r.recoverable.remove("synthetic-security-b")
    else:
        r.grants[-1]["revoked"] = True
    with pytest.raises(Denied, match="LAST_RECOVERABLE_CUSTODIAN"):
        r.apply_fixture(
            Packet(
                subject="synthetic-security-a", role="security_admin", action="revoke"
            )
        )


def test_concurrent_removal_serializes_fixture_last_custodian_check():
    r, barrier = Rehearsal(), Barrier(2)

    def remove(person):
        barrier.wait()
        try:
            r.apply_fixture(
                Packet(
                    subject=person,
                    role="security_admin",
                    action="revoke",
                    key="synthetic-" + person,
                )
            )
            return "simulated"
        except Denied as error:
            return str(error)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(
            pool.map(remove, ["synthetic-security-a", "synthetic-security-b"])
        )
    assert sorted(outcomes) == ["LAST_RECOVERABLE_CUSTODIAN", "simulated"]
    assert sum("security_admin" in r.roles(p) for p in r.recoverable) == 1


def test_receipt_replay_conflicting_key_and_revoked_authority():
    r, p = Rehearsal(), Packet()
    receipt = r.apply_fixture(p)
    assert r.apply_fixture(p) == receipt and len(r.audit) == 1
    with pytest.raises(Denied, match="KEY_REUSED"):
        r.apply_fixture(replace(p, reference="synthetic-other-review"))
    r.authority_current = False
    with pytest.raises(Denied, match="NO_AUTHORITY"):
        r.apply_fixture(p)


@pytest.mark.parametrize("failure", ["state", "audit", "receipt", "commit"])
def test_synthetic_transaction_failure_restores_all_history(failure):
    r, p = Rehearsal(), Packet()
    before = r.state()
    with pytest.raises(Denied):
        r.apply_fixture(p, failure=failure)
    assert r.state() == before
    assert r.apply_fixture(p)[0] == "SIMULATION_ONLY"
