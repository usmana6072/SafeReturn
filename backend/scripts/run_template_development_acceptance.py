"""Owner-approved single synthetic metadata fixture. No QR, assets or publication."""
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
assert dotenv_values(ROOT / "backend/.env").get("SAFERETURN_SUPABASE_URL", "").rstrip("/") == "https://fhuxryfkfrvycsojkzvq.supabase.co"
token = sys.stdin.read(16385).strip()
assert token.count(".") == 2 and len(token) < 16384
base = "/api/v1/admin/print-templates"
body = {"key": "dev-acceptance-20261025", "name": "Development acceptance fixture", "purpose": "lost"}
receipt = {"project": "fhuxryfkfrvycsojkzvq", "checked_at": datetime.now(UTC).isoformat(), "scope": "one owner-approved synthetic metadata key; mandatory audit and idempotency only", "checks": {}}
with httpx.Client(base_url="http://127.0.0.1:8032", timeout=25, follow_redirects=False, trust_env=False) as client:
    security = client.get("/api/v1/me/staff-security", headers={"Authorization": "Bearer " + token})
    assert security.status_code == 200 and security.json()["mfa_verified"] is True
    assert "operations" in security.json()["roles"]
    headers = {"Authorization": "Bearer " + token, "Origin": "http://127.0.0.1:3100", "Idempotency-Key": "dev-template-acceptance-20261025-v1"}
    anonymous = client.get(base)
    assert anonymous.status_code == 401
    receipt["checks"]["anonymous_denied"] = anonymous.status_code
    listed = client.get(base, headers=headers, params={"limit": "2", "purpose": "lost", "status": "draft"})
    assert listed.status_code == 200 and len(listed.json()["items"]) <= 2
    receipt["checks"]["listing"] = listed.status_code
    created = client.post(base, headers=headers, json=body)
    receipt["checks"]["creation"] = created.status_code
    if created.status_code != 201:
        receipt["failure_code"] = created.json().get("error", {}).get("code", "unavailable")
    else:
        value = created.json()
        template = value["result"]
        assert template["key"] == body["key"] and template["lifecycle_status"] == "draft"
        receipt["fixture_template_id"] = template["template_id"]
        replay = client.post(base, headers=headers, json=body)
        assert replay.status_code == 201 and replay.json() == value
        receipt["checks"]["encrypted_idempotent_replay"] = replay.status_code
        conflict = client.post(base, headers=headers, json=body | {"name": "Different uncommitted intent"})
        assert conflict.status_code == 409
        receipt["checks"]["changed_intent_denied"] = conflict.status_code
        detail = client.get(base + "/" + template["template_id"], headers=headers)
        assert detail.status_code == 200 and detail.json()["revisions"] == []
        assert detail.json()["template"]["template_id"] == template["template_id"]
        receipt["checks"]["detail_empty_revisions"] = detail.status_code
        assert detail.headers.get("etag") == '"1"'
        receipt["checks"]["version_etag"] = True
        assert "no-store" in detail.headers.get("cache-control", "")
        receipt["checks"]["private_no_store"] = True
receipt["passed"] = receipt["checks"].get("detail_empty_revisions") == 200
receipt["not_executed"] = ["design revisions: zero enrolled assets", "preview and QA submission: Windows isolation unsupported", "approval/publication: zero valid authorities/QA evidence", "binding: no approved applicable revision", "real QR operations"]
output = ROOT / "tmp/template-activation/live-acceptance.json"
output.write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
sys.exit(0 if receipt["passed"] else 1)
