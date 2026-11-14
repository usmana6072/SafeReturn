"""Offline: real schema/AEAD/intent checks, scripted transaction and route fence.

No live Auth/database, credentials, fixtures, network or migration execution.
"""

import asyncio
import base64
import hashlib
import json
import re
import sqlite3
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import httpx
import pytest
from pydantic import SecretStr
from test_support_metadata import ACTOR as METADATA_ACTOR
from test_support_metadata import Result
from test_support_metadata import harness as metadata_harness

from app.api.auth import AccessError, AuthContext
from app.core.auth import Principal
from app.core.config import Settings
from app.services.support_development_access import enforce
from app.services.support_provisioning import (
    AMENDMENT,
    CHANGE,
    EMAIL,
    PROJECT,
    SCOPE,
    SUNSET,
    Approval,
    ProvisioningDenied,
    Trust,
    canonical,
    execute,
    load_trust,
    read_document,
    validate_approval,
    verify_principal,
    verify_target,
)
from app.support_provisioning_cli import check, main, verify_running_backend

NOW = datetime(2026, 10, 24, 12, tzinfo=UTC)
ACTOR, SESSION = UUID(int=99), UUID(int=100)
harness = metadata_harness


def document():
    return {
        "approval": {
            "amendment": AMENDMENT,
            "version": "1.1",
            "change_id": CHANGE,
            "approval_id": str(UUID(int=123)),
            "action": "grant",
            "project": PROJECT,
            "environment": "development",
            "email": EMAIL,
            "subject_id": str(ACTOR),
            "executor_id": str(ACTOR),
            "role": "support",
            "scope": SCOPE,
            "decision": "APPROVE",
            "owner_authorization_reference": "synthetic-owner-exact-operation",
            "owner_self_grant_exception": True,
            "amendment_sha256": "a" * 64,
            "implementation_sha256": "b" * 64,
            "email_evidence_reference": "synthetic-email-evidence",
            "mfa_evidence_reference": "synthetic-mfa-evidence",
            "authorized_at": NOW.isoformat(),
            "approval_expires_at": (NOW + timedelta(hours=1)).isoformat(),
            "grant_expires_at": (NOW + timedelta(hours=2)).isoformat(),
        }
    }


def trust():
    return Trust(
        project=PROJECT,
        subject_id=ACTOR,
        executor_id=ACTOR,
        owner_human_reference="synthetic-owner",
        owner_authorization_reference="synthetic-owner-exact-operation",
        amendment_sha256="a" * 64,
        implementation_sha256="b" * 64,
        valid_until=SUNSET,
        revoked_approvals=[],
    )


def settings(**updates):
    return Settings(
        support_dev_enabled=True,
        support_dev_subject_id=ACTOR,
        supabase_url=f"https://{PROJECT}.supabase.co",
        profile_data_keys=SecretStr(
            json.dumps({"1": base64.b64encode(bytes(range(32))).decode()})
        ),
        profile_data_key_version=1,
        **updates,
    )


def principal(**updates):
    return Principal(
        **{
            "user_id": ACTOR,
            "session_id": SESSION,
            "mfa_claim": True,
            "authentication_time": int(NOW.timestamp()),
            **updates,
        }
    )


def test_valid_owner_exception_has_no_third_person_fields_or_signature():
    packet = validate_approval(document(), trust(), NOW)
    assert packet.subject_id == packet.executor_id
    assert b"Ahmad" not in canonical(packet) and b"signature" not in canonical(packet)


