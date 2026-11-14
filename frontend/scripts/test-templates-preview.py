"""Offline synthetic preview checks; no live DB or approval evidence."""
from pathlib import Path
import re
import sys
root = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(root / 'backend'), str(root / 'backend/tests')]
import pytest
from test_health import ASGIClient
original = ASGIClient.request
calls = []
def guarded(self, method, path, **kwargs):
    assert method == 'POST' and re.fullmatch(r'/api/v1/admin/print-templates/[0-9a-f-]{36}/revisions/[0-9a-f-]{36}/(?:preview|submit-qa)', path), path
    calls.append((method, path))
    return original(self, method, path, **kwargs)
ASGIClient.request = guarded
result = pytest.main(['-q', str(root / 'backend/tests/test_template_previews.py'), '-p', 'no:cacheprovider'])
print(f'{len(calls)} guarded synthetic preview/QA ASGI requests; zero excluded requests.')
print('Rendering tests use offline synthetic assets; HTTP orchestration replaces OS isolation and uses a scripted DB. No real Linux-worker, registry enrollment or physical QA acceptance claimed.')
raise SystemExit(result)
