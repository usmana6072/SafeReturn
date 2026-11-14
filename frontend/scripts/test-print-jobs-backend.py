"""Run inspected 349/350 metadata tests only; never enqueue or production paths."""

import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(root / "backend"), str(root / "backend/tests")]
import pytest
from test_health import ASGIClient

original = ASGIClient.request
calls = []


def guarded(self, method, path, **kw):
    target = path.split("?")[0]
    assert (
        method == "GET"
        and target in ["/api/v1/admin/print-jobs", "/api/v1/admin/print-jobs/counts"]
    ) or (method == "POST" and target == "/api/v1/admin/print-jobs/counts"), path
    calls.append((method, path))
    return original(self, method, path, **kw)


ASGIClient.request = guarded
names = [
    "auth_session_mfa_role_headers_and_no_inheritance",
    "closed_exact_filters",
    "production_sql_ties_live_pages_ceiling_and_cursor_bindings",
    "exact_search_half_open_dates_and_distinct_financial_states",
    "independent_capped_single_statement_counts",
    "failure_rollback_and_final_live_denial",
    "closed_projection_key_failure_route_registry_and_no_production_calls",
    "live_resolution_preserves_ceiling_and_filter_bound_paging",
    "aware_offset_normalizes_to_utc",
]
result = pytest.main(
    [
        "-q",
        str(root / "backend/tests/test_print_console.py"),
        "-k",
        " or ".join(names),
        "-p",
        "no:cacheprovider",
    ]
)
print(
    f"{len(calls)} guarded ASGI metadata requests; zero excluded requests. Enqueue tests deselected. SQLite-adapted SELECTs are not PostgreSQL/RLS acceptance."
)
raise SystemExit(result)
