"""Real HTTP/auth/AEAD/command code with a scripted repository, never PG proof."""

import base64
import json
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from test_auth import claims, signed
from test_auth import verifier as _verifier
from test_critical_workflow_boundaries import MemoryDatabase, Result
from test_health import ASGIClient

from app.api.v1.print_templates import Content, Create
from app.core.config import Settings
from app.main import create_app

verifier = _verifier
BASE = "/api/v1/admin/print-templates"
TID, RID = UUID(int=501), UUID(int=502)
ASSET = UUID(int=503)


def content():
    return {
        "schema_version": 1,
        "renderer": "safereturn-vector-v1",
        "preset": "fixed-footer-v1",
        "symbol_mm": "35.00",
        "width_mm": "55.00",
        "height_mm": "80.00",
        "qr_x_mm": "10.00",
        "qr_y_mm": "30.00",
        "logo_mm": "4.00",
        "min_pitch_mm": "0.40",
        "font_pt": "9.00",
        "header": "Synthetic Lost",
        "english_lines": ["Found this item?"],
        "urdu_lines": ["اسکین کریں"],
        "asset_set_id": str(ASSET),
        "material_codes": ["synthetic-paper"],
    }


def template():
    return {
        "template_id": str(TID),
        "key": "synthetic-key",
        "name": "Synthetic",
        "purpose": "lost",
        "lifecycle_status": "draft",
        "row_version": 1,
        "created_at": "2026-10-20T00:00:00Z",
    }


def revision():
    return {
        "revision_id": str(RID),
        "template_id": str(TID),
        "version": 1,
        "status": "draft",
        "row_version": 1,
        "content": content(),
        "fingerprint_sha256": None,
        "created_at": "2026-10-20T00:00:00Z",
        "published_at": None,
    }


class ScriptedDatabase(MemoryDatabase):
    """Only returns scripted SQL helper results; does not implement its lifecycle."""

    def __init__(self, owner):
        super().__init__(owner, uuid4())
        self.receipts = {}
        self.helper_calls = []
        self.helper_result = template()
        self.fail_receipt = False
        self.revoke_after_helper = False
        self.preview_spec = None
        self.admission = "ok"
        self.admissions = 0
        self.registry_available = False

    @contextmanager
    def begin_nested(self):
        before = deepcopy((self.receipts, self.audit, self.helper_calls))
        try:
            yield self
        except BaseException:
            self.receipts, self.audit, self.helper_calls = before
            raise

    @contextmanager
    def transaction(self):
        with self.begin_nested(), super().transaction():
            yield self

    def execute(self, statement, params=None):
        sql, p = str(statement), params or {}
        if "AS template_registry_available" in sql:
            return Result(self.registry_available)
        if "sr_template_lifecycle" in sql:
            return Result({"error":"PROVIDER_UNAVAILABLE"})
        if "FROM public.staff_roles" in sql:
            return Result(1 if self.roles.intersection(p["roles"]) else None)
        if "pg_advisory_xact_lock" in sql:
            return Result(None)
        if "SELECT * FROM public.idempotency_records" in sql:
            return Result(self.receipts.get((p["scope"], p["op"], p["key"])))
        if "INSERT INTO public.idempotency_records" in sql:
            if self.fail_receipt:
                raise IntegrityError(sql, {}, Exception("PRIVATE_CANARY_RECEIPT"))
            self.receipts[(p["scope"], p["op"], p["key"])] = {
                "request_hash": p["hash"],
                "response_body_ciphertext": p["cipher"],
                "response_key_version": p["kv"],
            }
            return Result(None)
        if "sr_template_preview_admit" in sql:
            self.admissions += 1
            return Result(self.admission)
        if "sr_template_service" in sql:
            self.helper_calls.append((p["action"], json.loads(p["payload"])))
            if p["action"] == "preview_input" and self.preview_spec is not None:
                return Result(deepcopy(self.preview_spec))
            if self.revoke_after_helper:
                self.roles = set()
            return Result(deepcopy(self.helper_result))
        return super().execute(statement, params)


