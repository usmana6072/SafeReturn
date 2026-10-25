"""Manual staff QA HTTP contract with scripted SQL and real encrypted receipts."""
import json

import pytest
from test_critical_workflow_boundaries import Result
from test_template_publication import env, registry, signed_evidence, verifier  # noqa: F401


@pytest.fixture
def api(registry):  # noqa: F811
    client, db, headers, settings = registry
    db.roles = {'operations'}
    original = db.execute
    state = {'available': True, 'calls': 0, 'conflict': False}
    def execute(statement, params=None):
        sql, p = str(statement), params or {}
        if 'AS template_qa_reviews_available' in sql: return Result(state['available'])
        if 'sr_template_lifecycle' in sql and p['action'] in {'manual_review_status', 'manual_review_decide'}:
            payload = json.loads(p['payload'])
            if state['conflict']: return Result({'error': 'VERSION_MISMATCH'})
            if p['action'] == 'manual_review_decide': state['calls'] += 1
            return Result({'revision_id': payload['revision_id'], 'revision_row_version': 2, 'review_version': 1, 'status': payload.get('decision', 'pending'), 'can_review': True, 'history': []})
        return original(statement, params)
    db.execute = execute
    p = db.evidence.payload
    path = f'/api/v1/admin/print-templates/{p.template_id}/revisions/{p.revision_id}'
    def request(decision='rejected', **extra):
        body = {'decision': decision, 'reason': 'Reviewed physical evidence', 'expected_review_version': 0, 'preview_fingerprint': str(p.revision_fingerprint_sha256), 'confirmed': True}
        body.update(extra)
        return client.post(path + '/qa-decision', json=body, headers=headers() | {'If-Match': f'"{p.revision_row_version}"', 'Origin': settings.print_template_web_origin})
    return client, db, headers, state, path, request

def test_manual_approval_without_signed_evidence_and_replay(api):
    _, db, _, state, _, request = api
    first = request('approved')
    assert first.status_code == 200, first.text
    assert first.json()['result']['status'] == 'approved' and db.approval is None
    assert request('approved').json() == first.json()
    assert state['calls'] == 1 and len(db.audit) == 1

def test_rejection_without_evidence(api):
    _, db, _, _state, _, request = api
    response = request()
    assert response.status_code == 200, response.text
    assert response.json()['result']['status'] == 'rejected'
    assert db.approval is None and len(db.audit) == 1

@pytest.mark.parametrize('roles', [{'security_admin'}, {'superadmin'}, {'support'}, set()])
def test_operations_role_required(api, roles):
    _, db, _, state, _, request = api
    db.roles = roles
    assert request().status_code == 403
    assert state['calls'] == 0 and not db.audit

def test_missing_migration(api):
    client, _, headers, state, path, request = api
    state['available'] = False
    assert client.get(path + '/qa', headers=headers()).status_code == 503
    assert request().status_code == 503 and state['calls'] == 0

def test_stale_decision(api):
    _, db, _, state, _, request = api
    state['conflict'] = True
    assert request().status_code == 412
    assert not db.audit and not db.receipts

def test_idempotency_binds_note(api):
    *_, request = api
    assert request().status_code == 200
    assert request(reason='Another review note').status_code == 409

@pytest.mark.parametrize('extra', [{'reason': '  '}, {'confirmed': False}, {'expected_review_version': -1}, {'envelope': {'fake': True}}])
def test_invalid_rejection(api, extra):
    _, db, _, state, _, request = api
    assert request(**extra).status_code == 422
    assert state['calls'] == 0 and not db.audit

def test_manual_approval_defaults_note_without_upload(api):
    client, db, headers, state, path, _ = api
    response = client.post(path + '/qa-decision', json={'decision': 'approved', 'expected_review_version': 0, 'preview_fingerprint': str(db.evidence.payload.revision_fingerprint_sha256), 'confirmed': True}, headers=headers() | {'If-Match': f'"{db.evidence.payload.revision_row_version}"', 'Origin': 'https://staff.test'})
    assert response.status_code == 200 and state['calls'] == 1 and db.approval is None


def test_invalid_pdf_fingerprint(api):
    _, db, _, state, _, request = api
    assert request('approved', preview_fingerprint='invalid').status_code == 422
    assert state['calls'] == 0 and not db.audit


@pytest.mark.parametrize('age,expected', [(1150, 200), (1201, 403)])
def test_review_twenty_minute_auth_window(api, age, expected):
    import time
    client, db, headers, state, path, _ = api
    p = db.evidence.payload
    response = client.post(path + '/qa-decision', json={'decision': 'rejected', 'reason': 'Window boundary review', 'expected_review_version': 0, 'preview_fingerprint': str(db.evidence.payload.revision_fingerprint_sha256), 'confirmed': True}, headers=headers(amr=[{'method': 'totp', 'timestamp': int(time.time()) - age}]) | {'If-Match': f'"{p.revision_row_version}"', 'Origin': 'https://staff.test'})
    assert response.status_code == expected
    assert state['calls'] == (1 if expected == 200 else 0)

@pytest.mark.parametrize('origin', [None, 'https://evil.test'])
def test_review_requires_matching_origin(api, origin):
    client, db, headers, state, path, _ = api
    h = headers() | {'If-Match': f'"{db.evidence.payload.revision_row_version}"'}
    h.pop('Origin', None)
    if origin: h['Origin'] = origin
    response = client.post(path + '/qa-decision', json={'decision': 'rejected', 'reason': 'CSRF rejected review', 'expected_review_version': 0, 'preview_fingerprint': str(db.evidence.payload.revision_fingerprint_sha256), 'confirmed': True}, headers=h)
    assert response.status_code == 403 and state['calls'] == 0