@pytest.mark.parametrize(
    "field,value",
    [
        ("project", "other"),
        ("email", "someone@synthetic.test"),
        ("environment", "production"),
        ("version", "1.0"),
        ("role", "security_admin"),
        ("role", "superadmin"),
        ("role", "finance"),
        ("scope", "all"),
        ("executor_id", str(UUID(int=101))),
        ("subject_id", str(UUID(int=101))),
        ("decision", None),
        ("owner_self_grant_exception", False),
        ("owner_authorization_reference", "other"),
        ("email_evidence_reference", ""),
        ("mfa_evidence_reference", ""),
        ("amendment_sha256", "c" * 64),
        ("implementation_sha256", "c" * 64),
        ("audit_actor", "forged"),
        ("reviewer", "Ahmad"),
    ],
)
def test_closed_one_account_scope_and_owner_intent(field, value):
    doc = document()
    doc["approval"][field] = value
    with pytest.raises(ProvisioningDenied):
        validate_approval(doc, trust(), NOW)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d["approval"].update(
            authorized_at=(NOW + timedelta(seconds=1)).isoformat()
        ),
        lambda d: d["approval"].update(
            authorized_at=NOW.replace(tzinfo=None).isoformat()
        ),
        lambda d: d["approval"].update(approval_expires_at=NOW.isoformat()),
        lambda d: d["approval"].update(
            approval_expires_at=(NOW + timedelta(hours=25)).isoformat()
        ),
        lambda d: d["approval"].update(
            grant_expires_at=(NOW + timedelta(hours=25)).isoformat()
        ),
        lambda d: d["approval"].update(grant_expires_at=NOW.isoformat()),
        lambda d: d.update(signature="invented"),
    ],
)
def test_invalid_or_expired_approval_never_passes(mutate):
    doc = document()
    mutate(doc)
    with pytest.raises(ProvisioningDenied):
        validate_approval(doc, trust(), NOW)


def test_owner_permit_revocation_and_absolute_sunset():
    t = trust()
    t.revoked_approvals.append(UUID(int=123))
    with pytest.raises(ProvisioningDenied):
        validate_approval(document(), t, NOW)
    with pytest.raises(ProvisioningDenied):
        validate_approval(document(), trust(), SUNSET)


@pytest.mark.parametrize(
    "override",
    [
        {"user_id": UUID(int=88)},
        {"mfa_claim": False},
        {"authentication_time": None},
        {"authentication_time": int(NOW.timestamp()) - 301},
        {"authentication_time": int(NOW.timestamp()) + 1},
    ],
)
def test_wrong_executor_missing_mfa_and_recent_auth_fail(override):
    with pytest.raises(ProvisioningDenied):
        verify_principal(
            Approval.model_validate(document()["approval"]), principal(**override), NOW
        )


def test_missing_or_unpinned_trust_and_duplicate_keys_fail(tmp_path):
    with pytest.raises(ProvisioningDenied):
        load_trust(settings())
    path = tmp_path / "owner-intent.json"
    path.write_text(trust().model_dump_json())
    cfg = settings(
        support_dev_trust_file=str(path),
        support_dev_trust_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )
    assert load_trust(cfg).subject_id == ACTOR
    path.write_text('{"project":"one","project":"two"}')
    with pytest.raises(ProvisioningDenied):
        read_document(path)
    with pytest.raises(ProvisioningDenied):
        load_trust(cfg)


def test_missing_command_credential_never_falls_back_to_runtime_or_migration():
    cfg = settings(
        database_url=SecretStr("postgresql://synthetic:CANARY@127.0.0.1/existing"),
        migration_database_url=SecretStr(
            "postgresql://synthetic:CANARY@127.0.0.1/existing"
        ),
    )
    with pytest.raises(ProvisioningDenied, match="EXECUTION_CONFIGURATION_UNAVAILABLE"):
        verify_target(cfg)


@pytest.mark.parametrize(
    "state,path,method,denied",
    [
        ("active", "/api/v1/admin/support-case-metadata", "GET", False),
        ("inactive", "/api/v1/admin/support-case-metadata", "GET", True),
        ("unregistered", "/api/v1/admin/support-case-metadata", "GET", True),
        ("active", "/api/v1/admin/support-case-metadata", "POST", True),
        ("active", "/api/v1/admin/support-cases", "GET", True),
        ("active", "/api/v1/admin/orders", "GET", True),
        (
            "active",
            "/api/v1/admin/support-case-metadata/{case_id}/history",
            "GET",
            False,
        ),
        ("inactive", "/api/v1/me/staff-security", "GET", True),
    ],
)
def test_central_route_scope_expiry_and_quarantine(state, path, method, denied):
    class Session:
        def execute(self, sql, params=None):
            return SimpleNamespace(scalar_one=lambda: state)

    context = AuthContext(Session(), principal(), True, True)
    request = SimpleNamespace(
        method=method,
        scope={
            "route": SimpleNamespace(path=path),
            "path": path.replace("{case_id}", str(UUID(int=1))),
        },
    )
    if denied:
        with pytest.raises(AccessError):
            enforce(context, settings(), request)
    else:
        enforce(context, settings(), request)


