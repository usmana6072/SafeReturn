"""Real Ed25519/closed-contract verification with synthetic enrolled authorities."""

import base64
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
import segno
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from test_print_templates import ASSET, RID, TID, content

from app.core.print_render import canonical, digest
from app.core.template_content import Content
from app.core.template_evidence import (
    Envelope,
    EvidenceInvalid,
    envelope_digest,
    message,
    parse,
    verify,
)


def uid(n):
    return str(UUID(int=n))


def stamp(value):
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture
def signed_evidence():
    now = datetime.now(UTC).replace(microsecond=0)
    assets = {
        "font": {"sha256": "a" * 64, "path": "synthetic/font.ttf"},
        "logo": {"sha256": "b" * 64, "path": "synthetic/logo.svg"},
    }
    c = Content.model_validate(content())
    fp = c.fingerprint("synthetic-key", 1, "lost", assets)
    policy = {
        "schema_version": 1,
        "canonical_origin": "https://qa.example.test",
        "token_length": 43,
        "token_format": "base64url32bytes-v1",
        "renderer": "safereturn-vector-v1",
        "max_qr_version": 6,
        "scanner_profiles": [uid(201), uid(202)],
        "printer_profiles": [uid(203)],
        "printer_processes": {uid(203): "8" * 64},
        "synthetic_cases": ["9" * 64],
        "required_cases": [[uid(201), "normal", "plain"], [uid(202), "low", "plain"]],
        "environments": ["indoor"],
        "symbol_tolerance_mm": "0.10",
        "min_cut_clearance_mm": "2.00",
        "allow_scope_consolidation": False,
        "allow_importer_publisher": False,
    }
    version = segno.make(
        policy["canonical_origin"] + "/q/" + "S" * 43,
        error="q",
        micro=False,
        boost_error=False,
    ).version
    payload = {
        "evidence_id": uid(1001),
        "template_id": str(TID),
        "revision_id": str(RID),
        "revision_row_version": 2,
        "revision_fingerprint_sha256": fp,
        "renderer": "safereturn-vector-v1",
        "preview_policy": "synthetic-issuer43-v1",
        "asset_set_id": str(ASSET),
        "font_sha256": "a" * 64,
        "logo_sha256": "b" * 64,
        "production_policy_id": uid(301),
        "production_policy_version": 1,
        "production_policy_sha256": digest(policy),
        "report_id": uid(302),
        "report_sha256": "c" * 64,
        "issued_at": stamp(now - timedelta(minutes=1)),
        "expires_at": stamp(now + timedelta(hours=1)),
        "material_matrix": [
            {
                "material_code": "synthetic-paper",
                "environment": "indoor",
                "printer_profile_id": uid(203),
                "process_sha256": "8" * 64,
                "symbol_mm": "35.00",
                "width_mm": "55.00",
                "height_mm": "80.00",
                "measured_symbol_mm": "35.00",
                "measured_quiet_zone_modules": 4,
                "measured_pitch_mm": "0.60",
                "logo_mm": "4.00",
                "cut_clearance_mm": "2.00",
                "actual_scale_passed": True,
                "scan_cases": [
                    {
                        "scanner_profile_id": uid(201),
                        "lighting": "normal",
                        "surface": "plain",
                        "synthetic_case_sha256": "9" * 64,
                        "qr_version": version,
                        "decoded_origin_policy_match": True,
                        "passed": True,
                    },
                    {
                        "scanner_profile_id": uid(202),
                        "lighting": "low",
                        "surface": "plain",
                        "synthetic_case_sha256": "9" * 64,
                        "qr_version": version,
                        "decoded_origin_policy_match": True,
                        "passed": True,
                    },
                ],
            }
        ],
        "copy_review": {
            "en_sha256": digest({"header": c.header, "lines": c.english_lines}),
            "ur_sha256": digest(c.urdu_lines),
            "native_urdu_passed": True,
            "privacy_safety_passed": True,
        },
        "license_review": {
            "font_license_reference": "synthetic-font-license",
            "logo_license_reference": "synthetic-logo-license",
            "font_license_evidence_sha256": "d" * 64,
            "logo_license_evidence_sha256": "e" * 64,
            "commercial_reproduction_passed": True,
        },
    }
    ctx = {
        "mode": "import",
        "actor_human": uid(401),
        "importer_human": None,
        "provenance_complete": True,
        "contributors": [uid(402)],
        "revision": {
            "template_id": str(TID),
            "revision_id": str(RID),
            "row_version": 2,
            "status": "pending_qa",
            "version": 1,
            "key": "synthetic-key",
            "purpose": "lost",
            "content": content(),
            "fingerprint_sha256": fp,
        },
        "assets": assets,
        "policy": {
            "policy_id": uid(301),
            "version": 1,
            "sha256": digest(policy),
            "body": policy,
        },
        "archive": {
            uid(302): {"kind": "report", "sha256": "c" * 64},
            "synthetic-font-license": {"kind": "license", "sha256": "d" * 64},
            "synthetic-logo-license": {"kind": "license", "sha256": "e" * 64},
        },
        "authorities": {},
    }
    private = {}
    attestations = []
    for n, scope in enumerate(("physical_scan", "copy_safety", "licenses"), start=1):
        key = Ed25519PrivateKey.generate()
        aid, kid = uid(500 + n), uid(600 + n)
        public = key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        private[kid] = key
        ctx["authorities"][aid] = {
            "human_id": uid(700 + n),
            "scopes": [scope],
            "valid_from": stamp(now - timedelta(days=1)),
            "expires_at": stamp(now + timedelta(days=1)),
            "revoked": False,
            "keys": {
                kid: {
                    "public_key": base64.b64encode(public).decode(),
                    "valid_from": stamp(now - timedelta(days=1)),
                    "expires_at": stamp(now + timedelta(days=1)),
                    "revoked": False,
                }
            },
        }
        attestations.append(
            {
                "authority_id": aid,
                "key_id": kid,
                "scopes": [scope],
                "signature": "A" * 86,
            }
        )
    env = Envelope.model_validate(
        {"schema_version": 1, "payload": payload, "attestations": attestations}
    )

    def sign(value):
        for a in value.attestations:
            a.signature = (
                base64.urlsafe_b64encode(private[str(a.key_id)].sign(message(value, a)))
                .decode()
                .rstrip("=")
            )
        return value

    return sign(env), ctx, now, sign


