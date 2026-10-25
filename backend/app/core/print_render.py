"""Locked, fingerprinted vector label rendering; no activation-credential access."""

import hashlib
import io
import json
import re
import threading
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

import segno
import uharfbuzz as hb
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont as SourceFont
from lxml import etree
from pydantic import BaseModel, ConfigDict, Field
from reportlab.graphics import renderPDF
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from svglib.svglib import svg2rlg


class OutlinePen(BasePen):
    def __init__(self, glyphset, path):
        super().__init__(glyphset)
        self.path = path

    def _moveTo(self, p):
        self.path.moveTo(*p)

    def _lineTo(self, p):
        self.path.lineTo(*p)

    def _curveToOne(self, a, b, c):
        self.path.curveTo(*a, *b, *c)

    def _closePath(self):
        self.path.close()

    def _endPath(self):
        pass


def urdu_run(c, text, font_data, font_source, x, y, size, max_width):
    # Captions are separate Urdu runs. Mixed Latin/Urdu lines need approved bidi layouts.
    if re.search("[A-Za-z0-9]", text):
        raise PrintUnavailable("mixed_direction_caption")
    face = hb.Face(font_data)
    font = hb.Font(face)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    buf.direction = "rtl"
    buf.language = "ur"
    hb.shape(font, buf, {"kern": True})
    width = sum(p.x_advance for p in buf.glyph_positions) * size / face.upem
    if width > max_width:
        raise PrintUnavailable("caption_overflow")
    glyphset = font_source.getGlyphSet()
    names = font_source.getGlyphOrder()
    cursor = x - width / 2
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        if info.codepoint == 0:
            raise PrintUnavailable("missing_urdu_glyph")
        c.saveState()
        c.translate(
            cursor + pos.x_offset * size / face.upem,
            y + pos.y_offset * size / face.upem,
        )
        c.scale(size / face.upem, size / face.upem)
        path = c.beginPath()
        glyphset[names[info.codepoint]].draw(OutlinePen(glyphset, path))
        c.drawPath(path, fill=1, stroke=0)
        c.restoreState()
        cursor += pos.x_advance * size / face.upem
    return width


RENDERER = "safereturn-vector-v1"
LOCK = threading.Lock()


class PrintUnavailable(ValueError):
    pass


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class Asset(Closed):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class Template(Closed):
    key: str = Field(pattern=r"^[a-zA-Z0-9._-]{3,80}$")
    version: int = Field(ge=1)
    tag_type: Literal["lost", "ice"]
    symbol_mm: float = Field(ge=30, le=100)
    width_mm: float = Field(ge=40, le=190)
    height_mm: float = Field(ge=60, le=270)
    qr_x_mm: float = Field(ge=4)
    qr_y_mm: float = Field(ge=18)
    logo_mm: float = Field(gt=0, le=6)
    min_pitch_mm: float = Field(ge=0.3)
    font_pt: float = Field(ge=8, le=14)
    header: str = Field(min_length=1, max_length=50)
    english_lines: list[str] = Field(min_length=1, max_length=4)
    urdu_lines: list[str] = Field(min_length=1, max_length=4)


class Bundle(Closed):
    renderer: Literal["safereturn-vector-v1"]
    approval_ref: str = Field(min_length=4, max_length=160)
    origin: str
    font: Asset
    logo: Asset
    templates: list[Template] = Field(min_length=2, max_length=20)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def asset_bytes(asset):
    try:
        data = Path(asset["path"]).read_bytes()
        if len(data) > 5_000_000 or hashlib.sha256(data).hexdigest() != asset["sha256"]:
            raise ValueError()
        return data
    except (OSError, ValueError):
        raise PrintUnavailable("asset_unavailable") from None


