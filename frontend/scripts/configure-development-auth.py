"""Configure only public frontend settings from the existing pinned dev config."""
import re
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
PROJECT_URL = "https://fhuxryfkfrvycsojkzvq.supabase.co"
source = dotenv_values(ROOT / "backend/.env", interpolate=False)
assert source.get("SAFERETURN_SUPABASE_URL", "").rstrip("/") == PROJECT_URL
key = source.get("SAFERETURN_SUPABASE_PUBLISHABLE_KEY") or ""
assert re.fullmatch(r"sb_publishable_[A-Za-z0-9_-]+", key), "Existing public publishable key required; never use a secret/service-role key"
values = {
    "SAFERETURN_API_ORIGIN": "http://127.0.0.1:8030",
    "SAFERETURN_WEB_ORIGIN": "http://127.0.0.1:3100",
    "SAFERETURN_SUPABASE_URL": PROJECT_URL,
    "SAFERETURN_SUPABASE_PUBLISHABLE_KEY": key,
}
target = ROOT / "frontend/.env.local"
text = target.read_text(encoding="utf-8-sig") if target.exists() else ""
existing = dotenv_values(target, interpolate=False) if target.exists() else {}
assert not existing.get("SAFERETURN_SUPABASE_URL") or existing["SAFERETURN_SUPABASE_URL"].rstrip("/") == PROJECT_URL
for name, value in values.items():
    text = re.sub(r"(?m)^\s*" + re.escape(name) + r"\s*=.*(?:\n|$)", "", text)
    text = text.rstrip() + f"\n{name}={value}\n"
target.write_text(text, encoding="utf-8")
print("Configured four public settings in frontend/.env.local; existing development key reused without display.")
for name, value in values.items():
    print(name + ("=" + value if name != "SAFERETURN_SUPABASE_PUBLISHABLE_KEY" else "=<existing public key; not displayed>"))