@pytest.fixture
def env(verifier):
    provider, private, _, _ = verifier
    actor = uuid4()
    db = ScriptedDatabase(actor)
    settings = Settings(
        _env_file=None,
        print_template_management_enabled=True,
        print_template_web_origin="https://staff.test",
        profile_data_keys=json.dumps({"1": base64.b64encode(b"t" * 32).decode()}),
    )
    app = create_app(settings)
    app.state.database, app.state.jwt_verifier = db, provider
    client = ASGIClient(app)

    def headers(**overrides):
        c = claims(
            **(
                {
                    "sub": str(actor),
                    "aal": "aal2",
                    "amr": [{"method": "totp", "timestamp": int(time.time())}],
                }
                | overrides
            )
        )
        return {
            "Authorization": "Bearer " + signed(private, c),
            "Idempotency-Key": "synthetic-key-001",
            "If-Match": '"1"',
        }

    return client, db, headers, settings


def test_real_create_and_encrypted_replay(env):
    client, db, headers, settings = env
    body = {"key": "synthetic-key", "name": "Synthetic", "purpose": "lost"}
    first = client.post(BASE, json=body, headers=headers())
    assert first.status_code == 201, first.text
    assert first.json()["result"] == template()
    second = client.post(BASE, json=body, headers=headers())
    assert second.json() == first.json()
    assert len(db.helper_calls) == len(db.audit) == len(db.receipts) == 1
    raw = next(iter(db.receipts.values()))["response_body_ciphertext"]
    assert raw.startswith(b"SRD1") and b"synthetic-key" not in raw
    body["name"] = "Changed"
    assert client.post(BASE, json=body, headers=headers()).status_code == 409
    db.roles = {"finance", "superadmin"}
    assert (
        client.post(
            BASE, json={**body, "name": "Synthetic"}, headers=headers()
        ).status_code
        == 403
    )
    settings.profile_data_keys = None
    db.roles = {"operations"}
    assert (
        client.post(
            BASE, json={**body, "name": "Synthetic"}, headers=headers()
        ).status_code
        == 503
    )


@pytest.mark.parametrize(
    "roles,status",
    [
        ({"operations"}, 201),
        ({"operations", "finance"}, 201),
        ({"security_admin"}, 403),
        ({"superadmin"}, 403),
        ({"finance"}, 403),
        ({"support"}, 403),
        (set(), 403),
    ],
)
def test_existing_role_writer_permissions(env, roles, status):
    client, db, headers, _ = env
    db.roles = roles
    result = client.post(
        BASE,
        json={"key": "synthetic-key", "name": "Synthetic", "purpose": "lost"},
        headers=headers(),
    )
    assert result.status_code == status


@pytest.mark.parametrize(
    "roles,status",
    [
        ({"operations"}, 200),
        ({"security_admin"}, 200),
        ({"superadmin"}, 200),
        ({"finance"}, 403),
        ({"support"}, 403),
    ],
)
def test_read_permissions_and_safe_headers(env, roles, status):
    client, db, headers, _ = env
    db.roles = roles
    db.helper_result = {
        "items": [],
        "next_cursor": None,
        "as_of": "2026-10-20T00:00:00Z",
    }
    response = client.get(BASE, headers=headers())
    assert response.status_code == status
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize(
    "change,status",
    [
        ({"aal": "aal1"}, 403),
        ({"amr": []}, 403),
        ({"amr": [{"method": "totp", "timestamp": 1}]}, 403),
        ({"exp": 1}, 401),
        ({"session_id": None}, 401),
    ],
)
def test_signed_session_mfa_recent_boundaries(env, change, status):
    client, db, headers, _ = env
    assert (
        client.post(
            BASE,
            json={"key": "synthetic-key", "name": "Synthetic", "purpose": "lost"},
            headers=headers(**change),
        ).status_code
        == status
    )
    assert not db.helper_calls


def test_revoked_live_session_and_disabled_mfa_flag(env):
    client, db, headers, settings = env
    body = {"key": "synthetic-key", "name": "Synthetic", "purpose": "lost"}
    assert client.post(BASE, json=body).status_code == 401
    db.active = False
    assert client.post(BASE, json=body, headers=headers()).status_code == 401
    db.active, db.mfa = True, False
    assert client.post(BASE, json=body, headers=headers()).status_code == 403
    db.mfa = True
    settings.print_template_management_enabled = False
    assert client.post(BASE, json=body, headers=headers()).status_code == 503


