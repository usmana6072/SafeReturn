"""API-339 configured-reference projection, synthetic guards only; no DB/provider I/O."""

from types import SimpleNamespace

import pytest
from test_auth import claims, signed
from test_auth import verifier as _verifier
from test_catalog_readiness import test_catalog_browser as _browser
from test_critical_workflow_boundaries import workflow as _workflow

verifier = _verifier
workflow = _workflow
PATH = "/api/v1/admin/catalog/approved-templates"


def check_headers(response):
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert len(response.headers["x-request-id"]) == 32
    assert "set-cookie" not in response.headers


def test_projection_sort_dedupe_and_empty(workflow):
    client, _db, headers, _, _ = workflow
    settings = client.application.state.settings
    settings.catalog_approved_templates = [
        "z-last@2",
        "A-first@10",
        "A-first@2",
        "z-last@2",
    ]
    before = settings.catalog_approved_templates.copy()
    response = client.get(PATH, headers=headers())
    assert response.status_code == 200
    check_headers(response)
    data = response.json()
    assert set(data) == {"as_of", "items"} and data["as_of"].endswith("Z")
    assert data["items"] == [
        {"template_key": "A-first", "template_version": 2},
        {"template_key": "A-first", "template_version": 10},
        {"template_key": "z-last", "template_version": 2},
    ]
    assert settings.catalog_approved_templates == before
    settings.catalog_approved_templates = []
    assert client.get(PATH, headers=headers()).json()["items"] == []
    schema = client.application.openapi()["paths"][PATH]
    assert set(schema) == {"get"} and schema["get"]["operationId"] == "API-339"


@pytest.mark.parametrize(
    "raw",
    [
        ["key@01"],
        ["key@0"],
        ["key@100001"],
        ["key@1.0"],
        ["key@+1"],
        ["key@１"],
        [" key@1"],
        ["key@1\n"],
        ["ab@1"],
        ["a" * 81 + "@1"],
        ["key@1@2"],
        ["private/path@1"],
        ["valid@1", "PRIVATE_CANARY_SECRET"],
        ["key@1"] * 101,
        [None],
        None,
        "key@1",
        [True],
    ],
)
def test_invalid_configuration_is_safe_whole_list_failure(workflow, raw, caplog):
    client, _, headers, _, _ = workflow
    client.application.state.settings.catalog_approved_templates = raw
    result = client.get(PATH, headers=headers())
    assert result.status_code == 503
    check_headers(result)
    assert result.json()["error"]["code"] == "PROVIDER_UNAVAILABLE"
    assert "PRIVATE_CANARY" not in result.text + caplog.text
    assert "items" not in result.json()


def test_supported_boundaries(workflow):
    client, _, headers, _, _ = workflow
    client.application.state.settings.catalog_approved_templates = [
        "a" * 80 + "@100000"
    ] + [f"key-{n:03}@1" for n in range(99)]
    response = client.get(PATH, headers=headers())
    assert response.status_code == 200 and len(response.json()["items"]) == 100


def test_guard_matrix_provider_assurance_and_invalid_request(workflow, verifier):
    client, db, headers, _, _ = workflow
    for role in ("operations", "security_admin", "superadmin"):
        db.roles = {role}
        assert client.get(PATH, headers=headers()).status_code == 200
    for roles in ({"finance"}, {"support"}, set()):
        db.roles = roles
        denied = client.get(PATH, headers=headers())
        assert denied.status_code == 403
        check_headers(denied)
    db.roles = {"operations", "finance"}
    assert client.get(PATH, headers=headers()).status_code == 200
    db.mfa = False
    assert client.get(PATH, headers=headers()).status_code == 403
    db.mfa = True
    private = verifier[1]
    aal1 = {
        "Authorization": "Bearer "
        + signed(private, claims(sub=str(db.owner), aal="aal1"))
    }
    assert client.get(PATH, headers=aal1).status_code == 403
    original = db.execute

    def unverified(statement, params=None):
        result = original(statement, params)
        if "sr_account_session_state" in str(statement):
            result.value = SimpleNamespace(email_verified=False, mfa_active=True)
        return result

    db.execute = unverified
    assert client.get(PATH, headers=headers()).status_code == 403
    db.execute = original
    db.active = False
    assert client.get(PATH, headers=headers()).status_code == 401
    db.active = True
    for h in ({}, headers(exp=1)):
        denied = client.get(PATH, headers=h)
        assert denied.status_code == 401
        check_headers(denied)
    for suffix in ("?limit=1", "?cursor=PRIVATE_CANARY", "?x=1&x=2"):
        response = client.get(PATH + suffix, headers=headers())
        assert response.status_code == 422
        check_headers(response)
        assert "PRIVATE_CANARY" not in response.text
    response = client.request("GET", PATH, headers=headers(), content=b"PRIVATE_CANARY")
    assert response.status_code == 422 and "PRIVATE_CANARY" not in response.text
    for method in ("POST", "HEAD", "PUT", "PATCH", "DELETE", "OPTIONS"):
        response = client.request(method, PATH, headers=headers())
        assert response.status_code == 405 and response.headers["allow"] == "GET"
        check_headers(response)


def test_unavailable_dependencies_fail_closed(workflow):
    client, _, headers, _, _ = workflow
    app = client.application
    schema = app.openapi()["paths"][PATH]["get"]
    for status in (401, 403, 405, 422, 503):
        assert schema["responses"][str(status)]["content"]["application/json"][
            "schema"
        ]["$ref"].endswith("/ErrorEnvelope")
    app.state.database = None
    response = client.get(PATH, headers=headers())
    assert response.status_code == 503
    check_headers(response)
    app.state.jwt_verifier = None
    response = client.get(PATH, headers=headers())
    assert response.status_code == 503
    check_headers(response)


def test_picker_browser(monkeypatch):
    monkeypatch.setenv("TASK51A_OUT", "output/task51a-discovery")
    monkeypatch.setenv("TASK51A_WEB", "tmp/task51a-discovery-web")
    monkeypatch.setenv("TASK51A_SPEC", "tests/catalog-template-picker.spec.ts")
    _browser()