def test_ordinary_accounts_unchanged_and_missing_binding_fails_closed():
    context = AuthContext(None, principal(), True, True)
    cfg = settings().model_copy(update={"support_dev_subject_id": UUID(int=999)})
    enforce(context, cfg, SimpleNamespace())
    with pytest.raises(AccessError):
        enforce(
            context,
            cfg.model_copy(update={"support_dev_subject_id": None}),
            SimpleNamespace(),
        )


def test_default_cli_is_offline_and_template_cannot_execute(capsys):
    assert main([]) == 0
    prepared = json.loads(capsys.readouterr().out)
    assert prepared["approval"]["decision"] is None
    assert prepared["approval"]["subject_id"] is None
    assert "Ahmad" not in json.dumps(prepared)
    assert main(["--execute"]) == 2
    with pytest.raises(ProvisioningDenied):
        validate_approval(prepared, trust(), NOW)
    with pytest.raises(ProvisioningDenied):
        check(settings(), document())


def test_canonical_body_binds_expiry_owner_intent_and_approval():
    one = Approval.model_validate(document()["approval"])
    two = one.model_copy(update={"grant_expires_at": NOW + timedelta(hours=3)})
    assert (
        hashlib.sha256(canonical(one)).digest()
        != hashlib.sha256(canonical(two)).digest()
    )
    assert canonical(one) == canonical(
        Approval.model_validate(json.loads(canonical(one)))
    )


def test_real_aead_receipt_is_verified_before_transaction_commits():
    class Store:
        committed, rolled_back = False, False

        @contextmanager
        def transaction(self):
            try:
                yield self
                self.committed = True
            except Exception:
                self.rolled_back = True
                raise

        def execute(self, sql, params=None):
            if params is None:
                return None
            row = {
                "grant_id": UUID(int=222),
                "expires_at": NOW + timedelta(hours=2),
                "cipher": params["cipher"],
                "key_version": params["version"],
            }
            if getattr(self, "tamper", False):
                row["cipher"] = bytes(64)
            return SimpleNamespace(mappings=lambda: SimpleNamespace(one=lambda: row))

    packet = Approval.model_validate(document()["approval"])
    good = Store()
    assert (
        execute(good, settings(), packet, principal(), UUID(int=1), now=NOW)["outcome"]
        == "granted"
    )
    assert good.committed and not good.rolled_back
    bad = Store()
    bad.tamper = True
    with pytest.raises(ValueError):
        execute(bad, settings(), packet, principal(), UUID(int=1), now=NOW)
    assert bad.rolled_back and not bad.committed


def test_migration_is_additive_unseeded_and_no_domain_or_qr_operations():
    sql = (
        Path(__file__).parents[1] / "alembic/versions/0044_support_dev_exception.sql"
    ).read_text()
    for forbidden in (
        "tag_pairs",
        "qr_codes",
        "order_pair_units",
        "INSERT INTO auth.",
        "DISABLE ROW LEVEL SECURITY",
        "GRANT ALL",
        "DELETE FROM",
        "DROP TABLE",
    ):
        assert forbidden not in sql
    assert "AS RESTRICTIVE" in sql and "SET search_path=pg_catalog" in sql
    assert "REPLAY_CONFLICT" in sql and "EXCEPTION_ALREADY_CONSUMED" in sql
    assert "sr_account_lock_key(uid)" in sql and "account-lifecycle-custody" in sql
    assert (
        "INSERT INTO public.audit_events" in sql
        and "INSERT INTO public.support_dev_receipts" in sql
    )
    assert "LIVE_EMAIL_MFA_OR_ACCOUNT_DENIED" in sql