@pytest.mark.parametrize(
    "extra",
    [
        {"role": "designer"},
        {"status": "published"},
        {"key": "../unsafe"},
        {"name": "<script>CANARY</script>"},
        {"purpose": "mixed"},
    ],
)
def test_closed_create_and_unsafe_inputs(env, extra):
    client, db, headers, _ = env
    response = client.post(
        BASE,
        json={"key": "synthetic-key", "name": "Synthetic", "purpose": "lost"} | extra,
        headers=headers(),
    )
    assert response.status_code == 422 and "CANARY" not in response.text
    assert not db.helper_calls


@pytest.mark.parametrize(
    "field,value",
    [
        ("symbol_mm", "29.99"),
        ("symbol_mm", 35),
        ("symbol_mm", "NaN"),
        ("symbol_mm", "35"),
        ("width_mm", "40.00"),
        ("qr_x_mm", "30.00"),
        ("logo_mm", "6.00"),
        ("min_pitch_mm", "0.20"),
        ("schema_version", True),
        ("schema_version", 1.0),
        ("english_lines", ["https://evil.test/a"]),
        ("english_lines", ["url(file:/secret)"]),
        ("urdu_lines", ["English"]),
        ("header", "<svg onload=evil>"),
        ("header", "x\nCANARY"),
        ("asset_set_id", "https://evil.test/asset"),
        ("asset_set_id", "../../font.ttf"),
        ("material_codes", ["z", "a"]),
        ("material_codes", ["a", "a"]),
        ("english_lines", ["x"] * 5),
        ("header", "x" * 51),
        ("font_path", "C:/private/font.ttf"),
        ("css", "body {}"),
    ],
)
def test_closed_content_geometry_and_unsafe_assets(field, value):
    with pytest.raises(ValidationError):
        Content.model_validate(content() | {field: value})


def test_renderer_mapping_and_authoritative_fingerprint():
    c = Content.model_validate(content())
    t = c.renderer_template("synthetic", 2, "ice")
    assert t.tag_type == "ice" and t.version == 2 and t.symbol_mm == 35
    assets = {"font": {"sha256": "a" * 64}, "logo": {"sha256": "b" * 64}}
    fingerprint = c.fingerprint("synthetic", 2, "ice", assets)
    assert len(fingerprint) == 64
    assert fingerprint != c.fingerprint("synthetic", 3, "ice", assets)
    assets["logo"]["sha256"] = "c" * 64
    assert fingerprint != c.fingerprint("synthetic", 2, "ice", assets)


@pytest.mark.parametrize(
    "failure", ["fail_audit", "fail_receipt", "fail_commit", "revoke_after_helper"]
)
def test_real_command_rollback_boundary(env, failure):
    client, db, headers, _ = env
    setattr(db, failure, True)
    response = client.post(
        BASE,
        json={"key": "synthetic-key", "name": "Synthetic", "purpose": "lost"},
        headers=headers(),
    )
    assert response.status_code in {403, 409, 503}
    assert not db.receipts and not db.audit and not db.helper_calls
    assert "PRIVATE_CANARY" not in response.text


@pytest.mark.parametrize(
    "code,status",
    [
        ("CONFLICT", 409),
        ("VERSION_MISMATCH", 412),
        ("NOT_FOUND", 404),
        ("PROVIDER_UNAVAILABLE", 503),
    ],
)
def test_repository_failures_have_no_receipt(env, code, status):
    client, db, headers, _ = env
    db.helper_result = {"error": code}
    response = client.post(
        BASE,
        json={"key": "synthetic-key", "name": "Synthetic", "purpose": "lost"},
        headers=headers(),
    )
    assert response.status_code == status and not db.receipts


def test_revision_resource_and_precondition_binding(env):
    client, db, headers, _ = env
    db.helper_result = {"template": template(), "revision": revision()}
    body = {
        "base_revision_id": None,
        "content": content(),
        "version_note": "Synthetic first draft",
    }
    path = BASE + f"/{TID}/revisions"
    response = client.post(path, json=body, headers=headers())
    assert response.status_code == 201, response.text
    assert db.helper_calls[0][1]["expected"] == 1
    assert db.helper_calls[0][1]["template_id"] == str(TID)
    h = headers()
    h["If-Match"] = '"2"'
    assert client.post(path, json=body, headers=h).status_code == 409
    assert (
        client.post(
            BASE + f"/{uuid4()}/revisions", json=body, headers=headers()
        ).status_code
        == 409
    )
    db.helper_result = revision()
    h["Idempotency-Key"] = "synthetic-edit-001"
    edited = client.request(
        "PATCH",
        path + f"/{RID}",
        json={"content": content(), "version_note": "Updated draft"},
        headers=h,
    )
    assert edited.status_code == 200, edited.text


