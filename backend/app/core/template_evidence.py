"""Versioned closed offline attestations. No enrollment, signing or external fetch."""

import base64
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Literal
from urllib.parse import urlsplit
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import Field, ValidationError, field_validator, model_validator

from app.core.print_render import canonical, digest
from app.core.template_content import Closed, Content, Millimeters

Sha = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Positive = Annotated[int, Field(ge=1, strict=True)]
Scope = Literal["physical_scan", "copy_safety", "licenses"]
Reference = Annotated[str, Field(pattern=r"^[A-Za-z0-9._-]{1,160}$")]
Stamp = Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")]
Truth = Literal[True]


class EvidenceInvalid(ValueError):
    """Fixed safe reason only; never put signed input in exceptions/logs."""


class ScanCase(Closed):
    scanner_profile_id: UUID
    lighting: Literal["normal", "low"]
    surface: Literal["plain", "laminated", "gloss"]
    synthetic_case_sha256: Sha
    qr_version: Annotated[int, Field(ge=1, le=6, strict=True)]
    decoded_origin_policy_match: Truth
    passed: Truth

    @field_validator("decoded_origin_policy_match", "passed", mode="before")
    @classmethod
    def truth(cls, value):
        if value is not True:
            raise ValueError("Boolean true required")
        return value


class MaterialReview(Closed):
    material_code: Annotated[str, Field(pattern=r"^[a-z0-9_-]{1,40}$")]
    environment: Literal["indoor", "outdoor"]
    printer_profile_id: UUID
    process_sha256: Sha
    symbol_mm: Millimeters
    width_mm: Millimeters
    height_mm: Millimeters
    measured_symbol_mm: Millimeters
    measured_quiet_zone_modules: Annotated[int, Field(ge=4, le=32, strict=True)]
    measured_pitch_mm: Millimeters
    logo_mm: Millimeters
    cut_clearance_mm: Millimeters
    actual_scale_passed: Truth
    scan_cases: list[ScanCase] = Field(min_length=2, max_length=20)

    @field_validator("actual_scale_passed", mode="before")
    @classmethod
    def truth(cls, value):
        if value is not True:
            raise ValueError("Boolean true required")
        return value


class CopyReview(Closed):
    en_sha256: Sha
    ur_sha256: Sha
    native_urdu_passed: Truth
    privacy_safety_passed: Truth

    @field_validator("native_urdu_passed", "privacy_safety_passed", mode="before")
    @classmethod
    def truth(cls, value):
        if value is not True:
            raise ValueError("Boolean true required")
        return value


class LicenseReview(Closed):
    font_license_reference: Reference
    logo_license_reference: Reference
    font_license_evidence_sha256: Sha
    logo_license_evidence_sha256: Sha
    commercial_reproduction_passed: Truth

    @field_validator("commercial_reproduction_passed", mode="before")
    @classmethod
    def truth(cls, value):
        if value is not True:
            raise ValueError("Boolean true required")
        return value


class Evidence(Closed):
    evidence_id: UUID
    template_id: UUID
    revision_id: UUID
    revision_row_version: Positive
    revision_fingerprint_sha256: Sha
    renderer: Literal["safereturn-vector-v1"]
    preview_policy: Literal["synthetic-issuer43-v1"]
    asset_set_id: UUID
    font_sha256: Sha
    logo_sha256: Sha
    production_policy_id: UUID
    production_policy_version: Positive
    production_policy_sha256: Sha
    report_id: UUID
    report_sha256: Sha
    issued_at: Stamp
    expires_at: Stamp
    material_matrix: list[MaterialReview] = Field(min_length=1, max_length=30)
    copy_review: CopyReview
    license_review: LicenseReview


class Attestation(Closed):
    authority_id: UUID
    key_id: UUID
    scopes: list[Scope] = Field(min_length=1, max_length=3)
    signature: Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{86}$")]

    @model_validator(mode="after")
    def unique_scopes(self):
        if self.scopes != sorted(set(self.scopes)):
            raise ValueError("Sorted unique scopes required")
        return self