def load_bundle(settings):
    if not settings.print_enabled or not settings.print_template_bundle_path:
        raise PrintUnavailable("print_not_configured")
    try:
        p = Path(settings.print_template_bundle_path)
        if p.stat().st_size > 100000:
            raise ValueError()
        data = p.read_bytes()
        if hashlib.sha256(data).hexdigest() != settings.print_template_bundle_sha256:
            raise ValueError()
        b = Bundle.model_validate_json(data).model_dump()
        u = urlsplit(b["origin"])
        if (
            u.scheme != "https"
            or not u.hostname
            or u.username
            or u.password
            or u.path not in ("", "/")
            or u.query
            or u.fragment
        ):
            raise ValueError()
        b["origin"] = b["origin"].rstrip("/")
        for name in ("font", "logo"):
            q = Path(b[name]["path"])
            b[name]["path"] = str(q if q.is_absolute() else (p.parent / q).resolve())
            asset_bytes(b[name])
        signatures = set()
        for t in b["templates"]:
            signature = (t["key"], t["version"], t["tag_type"], t["symbol_mm"])
            if signature in signatures:
                raise ValueError()
            signatures.add(signature)
            if (
                t["qr_x_mm"] + t["symbol_mm"] > t["width_mm"] - 4
                or t["qr_y_mm"] + t["symbol_mm"] > t["height_mm"] - 12
                or t["logo_mm"] > t["symbol_mm"] * 0.15
            ):
                raise ValueError()
        return b
    except (OSError, ValueError):
        raise PrintUnavailable("invalid_template_bundle") from None


def build_manifest(bundle, rows):
    if not rows or sum(int(r["copies"]) for r in rows) > 5000:
        raise PrintUnavailable("invalid_occurrences")
    result = {
        "renderer": RENDERER,
        "approval_ref": bundle["approval_ref"],
        "font": bundle["font"],
        "logo": bundle["logo"],
        "occurrences": [],
    }
    for r in rows:
        matches = [
            t
            for t in bundle["templates"]
            if t["key"] == r["template_key"]
            and t["version"] == r["template_version"]
            and t["tag_type"] == r["tag_type"]
            and t["symbol_mm"] == float(r["size_mm"])
        ]
        if len(matches) != 1 or not re.fullmatch(
            r"[A-Za-z0-9_-]{16,80}", r["public_token"]
        ):
            raise PrintUnavailable("template_binding_unavailable")
        result["occurrences"].append(
            {
                "use_id": str(r["use_id"]),
                "qr_id": str(r["qr_id"]),
                "copies": int(r["copies"]),
                "template": matches[0],
                "url": bundle["origin"] + "/q/" + r["public_token"],
            }
        )
    return result


def checked_logo(data):
    root = etree.fromstring(
        data, etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    )
    # Deliberately small vector subset: no scripts, images, external assets or CSS URLs.
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise PrintUnavailable("unsafe_logo")
    for e in root.iter():
        if etree.QName(e).localname not in {
            "svg",
            "g",
            "path",
            "rect",
            "circle",
            "ellipse",
            "polygon",
            "polyline",
            "line",
        }:
            raise PrintUnavailable("unsafe_logo")
        for k, v in e.attrib.items():
            if "href" in k or k.lower().startswith("on") or "url(" in v.lower():
                raise PrintUnavailable("unsafe_logo")
    return svg2rlg(io.BytesIO(data))


