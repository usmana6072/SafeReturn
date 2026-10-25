"""Run inspected template tests against scripted DB; guard every ASGI request."""
from pathlib import Path
import sys,re
root=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(root/'backend'),str(root/'backend/tests')]
import pytest
from test_health import ASGIClient
original=ASGIClient.request
calls=[]
def guarded(self,method,path,**kwargs):
    assert re.fullmatch(r'/api/v1/admin/print-templates(?:/[0-9a-f-]{36}(?:/revisions(?:/[0-9a-f-]{36}(?:/(?:preview|submit-qa|retire))?)?)?)?(?:\?[^#]*)?',path), path
    calls.append((method,path))
    return original(self,method,path,**kwargs)
ASGIClient.request=guarded
names=['real_create_and_encrypted_replay','existing_role_writer_permissions','read_permissions_and_safe_headers','signed_session_mfa_recent_boundaries','revoked_live_session_and_disabled_mfa_flag','closed_create_and_unsafe_inputs','closed_content_geometry_and_unsafe_assets','revision_resource_and_precondition_binding','transport_limits_origin_and_preconditions','cursor_actor_filter_and_integrity_binding','unique_key_contract_does_not_strip_or_fold','unavailable_qa_and_preview_never_leak_or_mutate']
result=pytest.main(['-q',str(root/'backend/tests/test_print_templates.py'),'-k','('+' or '.join(names)+') and not publish','-p','no:cacheprovider'])
print(f'{len(calls)} ASGI requests guarded: template metadata/draft paths only; zero excluded requests.')
raise SystemExit(result)