class Envelope(Closed):
    schema_version: Literal[1]
    payload: Evidence
    attestations: list[Attestation] = Field(min_length=1, max_length=10)

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer(cls, value):
        if type(value) is not int:
            raise ValueError("Integer required")
        return value


class ProductionPolicy(Closed):
    schema_version: Annotated[int, Field(ge=1, le=1, strict=True)]
    canonical_origin: str = Field(max_length=200)
    token_length: Annotated[int, Field(ge=43, le=43, strict=True)]
    token_format: Literal["base64url32bytes-v1"]
    renderer: Literal["safereturn-vector-v1"]
    max_qr_version: Annotated[int, Field(ge=1, le=6, strict=True)]
    scanner_profiles: list[UUID] = Field(min_length=2, max_length=20)
    printer_profiles: list[UUID] = Field(min_length=1, max_length=10)
    printer_processes: dict[str, Sha] = Field(min_length=1, max_length=10)
    synthetic_cases: list[Sha] = Field(min_length=1, max_length=20)
    # Required cases are explicit owner/reviewer-approved matrix cells, no guessed defaults.
    required_cases: list[
        tuple[UUID, Literal["normal", "low"], Literal["plain", "laminated", "gloss"]]
    ] = Field(min_length=2, max_length=20)
    environments: list[Literal["indoor", "outdoor"]] = Field(min_length=1, max_length=2)
    symbol_tolerance_mm: Millimeters
    min_cut_clearance_mm: Millimeters
    allow_scope_consolidation: bool = Field(strict=True)
    allow_importer_publisher: bool = Field(strict=True)

    @model_validator(mode="after")
    def unambiguous_matrix(self):
        for values in (
            self.scanner_profiles,
            self.printer_profiles,
            self.synthetic_cases,
            self.required_cases,
            self.environments,
        ):
            if len(values) != len(set(values)):
                raise ValueError("Unique policy entries required")
        if set(self.printer_processes) != {str(p) for p in self.printer_profiles} or {
            c[0] for c in self.required_cases
        } != set(self.scanner_profiles):
            raise ValueError("Complete registered policy matrix required")
        return self

    @field_validator("canonical_origin")
    @classmethod
    def origin(cls, value):
        u = urlsplit(value)
        if (
            u.scheme != "https"
            or not u.hostname
            or u.username
            or u.password
            or u.path
            or u.query
            or u.fragment
            or u.port not in (None, 443)
        ):
            raise ValueError("Approved origin required")
        return value


def timestamp(value):
    return datetime.fromisoformat(value)


def parse(raw: bytes) -> Envelope:
    def unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise EvidenceInvalid("invalid_envelope")
            result[k] = v
        return result

    if not isinstance(raw, bytes) or len(raw) > 131072:
        raise EvidenceInvalid("invalid_envelope")
    try:
        value = json.loads(
            raw,
            object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(
                EvidenceInvalid("invalid_envelope")
            ),
        )
        return Envelope.model_validate(value)
    except (ValidationError, ValueError, TypeError, RecursionError):
        raise EvidenceInvalid("invalid_envelope") from None


def message(envelope, attestation):
    value = {
        "payload": envelope.payload.model_dump(mode="json"),
        "authority_id": str(attestation.authority_id),
        "key_id": str(attestation.key_id),
        "scopes": attestation.scopes,
    }
    return b"SafeReturn:template-qa:v1\n" + canonical(value).encode("utf-8")


def envelope_digest(envelope):
    value = envelope.model_dump(mode="json")
    value["attestations"] = sorted(
        value["attestations"],
        key=lambda a: (a["authority_id"], a["key_id"], a["scopes"]),
    )
    return digest(value)


def verify(envelope: Envelope, context: dict, *, now=None) -> dict:
    """Context must come from the protected repository, never request DTO fields."""
    try:
        return _verify(envelope, context, now or datetime.now(UTC))
    except (KeyError, TypeError, ValueError, InvalidSignature):
        raise EvidenceInvalid("evidence_not_eligible") from None


