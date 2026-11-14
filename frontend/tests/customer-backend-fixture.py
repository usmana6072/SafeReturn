"""Loopback-only real FastAPI routes with synthetic auth/SQL dependencies.

No database engine, provider, environment file or production resource is used.
This verifies HTTP/DTO integration, not PostgreSQL entitlement or real Auth.
"""
import socket
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
import uvicorn
from fastapi import FastAPI, Header
from app.api.auth import AccessError, access_error, get_auth_context
from app.api.v1 import standalone_owner, item_checkout

def identity(n):
    return f"00000000-0000-4000-8000-{n:012d}"

class FixtureSession:
    active = False
    revision = 1
    status = "unactivated"

    def execute(self, query, params):
        sql = str(query)
        item = dict(logical_item_id=identity(1), qr_id=identity(2), order_id=identity(3),
                    product_name_snapshot="HTTP fixture", tag_type="lost",
                    ownership_status="active" if self.active else "unclaimed",
                    public_status=self.status, revision=self.revision,
                    activated_at="2026-10-26T00:00:00Z" if self.active else None,
                    can_activate=not self.active)
        if "sr_standalone_owner_list" in sql:
            result = {"items": [item], "activation_released": True}
        elif "sr_standalone_begin" in sql:
            result = dict(intent_id=identity(4), logical_item_id=identity(1), qr_id=identity(2),
                          expires_at=(datetime.now(timezone.utc)+timedelta(seconds=30)).isoformat(),
                          method="delivered_purchaser")
        elif "sr_standalone_confirm" in sql:
            assert len(params["kh"]) == 64
            self.active, self.status, self.revision = True, "active", 2
            result = dict(qr_id=identity(2), logical_item_id=identity(1), status="active", revision=2, activated_at="2026-10-26T00:00:00Z")
        elif "sr_standalone_availability" in sql:
            self.status, self.revision = params["wanted"], self.revision+1
            result = dict(qr_id=identity(2), public_status=self.status, revision=self.revision)
        elif "sr_standalone_history" in sql:
            result = dict(qr_id=identity(2), items=[dict(event_id=identity(5), event_type="activated", state_revision=2, created_at="2026-10-26T00:00:00Z")], next_revision=None)
        else:
            raise AssertionError("Unexpected SQL in isolated fixture")
        return SimpleNamespace(scalar_one=lambda: result)

session = FixtureSession()
def auth(authorization: str | None = Header(default=None)):
    if authorization != "Bearer synthetic-customer":
        raise AccessError(401)
    return SimpleNamespace(session=session, email_verified=True,
                           principal=SimpleNamespace(user_id=UUID(identity(6)), session_id=UUID(identity(7))))

app = FastAPI()
app.add_exception_handler(AccessError, access_error)
app.dependency_overrides[get_auth_context] = auth
app.include_router(standalone_owner.router, prefix="/api/v1")
app.include_router(item_checkout.router, prefix="/api/v1")

if __name__ == "__main__":
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    print(f"PORT={listener.getsockname()[1]}", flush=True)
    uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False)).run(sockets=[listener])
