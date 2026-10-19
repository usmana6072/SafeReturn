import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parents[2] / "ops" / "validate-pilot-gates.py"
SPEC = importlib.util.spec_from_file_location("release_gates", SCRIPT)
release_gates = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(release_gates)


def ready_record():
    return {
        "release_id": "pilot-2026-10-16",
        "status": "ready",
        "app_commit": "abc123",
        "migration_revision": "0017_print_download_grants",
        "physical": {
            "templates": {
                tag: {"status": "approved", "version": "v1", "sha256": "a" * 64}
                for tag in ("lost", "ice")
            },
            "dimensions_mm": {
                "quiet_zone_modules": 4,
                "indoor_qr_symbol_min": 30,
                "outdoor_qr_symbol_min": 35,
            },
            "bilingual_copy": {"en": "approved", "ur": "approved"},
            "fonts": {"status": "approved", "sha256": "b" * 64},
            "scan_matrix": {
                "status": "passed",
                "devices_tested": 2,
                "materials_tested": 1,
            },
        },
        "providers": {
            provider: {"status": "passed"}
            for provider in ("supabase", "resend", "google_sheets", "cloudinary")
        },
        "gates": {
            gate: {"status": "passed", "evidence": f"evidence/{gate}.json"}
            for gate in release_gates.REQUIRED_GATES
        },
    }


def test_release_gate_record_is_fail_closed_until_all_evidence_exists():
    record = ready_record()
    assert release_gates.validate(record) == []
    record["physical"]["scan_matrix"]["devices_tested"] = 1
    assert "at least two physical scan devices must pass" in release_gates.validate(record)


def test_release_gate_record_rejects_unapproved_provider():
    record = ready_record()
    record["providers"]["resend"]["status"] = "not_run"
    assert "resend provider gate is not passed" in release_gates.validate(record)