def _verify(envelope, ctx, now):
    p = envelope.payload
    issued, expires = timestamp(p.issued_at), timestamp(p.expires_at)
    if (
        issued.timestamp() > now.timestamp() + 60
        or not issued < expires
        or (expires - issued).total_seconds() > 86400
        or expires <= now
    ):
        raise EvidenceInvalid("evidence_not_eligible")
    revision = ctx["revision"]
    c = Content.model_validate(revision["content"])
    if (
        not ctx["provenance_complete"]
        or not ctx["contributors"]
        or None in ctx["contributors"]
    ):
        raise EvidenceInvalid("evidence_not_eligible")
    if (
        revision["status"] != "pending_qa"
        or str(p.template_id) != revision["template_id"]
        or str(p.revision_id) != revision["revision_id"]
        or p.revision_row_version != revision["row_version"]
        or p.revision_fingerprint_sha256 != revision["fingerprint_sha256"]
    ):
        raise EvidenceInvalid("evidence_not_eligible")
    if (
        str(p.asset_set_id) != str(c.asset_set_id)
        or p.font_sha256 != ctx["assets"]["font"]["sha256"]
        or p.logo_sha256 != ctx["assets"]["logo"]["sha256"]
    ):
        raise EvidenceInvalid("evidence_not_eligible")
    if (
        c.fingerprint(
            revision["key"], revision["version"], revision["purpose"], ctx["assets"]
        )
        != p.revision_fingerprint_sha256
    ):
        raise EvidenceInvalid("evidence_not_eligible")
    policy_row = ctx["policy"]
    policy = ProductionPolicy.model_validate(policy_row["body"])
    if (
        str(p.production_policy_id) != policy_row["policy_id"]
        or p.production_policy_version != policy_row["version"]
        or p.production_policy_sha256 != digest(policy_row["body"])
        or p.production_policy_sha256 != policy_row["sha256"]
    ):
        raise EvidenceInvalid("evidence_not_eligible")
    # Density of the approved production origin is separate from preview.invalid.
    import segno

    code = segno.make(
        policy.canonical_origin + "/q/" + "S" * 43,
        error="q",
        micro=False,
        boost_error=False,
    )
    if code.version > policy.max_qr_version or Decimal(c.symbol_mm) / Decimal(
        len(code.matrix) + 8
    ) < Decimal(c.min_pitch_mm):
        raise EvidenceInvalid("evidence_not_eligible")
    if p.copy_review.en_sha256 != digest(
        {"header": c.header, "lines": c.english_lines}
    ) or p.copy_review.ur_sha256 != digest(c.urdu_lines):
        raise EvidenceInvalid("evidence_not_eligible")
    archive = ctx["archive"]
    for ref, sha, kind in [
        (str(p.report_id), p.report_sha256, "report"),
        (
            p.license_review.font_license_reference,
            p.license_review.font_license_evidence_sha256,
            "license",
        ),
        (
            p.license_review.logo_license_reference,
            p.license_review.logo_license_evidence_sha256,
            "license",
        ),
    ]:
        if archive[ref] != {"sha256": sha, "kind": kind}:
            raise EvidenceInvalid("evidence_not_eligible")
    wanted = {(m, e) for m in c.material_codes for e in policy.environments}
    seen = set()
    for row in p.material_matrix:
        cell = (row.material_code, row.environment)
        if (
            cell in seen
            or cell not in wanted
            or row.printer_profile_id not in policy.printer_profiles
            or policy.printer_processes.get(str(row.printer_profile_id))
            != row.process_sha256
        ):
            raise EvidenceInvalid("evidence_not_eligible")
        seen.add(cell)
        if any(
            getattr(row, name) != getattr(c, name)
            for name in ("symbol_mm", "width_mm", "height_mm", "logo_mm")
        ):
            raise EvidenceInvalid("evidence_not_eligible")
        if (
            Decimal(row.measured_symbol_mm)
            < (35 if row.environment == "outdoor" else 30)
            or abs(Decimal(row.measured_symbol_mm) - Decimal(c.symbol_mm))
            > Decimal(policy.symbol_tolerance_mm)
            or Decimal(row.measured_pitch_mm) < Decimal(c.min_pitch_mm)
            or Decimal(row.cut_clearance_mm) < Decimal(policy.min_cut_clearance_mm)
        ):
            raise EvidenceInvalid("evidence_not_eligible")
        cases = set()
        for case in row.scan_cases:
            cell = (case.scanner_profile_id, case.lighting, case.surface)
            if (
                cell in cases
                or case.scanner_profile_id not in policy.scanner_profiles
                or case.qr_version != code.version
                or case.synthetic_case_sha256 not in policy.synthetic_cases
            ):
                raise EvidenceInvalid("evidence_not_eligible")
            cases.add(cell)
        if not set(policy.required_cases).issubset(cases):
            raise EvidenceInvalid("evidence_not_eligible")
    if seen != wanted:
        raise EvidenceInvalid("evidence_not_eligible")
    scopes = set()
    people = set()
    pairs = set()
    attestations = []
    for a in envelope.attestations:
        identity = (str(a.authority_id), str(a.key_id))
        if identity in pairs or scopes.intersection(a.scopes):
            raise EvidenceInvalid("evidence_not_eligible")
        pairs.add(identity)
        authority = ctx["authorities"][str(a.authority_id)]
        k = authority["keys"][str(a.key_id)]
        human = authority["human_id"]
        if (
            human in ctx["contributors"]
            or not set(a.scopes).issubset(authority["scopes"])
            or timestamp(k["valid_from"]) > min(issued, now)
            or timestamp(k["expires_at"]) <= now
            or k["revoked"]
            or authority["revoked"]
            or timestamp(authority["valid_from"]) > min(issued, now)
            or timestamp(authority["expires_at"]) <= now
        ):
            raise EvidenceInvalid("evidence_not_eligible")
        if not policy.allow_scope_consolidation and (
            len(a.scopes) > 1 or human in people
        ):
            raise EvidenceInvalid("evidence_not_eligible")
        public = base64.b64decode(k["public_key"], altchars=b"-_", validate=True)
        signature = base64.urlsafe_b64decode(a.signature + "==")
        if base64.urlsafe_b64encode(signature).decode().rstrip("=") != a.signature:
            raise EvidenceInvalid("evidence_not_eligible")
        Ed25519PublicKey.from_public_bytes(public).verify(
            signature, message(envelope, a)
        )
        scopes.update(a.scopes)
        people.add(human)
        attestations.append(
            {
                "authority_id": str(a.authority_id),
                "key_id": str(a.key_id),
                "human_id": human,
                "scopes": a.scopes,
            }
        )
    if scopes != {"physical_scan", "copy_safety", "licenses"}:
        raise EvidenceInvalid("evidence_not_eligible")
    if (ctx["mode"] == "import" and ctx["actor_human"] in people) or (
        ctx["mode"] == "publish" and ctx.get("importer_human") in people
    ):
        raise EvidenceInvalid("evidence_not_eligible")
    if ctx["mode"] == "publish" and (
        ctx["actor_human"] in (people | set(ctx["contributors"]))
        or (
            not policy.allow_importer_publisher
            and ctx["actor_human"] == ctx.get("importer_human")
        )
    ):
        raise EvidenceInvalid("evidence_not_eligible")
    return {
        "evidence_id": str(p.evidence_id),
        "revision_id": str(p.revision_id),
        "revision_row_version": p.revision_row_version,
        "revision_fingerprint_sha256": p.revision_fingerprint_sha256,
        "evidence_sha256": envelope_digest(envelope),
        "expires_at": p.expires_at,
        "policy_id": str(p.production_policy_id),
        "policy_version": p.production_policy_version,
        "policy_sha256": p.production_policy_sha256,
        "attestations": attestations,
        "material_matrix": [r.model_dump(mode="json") for r in p.material_matrix],
        "archive_references": [
            str(p.report_id),
            p.license_review.font_license_reference,
            p.license_review.logo_license_reference,
        ],
        "allow_importer_publisher": policy.allow_importer_publisher,
    }