def test_real_signatures_bind_exact_report_revision_asset_and_policy(signed_evidence):
    env, ctx, now, _ = signed_evidence
    result = verify(
        parse(canonical(env.model_dump(mode="json")).encode()), ctx, now=now
    )
    assert result["evidence_sha256"] == envelope_digest(env)
    assert {s for a in result["attestations"] for s in a["scopes"]} == {
        "physical_scan",
        "copy_safety",
        "licenses",
    }
    ctx["mode"] = "publish"
    ctx["actor_human"] = uid(800)
    ctx["importer_human"] = uid(401)
    assert verify(env, ctx, now=now) == result


@pytest.mark.parametrize(
    "case",
    [
        "signature",
        "missing_scope",
        "duplicate_attestation",
        "unknown_authority",
        "revoked_key",
        "expired_key",
        "future_key",
        "revoked_authority",
        "wrong_scope",
        "same_human",
        "unknown_editor",
        "missing_history",
        "no_contributors",
        "contributor_signer",
        "contributor_publisher",
        "reviewer_publisher",
        "importer_publisher",
        "wrong_revision",
        "stale_revision",
        "wrong_fingerprint",
        "changed_content",
        "changed_assets",
        "wrong_policy",
        "changed_policy",
        "missing_archive",
        "wrong_archive",
        "expired",
        "future",
        "long_window",
        "wrong_process",
        "unregistered_case",
        "incomplete_matrix",
        "duplicate_matrix",
        "wrong_dimensions",
        "bad_measurement",
        "bad_pitch",
        "bad_cut",
        "wrong_qr_version",
        "missing_device",
        "wrong_copy",
        "wrong_license",
    ],
)
def test_closed_independent_evidence_denials(signed_evidence, case):
    env, ctx, now, sign = signed_evidence
    env = env.model_copy(deep=True)
    ctx = deepcopy(ctx)
    a = env.attestations[0]
    authority = ctx["authorities"][str(a.authority_id)]
    k = authority["keys"][str(a.key_id)]
    if case == "signature":
        a.signature = "A" * 86
    elif case == "missing_scope":
        env.attestations.pop()
    elif case == "duplicate_attestation":
        env.attestations.append(a.model_copy())
    elif case == "unknown_authority":
        ctx["authorities"].pop(str(a.authority_id))
    elif case == "revoked_key":
        k["revoked"] = True
    elif case == "expired_key":
        k["expires_at"] = stamp(now)
    elif case == "future_key":
        k["valid_from"] = stamp(now + timedelta(hours=1))
    elif case == "revoked_authority":
        authority["revoked"] = True
    elif case == "wrong_scope":
        authority["scopes"] = ["custody"]
    elif case == "same_human":
        ctx["authorities"][str(env.attestations[1].authority_id)]["human_id"] = (
            authority["human_id"]
        )
    elif case == "unknown_editor":
        ctx["contributors"].append(None)
    elif case == "missing_history":
        ctx["provenance_complete"] = False
    elif case == "no_contributors":
        ctx["contributors"] = []
    elif case == "contributor_signer":
        ctx["contributors"].append(authority["human_id"])
    elif case == "contributor_publisher":
        ctx.update(mode="publish", actor_human=ctx["contributors"][0])
    elif case == "reviewer_publisher":
        ctx.update(mode="publish", actor_human=authority["human_id"])
    elif case == "importer_publisher":
        ctx.update(mode="publish", actor_human=uid(401), importer_human=uid(401))
    elif case == "wrong_revision":
        env.payload.revision_id = UUID(uid(9999))
    elif case == "stale_revision":
        ctx["revision"]["row_version"] += 1
    elif case == "wrong_fingerprint":
        env.payload.revision_fingerprint_sha256 = "0" * 64
    elif case == "changed_content":
        ctx["revision"]["content"]["header"] = "Changed"
    elif case == "changed_assets":
        ctx["assets"]["font"]["sha256"] = "0" * 64
    elif case == "wrong_policy":
        env.payload.production_policy_version = 2
    elif case == "changed_policy":
        ctx["policy"]["body"]["max_qr_version"] = 1
    elif case == "missing_archive":
        ctx["archive"] = {}
    elif case == "wrong_archive":
        ctx["archive"][str(env.payload.report_id)]["sha256"] = "0" * 64
    elif case == "expired":
        env.payload.expires_at = stamp(now)
    elif case == "future":
        env.payload.issued_at = stamp(now + timedelta(minutes=2))
    elif case == "long_window":
        env.payload.expires_at = stamp(now + timedelta(days=2))
    elif case == "wrong_process":
        env.payload.material_matrix[0].process_sha256 = "0" * 64
    elif case == "unregistered_case":
        env.payload.material_matrix[0].scan_cases[0].synthetic_case_sha256 = "0" * 64
    elif case == "incomplete_matrix":
        env.payload.material_matrix[0].material_code = "other"
    elif case == "duplicate_matrix":
        env.payload.material_matrix.append(
            env.payload.material_matrix[0].model_copy(deep=True)
        )
    elif case == "wrong_dimensions":
        env.payload.material_matrix[0].width_mm = "56.00"
    elif case == "bad_measurement":
        env.payload.material_matrix[0].measured_symbol_mm = "29.00"
    elif case == "bad_pitch":
        env.payload.material_matrix[0].measured_pitch_mm = "0.10"
    elif case == "bad_cut":
        env.payload.material_matrix[0].cut_clearance_mm = "0.00"
    elif case == "wrong_qr_version":
        env.payload.material_matrix[0].scan_cases[0].qr_version = 1
    elif case == "missing_device":
        env.payload.material_matrix[0].scan_cases.pop()
    elif case == "wrong_copy":
        env.payload.copy_review.ur_sha256 = "0" * 64
    elif case == "wrong_license":
        env.payload.license_review.font_license_reference = "other-license"
    if case != "signature":
        sign(env)
    with pytest.raises(EvidenceInvalid, match="evidence_not_eligible"):
        verify(env, ctx, now=now)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda v: v.update(extra="PRIVATE_CANARY"),
        lambda v: v.update(schema_version=True),
        lambda v: v["payload"].update(role="designer"),
        lambda v: v["payload"]["copy_review"].update(native_urdu_passed=1),
        lambda v: v["payload"]["material_matrix"][0].update(actual_scale_passed=1),
        lambda v: v["payload"].update(revision_row_version=2.0),
        lambda v: v["payload"]["license_review"].update(
            font_license_reference="https://evil.test"
        ),
    ],
)
def test_closed_envelope_and_strict_values(signed_evidence, mutation):
    env, _, _, _ = signed_evidence
    value = env.model_dump(mode="json")
    mutation(value)
    with pytest.raises(EvidenceInvalid, match="invalid_envelope"):
        parse(json.dumps(value).encode())


