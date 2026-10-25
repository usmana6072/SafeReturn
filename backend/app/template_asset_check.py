"""Offline packaged-asset/isolated-worker build check. No database or real QR input."""
import hashlib
import json
from pathlib import Path

from app.core.template_content import Content
from app.core.template_preview import isolated_preview


def main():
    root = Path("/app/print-assets")
    manifest = json.loads((root / "manifest.json").read_text())
    assert manifest["project"] == "fhuxryfkfrvycsojkzvq"
    for name, expected in manifest["files"].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected
    content = Content.model_validate(json.loads((root / "draft-40x60.json").read_text()))
    spec = {"content": content.model_dump(mode="json"), "key": "dev-lost-40x60-candidate", "version": 1, "purpose": "lost", "assets": {
        "font": {"path": str(root / "Amiri-Regular.ttf"), "sha256": manifest["files"]["Amiri-Regular.ttf"]},
        "logo": {"path": str(root / "logo.svg"), "sha256": manifest["files"]["logo.svg"]},
    }}
    pdf = isolated_preview(spec, str(root))
    assert pdf.startswith(b"%PDF-") and len(pdf) <= 2 * 1024 * 1024
    print(json.dumps({"packaged_assets": "verified", "isolated_synthetic_preview": "passed", "pdf_bytes": len(pdf), "publication_approval": False}))


if __name__ == "__main__":
    main()