@pytest.mark.parametrize(
    "suffix,body",
    [
        ("preview", {"expected_revision": 1}),
        ("submit-qa", {"reason": "Synthetic QA"}),
        ("publish", {"approval_id": str(UUID(int=900)), "confirmed": True}),
        ("retire", {"reason": "Synthetic retire", "confirmed": True}),
    ],
)
def test_unavailable_qa_and_preview_never_leak_or_mutate(env, suffix, body):
    client, db, headers, _ = env
    response = client.post(
        BASE + f"/{TID}/revisions/{RID}/{suffix}", json=body, headers=headers()
    )
    assert response.status_code == 503
    assert "preview" not in response.json() and "approval_id" not in response.text
    assert response.headers["cache-control"] == "private, no-store"
    assert not db.audit and not db.receipts and not db.helper_calls
    bad = client.post(
        BASE + f"/{TID}/revisions/{RID}/{suffix}",
        json=body | {"order_id": "PRIVATE_CANARY"},
        headers=headers(),
    )
    assert bad.status_code == 422 and "PRIVATE_CANARY" not in bad.text


def test_concurrent_publication_and_binding_remain_unavailable(env):
    client, db, headers, _ = env
    requests = [
        (
            BASE + f"/{TID}/revisions/{RID}/publish",
            {"approval_id": str(UUID(int=901)), "confirmed": True},
        ),
        (
            "/api/v1/admin/print-template-bindings",
            {
                "variant_id": str(UUID(int=902)),
                "revision_id": str(RID),
                "tag_type": "lost",
                "expected_variant_version": 1,
                "expected_binding_id": None,
                "confirmed": True,
            },
        ),
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda args: (
                    client.post(args[0], json=args[1], headers=headers()).status_code
                ),
                requests,
            )
        )
    assert results == [503, 503]
    assert not db.helper_calls and not db.audit and not db.receipts


def test_transport_limits_origin_and_preconditions(env):
    client, _db, headers, _ = env
    body = {"key": "synthetic-key", "name": "Synthetic", "purpose": "lost"}
    h = headers() | {"Origin": "https://evil.test"}
    assert client.post(BASE, json=body, headers=h).status_code == 403
    h["Origin"] = "https://staff.test"
    assert client.post(BASE, json=body, headers=h).status_code == 201
    for field in ("Idempotency-Key",):
        h = headers()
        del h[field]
        assert client.post(BASE, json=body, headers=h).status_code == 400
    h = headers() | {"Content-Type": "application/json"}
    assert client.post(BASE, content=b"X" * 32769, headers=h).status_code == 413
    assert client.post(BASE, content=b"CANARY", headers=headers()).status_code == 422
    h = headers()
    del h["If-Match"]
    assert (
        client.post(
            BASE + f"/{TID}/revisions/{RID}/preview",
            json={"expected_revision": 1},
            headers=h,
        ).status_code
        == 400
    )
    assert client.get(BASE + "?unknown=CANARY", headers=headers()).status_code == 422
    assert client.get(BASE + "?limit=51", headers=headers()).status_code == 422


def test_cursor_actor_filter_and_integrity_binding(env):
    client, db, headers, _settings = env
    db.helper_result = {
        "items": [template()],
        "next_cursor": str(TID),
        "as_of": "2026-10-20T00:00:00Z",
    }
    page = client.get(BASE + "?limit=1", headers=headers())
    assert page.status_code == 200, page.text
    token = page.json()["next_cursor"]
    assert str(TID) not in token
    db.helper_result["next_cursor"] = None
    second = client.get(BASE + "?limit=1&cursor=" + token, headers=headers())
    assert second.status_code == 200 and db.helper_calls[-1][1]["after"] == str(TID)
    for suffix in (
        "?limit=2&cursor=" + token,
        "?limit=1&cursor=" + token[:-4] + "AAAA",
    ):
        assert client.get(BASE + suffix, headers=headers()).status_code in {422, 503}