@pytest.mark.parametrize(
    "raw",
    [
        b'{"schema_version":1,"schema_version":1}',
        b'{"payload":{"x":1,"x":2}}',
        b'{"number":NaN}',
        b"X" * 131073,
        b'{"url":"PRIVATE_CANARY"}',
        b"[" * 500,
    ],
    ids=[
        "duplicate-root",
        "duplicate-nested",
        "nan",
        "oversized",
        "unknown-field",
        "deep-json",
    ],
)
def test_duplicate_malformed_or_unbounded_json_is_safe(raw):
    with pytest.raises(EvidenceInvalid):
        parse(raw)


@pytest.mark.parametrize(
    "case",
    [
        "authority-not-yet-issued",
        "authority-expired",
        "importer-signer",
        "publisher-importer-signer",
        "duplicate-policy-profile",
        "missing-policy-process",
    ],
)
def test_authority_issue_time_and_policy_matrix_are_not_inferred(signed_evidence, case):
    env, ctx, now, sign = signed_evidence
    human = ctx["authorities"][str(env.attestations[0].authority_id)]
    if case == "authority-not-yet-issued":
        human["valid_from"] = stamp(now)
    elif case == "authority-expired":
        human["expires_at"] = stamp(now)
    elif case == "importer-signer":
        ctx["actor_human"] = human["human_id"]
    elif case == "publisher-importer-signer":
        ctx.update(
            mode="publish", actor_human=uid(800), importer_human=human["human_id"]
        )
    elif case == "duplicate-policy-profile":
        ctx["policy"]["body"]["scanner_profiles"].append(
            ctx["policy"]["body"]["scanner_profiles"][0]
        )
    else:
        ctx["policy"]["body"]["printer_processes"] = {}
    if case in {"duplicate-policy-profile", "missing-policy-process"}:
        ctx["policy"]["sha256"] = digest(ctx["policy"]["body"])
        env.payload.production_policy_sha256 = ctx["policy"]["sha256"]
        sign(env)
    with pytest.raises(EvidenceInvalid):
        verify(env, ctx, now=now)
