"""Narrow bootstrap DTO tests; no real Auth/provider/account writes."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.api.auth import AccessError
from app.api.v1.account import staff_security


class Query:
    def __init__(self, roles):
        self.roles = roles

    def scalars(self):
        return iter(self.roles)


def context(roles, *, verified=True, mfa=False):
    calls = []

    def execute(statement, params):
        calls.append((str(statement), params))
        return Query(roles)

    return SimpleNamespace(
        email_verified=verified,
        mfa_verified=mfa,
        principal=SimpleNamespace(user_id=uuid4()),
        session=SimpleNamespace(execute=execute),
    ), calls


def test_bootstrap_preserves_both_roles_without_granting_mfa():
    ctx, calls = context(["finance", "operations"])
    result = staff_security(ctx)
    assert result.roles == ["finance", "operations"]
    assert result.mfa_verified is False
    assert len(calls) == 1
    assert "revoked_at IS NULL" in calls[0][0]
    assert calls[0][1] == {"uid": ctx.principal.user_id}


@pytest.mark.parametrize("roles", [[], ["unknown"]])
def test_missing_or_revoked_roles_denied(roles):
    ctx, _ = context(roles)
    with pytest.raises(AccessError) as error:
        staff_security(ctx)
    assert error.value.status == 403


def test_unverified_email_denied_before_role_read():
    ctx, calls = context(["finance"], verified=False)
    with pytest.raises(AccessError):
        staff_security(ctx)
    assert calls == []


def test_bootstrap_exposes_existing_verified_assurance():
    ctx, _ = context(["operations"], mfa=True)
    assert staff_security(ctx).mfa_verified is True


@pytest.mark.parametrize(
    ("roles", "expected"),
    [
        (
            ["operations"],
            [
                "catalog.manage",
                "fulfillment.manage",
                "notifications.manage",
                "printing.manage",
            ],
        ),
        (["finance"], ["payments.review"]),
        (["support"], ["support.manage"]),
        (["security_admin"], ["catalog.manage", "notifications.manage"]),
        (["superadmin"], ["catalog.manage"]),
        (
            ["operations", "finance"],
            [
                "catalog.manage",
                "fulfillment.manage",
                "notifications.manage",
                "payments.review",
                "printing.manage",
            ],
        ),
    ],
)
@pytest.mark.parametrize("mfa", [False, True])
def test_explicit_role_capability_matrix(roles, expected, mfa):
    ctx, _ = context(roles, mfa=mfa)
    assert staff_security(ctx).capabilities == (expected if mfa else [])
