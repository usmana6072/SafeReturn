"""Closed fixed-renderer content contract. No executable layouts or asset URLs."""

import re
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.print_render import Template, digest


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


Millimeters = Annotated[str, Field(pattern=r"^[0-9]{1,3}\.[0-9]{2}$")]
Line = Annotated[str, Field(min_length=1, max_length=120)]


def plain(value: str) -> str:
    if (
        not value.strip()
        or any(ord(c) < 32 or ord(c) == 127 for c in value)
        or any(c in value for c in "<>{}\\")
        or re.search(r"[a-z][a-z0-9+.-]*\s*:", value, re.IGNORECASE)
        or re.search(r"(?:javascript|@import|url\s*\(|\$\(|`)", value, re.IGNORECASE)
    ):
        raise ValueError("Plain text required")
    return value


class Content(Closed):
    schema_version: Literal[1]
    renderer: Literal["safereturn-vector-v1"]
    preset: Literal["fixed-footer-v1"]
    symbol_mm: Millimeters
    width_mm: Millimeters
    height_mm: Millimeters
    qr_x_mm: Millimeters
    qr_y_mm: Millimeters
    logo_mm: Millimeters
    min_pitch_mm: Millimeters
    font_pt: Millimeters
    header: str = Field(min_length=1, max_length=50)
    english_lines: list[Line] = Field(min_length=1, max_length=4)
    urdu_lines: list[Line] = Field(min_length=1, max_length=4)
    asset_set_id: UUID
    material_codes: list[Annotated[str, Field(pattern=r"^[a-z0-9_-]{1,40}$")]] = Field(
        min_length=1, max_length=10
    )

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("Integer version required")
        return value

    @field_validator("header")
    @classmethod
    def header_text(cls, value):
        return plain(value)

    @field_validator("english_lines", "urdu_lines")
    @classmethod
    def lines(cls, values):
        return [plain(value) for value in values]

    @model_validator(mode="after")
    def geometry(self):
        if self.material_codes != sorted(set(self.material_codes)):
            raise ValueError("Unique sorted material codes required")
        if any(re.search(r"[A-Za-z0-9]", line) for line in self.urdu_lines):
            raise ValueError("Unsupported mixed-direction caption")
        for name in (
            "symbol_mm",
            "width_mm",
            "height_mm",
            "qr_x_mm",
            "qr_y_mm",
            "logo_mm",
            "min_pitch_mm",
            "font_pt",
        ):
            if not Decimal(0) < Decimal(getattr(self, name)) <= Decimal(270):
                raise ValueError("Invalid geometry bound")
        t = self.renderer_template("validation", 1, "lost")
        if (
            Decimal(self.qr_x_mm) + Decimal(self.symbol_mm) > Decimal(self.width_mm) - 4
            or Decimal(self.qr_y_mm) + Decimal(self.symbol_mm)
            > Decimal(self.height_mm) - 12
            or Decimal(self.logo_mm) > Decimal(self.symbol_mm) * Decimal("0.15")
            or Decimal(self.qr_y_mm)
            - 4
            - Decimal(str(t.font_pt))
            * Decimal("1.5")
            / Decimal("2.8346456693")
            * (len(self.english_lines) + len(self.urdu_lines) - 1)
            < 4
        ):
            raise ValueError("Invalid QR or caption placement")
        return self

    def renderer_template(self, key: str, version: int, purpose: str) -> Template:
        fields = set(Template.model_fields) - {"key", "version", "tag_type"}
        return Template.model_validate(
            {"key": key, "version": version, "tag_type": purpose}
            | {name: getattr(self, name) for name in fields}
        )

    def fingerprint(self, key, version, purpose, assets):
        return digest(
            {
                "content": self.model_dump(mode="json"),
                "key": key,
                "version": version,
                "purpose": purpose,
                "assets": {name: assets[name]["sha256"] for name in ("font", "logo")},
                "preview_policy": "synthetic-issuer43-v1",
            }
        )