@pytest.mark.parametrize(
    "field,value",
    [
        (None, None),
        ("u.email", "other@synthetic.test"),
        ("u.email_confirmed_at", None),
        ("u.deleted_at", 1),
        ("u.is_anonymous", 1),
        ("u.banned_until", 999),
        ("s.id", "other-session"),
        ("s.aal", "aal1"),
        ("s.not_after", 1),
        ("f.status", "unverified"),
        ("f.factor_type", "phone"),
        ("f.user_id", "different-user"),
    ],
)
def test_actual_subject_only_provider_predicate_rejects_bad_email_mfa_session(
    field, value
):
    # Execute the actual migration admission SELECT after SQLite dialect adaptation.
    # This tests its predicates, not PostgreSQL Auth/RLS/locking or genuine MFA.
    sql = (
        Path(__file__).parents[1] / "alembic/versions/0044_support_dev_exception.sql"
    ).read_text()
    query = re.search(
        r"IF NOT EXISTS\((SELECT 1 FROM auth.users.*?factor_type::text='totp'\))\)",
        sql,
        re.DOTALL,
    )[1]
    query = (
        query.replace("auth.", "")
        .replace("public.sr_account_epoch_allows", "epoch_allows")
        .replace("::text", "")
    )
    query = (
        query.replace("clock_timestamp()", "100")
        .replace("u.id=uid", "u.id=:uid")
        .replace("s.id=sid", "s.id=:sid")
    )
    with sqlite3.connect(":memory:") as db:
        db.create_function("epoch_allows", 2, lambda uid, issued: 1)
        db.executescript("""CREATE TABLE users(id TEXT,email TEXT,email_confirmed_at INT,deleted_at INT,is_anonymous INT,banned_until INT);
        CREATE TABLE sessions(id TEXT,user_id TEXT,aal TEXT,not_after INT,created_at INT);
        CREATE TABLE mfa_factors(user_id TEXT,status TEXT,factor_type TEXT);""")
        db.execute(
            "INSERT INTO users VALUES('synthetic-user',?,1,NULL,0,NULL)", (EMAIL,)
        )
        db.execute(
            "INSERT INTO sessions VALUES('synthetic-session','synthetic-user','aal2',NULL,1)"
        )
        db.execute("INSERT INTO mfa_factors VALUES('synthetic-user','verified','totp')")
        if field:
            table, column = field.split(".")
            table = {"u": "users", "s": "sessions", "f": "mfa_factors"}[table]
            db.execute(f"UPDATE {table} SET {column}=?", (value,))
        row = db.execute(
            query, {"uid": "synthetic-user", "sid": "synthetic-session"}
        ).fetchone()
        assert bool(row) == (field is None)


def test_permission_configuration_rejects_insecure_tls_other_project_and_other_host(
    tmp_path,
):
    root = tmp_path / "root.pem"
    root.write_text("synthetic-ca-not-the-approved-root")
    for url in [
        f"postgresql://synthetic.{PROJECT}:CANARY@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres?sslmode=require&sslrootcert={root.as_posix()}",
        f"postgresql://synthetic.otherproject:CANARY@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres?sslmode=verify-full&sslrootcert={root.as_posix()}",
        f"postgresql://synthetic.{PROJECT}:CANARY@other.test:5432/postgres?sslmode=verify-full&sslrootcert={root.as_posix()}",
    ]:
        with pytest.raises(ProvisioningDenied):
            verify_target(settings(support_dev_database_url=SecretStr(url)))


