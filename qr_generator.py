"""Core utilities for generating QR-code PNG and SVG images."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from html import escape
from io import BytesIO
import re
from urllib.parse import urlparse

import qrcode
from PIL import Image, ImageColor, ImageDraw
from qrcode.exceptions import DataOverflowError


ERROR_CORRECTION_LEVELS = {
    "L": qrcode.constants.ERROR_CORRECT_L,
    "M": qrcode.constants.ERROR_CORRECT_M,
    "Q": qrcode.constants.ERROR_CORRECT_Q,
    "H": qrcode.constants.ERROR_CORRECT_H,
}


@dataclass(frozen=True)
class QRCodeResult:
    """Generated QR code exports and useful display properties."""

    png_bytes: bytes
    svg_bytes: bytes
    version: int
    module_count: int
    pixel_size: int
    logo_area_pixels: int


def validate_http_url(value: str) -> str:
    """Return a normalized HTTP(S) URL or raise ``ValueError``."""
    normalized = value.strip()
    if not normalized:
        raise ValueError("Please enter a URL.")
    if any(character.isspace() for character in normalized):
        raise ValueError("The URL cannot contain spaces. Encode spaces as %20.")

    parsed = urlparse(normalized)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("The URL must begin with http:// or https://.")
    if not parsed.netloc or parsed.hostname is None:
        raise ValueError("The URL must include a valid host name.")

    return normalized


def parse_hex_color(value: str) -> tuple[int, int, int, int]:
    """Convert a Pillow-compatible color to an opaque RGBA tuple."""
    try:
        red, green, blue = ImageColor.getrgb(value)
    except ValueError as exc:
        raise ValueError(
            "Choose a valid color, such as #111827, navy, or royalblue."
        ) from exc
    return red, green, blue, 255


def contrast_ratio_against_white(color: str) -> float:
    """Calculate WCAG-style contrast against white for scanability guidance."""
    red, green, blue, _ = parse_hex_color(color)

    def linearize(channel: int) -> float:
        value = channel / 255
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

    luminance = (
        0.2126 * linearize(red)
        + 0.7152 * linearize(green)
        + 0.0722 * linearize(blue)
    )
    return 1.05 / (luminance + 0.05)


def _build_qr_matrix(url: str, border: int, error_correction: str) -> tuple[list[list[bool]], int]:
    normalized_url = validate_http_url(url)
    if border < 4:
        raise ValueError("The quiet-zone border must be at least 4 modules.")
    if error_correction not in ERROR_CORRECTION_LEVELS:
        raise ValueError("Error correction must be one of L, M, Q, or H.")

    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECTION_LEVELS[error_correction],
        box_size=1,
        border=border,
    )
    qr.add_data(normalized_url)
    try:
        qr.make(fit=True)
    except DataOverflowError as exc:
        raise ValueError("The URL is too long to fit in a QR code.") from exc
    return qr.get_matrix(), int(qr.version)


def _logo_area_size(pixel_size: int, logo_area_percent: int) -> int:
    if not 0 <= logo_area_percent <= 30:
        raise ValueError("Logo area must be between 0% and 30% of the QR width.")
    if logo_area_percent == 0:
        return 0
    size = round(pixel_size * logo_area_percent / 100)
    return max(1, size)


def _prepare_logo(logo_bytes: bytes, max_size: int) -> Image.Image:
    try:
        logo = Image.open(BytesIO(logo_bytes)).convert("RGBA")
    except Exception as exc:
        raise ValueError("The logo must be a valid PNG, JPEG, or WebP image.") from exc

    if max_size < 1:
        raise ValueError("Enable a logo area before adding a logo image.")

    logo.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    return logo


def _svg_color(color: str) -> str:
    red, green, blue, _ = parse_hex_color(color)
    return f"#{red:02x}{green:02x}{blue:02x}"


def generate_qr(
    url: str,
    color: str = "#111827",
    box_size: int = 12,
    border: int = 4,
    error_correction: str = "M",
    logo_area_percent: int = 0,
    logo_bytes: bytes | None = None,
) -> QRCodeResult:
    """Generate PNG and SVG QR exports with an optional centered white logo area."""
    if box_size < 1:
        raise ValueError("Box size must be at least 1 pixel.")

    rgba_color = parse_hex_color(color)
    matrix, version = _build_qr_matrix(url, border, error_correction)
    module_count = len(matrix)
    pixel_size = module_count * box_size
    logo_area_pixels = _logo_area_size(pixel_size, logo_area_percent)

    logo: Image.Image | None = None
    if logo_bytes:
        logo_padding = max(2, round(logo_area_pixels * 0.12))
        logo = _prepare_logo(logo_bytes, logo_area_pixels - 2 * logo_padding)

    # PNG export: transparent background, except the optional centered white area.
    image = Image.new("RGBA", (pixel_size, pixel_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    for row_index, row in enumerate(matrix):
        for column_index, is_dark in enumerate(row):
            if is_dark:
                left = column_index * box_size
                top = row_index * box_size
                draw.rectangle(
                    (left, top, left + box_size - 1, top + box_size - 1),
                    fill=rgba_color,
                )

    if logo_area_pixels:
        area_left = (pixel_size - logo_area_pixels) // 2
        area_top = (pixel_size - logo_area_pixels) // 2
        draw.rectangle(
            (area_left, area_top, area_left + logo_area_pixels - 1, area_top + logo_area_pixels - 1),
            fill=(255, 255, 255, 255),
        )
        if logo is not None:
            logo_left = (pixel_size - logo.width) // 2
            logo_top = (pixel_size - logo.height) // 2
            image.alpha_composite(logo, (logo_left, logo_top))

    png_buffer = BytesIO()
    image.save(png_buffer, format="PNG", optimize=True)

    # SVG export uses compact horizontal runs of dark modules.
    svg_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{pixel_size}" height="{pixel_size}" '
        f'viewBox="0 0 {pixel_size} {pixel_size}" shape-rendering="crispEdges">',
        f'<g fill="{escape(_svg_color(color))}">',
    ]
    for row_index, row in enumerate(matrix):
        start: int | None = None
        for column_index, is_dark in enumerate(row + [False]):
            if is_dark and start is None:
                start = column_index
            elif not is_dark and start is not None:
                x = start * box_size
                y = row_index * box_size
                width = (column_index - start) * box_size
                svg_parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="{box_size}"/>')
                start = None
    svg_parts.append("</g>")

    if logo_area_pixels:
        area_left = (pixel_size - logo_area_pixels) // 2
        area_top = (pixel_size - logo_area_pixels) // 2
        svg_parts.append(
            f'<rect x="{area_left}" y="{area_top}" width="{logo_area_pixels}" '
            f'height="{logo_area_pixels}" fill="#ffffff"/>'
        )
        if logo is not None:
            logo_buffer = BytesIO()
            logo.save(logo_buffer, format="PNG")
            encoded_logo = base64.b64encode(logo_buffer.getvalue()).decode("ascii")
            logo_left = (pixel_size - logo.width) // 2
            logo_top = (pixel_size - logo.height) // 2
            svg_parts.append(
                f'<image x="{logo_left}" y="{logo_top}" width="{logo.width}" height="{logo.height}" '
                f'href="data:image/png;base64,{encoded_logo}"/>'
            )

    svg_parts.append("</svg>")
    svg_bytes = "".join(svg_parts).encode("utf-8")

    return QRCodeResult(
        png_bytes=png_buffer.getvalue(),
        svg_bytes=svg_bytes,
        version=version,
        module_count=module_count,
        pixel_size=pixel_size,
        logo_area_pixels=logo_area_pixels,
    )


def generate_qr_png(
    url: str,
    color: str = "#111827",
    box_size: int = 12,
    border: int = 4,
    error_correction: str = "M",
) -> QRCodeResult:
    """Backward-compatible helper for callers that only need the original defaults."""
    return generate_qr(url, color, box_size, border, error_correction)


def suggested_filename(url: str, extension: str = "png") -> str:
    """Create a safe export file name based on the URL host."""
    normalized_url = validate_http_url(url)
    hostname = urlparse(normalized_url).hostname or "qr-code"
    stem = re.sub(r"[^A-Za-z0-9.-]+", "-", hostname).strip(".-").lower()
    extension = extension.lower().lstrip(".")
    if extension not in {"png", "svg"}:
        raise ValueError("File extension must be PNG or SVG.")
    return f"{stem or 'qr-code'}-qr.{extension}"
