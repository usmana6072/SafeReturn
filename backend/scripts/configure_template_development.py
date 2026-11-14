"""Apply/revert only two public local settings after pinned live acceptance."""
import json
import re
import sys
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / "backend/.env"
env = dotenv_values(path, interpolate=False)
assert env.get("SAFERETURN_SUPABASE_URL", "").rstrip("/") == "https://fhuxryfkfrvycsojkzvq.supabase.co"
changes = {"SAFERETURN_PRINT_TEMPLATE_MANAGEMENT_ENABLED": "true", "SAFERETURN_PRINT_TEMPLATE_WEB_ORIGIN": "http://127.0.0.1:3100"}
journal = ROOT / "tmp/template-activation/local-settings-before.json"
if "--rollback" in sys.argv:
    changes = json.loads(journal.read_text())
else:
    receipt = json.loads((ROOT / "tmp/template-activation/live-acceptance.json").read_text())
    assert receipt["project"] == "fhuxryfkfrvycsojkzvq" and receipt["passed"] is True
    if not journal.exists():
        journal.write_text(json.dumps({key: env.get(key) for key in changes}, indent=2) + "\n")
content = path.read_text()
for key, value in changes.items():
    pattern = rf"(?m)^\s*{re.escape(key)}=.*$"
    content = re.sub(pattern, "", content)
    if value is not None:
        assert "\n" not in value and "\r" not in value
        content = content.rstrip() + f"\n{key}={value}\n"
path.write_text(content)
print("Only the two public local template settings updated. Restart this development backend.")
