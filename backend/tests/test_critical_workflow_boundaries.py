"""Task 6.1 in-memory HTTP/transaction orchestration; not PostgreSQL proof."""

from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import OperationalError
from test_auth import claims, signed
from test_auth import verifier as _verifier
from test_health import ASGIClient

from app.core.config import Settings
from app.main import create_app
from app.workers.finance_retention import LeaseLost, cleanup_private_artifact

verifier = _verifier


class Result:
    def __init__(self, value):
        self.value = value

    def mappings(self):
        return self

    def __iter__(self):
        return iter(self.value)

    def one_or_none(self):
        return self.value

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.value

    def first(self):
        return self.value


class MemoryDatabase:
    """Tiny repository stand-in with rollback snapshots, no SQL engine or I/O."""

    def __init__(self, owner, order):
        self.owner, self.order = owner, order
        self.profile = {
            "display_name": "Before",
            "preferred_locale": "en",
            "has_phone": False,
            "version": "1.000001",
        }
        self.roles = {"operations"}
        self.active = True
        self.mfa = True
        self.info = {}
        self.audit = []
        self.actor = None
        self.fail_audit = False
        self.fail_commit = False
        self.commits = 0
        self.rollbacks = 0
        self.statements = []

    @contextmanager
    def transaction(self):
        before = deepcopy((self.profile, self.audit))
        try:
            yield self
            if self.fail_commit:
                raise OperationalError("COMMIT", {}, Exception("PRIVATE_CANARY_COMMIT"))
        except BaseException:
            self.profile, self.audit = before
            self.rollbacks += 1
            raise
        else:
            self.commits += 1
        finally:
            self.actor = None

    def execute(self, statement, params=None):
        sql = str(statement)
        params = params or {}
        if "AS template_registry_available" in sql:
            return Result(False)
        self.statements.append(sql)
        if "set_config('safereturn.actor_id'" in sql:
            self.actor = params["actor"]
            return Result(None)
        if "SET LOCAL ROLE" in sql or "set_config('safereturn.mfa_verified'" in sql:
            return Result(None)
        if "sr_account_session_state" in sql:
            return Result(
                SimpleNamespace(email_verified=True, mfa_active=self.mfa)
                if self.active
                else None
            )
        if "SELECT 1 FROM public.orders" in sql:
            return Result(
                1
                if params["id"] == self.order and params["uid"] == self.owner
                else None
            )
        if "FROM public.shipments WHERE order_id" in sql:
            return Result(
                [
                    {
                        "id": str(UUID(int=10)),
                        "carrier": "Synthetic carrier",
                        "tracking_reference": "synthetic-tracking",
                        "status": "preparing",
                        "packed_at": None,
                        "dispatched_at": None,
                        "delivered_at": None,
                    }
                ]
            )
        if "SELECT 1 FROM public.staff_roles" in sql:
            return Result(1 if self.roles.intersection(params["roles"]) else None)
        if "FROM public.orders o" in sql:
            return Result([])
        if "UPDATE public.user_profiles SET" in sql:
            if params["version"] != self.profile["version"]:
                return Result(None)
            if params["name_set"]:
                self.profile["display_name"] = params["name"]
            if params["locale_set"]:
                self.profile["preferred_locale"] = params["locale"]
            self.profile["version"] = "1.000002"
            return Result(params["uid"])
        if "FROM public.user_profiles" in sql:
            return Result(self.profile.copy())
        if "INSERT INTO public.audit_events" in sql:
            if self.fail_audit:
                raise OperationalError(
                    "INSERT audit", {}, Exception("PRIVATE_CANARY_AUDIT")
                )
            self.audit.append(params.copy())
            return Result(None)
        raise AssertionError("Unexpected query in narrow Task 6.1 fixture")


@pytest.fixture
def workflow(verifier):
    provider, private, _, _ = verifier
    owner, foreign, oid = uuid4(), uuid4(), uuid4()
    database = MemoryDatabase(owner, oid)
    app = create_app(Settings())
    app.state.database = database
    app.state.jwt_verifier = provider
    client = ASGIClient(app)

    def headers(uid=owner, **overrides):
        return {
            "Authorization": "Bearer "
            + signed(private, claims(sub=str(uid), aal="aal2", **overrides))
        }

    return client, database, headers, foreign, oid