def render_pdf(manifest):
    if manifest.get("renderer") != RENDERER:
        raise PrintUnavailable("unsupported_renderer")
    with LOCK:
        font_data = asset_bytes(manifest["font"])
        logo = checked_logo(asset_bytes(manifest["logo"]))
        font_name = "SR" + manifest["font"]["sha256"][:16]
        if font_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(
                TTFont(font_name, io.BytesIO(font_data), shapable=True)
            )
        font = pdfmetrics.getFont(font_name)
        source = SourceFont(io.BytesIO(font_data))
        buffer = io.BytesIO()
        c = Canvas(
            buffer, pagesize=(210 * mm, 297 * mm), pageCompression=1, invariant=1
        )
        c.setTitle("SafeReturn private print")
        c.setAuthor("SafeReturn")
        c.setCreator(RENDERER)
        x = 10
        y = 287
        row_height = 0
        forms = {}
        counts = {"lost": 0, "ice": 0}
        placements = []
        for occurrence in manifest["occurrences"]:
            t = occurrence["template"]
            width = t["width_mm"]
            height = t["height_mm"]
            url = occurrence["url"]
            code = segno.make(url, error="q", micro=False, boost_error=False)
            matrix = list(code.matrix)
            n = len(matrix)
            pitch = t["symbol_mm"] / (n + 8)
            if pitch < t["min_pitch_mm"] or code.version > 6:
                raise PrintUnavailable("qr_density_unapproved")
            if t["tag_type"] not in counts:
                raise PrintUnavailable("invalid_tag_type")
            form = digest({"url": url, "template": t})
            if form not in forms:
                c.beginForm(form, 0, 0, width * mm, height * mm)
                c.setStrokeColorRGB(0.1, 0.15, 0.17)
                c.setLineWidth(0.3)
                c.rect(0, 0, width * mm, height * mm)
                c.setFillColorRGB(0.03, 0.22, 0.23) if t[
                    "tag_type"
                ] == "lost" else c.setFillColorRGB(0.5, 0.1, 0.12)
                c.rect(
                    2 * mm,
                    (height - 9) * mm,
                    (width - 4) * mm,
                    7 * mm,
                    stroke=0,
                    fill=1,
                )
                c.setFillColorRGB(1, 1, 1)
                c.setFont(font_name, t["font_pt"])
                if (
                    pdfmetrics.stringWidth(t["header"], font_name, t["font_pt"])
                    > (width - 8) * mm
                ):
                    raise PrintUnavailable("header_overflow")
                c.drawCentredString(width * mm / 2, (height - 6.5) * mm, t["header"])
                qx = t["qr_x_mm"]
                qy = t["qr_y_mm"]
                size = t["symbol_mm"]
                c.setFillColorRGB(1, 1, 1)
                c.rect(qx * mm, qy * mm, size * mm, size * mm, stroke=0, fill=1)
                c.setFillColorRGB(0, 0, 0)
                path = c.beginPath()
                for j, row in enumerate(matrix):
                    for i, dark in enumerate(row):
                        if dark:
                            path.rect(
                                (qx + (i + 4) * pitch) * mm,
                                (qy + (n - j + 3) * pitch) * mm,
                                pitch * mm,
                                pitch * mm,
                            )
                c.drawPath(path, stroke=0, fill=1)
                ls = t["logo_mm"]
                cx = (qx + size / 2 - ls / 2) * mm
                cy = (qy + size / 2 - ls / 2) * mm
                c.setFillColorRGB(1, 1, 1)
                c.rect(cx, cy, ls * mm, ls * mm, stroke=0, fill=1)
                c.saveState()
                c.translate(cx, cy)
                c.scale(ls * mm / logo.width, ls * mm / logo.height)
                renderPDF.draw(logo, c, 0, 0)
                c.restoreState()
                yy = qy - 4
                c.setFillColorRGB(0.05, 0.08, 0.1)
                for text, rtl in [(s, False) for s in t["english_lines"]] + [
                    (s, True) for s in t["urdu_lines"]
                ]:
                    if yy < 4 or any(
                        ord(ch) not in font.face.charToGlyph
                        for ch in text
                        if not ch.isspace()
                    ):
                        raise PrintUnavailable("caption_unrenderable")
                    if rtl:
                        urdu_run(
                            c,
                            text,
                            font_data,
                            source,
                            width * mm / 2,
                            yy * mm,
                            t["font_pt"],
                            (width - 8) * mm,
                        )
                    else:
                        if (
                            pdfmetrics.stringWidth(text, font_name, t["font_pt"])
                            > (width - 8) * mm
                        ):
                            raise PrintUnavailable("caption_overflow")
                        c.drawCentredString(width * mm / 2, yy * mm, text)
                    yy -= t["font_pt"] * 1.5 / mm
                c.endForm()
                forms[form] = True
            for _ in range(occurrence["copies"]):
                if x + width > 200:
                    x = 10
                    y -= row_height + 5
                    row_height = 0
                if y - height < 10:
                    c.showPage()
                    x = 10
                    y = 287
                    row_height = 0
                c.saveState()
                c.translate(x * mm, (y - height) * mm)
                c.doForm(form)
                c.restoreState()
                placements.append(
                    {
                        "tag_type": t["tag_type"],
                        "qr_id": occurrence["qr_id"],
                        "symbol_mm": t["symbol_mm"],
                    }
                )
                counts[t["tag_type"]] += 1
                x += width + 5
                row_height = max(row_height, height)
        if manifest["approval_ref"].startswith("SYNTHETIC"):
            c.setFont("Helvetica", 8)
            c.setFillColorRGB(0.6, 0.1, 0.1)
            c.drawString(
                10 * mm,
                5 * mm,
                "SYNTHETIC TEST - NOT APPROVED FOR PRODUCTION. Print actual size; physical QA required.",
            )
        c.save()
        data = buffer.getvalue()
        if len(data) > 20_000_000:
            raise PrintUnavailable("artifact_too_large")
        return data, {
            "counts": counts,
            "placements": placements,
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
        }