@pytest.mark.parametrize(
    "state,status", [("active", 200), ("inactive", 403), ("unregistered", 403)]
)
def test_real_asgi_route_template_and_final_staff_check(harness, state, status):
    # Existing real JWT/ASGI/AEAD harness with mock public-key transport and scripted SQL.
    h = harness
    h.app.state.settings.support_dev_enabled = True
    h.app.state.settings.support_dev_subject_id = METADATA_ACTOR
    h.app.state.settings.supabase_url = f"https://{PROJECT}.supabase.co"
    original = h.db.execute

    def query(sql, params=None):
        if "sr_support_dev_state" in str(sql):
            return Result(state)
        return original(sql, params)

    h.db.execute = query
    assert h.get().status_code == status, [str(sql) for sql, _ in h.db.calls]


@pytest.mark.parametrize(
    "change,allowed",
    [
        ({}, True),
        ({"state": "active"}, True),
        ({"state": "inactive"}, False),
        ({"project": "different"}, False),
        ({"subject_id": "different"}, False),
        ({"implementation_sha256": "old-process"}, False),
        ({"metadata_only": False}, False),
    ],
)
def test_live_fence_readiness_transport_rejects_stale_backend_without_real_network(
    change, allowed
):
    packet = Approval.model_validate(document()["approval"])

    def transport(request):
        assert (
            str(request.url)
            == "http://127.0.0.1:3031/api/v1/me/support-development-readiness"
        )
        assert request.headers["authorization"] == "Bearer SYNTHETIC_NOT_A_TOKEN"
        return httpx.Response(
            200,
            json={
                "project": PROJECT,
                "subject_id": str(ACTOR),
                "implementation_sha256": packet.implementation_sha256,
                "metadata_only": True,
                "state": "unregistered",
                **change,
            },
        )

    if allowed:
        verify_running_backend(
            settings(),
            packet,
            "SYNTHETIC_NOT_A_TOKEN",
            transport=httpx.MockTransport(transport),
        )
    else:
        with pytest.raises(ProvisioningDenied):
            verify_running_backend(
                settings(),
                packet,
                "SYNTHETIC_NOT_A_TOKEN",
                transport=httpx.MockTransport(transport),
            )


def test_readiness_cannot_send_private_session_to_remote_endpoint():
    cfg = settings().model_copy(
        update={"support_dev_backend_origin": "https://other.test"}
    )
    with pytest.raises(ProvisioningDenied):
        verify_running_backend(
            cfg,
            Approval.model_validate(document()["approval"]),
            "SYNTHETIC_NOT_A_TOKEN",
        )


def test_own_readiness_real_app_requires_verified_email_current_mfa_and_recent_auth(
    harness,
):
    from app.main import create_app
    from app.support_provisioning_cli import implementation_digest

    cfg = harness.app.state.settings.model_copy(
        update={
            "support_dev_enabled": True,
            "support_dev_subject_id": METADATA_ACTOR,
            "supabase_url": f"https://{PROJECT}.supabase.co",
        }
    )
    app = create_app(cfg)
    app.state.database = harness.db
    app.state.jwt_verifier = harness.app.state.jwt_verifier
    original = harness.db.execute

    def query(sql, params=None):
        if "sr_support_dev_state" in str(sql):
            return Result("unregistered")
        return original(sql, params)

    harness.db.execute = query

    async def request(token):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:3031"
        ) as client:
            return await client.get(
                "/api/v1/me/support-development-readiness",
                headers={"Authorization": "Bearer " + token},
            )

    fresh = {"amr": [{"method": "totp", "timestamp": int(time.time())}]}
    response = asyncio.run(request(harness.token(**fresh)))
    assert response.status_code == 200
    assert response.json() == {
        "project": PROJECT,
        "subject_id": str(METADATA_ACTOR),
        "metadata_only": True,
        "state": "unregistered",
        "implementation_sha256": implementation_digest(),
    }
    assert response.headers["cache-control"] == "no-store"
    assert asyncio.run(request(harness.token())).status_code == 403
    assert asyncio.run(request(harness.token(aal="aal1", **fresh))).status_code == 403
    harness.db.email = False
    assert asyncio.run(request(harness.token(**fresh))).status_code == 403
    assert not any("support_cases" in str(sql) for sql, _ in harness.db.calls)