def test_owner_shipments_http_projection_and_cross_user_denial(workflow):
    client, db, headers, foreign, oid = workflow
    path = f"/api/v1/me/orders/{oid}/shipments"
    own = client.get(path, headers=headers())
    assert (
        own.status_code == 200 and own.headers["cache-control"] == "private, no-store"
    )
    assert set(own.json()["items"][0]) == {
        "id",
        "carrier",
        "tracking_reference",
        "status",
        "packed_at",
        "dispatched_at",
        "delivered_at",
    }
    # Foreign checks must stop before reading any shipment metadata.
    before = db.statements.count(
        next(q for q in db.statements if "FROM public.shipments" in q)
    )
    denied = client.get(path, headers=headers(foreign))
    assert denied.status_code == 404
    assert sum("FROM public.shipments" in q for q in db.statements) == before
    assert "synthetic-tracking" not in denied.text
    assert (
        client.get(
            f"/api/v1/me/orders/{uuid4()}/shipments", headers=headers()
        ).status_code
        == 404
    )


def test_live_session_mfa_and_explicit_role_boundaries(workflow):
    client, db, headers, _, _ = workflow
    path = "/api/v1/admin/orders/ready-to-ship"
    assert client.get(path).status_code == 401
    assert client.get(path, headers=headers(exp=1)).status_code == 401
    db.active = False
    assert client.get(path, headers=headers()).status_code == 401
    db.active = True
    db.mfa = False
    assert client.get(path, headers=headers()).status_code == 403
    db.mfa = True
    for role in ("finance", "security_admin", "superadmin", "support"):
        db.roles = {role}
        assert client.get(path, headers=headers()).status_code == 403
    db.roles = {"operations", "finance"}
    assert client.get(path, headers=headers()).status_code == 200


@pytest.mark.parametrize("failure", ["fail_audit", "fail_commit"])
def test_profile_and_audit_rollback_before_response_then_safe_retry(
    workflow, failure, caplog
):
    client, db, headers, _, _ = workflow
    original = deepcopy(db.profile)
    setattr(db, failure, True)

    def edit():
        return client.request(
            "PATCH",
            "/api/v1/me",
            headers={**headers(), "If-Match": '"1.000001"'},
            json={"display_name": "After"},
        )

    unavailable = edit()
    assert (
        unavailable.status_code == 503
        and unavailable.headers["cache-control"] == "no-store"
    )
    assert "PRIVATE_CANARY" not in unavailable.text + caplog.text
    assert db.profile == original and db.audit == [] and db.rollbacks == 1
    setattr(db, failure, False)
    assert edit().status_code == 200
    assert db.profile["display_name"] == "After" and len(db.audit) == 1
    # Versioned retries cannot duplicate audit or overwrite later edits.
    assert edit().status_code == 412 and len(db.audit) == 1


@pytest.mark.parametrize("held", [True, False])
def test_cleanup_hold_or_lost_lease_prevents_storage_access(held):
    artifact = uuid4()
    lease = {
        "id": uuid4(),
        "aggregate_id": artifact,
        "aggregate_type": "print_artifact",
        "lease_owner": "synthetic-61",
        "attempt_count": 1,
    }
    calls = []

    class DB:
        @contextmanager
        def transaction(self):
            yield self

        def execute(self, statement, params=None):
            query = str(statement)
            calls.append(query)
            if "FROM public.durable_jobs" in query:
                return Result((lease["id"],) if held else None)
            if "sr_retention_prepare" in query:
                return Result({"authorized": False, "deleted": False, "reason": "held"})
            return Result(None)

    class Store:
        def delete(self, **kwargs):
            pytest.fail("Hold or lost lease reached object deletion")

    kwargs = {
        "worker_id": "synthetic-61",
        "artifact_id": artifact,
        "settings": Settings(print_retention_approval="synthetic-policy-only"),
        "lease": lease,
    }
    if held:
        assert cleanup_private_artifact(DB(), Store(), **kwargs)["reason"] == "held"
    else:
        with pytest.raises(LeaseLost):
            cleanup_private_artifact(DB(), Store(), **kwargs)
        assert not any("sr_retention_prepare" in q for q in calls)
    assert not any("sr_retention_finish" in q for q in calls)
