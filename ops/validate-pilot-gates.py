"""Validate a SafeReturn physical/provider pilot release record.

The record is evidence metadata only. This command never scans a QR, contacts a
provider, uploads an artifact, or changes a deployment.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REQUIRED_GATES = (
    "artwork_approval",
    "bilingual_copy_review",
    "font_rendering",
    "qr_scan_matrix",
    "provider_smoke",
    "pilot_signoff",
)
REQUIRED_TEMPLATES = {"lost", "ice"}
REQUIRED_PROVIDERS = {"supabase", "resend", "google_sheets", "cloudinary"}


def validate(record: dict) -> list[str]:
    errors: list[str] = []
    if record.get("status") != "ready":
        errors.append("release status must be ready")
    if not record.get("release_id") or not record.get("app_commit"):
        errors.append("release_id and app_commit are required")
    if not record.get("migration_revision"):
        errors.append("migration_revision is required")

    physical = record.get("physical", {})
    templates = physical.get("templates", {})
    if set(templates) != REQUIRED_TEMPLATES:
        errors.append("exactly locked lost and ice templates are required")
    for tag_type in REQUIRED_TEMPLATES:
        template = templates.get(tag_type, {})
        if template.get("status") != "approved":
            errors.append(f"{tag_type} template is not approved")
        if not template.get("version") or not template.get("sha256"):
            errors.append(f"{tag_type} template version and sha256 are required")

    dimensions = physical.get("dimensions_mm", {})
    if dimensions.get("quiet_zone_modules") != 4:
        errors.append("quiet zone must be 4 modules")
    if dimensions.get("indoor_qr_symbol_min") != 30:
        errors.append("indoor QR symbol minimum must be 30 mm")
    if dimensions.get("outdoor_qr_symbol_min") != 35:
        errors.append("outdoor QR symbol minimum must be 35 mm")

    copy = physical.get("bilingual_copy", {})
    if copy.get("en") != "approved" or copy.get("ur") != "approved":
        errors.append("English and Urdu copy must both be approved")
    fonts = physical.get("fonts", {})
    if fonts.get("status") != "approved" or not fonts.get("sha256"):
        errors.append("reviewed font assets and fingerprint are required")
    scan = physical.get("scan_matrix", {})
    if scan.get("status") != "passed" or scan.get("devices_tested", 0) < 2:
        errors.append("at least two physical scan devices must pass")
    if scan.get("materials_tested", 0) < 1:
        errors.append("at least one physical print material must be tested")

    providers = record.get("providers", {})
    if set(providers) != REQUIRED_PROVIDERS:
        errors.append("all required provider gates must be present")
    for provider in REQUIRED_PROVIDERS:
        if providers.get(provider, {}).get("status") != "passed":
            errors.append(f"{provider} provider gate is not passed")

    gates = record.get("gates", {})
    for gate in REQUIRED_GATES:
        if gates.get(gate, {}).get("status") != "passed":
            errors.append(f"{gate} gate is not passed")
        if not gates.get(gate, {}).get("evidence"):
            errors.append(f"{gate} evidence is required")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    args = parser.parse_args()
    try:
        record = json.loads(args.record.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"invalid release record: {error}", file=sys.stderr)
        return 2
    errors = validate(record)
    if errors:
        for error in errors:
            print(f"BLOCKED: {error}", file=sys.stderr)
        return 1
    print(f"READY: {record['release_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