def test_draft_migration_is_offline_partial_and_not_a_publish_backdoor():
    root = Path(__file__).parents[1]
    migration = root / "alembic/versions/0033_print_template_drafts"
    assert (
        'down_revision = "0032_owner_qr_lifecycle"'
        in migration.with_suffix(".py").read_text()
    )
    sql = migration.with_suffix(".sql").read_text()
    assert "CHECK (status IN ('draft','pending_qa'))" in sql
    assert "WHERE status='draft'" in sql
    assert "FOR UPDATE" in sql and "row_version=row_version+1" in sql
    assert "WHERE template_id=t.template_id AND revision_id=" in sql
    assert "GRANT EXECUTE ON FUNCTION public.sr_template_service" in sql
    assert "GRANT INSERT" not in sql and "GRANT UPDATE" not in sql
    assert "UPDATE public.order" not in sql and "UPDATE public.print_jobs" not in sql
    assert "CHECK (lifecycle_status='draft')" in sql
    assert "'publish'" not in sql and "'bind'" not in sql


def test_unique_key_contract_does_not_strip_or_fold():
    assert Create(key="Case-key", name="Synthetic", purpose="lost").key == "Case-key"
    with pytest.raises(ValidationError):
        Create(key=" Case-key", name="Synthetic", purpose="lost")


def test_contract_openapi_is_explicit_and_339_unchanged(env):
    client, _, _, _ = env
    paths = client.application.openapi()["paths"]
    ids = {
        op["operationId"]
        for path, methods in paths.items()
        if "print-template" in path
        for op in methods.values()
    }
    assert ids == {f"API-{n}" for n in range(300, 313)}
    assert (
        paths["/api/v1/admin/catalog/approved-templates"]["get"]["operationId"]
        == "API-339"
    )
    assert paths[BASE]["post"]["responses"]["201"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/CreateReceipt")


def test_all_existing_openapi_paths_and_models_remain_unchanged(env):
    client, _, _, settings = env
    current = client.application.openapi()
    baseline = create_app(settings)
    baseline.router.routes = [
        route
        for route in baseline.router.routes
        if not getattr(route, "path", "").startswith(
            (BASE, "/api/v1/admin/print-template-bindings")
        )
    ]
    previous = baseline.openapi()
    for path, contract in previous["paths"].items():
        assert current["paths"][path] == contract, path
    for name, model in previous["components"]["schemas"].items():
        assert current["components"]["schemas"][name] == model, name

def test_precise_disabled_and_origin_errors(env):
    client, db, headers, settings = env
    settings.print_template_management_enabled = False
    response = client.get(BASE, headers=headers())
    assert response.status_code == 503
    assert response.json()['error']['code'] == 'TEMPLATE_MANAGEMENT_DISABLED'
    settings.print_template_management_enabled = True
    response = client.post(BASE, json={'key':'synthetic-key','name':'Synthetic','purpose':'lost'}, headers=headers() | {'Origin':'https://wrong.test'})
    assert response.status_code == 403
    assert response.json()['error']['code'] == 'TEMPLATE_ORIGIN_MISMATCH'
    assert not db.helper_calls

@pytest.mark.parametrize('age,status',[(301,201),(850,201),(1150,201),(1201,403)])
def test_draft_twenty_minute_window(env,age,status):
    client,_db,headers,_=env
    response=client.post(BASE,json={'key':'window-test','name':'Window test','purpose':'lost'},headers=headers(amr=[{'method':'totp','timestamp':int(time.time())-age}]))
    assert response.status_code==status


@pytest.mark.parametrize('age,denied', [(400,False),(1150,False),(1201,True)])
def test_sensitive_template_actions_twenty_minutes(env,age,denied):
    client,_db,headers,_=env
    response=client.post(BASE+f'/{TID}/revisions/{RID}/submit-qa',json={'reason':'Reviewed draft'},headers=headers(amr=[{'method':'totp','timestamp':int(time.time())-age}]))
    if denied:
        assert response.status_code==403
        assert response.json()['error']['code']=='REAUTH_REQUIRED'
    else:
        assert response.json().get('error',{}).get('code')!='REAUTH_REQUIRED'
